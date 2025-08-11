#!/usr/bin/env python3
"""Google Chat 웹훅 디버깅 스크립트"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_github_actions_format():
    """GitHub Actions에서 사용하는 형태로 테스트"""
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ GOOGLE_CHAT_WEBHOOK_URL 환경변수가 없습니다.")
        print("💡 .env 파일에 추가하거나 직접 입력해주세요.")
        webhook_url = input("웹훅 URL을 입력하세요: ").strip()
        
        if not webhook_url:
            print("❌ 웹훅 URL이 필요합니다.")
            return False
    
    print(f"🔗 사용할 웹훅 URL: {webhook_url[:50]}...")
    
    # GitHub Actions에서 사용하는 정확한 페이로드 형태
    payload = {
        "text": "*GitHub Actions 테스트*",
        "cards": [{
            "header": {
                "title": "GraphRAG 배포 테스트",
                "subtitle": "로컬에서 GitHub Actions 형태 테스트"
            },
            "sections": [{
                "widgets": [
                    {
                        "keyValue": {
                            "topLabel": "테스트 상태",
                            "content": "로컬 테스트",
                            "contentMultiline": False,
                            "icon": "CHECK_CIRCLE"
                        }
                    },
                    {
                        "keyValue": {
                            "topLabel": "환경",
                            "content": "로컬 개발환경",
                            "contentMultiline": False
                        }
                    },
                    {
                        "keyValue": {
                            "topLabel": "브랜치",
                            "content": "main",
                            "contentMultiline": False
                        }
                    },
                    {
                        "keyValue": {
                            "topLabel": "커밋",
                            "content": "abc1234",
                            "contentMultiline": False
                        }
                    }
                ]
            }],
            "cardActions": [{
                "actionLabel": "테스트 완료",
                "onClick": {
                    "openLink": {
                        "url": "https://github.com"
                    }
                }
            }]
        }]
    }
    
    try:
        print("📡 Google Chat으로 테스트 메시지 전송 중...")
        
        response = requests.post(
            webhook_url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        
        print(f"📊 응답 상태 코드: {response.status_code}")
        print(f"📄 응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ 테스트 메시지 전송 성공!")
            print("📱 Google Chat에서 메시지를 확인하세요.")
            return True
        else:
            print(f"❌ 테스트 실패: HTTP {response.status_code}")
            print(f"📄 응답 내용: {response.text}")
            
            # 일반적인 오류 해석
            if response.status_code == 400:
                print("💡 400 오류: 잘못된 요청 형식. JSON 페이로드를 확인하세요.")
            elif response.status_code == 403:
                print("💡 403 오류: 권한 없음. 웹훅 URL이나 Space 설정을 확인하세요.")
            elif response.status_code == 404:
                print("💡 404 오류: 웹훅을 찾을 수 없음. URL이 올바른지 확인하세요.")
                
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 요청 시간 초과 (30초)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def test_simple_format():
    """간단한 텍스트 메시지로 테스트"""
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ GOOGLE_CHAT_WEBHOOK_URL 환경변수가 없습니다.")
        return False
    
    payload = {
        "text": "🧪 간단한 테스트 메시지입니다."
    }
    
    try:
        print("📡 간단한 텍스트 메시지 전송 중...")
        
        response = requests.post(
            webhook_url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=10
        )
        
        print(f"📊 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 간단한 메시지 전송 성공!")
            return True
        else:
            print(f"❌ 간단한 메시지도 실패: {response.status_code}")
            print(f"📄 응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 간단한 테스트 실패: {e}")
        return False

def analyze_webhook_url():
    """웹훅 URL 분석"""
    webhook_url = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ 웹훅 URL이 설정되지 않았습니다.")
        return
    
    print(f"🔍 웹훅 URL 분석:")
    print(f"   길이: {len(webhook_url)} 문자")
    print(f"   시작: {webhook_url[:50]}...")
    print(f"   끝: ...{webhook_url[-30:]}")
    
    # URL 구조 확인
    if webhook_url.startswith('https://chat.googleapis.com/v1/spaces/'):
        print("✅ 올바른 Google Chat 웹훅 URL 형식입니다.")
        
        # 파라미터 확인
        if 'key=' in webhook_url and 'token=' in webhook_url:
            print("✅ 필수 파라미터 (key, token)가 포함되어 있습니다.")
        else:
            print("❌ key 또는 token 파라미터가 누락되었습니다.")
            
    else:
        print("❌ 올바른 Google Chat 웹훅 URL 형식이 아닙니다.")
        print("💡 올바른 형식: https://chat.googleapis.com/v1/spaces/...")

if __name__ == "__main__":
    print("Google Chat 웹훅 디버깅 시작\n")
    
    # 1. 웹훅 URL 분석
    print("=" * 50)
    analyze_webhook_url()
    
    # 2. 간단한 메시지 테스트
    print("\n" + "=" * 50)
    print("📝 간단한 메시지 테스트")
    simple_success = test_simple_format()
    
    # 3. GitHub Actions 형태 테스트
    print("\n" + "=" * 50)
    print("🚀 GitHub Actions 형태 테스트")
    github_success = test_github_actions_format()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약:")
    print(f"   간단한 메시지: {'✅ 성공' if simple_success else '❌ 실패'}")
    print(f"   GitHub Actions 형태: {'✅ 성공' if github_success else '❌ 실패'}")
    
    if simple_success and github_success:
        print("\n🎉 모든 테스트 성공! GitHub Actions가 작동해야 합니다.")
        print("💡 GitHub Actions 워크플로우 로그를 확인해보세요.")
    elif simple_success:
        print("\n⚠️ 간단한 메시지는 되지만 복잡한 카드 형식은 실패")
        print("💡 GitHub Actions 워크플로우의 JSON 형식을 수정해야 할 수 있습니다.")
    else:
        print("\n❌ 기본 연결도 실패했습니다.")
        print("💡 웹훅 URL이나 Google Chat 설정을 다시 확인해주세요.")
        
    print("\n🔍 다음 단계:")
    print("1. GitHub Actions 워크플로우 실행")
    print("2. Actions 탭에서 로그 확인") 
    print("3. 알림 단계에서 오류 메시지 확인")