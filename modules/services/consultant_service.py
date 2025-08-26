"""상담사 연결 서비스"""
import json
import logging
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..config import Config

logger = logging.getLogger(__name__)

class ConsultantService:
    """상담사 연결 서비스 클래스"""
    
    def __init__(self):
        self.google_chat_webhook_url = None
        self.session = None
    
    async def get_session(self):
        """HTTP 세션 관리"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def send_to_google_chat(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Google Chat으로 상담 요청 전송"""
        try:
            # 환경변수에서 웹훅 URL 가져오기
            webhook_url = Config.get_env_var("GOOGLE_CHAT_WEBHOOK_URL")
            if not webhook_url:
                logger.error("Google Chat 웹훅 URL이 설정되지 않았습니다")
                return {"success": False, "error": "Google Chat webhook URL is not configured."}
            
            session = await self.get_session()
            
            # 대화 내용 포맷팅
            conversation_text = self._format_conversation_for_chat(conversation_data)
            
            # Google Chat 메시지 페이로드 구성
            chat_payload = {
                "text": f"🔔 *새로운 상담 요청*\n\n{conversation_text}",
                "cards": [{
                    "sections": [{
                        "widgets": [
                            {
                                "keyValue": {
                                    "topLabel": "요청 시간",
                                    "content": conversation_data.get("timestamp", datetime.now().isoformat())
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "세션 ID",
                                    "content": conversation_data.get("session_id", "N/A")
                                }
                            },
                            {
                                "keyValue": {
                                    "topLabel": "민감한 카테고리",
                                    "content": ", ".join(conversation_data.get("sensitive_categories", []))
                                }
                            }
                        ]
                    }]
                }]
            }
            
            async with session.post(webhook_url, json=chat_payload) as response:
                if response.status == 200:
                    logger.info("Google Chat으로 상담 요청 전송 성공")
                    return {"success": True}
                else:
                    error_text = await response.text()
                    logger.error(f"Google Chat 전송 실패: {response.status} - {error_text}")
                    return {"success": False, "error": f"Google Chat API returned status {response.status}: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Google Chat 전송 중 오류 발생: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_conversation_for_chat(self, conversation_data: Dict[str, Any]) -> str:
        """Google Chat용 대화 내용 포맷팅"""
        conversation_history = conversation_data.get("conversation_history", [])
        user_query = conversation_data.get("user_query", "")
        
        formatted_text = f"*최근 질문:* {user_query}\n\n"
        
        if conversation_history:
            formatted_text += "*대화 내역:*\n"
            # 최근 대화만 표시
            recent_conversations = conversation_history[-Config.MAX_CONVERSATION_HISTORY:] if len(conversation_history) > Config.MAX_CONVERSATION_HISTORY else conversation_history
            
            for i, msg in enumerate(recent_conversations):
                role = "👤 사용자" if msg.get("role") == "user" else "🤖 AI"
                content = ""
                if msg.get("parts") and len(msg["parts"]) > 0:
                    content = msg["parts"][0].get("text", "")
                
                # 텍스트 길이 제한
                if len(content) > Config.MAX_TEXT_LENGTH:
                    content = content[:Config.MAX_TEXT_LENGTH] + "..."
                
                formatted_text += f"\n{role}: {content}\n"
        
        return formatted_text
    
    async def create_consultation_request(self, 
                                        user_query: str, 
                                        conversation_history: List[Dict[str, Any]],
                                        session_id: Optional[str] = None,
                                        sensitive_categories: List[str] = None) -> Dict[str, Any]:
        """상담 요청 생성 및 Google Chat 전송"""
        try:
            consultation_data = {
                "user_query": user_query,
                "conversation_history": conversation_history,
                "session_id": session_id or f"session_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "sensitive_categories": sensitive_categories or [],
                "status": "requested"
            }
            
            # Google Chat으로 전송
            chat_result = await self.send_to_google_chat(consultation_data)
            
            result = {
                "success": chat_result["success"],
                "consultation_id": consultation_data["session_id"],
                "message": "상담 요청이 전송되었습니다" if chat_result["success"] else "상담 요청 전송에 실패했습니다",
                "timestamp": consultation_data["timestamp"]
            }
            if not chat_result["success"]:
                result["error"] = chat_result.get("error", "Unknown error from consultant_service")

            logger.info(f"상담 요청 처리 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"상담 요청 생성 중 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "상담 요청 처리 중 오류가 발생했습니다"
            }
    
    async def close(self):
        """세션 정리"""
        if self.session and not self.session.closed:
            await self.session.close()

# 전역 인스턴스
consultant_service = ConsultantService()