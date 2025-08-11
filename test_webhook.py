#!/usr/bin/env python3
"""Google Chat 웹훅 테스트 스크립트"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_google_chat_webhook():
    """Google Chat 웹훅 테스트"""
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ GOOGLE_CHAT_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print("📝 .env 파일에 웹훅 URL을 추가하세요:")
        print("GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/YOUR_SPACE/messages?key=YOUR_KEY&token=YOUR_TOKEN")
        return False
    
    # 테스트 메시지 payload
    test_payload = {
        "text": "🧪 *웹훅 테스트*\n\n상담사 연결 시스템이 정상적으로 작동합니다!",
        "cards": [{
            "sections": [{
                "widgets": [
                    {
                        "keyValue": {
                            "topLabel": "테스트 시간",
                            "content": "지금"
                        }
                    },
                    {
                        "keyValue": {
                            "topLabel": "상태",
                            "content": "✅ 연결 성공"
                        }
                    }
                ]
            }]
        }]
    }
    
    try:
        print(f"🔄 Google Chat으로 테스트 메시지 전송 중...")
        print(f"📡 웹훅 URL: {webhook_url[:50]}...")
        
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ 테스트 메시지 전송 성공!")
            print("📱 Google Chat Space에서 메시지를 확인하세요.")
            return True
        else:
            print(f"❌ 테스트 실패: HTTP {response.status_code}")
            print(f"📄 응답 내용: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 요청 시간 초과 - 네트워크 연결을 확인하세요.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Google Chat 웹훅 테스트를 시작합니다...\n")
    
    success = test_google_chat_webhook()
    
    print("\n" + "="*50)
    if success:
        print("🎉 테스트 완료! 상담사 연결 시스템이 준비되었습니다.")
        print("\n📋 다음 단계:")
        print("1. 챗봇에서 '가격이 얼마예요?' 같은 민감한 질문 테스트")
        print("2. 상담사 연결 버튼 클릭 테스트")
        print("3. Google Chat에서 알림 수신 확인")
    else:
        print("🔧 웹훅 설정을 다시 확인해주세요.")
        print("\n🔍 확인사항:")
        print("1. Google Chat Space가 올바르게 생성되었는지")
        print("2. Incoming Webhook 앱이 추가되었는지")
        print("3. 웹훅 URL이 정확히 복사되었는지")
        print("4. .env 파일이 올바른 위치에 있는지")