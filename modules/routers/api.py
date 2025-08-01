"""FastAPI 라우터 모듈"""
import json
import logging
import os
import mimetypes
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import Config
from ..auth import is_authenticated, get_storage_client
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

# _build_vertex_payload 함수는 더 이상 사용하지 않음 - Discovery Engine으로 대체됨

@router.post('/api/generate')
async def generate_content(userPrompt: str = Form(""), conversationHistory: str = Form("[]")):
    """메인 답변 생성 엔드포인트 - Discovery Engine 사용"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        conversation_history = json.loads(conversationHistory)
        
        # Discovery Engine을 통한 답변 생성
        discovery_result = await get_complete_discovery_answer(userPrompt)
        
        # 답변 텍스트 추출
        answer_text = discovery_result.get("answer_text", "")
        
        # 디버그 로깅
        logger.info(f"Discovery 결과 - answer_text: {len(answer_text)}자")
        if not answer_text:
            logger.warning("빈 answer_text 감지!")
            logger.debug(f"Discovery result keys: {list(discovery_result.keys())}")
        
        # 최종 답변 생성
        if answer_text and answer_text.strip():
            final_answer = answer_text
        else:
            # 기본 답변 - Discovery Engine에서 아무것도 찾지 못한 경우
            final_answer = "죄송하지만 관련 정보를 찾을 수 없습니다. 처음서비스와 관련된 구체적인 질문을 해주시면 더 정확한 답변을 제공할 수 있습니다."
            logger.warning(f"기본 답변 사용 - 원래 answer_text: '{answer_text}'")
        
        # 대화 히스토리 업데이트
        updated_history = conversation_history + [{
            "role": "user", 
            "parts": [{"text": userPrompt}]
        }, {
            "role": "model",
            "parts": [{"text": final_answer}]
        }]
        
        logger.info(json.dumps({
            "stage": "discovery_main_answer_generated",
            "user_prompt": userPrompt,
            "answer_length": len(final_answer),
            "citations_count": len(discovery_result.get("citations", [])),
            "search_results_count": len(discovery_result.get("search_results", []))
        }, ensure_ascii=False))

        return JSONResponse({
            "answer": final_answer,
            "summary_answer": final_answer,  # 기존 프론트엔드 호환성을 위해 추가
            "citations": discovery_result.get("citations", []),
            "search_results": discovery_result.get("search_results", []),
            "related_questions": discovery_result.get("related_questions", []),
            "updatedHistory": updated_history,
            "metadata": {
                "engine_type": "discovery_engine_main",
                "query_id": discovery_result.get("query_id"),
                "session_id": discovery_result.get("session_id")
            },
            "quality_check": {
                "has_answer": bool(final_answer and final_answer.strip()),
                "discovery_success": True
            }
        })

    except Exception as e:
        logger.exception(f"예상치 못한 오류 - 사용자 입력: {userPrompt}")
        # 에러 시에도 기본 답변 제공
        return JSONResponse({
            "answer": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "summary_answer": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "citations": [],
            "search_results": [],
            "related_questions": [],
            "updatedHistory": json.loads(conversationHistory),
            "metadata": {
                "engine_type": "error_fallback",
                "error": str(e)
            },
            "quality_check": {
                "has_answer": True,
                "discovery_success": False,
                "error": True
            }
        }, status_code=200)  # 200으로 반환하여 프론트엔드에서 오류 메시지 표시

@router.get("/gcs/{bucket_name}/{file_path:path}")
async def proxy_gcs_file(bucket_name: str, file_path: str):
    """GCS 파일 프록시 엔드포인트 - URL 디코딩 지원"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="스토리지 인증 실패")
    
    storage_client = get_storage_client()

    try:
        # URL 디코딩 처리 (한글 파일명 지원)
        import urllib.parse
        decoded_file_path = urllib.parse.unquote(file_path, encoding='utf-8')
        
        logger.info(f"GCS 파일 요청 - 원본: {file_path}, 디코딩: {decoded_file_path}")
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(decoded_file_path)
        
        if not blob.exists():
            # 원본 경로로도 시도
            blob = bucket.blob(file_path)
            if not blob.exists():
                logger.warning(f"파일 없음 - {bucket_name}/{decoded_file_path}")
                raise HTTPException(status_code=404, detail="파일 없음")

        def iterfile():
            with blob.open("rb") as f:
                yield from f

        content_type, _ = mimetypes.guess_type(decoded_file_path)
        content_type = content_type or "application/octet-stream"
        
        # 한글 파일명을 위한 Content-Disposition 헤더 설정
        filename = os.path.basename(decoded_file_path)
        encoded_filename = urllib.parse.quote(filename, encoding='utf-8')
        headers = {
            'Content-Disposition': f'inline; filename*=UTF-8\'\'{encoded_filename}'
        }
        
        return StreamingResponse(iterfile(), media_type=content_type, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GCS 프록시 오류 - {bucket_name}/{file_path}", exc_info=True)
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
                "engine_type": "discovery_engine_answer",
                "final_query_used": discovery_result.get("final_query_used", userPrompt)
            }
        })

    except Exception as e:
        logger.exception("Discovery Engine Answer API 오류")
        raise HTTPException(status_code=500, detail=f"Discovery Engine 답변 생성 실패: {str(e)}")

