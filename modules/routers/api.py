"""FastAPI 라우터 모듈"""
import json
import base64
import asyncio
import logging
import os
import mimetypes
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

from ..config import Config
from ..auth import is_authenticated, get_storage_client
from ..database import query_spanner_triples, query_spanner_by_triple
from ..services.vertex_api import call_vertex_api, build_triple_only_payload, build_summary_payload
from ..services.triple_service import extract_triple_from_prompt
from ..services.validation_service import validate_response_relevance
from ..services.discovery_engine_api import get_complete_discovery_answer

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/health')
async def health_check():
    """기본 헬스 체크 엔드포인트 - 빠른 응답"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "graphrag-api",
        "version": "2.0.0"
    }

@router.get('/api/health/detailed')
async def detailed_health_check():
    """상세 헬스 체크 엔드포인트 - 인증 포함"""
    from main import get_auth_status
    try:
        # 백그라운드 인증 상태 확인 (빠른 응답)
        auth_status = get_auth_status()
        
        # 실제 인증 함수도 확인 (선택적)
        try:
            from ..auth import is_authenticated
            detailed_auth_status = is_authenticated()
        except:
            detailed_auth_status = auth_status
        
        return {
            "status": "healthy" if auth_status else "degraded",
            "authenticated": auth_status,
            "detailed_auth": detailed_auth_status,
            "timestamp": datetime.now().isoformat(),
            "service": "graphrag-api",
            "version": "2.0.0",
            "components": {
                "auth": "ok" if auth_status else "warning",
                "api": "ok",
                "detailed_auth": "ok" if detailed_auth_status else "warning"
            }
        }
    except Exception as e:
        logger.warning(f"인증 상태 확인 실패: {e}")
        return {
            "status": "degraded",
            "authenticated": False,
            "timestamp": datetime.now().isoformat(),
            "service": "graphrag-api",
            "version": "2.0.0",
            "components": {
                "auth": "error",
                "api": "ok"
            },
            "error": str(e)
        }

async def _build_vertex_payload(
    user_prompt: str,
    conversation_history: list,
    image_file: Optional[UploadFile],
    preloaded_triples: Optional[list] = None
) -> tuple:
    """Vertex AI 검색을 위한 페이로드 구성"""
    user_content_parts = []
    if image_file:
        image_base64 = base64.b64encode(await image_file.read()).decode('utf-8')
        user_content_parts.append({"inlineData": {"mimeType": image_file.content_type, "data": image_base64}})

    if user_prompt:
        user_content_parts.append({"text": user_prompt})

    current_contents = conversation_history + [{"role": "user", "parts": user_content_parts}]

    # Triple grounding: 미리 받아온 게 있으면 쓰고, 없으면 추출
    if preloaded_triples is not None:
        triples = preloaded_triples
    else:
        try:
            subject, predicate, object_ = await extract_triple_from_prompt(user_prompt)
            triples = query_spanner_by_triple(subject, predicate, object_)
        except Exception as e:
            logger.warning(f"Triple 추출 또는 검색 실패: {e}")
            triples = []

    # grounding 내용 system prompt 앞에 삽입
    if triples:
        triple_text = "\n".join(triples)
        current_contents.insert(0, {
            "role": "user",
            "parts": [{"text": f"[Spanner Triple Grounding]\n{triple_text}"}]
        })

    payload = {
        "systemInstruction": {"parts": [{"text": Config.load_system_instruction()}]},
        "contents": current_contents,
        "tools": [{"retrieval": {"vertexAiSearch": {"datastore": Config.get_datastore_path()}}}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 8192,
            "topP": 0.3
        }
    }

    return payload, current_contents

@router.post('/api/generate')
async def generate_content(userPrompt: str = Form(""), conversationHistory: str = Form("[]"), imageFile: Optional[UploadFile] = File(None)):
    """메인 답변 생성 엔드포인트"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        conversation_history = json.loads(conversationHistory)

        # 🔹 Step 1: Triple 검색 및 기반 응답
        triples = query_spanner_triples(userPrompt)
        
        # Triple이 없으면 추출하여 다시 검색 시도
        if not triples:
            try:
                subject, predicate, object_ = await extract_triple_from_prompt(userPrompt)
                triples = query_spanner_by_triple(subject, predicate, object_)
                logger.info(f"Fallback triple 검색 결과: {len(triples)}건")
            except Exception as e:
                logger.warning(f"Fallback triple 검색 실패: {e}")

        # 🚀 Step 1&2: Triple 기반 응답과 Vertex AI 검색을 병렬 처리
        triple_payload = await build_triple_only_payload(userPrompt, triples)
        full_payload, full_history = await _build_vertex_payload(userPrompt, conversation_history, imageFile, preloaded_triples=triples)
        
        # 병렬 API 호출로 속도 2배 향상
        triple_task = asyncio.create_task(call_vertex_api(triple_payload))
        vertex_task = asyncio.create_task(call_vertex_api(full_payload))
        
        triple_result, vertex_result = await asyncio.gather(triple_task, vertex_task)
        
        triple_text = triple_result['candidates'][0]['content']['parts'][0]['text']
        vertex_text = vertex_result['candidates'][0]['content']['parts'][0]['text']
        
        logger.info(json.dumps({
            "stage": "parallel_answers_generated",
            "triple_input": userPrompt,
            "triples_used": triples,
            "triple_answer_length": len(triple_text),
            "vertex_answer_length": len(vertex_text)
        }, ensure_ascii=False))

        # 🔹 Step 3&4: 요약과 검증을 병렬 처리
        summary_payload = await build_summary_payload(triple_text, vertex_text, userPrompt)
        
        summary_task = asyncio.create_task(call_vertex_api(summary_payload))
        validation_task = asyncio.create_task(validate_response_relevance(userPrompt, f"{triple_text[:300]}..."))
        
        summary_result, is_relevant_preview = await asyncio.gather(summary_task, validation_task)
        summary_text = summary_result['candidates'][0]['content']['parts'][0]['text']
        
        # 최종 검증 (요약 결과 기준)
        is_relevant = await validate_response_relevance(userPrompt, summary_text) if not is_relevant_preview else True
        
        if not is_relevant:
            logger.warning(f"응답 연관성 검증 실패 - 질문: {userPrompt}")
            # 처음서비스와 무관한 질문에 대한 표준 응답
            summary_text = f"""죄송하지만, **"{userPrompt}"**에 대한 정보는 현재 제공해드리기 어렵습니다.

**처음서비스**의 제품 및 서비스에 관한 구체적인 질문을 해주시면, 더 정확하고 유용한 답변을 드릴 수 있습니다.

예를 들어:
- 특정 기능의 사용 방법
- 설정 및 구성 관련 문의  
- 문제 해결 방법
- 서비스 이용 가이드

추가 도움이 필요하시면 언제든 문의해 주세요! 😊"""

        logger.info(json.dumps({
            "stage": "summary_answer_generated",
            "user_prompt": userPrompt,
            "is_relevant": is_relevant,
            "summary_answer": summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
        }, ensure_ascii=False))

        return JSONResponse({
            "triple_answer": triple_text,
            "vertex_answer": vertex_text,
            "summary_answer": summary_text,
            "updatedHistory": full_history,
            "quality_check": {
                "relevance_passed": is_relevant,
                "triples_found": len(triples) > 0
            }
        })

    except Exception as e:
        logger.exception("예상치 못한 오류")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gcs/{bucket_name}/{file_path:path}")
async def proxy_gcs_file(bucket_name: str, file_path: str):
    """GCS 파일 프록시 엔드포인트"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="스토리지 인증 실패")
    
    storage_client = get_storage_client()

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="파일 없음")

        def iterfile():
            with blob.open("rb") as f:
                yield from f

        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"
        headers = {'Content-Disposition': f'inline; filename="{os.path.basename(file_path)}"'}
        return StreamingResponse(iterfile(), media_type=content_type, headers=headers)
    except Exception as e:
        logger.error("GCS 프록시 오류", exc_info=True)
        raise HTTPException(status_code=500, detail="파일 읽기 실패")

@router.post('/api/discovery-answer')
async def discovery_answer(userPrompt: str = Form("")):
    """Discovery Engine Answer API 테스트 엔드포인트"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        # Discovery Engine을 통한 답변 생성
        discovery_result = await get_complete_discovery_answer(userPrompt)
        
        logger.info(json.dumps({
            "stage": "discovery_answer_generated",
            "user_prompt": userPrompt,
            "answer_length": len(discovery_result.get("answer_text", "")),
            "citations_count": len(discovery_result.get("citations", [])),
            "search_results_count": len(discovery_result.get("search_results", []))
        }, ensure_ascii=False))

        return JSONResponse({
            "answer": discovery_result.get("answer_text", ""),
            "citations": discovery_result.get("citations", []),
            "search_results": discovery_result.get("search_results", []),
            "related_questions": discovery_result.get("related_questions", []),
            "metadata": {
                "query_id": discovery_result.get("query_id"),
                "session_id": discovery_result.get("session_id"),
                "engine_type": "discovery_engine_answer"
            }
        })

    except Exception as e:
        logger.exception("Discovery Engine Answer API 오류")
        raise HTTPException(status_code=500, detail=f"Discovery Engine 답변 생성 실패: {str(e)}")

@router.post('/api/compare-answers')
async def compare_answers(userPrompt: str = Form("")):
    """기존 방식과 Discovery Engine Answer API 비교 테스트"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        # 병렬로 두 방식 모두 실행
        original_task = asyncio.create_task(_get_original_answer(userPrompt))
        discovery_task = asyncio.create_task(get_complete_discovery_answer(userPrompt))
        
        original_result, discovery_result = await asyncio.gather(
            original_task, discovery_task, return_exceptions=True
        )
        
        # 결과 정리
        response = {
            "user_prompt": userPrompt,
            "timestamp": datetime.now().isoformat(),
            "original_method": {},
            "discovery_method": {}
        }
        
        # 기존 방식 결과 처리
        if isinstance(original_result, Exception):
            response["original_method"] = {
                "status": "error",
                "error": str(original_result)
            }
        else:
            response["original_method"] = {
                "status": "success",
                "triple_answer": original_result.get("triple_answer", ""),
                "vertex_answer": original_result.get("vertex_answer", ""),
                "summary_answer": original_result.get("summary_answer", ""),
                "quality_check": original_result.get("quality_check", {})
            }
        
        # Discovery Engine 결과 처리
        if isinstance(discovery_result, Exception):
            response["discovery_method"] = {
                "status": "error", 
                "error": str(discovery_result)
            }
        else:
            response["discovery_method"] = {
                "status": "success",
                "answer": discovery_result.get("answer_text", ""),
                "citations_count": len(discovery_result.get("citations", [])),
                "search_results_count": len(discovery_result.get("search_results", [])),
                "related_questions": discovery_result.get("related_questions", [])
            }
        
        return JSONResponse(response)

    except Exception as e:
        logger.exception("답변 비교 테스트 오류")
        raise HTTPException(status_code=500, detail=f"답변 비교 실패: {str(e)}")

async def _get_original_answer(user_prompt: str) -> Dict[str, Any]:
    """기존 방식의 답변 생성 (내부 헬퍼 함수)"""
    # 기존 /api/generate 로직을 재사용
    triples = query_spanner_triples(user_prompt)
    
    if not triples:
        try:
            subject, predicate, object_ = await extract_triple_from_prompt(user_prompt)
            triples = query_spanner_by_triple(subject, predicate, object_)
        except Exception as e:
            logger.warning(f"Fallback triple 검색 실패: {e}")

    # 병렬 처리
    triple_payload = await build_triple_only_payload(user_prompt, triples)
    full_payload, _ = await _build_vertex_payload(user_prompt, [], None, preloaded_triples=triples)
    
    triple_task = asyncio.create_task(call_vertex_api(triple_payload))
    vertex_task = asyncio.create_task(call_vertex_api(full_payload))
    
    triple_result, vertex_result = await asyncio.gather(triple_task, vertex_task)
    
    triple_text = triple_result['candidates'][0]['content']['parts'][0]['text']
    vertex_text = vertex_result['candidates'][0]['content']['parts'][0]['text']
    
    # 요약 생성
    summary_payload = await build_summary_payload(triple_text, vertex_text, user_prompt)
    summary_result = await call_vertex_api(summary_payload)
    summary_text = summary_result['candidates'][0]['content']['parts'][0]['text']
    
    # 검증
    is_relevant = await validate_response_relevance(user_prompt, summary_text)
    
    return {
        "triple_answer": triple_text,
        "vertex_answer": vertex_text, 
        "summary_answer": summary_text,
        "quality_check": {
            "relevance_passed": is_relevant,
            "triples_found": len(triples) > 0
        }
    }