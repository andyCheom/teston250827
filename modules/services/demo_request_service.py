"""데모 신청 서비스"""
import json
import logging
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional
from ..config import Config

logger = logging.getLogger(__name__)

class DemoRequestService:
    """데모 신청 서비스 클래스"""
    
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        """HTTP 세션 관리"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def send_demo_request_to_google_chat(self, demo_data: Dict[str, Any]) -> bool:
        """Google Chat으로 데모 신청 정보 전송"""
        try:
            # 환경변수에서 웹훅 URL 가져오기
            webhook_url = Config.get_env_var("GOOGLE_CHAT_WEBHOOK_URL")
            if not webhook_url:
                logger.error("Google Chat 웹훅 URL이 설정되지 않았습니다")
                return False
            
            session = await self.get_session()
            
            # Google Chat 메시지 페이로드 구성
            chat_payload = {
                "text": f"🎯 *새로운 데모 신청*",
                "cards": [{
                    "header": {
                        "title": "GraphRAG 데모 신청 알림",
                        "subtitle": "새로운 데모 신청이 접수되었습니다"
                    },
                    "sections": [{
                        "widgets": [
                            {
                                "keyValue": {
                                    "topLabel": "신청 시간",
                                    "content": demo_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                    "contentMultiline": False
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "회사명",
                                    "content": demo_data.get("company_name", "미입력"),
                                    "contentMultiline": False
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "고객명",
                                    "content": demo_data.get("customer_name", "미입력"),
                                    "contentMultiline": False
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "이메일",
                                    "content": demo_data.get("email", "미입력"),
                                    "contentMultiline": False
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "전화번호",
                                    "content": demo_data.get("phone", "미입력"),
                                    "contentMultiline": False
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "발송타입",
                                    "content": demo_data.get("send_type", "미입력"),
                                    "contentMultiline": False
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "사용목적 및 이용방식",
                                    "content": demo_data.get("usage_purpose", "미입력"),
                                    "contentMultiline": True
                                }
                            }
                        ]
                    }]
                }]
            }
            
            async with session.post(webhook_url, json=chat_payload) as response:
                if response.status == 200:
                    logger.info("Google Chat으로 데모 신청 알림 전송 성공")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Google Chat 전송 실패: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Google Chat 전송 중 오류 발생: {e}")
            return False
    
    def validate_demo_request(self, demo_data: Dict[str, Any]) -> Dict[str, Any]:
        """데모 신청 데이터 검증"""
        errors = []
        warnings = []
        
        # 필수 필드 검증
        required_fields = {
            "company_name": "회사명",
            "customer_name": "고객명", 
            "email": "이메일",
            "phone": "전화번호"
        }
        
        for field, field_name in required_fields.items():
            if not demo_data.get(field) or demo_data.get(field).strip() == "":
                errors.append(f"{field_name}은(는) 필수 입력 항목입니다.")
        
        # 이메일 형식 간단 검증
        email = demo_data.get("email", "").strip()
        if email and "@" not in email or "." not in email:
            errors.append("올바른 이메일 형식을 입력해주세요.")
        
        # 전화번호 형식 간단 검증 (숫자와 하이픈만 허용)
        phone = demo_data.get("phone", "").strip()
        if phone:
            cleaned_phone = phone.replace("-", "").replace(" ", "")
            if not cleaned_phone.isdigit():
                warnings.append("전화번호는 숫자와 하이픈만 입력해주세요.")
        
        # 선택 필드 체크
        if not demo_data.get("send_type", "").strip():
            warnings.append("발송타입을 선택하시면 더 정확한 데모를 제공할 수 있습니다.")
            
        if not demo_data.get("usage_purpose", "").strip():
            warnings.append("사용목적을 입력하시면 맞춤형 데모를 제공할 수 있습니다.")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def process_demo_request(self, demo_data: Dict[str, Any]) -> Dict[str, Any]:
        """데모 신청 처리"""
        try:
            # 데이터 검증
            validation_result = self.validate_demo_request(demo_data)
            
            if not validation_result["is_valid"]:
                return {
                    "success": False,
                    "message": "입력 정보를 확인해주세요.",
                    "errors": validation_result["errors"],
                    "warnings": validation_result["warnings"]
                }
            
            # 타임스탬프 추가
            demo_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            demo_data["request_id"] = f"demo_{datetime.now().timestamp()}"
            
            # Google Chat으로 전송
            chat_success = await self.send_demo_request_to_google_chat(demo_data)
            
            result = {
                "success": chat_success,
                "request_id": demo_data["request_id"],
                "message": "데모 신청이 완료되었습니다. 빠른 시일 내에 연락드리겠습니다!" if chat_success else "데모 신청 처리 중 오류가 발생했습니다.",
                "timestamp": demo_data["timestamp"],
                "warnings": validation_result["warnings"]
            }
            
            logger.info(f"데모 신청 처리 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"데모 신청 처리 중 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "데모 신청 처리 중 오류가 발생했습니다."
            }
    
    async def close(self):
        """세션 정리"""
        if self.session and not self.session.closed:
            await self.session.close()

# 전역 인스턴스
demo_service = DemoRequestService()