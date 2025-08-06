#!/usr/bin/env python3
"""
GCS 기반 ConversationLogger 테스트 스크립트
실제 GCS 버킷 연동 테스트
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from modules.services.conversation_logger import conversation_logger
from modules.config import Config

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_conversation_logger():
    """ConversationLogger GCS 기능 테스트"""
    
    print("=" * 50)
    print("ConversationLogger GCS 기능 테스트")
    print("=" * 50)
    
    # 1. 설정 확인
    print(f"대화 저장용 버킷: {Config.CONVERSATION_BUCKET}")
    
    if not Config.CONVERSATION_BUCKET:
        print("❌ CONVERSATION_BUCKET이 설정되지 않았습니다")
        return False
    
    # 2. 테스트 대화 로깅
    print("\n1️⃣ 테스트 대화 로깅...")
    test_session_id = "test-session-12345"
    
    success = conversation_logger.log_conversation(
        session_id=test_session_id,
        user_question="GCS 기반 로깅이 잘 작동하나요?",
        ai_answer="네, GCS 버킷에 JSON 파일로 저장됩니다.",
        metadata={
            "engine_type": "test",
            "test_mode": True
        }
    )
    
    if success:
        print("✅ 대화 로깅 성공")
    else:
        print("❌ 대화 로깅 실패")
        return False
    
    # 3. 세션 정보 조회
    print("\n2️⃣ 세션 정보 조회...")
    session_info = conversation_logger.get_session_info(test_session_id)
    
    if session_info:
        print(f"✅ 세션 정보 조회 성공: {session_info}")
    else:
        print("❌ 세션 정보 조회 실패")
        return False
    
    # 4. 대화 내용 조회
    print("\n3️⃣ 대화 내용 조회...")
    conversations = conversation_logger.get_session_conversations(test_session_id)
    
    if conversations:
        print(f"✅ 대화 내용 조회 성공: {len(conversations)}개 대화")
        print(f"첫 번째 대화: {conversations[0]['user_question'][:30]}...")
    else:
        print("❌ 대화 내용 조회 실패")
        return False
    
    # 5. 두 번째 대화 추가
    print("\n4️⃣ 추가 대화 로깅...")
    success2 = conversation_logger.log_conversation(
        session_id=test_session_id,
        user_question="두 번째 질문입니다.",
        ai_answer="두 번째 답변입니다. 같은 세션에 저장됩니다.",
        metadata={
            "engine_type": "test",
            "conversation_index": 2
        }
    )
    
    if success2:
        print("✅ 두 번째 대화 로깅 성공")
    else:
        print("❌ 두 번째 대화 로깅 실패")
        return False
    
    # 6. 업데이트된 대화 내용 확인
    print("\n5️⃣ 업데이트된 대화 내용 확인...")
    updated_conversations = conversation_logger.get_session_conversations(test_session_id)
    
    if updated_conversations and len(updated_conversations) == 2:
        print(f"✅ 대화 내용 업데이트 성공: {len(updated_conversations)}개 대화")
    else:
        print(f"❌ 대화 내용 업데이트 실패: {len(updated_conversations) if updated_conversations else 0}개")
        return False
    
    # 7. 세션 목록 조회
    print("\n6️⃣ 세션 목록 조회...")
    sessions = conversation_logger.list_sessions()
    
    print(f"✅ 총 {len(sessions)}개 세션 발견")
    if sessions:
        print(f"최신 세션: {sessions[0]['session_id']}")
    
    print("\n" + "=" * 50)
    print("✅ 모든 테스트 완료!")
    print("🎉 GCS 기반 ConversationLogger가 정상 작동합니다.")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    try:
        # 환경변수 로드
        from dotenv import load_dotenv
        load_dotenv()
        
        success = test_conversation_logger()
        
        if success:
            print("\n🚀 실제 애플리케이션에서 사용할 준비가 완료되었습니다!")
        else:
            print("\n❌ 테스트 실패. 설정을 확인해주세요.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)