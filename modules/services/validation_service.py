"""응답 검증 서비스"""
import logging
from .vertex_api import call_discovery_engine

logger = logging.getLogger(__name__)

def validate_response_relevance(user_prompt: str, response: str) -> bool:
    """응답이 질문과 연관성이 있는지 검증"""
    # 간단한 키워드 기반 검증으로 변경
    response_lower = response.lower()
    
    # 회피 답변 키워드 체크
    avoid_keywords = [
        "죄송하지만", "답변드릴 수 없습니다", "제공해드리기 어렵습니다",
        "정보가 없습니다", "확인할 수 없습니다", "알 수 없습니다"
    ]
    
    # 회피 답변인지 체크
    has_avoid_keywords = any(keyword in response_lower for keyword in avoid_keywords)
    if has_avoid_keywords:
        return False
    
    # 처음서비스 관련 키워드 체크
    relevant_keywords = [
        "처음서비스", "마이메일러", "처음소프트", "이메일", "발송", 
        "설문", "서비스", "솔루션", "고객", "기업", "대행"
    ]
    
    # 관련 키워드가 있는지 체크
    has_relevant_content = any(keyword in response_lower for keyword in relevant_keywords)
    
    # 적절한 길이인지 체크 (너무 짧으면 부적절)
    has_adequate_length = len(response.strip()) > 50
    
    result = has_relevant_content and has_adequate_length and not has_avoid_keywords
    
    if not result:
        logger.warning(f"검증 실패 - 회피답변: {has_avoid_keywords}, 관련내용: {has_relevant_content}, 적절길이: {has_adequate_length}")
    
    return result