"""응답 검증 서비스"""
import logging
from .vertex_api import call_vertex_api

logger = logging.getLogger(__name__)

async def validate_response_relevance(user_prompt: str, response: str) -> bool:
    """응답이 질문과 연관성이 있는지 검증"""
    validation_prompt = f"""
사용자 질문: "{user_prompt}"
AI 응답: "{response[:500]}..."

위 응답이 질문에 적절히 답하고 있는지 판단해줘.

판단 기준:
1. 질문의 핵심 의도에 부합하는가?
2. 구체적이고 유용한 정보를 제공하는가?
3. "죄송합니다", "답변드릴 수 없습니다" 같은 회피 답변이 아닌가?

응답: YES 또는 NO
"""
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": validation_prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
    }
    
    try:
        api_response = await call_vertex_api(payload)
        result = api_response["candidates"][0]["content"]["parts"][0]["text"].strip()
        return result.upper() == "YES"
    except Exception as e:
        logger.warning(f"응답 검증 실패, 기본값 사용: {e}")
        return True  # 검증 실패 시 기본적으로 통과