"""FastAPI 라우터 모듈"""
import json
import base64
import asyncio
import logging
import os
import mimetypes
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

from ..config import Config
from ..auth import is_authenticated, get_storage_client
from ..database import query_spanner_triples, query_spanner_by_triple
from ..services.vertex_api import call_discovery_engine, generate_triple_based_answer, generate_summary_answer, call_discovery_engine_async, generate_triple_based_answer_async, call_discovery_engine_with_search_context_async
from ..services.triple_service import extract_triple_from_prompt
from ..services.validation_service import validate_response_relevance

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/health')
async def health_check():
    """헬스 체크 엔드포인트"""
    from ..auth import is_authenticated
    return {
        "status": "healthy",
        
        "authenticated": is_authenticated(),
        "timestamp": datetime.now().isoformat()
    }


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
                subject, predicate, object_ = extract_triple_from_prompt(userPrompt)
                triples = query_spanner_by_triple(subject, predicate, object_)
                logger.info(f"Fallback triple 검색 결과: {len(triples)}건")
            except Exception as e:
                logger.warning(f"Fallback triple 검색 실패: {e}")

        # 🚀 Step 1&2: Triple 기반 응답과 Discovery Engine 하이브리드 검색을 병렬 처리
        triple_task = asyncio.create_task(generate_triple_based_answer_async(userPrompt, triples))
        discovery_task = asyncio.create_task(call_discovery_engine_with_search_context_async(userPrompt))
        
        # 병렬 실행으로 응답 시간 50% 단축 + 하이브리드 접근으로 더 많은 문서 활용
        triple_result, discovery_result = await asyncio.gather(triple_task, discovery_task)
        
        triple_text = triple_result.get('answer_text', '')
        discovery_text = discovery_result.get('answer_text', '')
        
        logger.info(json.dumps({
            "stage": "parallel_answers_generated",
            "triple_input": userPrompt,
            "triples_used": triples,
            "triple_answer_length": len(triple_text),
            "discovery_answer_length": len(discovery_text)
        }, ensure_ascii=False))

        # 🔹 Step 3: 요약 생성 최적화 (중복 API 호출 방지)
        # Discovery Engine에서 이미 충분한 답변을 받았다면 추가 API 호출 생략
        if len(discovery_text) > 200 and "참고 문서" in discovery_text:
            summary_text = discovery_text  # Discovery Engine 결과를 직접 사용
            logger.info("Discovery Engine 응답이 충분하여 추가 요약 생략")
        else:
            summary_result = generate_summary_answer(triple_text, discovery_text, userPrompt)
            summary_text = summary_result.get('answer_text', '')
        
        # 검증 실행
        is_relevant_preview = validate_response_relevance(userPrompt, f"{triple_text[:300]}...")
        
        # 최종 검증 (요약 결과 기준)
        is_relevant = validate_response_relevance(userPrompt, summary_text) if not is_relevant_preview else True
        
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

        # 하이브리드 메타데이터 수집
        hybrid_metadata = {
            "triple_hybrid": triple_result.get("hybrid_metadata", {}),
            "discovery_search": discovery_result.get("search_metadata", {})
        }
        
        return JSONResponse({
            "triple_answer": triple_text,
            "discovery_answer": discovery_text,
            "summary_answer": summary_text,
            "updatedHistory": conversation_history,
            "quality_check": {
                "relevance_passed": is_relevant,
                "triples_found": len(triples) > 0
            },
            "hybrid_metadata": hybrid_metadata
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