#!/usr/bin/env python3
"""질문 분류 시스템 테스트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.services.sensitive_query_detector import sensitive_detector

def test_query_classification():
    """다양한 질문 유형을 테스트"""
    
    # 테스트 질문들
    test_queries = [
        # 일반 요금제 정보 (RAG 우선 시도)
        "요금제 종류가 뭐가 있나요?",
        "프리미엄 플랜의 기능이 뭐죠?",
        "베이직 플랜과 프로 플랜의 차이점은?",
        "추천하는 요금제가 있나요?",
        "어떤 서비스를 제공하나요?",
        
        # 구체적 가격 문의 (상담사 연결)
        "프리미엄 플랜이 정확히 얼마예요?",
        "베이직 요금제 가격이 어떻게 되나요?",
        "한 달에 얼마나 받나요?",
        "구체적인 비용을 알고 싶어요",
        "정확한 요금을 알려주세요",
        
        # 할인/프로모션 (상담사 연결)
        "할인이 있나요?",
        "프로모션 진행 중인 게 있나요?",
        "특가나 세일하는 플랜 있나요?",
        
        # 상담원 직접 요청 (상담사 연결)
        "상담원과 연결해주세요",
        "사람과 직접 통화하고 싶어요",
        "직접 상담받고 싶습니다",
        
        # 일반 질문 (정상 RAG 처리)
        "회사 소개를 해주세요",
        "마이메일러가 뭔가요?",
        "어떤 기능들이 있나요?",
        "사용법을 알려주세요"
    ]
    
    print("질문 분류 시스템 테스트\n")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i:2d}. 질문: {query}")
        result = sensitive_detector.is_sensitive_query(query)
        
        print(f"    분류 결과:")
        print(f"       - 질문 유형: {result['query_type']}")
        print(f"       - 민감한 질문: {'예' if result['is_sensitive'] else '아니오'}")
        print(f"       - RAG 우선: {'예' if result['should_try_rag_first'] else '아니오'}")
        print(f"       - 신뢰도: {result['confidence']:.2f}")
        print(f"       - 카테고리: {result['categories']}")
        
        if result['matched_keywords']:
            print(f"       - 매칭 키워드: {result['matched_keywords']}")
        
        # 처리 방식 결정
        if result['should_try_rag_first']:
            action = "RAG 먼저 시도 -> 답변 부족시 상담사 연결"
        elif result['is_sensitive']:
            action = "즉시 상담사 연결"
        else:
            action = "일반 RAG 처리"
        
        print(f"    처리 방식: {action}")
        print("    " + "-" * 76)

if __name__ == "__main__":
    test_query_classification()
    
    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("\n분류 규칙 요약:")
    print("1. 일반 요금제 정보 -> RAG 우선 시도")
    print("2. 구체적 가격 문의 -> 즉시 상담사 연결") 
    print("3. 할인/프로모션 -> 즉시 상담사 연결")
    print("4. 상담원 요청 -> 즉시 상담사 연결")
    print("5. 기타 일반 질문 -> 정상 RAG 처리")