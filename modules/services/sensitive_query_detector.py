"""민감한 질문 감지 서비스"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SensitiveQueryDetector:
    """민감한 질문을 감지하는 클래스"""
    
    def __init__(self):
        # 구체적 가격 문의 키워드 (상담사 연결 필요)
        self.specific_price_keywords = [
            "얼마", "정확히", "exactly", "구체적으로", "specifically",
            "돈", "금액", "원", "달러", "만원", "천원", "가격이",
            "비용이", "요금이", "결제", "payment", "pay", "billing"
        ]
        
        # 일반 요금제/플랜 정보 키워드 (RAG로 처리 가능)
        self.general_plan_keywords = [
            "요금제", "플랜", "plan", "종류", "타입", "type", "옵션", "option",
            "서비스", "service", "기능", "feature", "제공", "포함",
            "차이", "difference", "비교", "compare", "추천", "recommend"
        ]
        
        # 할인, 프로모션 관련 키워드
        self.discount_keywords = [
            "할인", "discount", "sale", "세일", "특가", "프로모션",
            "promotion", "coupon", "쿠폰", "이벤트", "event",
            "혜택", "benefit", "offer", "deal", "딜",
            "캠페인", "campaign", "기간한정", "limited"
        ]
        
        # 상담원 연결 요청 키워드
        self.consultant_keywords = [
            "상담원", "상담사", "직접", "통화", "전화", "연결",
            "consultant", "agent", "support", "help", "서포트",
            "문의", "inquiry", "contact", "담당자", "직원",
            "사람", "person", "human", "실제", "real"
        ]
        
        # 계약, 계약서 관련 키워드
        self.contract_keywords = [
            "계약", "contract", "agreement", "계약서", "약관",
            "terms", "조건", "condition", "정책", "policy",
            "법적", "legal", "소송", "lawsuit", "분쟁", "dispute"
        ]
        
        # 개인정보, 보안 관련 키워드
        self.privacy_keywords = [
            "개인정보", "privacy", "보안", "security", "비밀번호", "password",
            "아이디", "id", "계정", "account", "로그인", "login",
            "데이터", "data", "정보보호", "GDPR", "개인정보보호법"
        ]
    
    def is_sensitive_query(self, query: str) -> Dict[str, Any]:
        """
        질문이 민감한 내용인지 확인 (지능적 분류)
        
        Args:
            query: 사용자 질문
            
        Returns:
            Dict containing:
                - is_sensitive: 민감한 질문 여부 (상담사 연결 필요)
                - should_try_rag_first: RAG 우선 시도 여부
                - category: 민감한 카테고리
                - confidence: 신뢰도 (0.0 ~ 1.0)
                - matched_keywords: 매칭된 키워드 리스트
                - query_type: 질문 유형 (general_info, specific_price, discount, etc.)
        """
        query_lower = query.lower()
        matched_keywords = []
        categories = []
        query_type = "general"
        should_try_rag_first = False
        
        # 1. 요금제/플랜 관련 질문 분석
        has_general_plan = self._check_keywords(query_lower, self.general_plan_keywords)
        has_specific_price = self._check_keywords(query_lower, self.specific_price_keywords)
        
        if has_general_plan and not has_specific_price:
            # 일반적인 요금제/플랜 정보 질문 - RAG 우선 시도
            query_type = "general_plan_info"
            should_try_rag_first = True
            logger.info(f"일반 요금제 질문으로 분류 (RAG 우선): {query[:50]}...")
            
        elif has_specific_price:
            # 구체적 가격 문의 - 상담사 연결
            categories.append("specific_price")
            matched_keywords.extend(self._get_matched_keywords(query_lower, self.specific_price_keywords))
            query_type = "specific_price"
            logger.info(f"구체적 가격 질문으로 분류 (상담사 연결): {query[:50]}...")
        
        # 2. 기타 민감한 카테고리 검사
        if self._check_keywords(query_lower, self.discount_keywords):
            categories.append("discount")
            matched_keywords.extend(self._get_matched_keywords(query_lower, self.discount_keywords))
            query_type = "discount"
            
        if self._check_keywords(query_lower, self.consultant_keywords):
            categories.append("consultant")
            matched_keywords.extend(self._get_matched_keywords(query_lower, self.consultant_keywords))
            query_type = "consultant_request"
            
        if self._check_keywords(query_lower, self.contract_keywords):
            categories.append("contract")
            matched_keywords.extend(self._get_matched_keywords(query_lower, self.contract_keywords))
            query_type = "contract"
            
        if self._check_keywords(query_lower, self.privacy_keywords):
            categories.append("privacy")
            matched_keywords.extend(self._get_matched_keywords(query_lower, self.privacy_keywords))
            query_type = "privacy"
        
        # 3. 민감한 질문 패턴 검사 (구체적 가격 문의)
        specific_price_patterns = [
            r"얼마.*받.*나",      # "얼마나 받나요?"
            r"가격.*어떻.*되",    # "가격이 어떻게 되나요?"
            r"비용.*얼마",       # "비용이 얼마인가요?"
            r"정확.*가격",       # "정확한 가격"
            r"구체적.*비용",     # "구체적인 비용"
            r".*원.*정도",       # "몇 원 정도"
        ]
        
        # 일반 정보 패턴 (RAG로 처리 가능)
        general_info_patterns = [
            r"요금제.*종류",     # "요금제 종류가"
            r"플랜.*있.*나",     # "플랜이 있나요"
            r"서비스.*차이",     # "서비스 차이"
            r"기능.*비교",       # "기능 비교"
            r"추천.*플랜",       # "추천하는 플랜"
        ]
        
        pattern_matched_specific = False
        pattern_matched_general = False
        
        for pattern in specific_price_patterns:
            if re.search(pattern, query_lower):
                pattern_matched_specific = True
                categories.append("specific_price")
                query_type = "specific_price"
                break
                
        for pattern in general_info_patterns:
            if re.search(pattern, query_lower):
                pattern_matched_general = True
                should_try_rag_first = True
                query_type = "general_plan_info"
                break
        
        # 상담원 연결 요청 패턴
        consultant_patterns = [
            r"상담원.*연결",     # "상담원 연결해주세요"
            r"직접.*통화",       # "직접 통화하고 싶어요"
            r"사람.*대화",       # "사람과 대화하고 싶어요"
        ]
        
        for pattern in consultant_patterns:
            if re.search(pattern, query_lower):
                categories.append("consultant")
                query_type = "consultant_request"
                break
        
        # 4. 신뢰도 계산
        confidence = 0.0
        if categories:
            confidence = min(0.4 * len(categories) + 0.15 * len(matched_keywords), 1.0)
        if pattern_matched_specific:
            confidence = max(confidence, 0.9)
        elif pattern_matched_general:
            confidence = max(confidence, 0.7)
        
        # 5. 최종 분류 결정
        is_sensitive = len(categories) > 0 or pattern_matched_specific
        
        # 일반 요금제 질문이면서 구체적 가격 문의가 아닌 경우 RAG 우선
        if should_try_rag_first and not pattern_matched_specific:
            is_sensitive = False  # 일단 RAG 시도
        
        result = {
            "is_sensitive": is_sensitive,
            "should_try_rag_first": should_try_rag_first,
            "categories": categories,
            "confidence": confidence,
            "matched_keywords": list(set(matched_keywords)),
            "pattern_matched": pattern_matched_specific or pattern_matched_general,
            "query_type": query_type
        }
        
        logger.info(f"질문 분류: {query[:50]}... -> {result}")
        
        return result
    
    def _check_keywords(self, query: str, keywords: List[str]) -> bool:
        """키워드 리스트 중 하나라도 포함되어 있는지 확인"""
        return any(keyword in query for keyword in keywords)
    
    def _get_matched_keywords(self, query: str, keywords: List[str]) -> List[str]:
        """매칭된 키워드 리스트 반환"""
        return [keyword for keyword in keywords if keyword in query]
    
    def get_sensitive_response(self, categories: List[str]) -> str:
        """민감한 질문에 대한 표준 응답 생성"""
        if "consultant" in categories or "consultant_request" in categories:
            return "해당 질문은 제가 처리할 수 없습니다. 상담사와 연결을 도와드릴까요?"
        elif "specific_price" in categories:
            return "구체적인 가격 정보는 제가 정확하게 안내드리기 어렵습니다. 정확한 요금 안내를 위해 상담사와 연결을 도와드릴까요?"
        elif "discount" in categories:
            return "할인이나 프로모션에 관한 문의는 제가 정확한 정보를 제공하기 어렵습니다. 상담사와 연결을 도와드릴까요?"
        elif "contract" in categories:
            return "계약이나 법적 사항에 대한 문의는 제가 처리할 수 없습니다. 상담사와 연결을 도와드릴까요?"
        elif "privacy" in categories:
            return "개인정보나 보안 관련 문의는 제가 처리할 수 없습니다. 상담사와 연결을 도와드릴까요?"
        elif "general_plan_info" in categories or "rag_insufficient" in categories:
            return "요금제 관련 정보를 찾지 못했습니다. 더 정확한 안내를 위해 상담사와 연결을 도와드릴까요?"
        elif "rag_error" in categories:
            return "일시적인 시스템 오류가 발생했습니다. 정확한 안내를 위해 상담사와 연결을 도와드릴까요?"
        else:
            return "해당 질문은 제가 처리할 수 없습니다. 상담사와 연결을 도와드릴까요?"

# 전역 인스턴스
sensitive_detector = SensitiveQueryDetector()