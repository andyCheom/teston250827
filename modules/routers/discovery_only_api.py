"""Discovery Engine 전용 답변 생성 API"""
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse

from ..config import Config
from ..auth import is_authenticated
from ..services.discovery_engine_api import get_complete_discovery_answer

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post('/api/discovery-only')
async def discovery_only_answer(
    userPrompt: str = Form(""), 
    imageFile: Optional[UploadFile] = File(None)
):
    """Discovery Engine만을 사용한 답변 생성 엔드포인트 - prompt.txt 형식 적용"""
    if not is_authenticated():
        raise HTTPException(status_code=503, detail="서버 인증 실패 - Google Cloud 인증을 확인하세요")

    try:
        # Discovery Engine을 통한 답변 생성 (이미지 분석 포함)
        discovery_result = await get_complete_discovery_answer(userPrompt, imageFile)
        
        # prompt.txt 형식에 맞춰 최종 답변 구성
        answer_text = discovery_result.get("answer_text", "")
        image_analysis = discovery_result.get("image_analysis", "")
        
        # 이미지 분석 결과가 있으면 답변에 반영
        if image_analysis and answer_text:
            # 이미지 분석 내용을 바탕으로 더 상세한 답변 제공
            final_answer = f"""**스크린샷 분석 결과:**
{image_analysis}

**관련 정보 및 해결 방안:**
{answer_text}"""
        elif image_analysis and not answer_text:
            # 이미지 분석만 있는 경우
            final_answer = f"""**스크린샷 분석 결과:**
{image_analysis}

**추가 도움:**
스크린샷을 분석한 결과입니다. 더 구체적인 문제 해결을 위해서는 처음서비스 관련 구체적인 질문을 함께 해주시면 더 정확한 답변을 제공할 수 있습니다."""
        else:
            # 텍스트 답변만 있는 경우
            final_answer = answer_text or "죄송하지만 관련 정보를 찾을 수 없습니다. 처음서비스와 관련된 구체적인 질문을 해주시면 더 정확한 답변을 제공할 수 있습니다."

        logger.info(json.dumps({
            "stage": "discovery_only_answer_generated",
            "user_prompt": userPrompt,
            "has_image": imageFile is not None,
            "answer_length": len(final_answer),
            "citations_count": len(discovery_result.get("citations", [])),
            "search_results_count": len(discovery_result.get("search_results", []))
        }, ensure_ascii=False))

        return JSONResponse({
            "answer": final_answer,
            "citations": discovery_result.get("citations", []),
            "search_results": discovery_result.get("search_results", []),
            "related_questions": discovery_result.get("related_questions", []),
            "image_analysis": image_analysis,
            "metadata": {
                "query_id": discovery_result.get("query_id"),
                "session_id": discovery_result.get("session_id"),
                "engine_type": "discovery_engine_only",
                "has_image": imageFile is not None,
                "final_query_used": discovery_result.get("final_query_used", userPrompt),
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        logger.exception("Discovery Engine 전용 답변 생성 오류")
        raise HTTPException(status_code=500, detail=f"Discovery Engine 답변 생성 실패: {str(e)}")