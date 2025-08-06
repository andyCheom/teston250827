"""대화 내용 GCS JSON 로깅 모듈"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
from google.cloud import storage
from google.cloud.exceptions import NotFound

from ..config import Config
from ..auth import get_storage_client

logger = logging.getLogger(__name__)

class ConversationLogger:
    """대화 세션별 GCS JSON 로깅 관리자 (기존 API 호환)"""
    
    def __init__(self, bucket_name: str = None):
        """
        Args:
            bucket_name: GCS 버킷 이름 (None이면 환경변수에서 가져옴)
        """
        self.bucket_name = bucket_name or Config.CONVERSATION_BUCKET
        self.storage_client = None
        self.bucket = None
        self._initialize_gcs()
    
    def _initialize_gcs(self) -> bool:
        """GCS 클라이언트 및 버킷 초기화"""
        try:
            self.storage_client = get_storage_client()
            if not self.storage_client:
                logger.error("❌ GCS 클라이언트 초기화 실패")
                return False
                
            if not self.bucket_name:
                logger.error("❌ 대화 저장용 버킷 이름이 설정되지 않았습니다")
                return False
                
            self.bucket = self.storage_client.bucket(self.bucket_name)
            
            # 버킷 존재 확인
            if not self.bucket.exists():
                logger.error(f"❌ 대화 저장용 버킷이 존재하지 않습니다: {self.bucket_name}")
                return False
                
            logger.info(f"✅ GCS 대화 로깅 초기화 완료 - 버킷: {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ GCS 초기화 실패: {e}")
            return False
        
    def _get_session_blob_path(self, session_id: str) -> str:
        """세션 ID로 GCS blob 경로 생성"""
        safe_session_id = session_id.replace("/", "_").replace("\\", "_")
        return f"sessions/session_{safe_session_id}.json"
    
    def _load_session_data(self, session_id: str) -> Dict[str, Any]:
        """GCS에서 세션 데이터 로드"""
        if not self.bucket:
            logger.error("GCS 버킷이 초기화되지 않았습니다")
            return self._create_new_session_data(session_id)
            
        blob_path = self._get_session_blob_path(session_id)
        blob = self.bucket.blob(blob_path)
        
        try:
            if blob.exists():
                content = blob.download_as_text(encoding='utf-8')
                return json.loads(content)
            else:
                return self._create_new_session_data(session_id)
        except Exception as e:
            logger.warning(f"GCS 세션 데이터 로드 실패 {session_id}: {e}")
            return self._create_new_session_data(session_id)
    
    def _create_new_session_data(self, session_id: str) -> Dict[str, Any]:
        """새로운 세션 데이터 구조 생성"""
        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "conversation_count": 0,
            "conversations": []
        }
    
    def _save_session_data(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """세션 데이터를 GCS에 저장"""
        if not self.bucket:
            logger.error("GCS 버킷이 초기화되지 않았습니다")
            return False
            
        try:
            blob_path = self._get_session_blob_path(session_id)
            blob = self.bucket.blob(blob_path)
            
            session_data["updated_at"] = datetime.now().isoformat()
            
            # JSON 문자열로 변환 후 업로드
            json_content = json.dumps(session_data, ensure_ascii=False, indent=2)
            blob.upload_from_string(
                json_content, 
                content_type='application/json',
                encoding='utf-8'
            )
            
            return True
        except Exception as e:
            logger.error(f"GCS 세션 데이터 저장 실패 {session_id}: {e}")
            return False
    
    def log_conversation(self, 
                        session_id: Optional[str],
                        user_question: str,
                        ai_answer: str,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """대화 내용을 세션별 JSON 파일에 로깅
        
        Args:
            session_id: 세션 ID (None이면 새로 생성)
            user_question: 사용자 질문
            ai_answer: AI 응답
            metadata: 추가 메타데이터 (citations, search_results 등)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 세션 ID가 없으면 새로 생성
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # 기존 세션 데이터 로드
            session_data = self._load_session_data(session_id)
            
            # 새로운 대화 항목 생성
            conversation_item = {
                "timestamp": datetime.now().isoformat(),
                "conversation_index": session_data["conversation_count"] + 1,
                "user_question": user_question,
                "ai_answer": ai_answer,
                "metadata": metadata or {}
            }
            
            # 세션 데이터에 대화 추가
            session_data["conversations"].append(conversation_item)
            session_data["conversation_count"] += 1
            
            # 파일에 저장
            success = self._save_session_data(session_id, session_data)
            
            if success:
                logger.info(f"대화 로깅 성공 - 세션: {session_id}, 대화 번호: {conversation_item['conversation_index']}")
            else:
                logger.error(f"대화 로깅 실패 - 세션: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"대화 로깅 중 오류 발생: {e}")
            return False
    
    def get_session_conversations(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """특정 세션의 모든 대화 내용 조회"""
        try:
            session_data = self._load_session_data(session_id)
            return session_data.get("conversations", [])
        except Exception as e:
            logger.error(f"세션 대화 조회 실패 {session_id}: {e}")
            return None
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 정보 조회 (대화 내용 제외)"""
        try:
            session_data = self._load_session_data(session_id)
            return {
                "session_id": session_data["session_id"],
                "created_at": session_data["created_at"],
                "updated_at": session_data["updated_at"],
                "conversation_count": session_data["conversation_count"]
            }
        except Exception as e:
            logger.error(f"세션 정보 조회 실패 {session_id}: {e}")
            return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """GCS에서 모든 세션 목록 조회"""
        if not self.bucket:
            logger.error("GCS 버킷이 초기화되지 않았습니다")
            return []
            
        sessions = []
        try:
            # sessions/ 폴더의 모든 JSON 파일 조회
            blobs = self.bucket.list_blobs(prefix="sessions/session_", delimiter=None)
            
            for blob in blobs:
                if not blob.name.endswith('.json'):
                    continue
                    
                try:
                    content = blob.download_as_text(encoding='utf-8')
                    session_data = json.loads(content)
                    sessions.append({
                        "session_id": session_data["session_id"],
                        "created_at": session_data["created_at"],
                        "updated_at": session_data["updated_at"],
                        "conversation_count": session_data["conversation_count"],
                        "blob_path": blob.name,
                        "blob_size": blob.size
                    })
                except Exception as e:
                    logger.warning(f"GCS 세션 데이터 읽기 실패 {blob.name}: {e}")
                    continue
            
            # 최신 순으로 정렬
            sessions.sort(key=lambda x: x["updated_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"GCS 세션 목록 조회 실패: {e}")
        
        return sessions
    
    def cleanup_old_sessions(self, days_to_keep: int = 30) -> int:
        """GCS에서 오래된 세션 파일들 정리
        
        Args:
            days_to_keep: 보관할 일수
            
        Returns:
            int: 삭제된 파일 수
        """
        if not self.bucket:
            logger.error("GCS 버킷이 초기화되지 않았습니다")
            return 0
            
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            # sessions/ 폴더의 모든 JSON 파일 조회
            blobs = self.bucket.list_blobs(prefix="sessions/session_", delimiter=None)
            
            for blob in blobs:
                if not blob.name.endswith('.json'):
                    continue
                    
                try:
                    content = blob.download_as_text(encoding='utf-8')
                    session_data = json.loads(content)
                    
                    updated_at = datetime.fromisoformat(session_data.get("updated_at", ""))
                    
                    if updated_at < cutoff_date:
                        blob.delete()  # GCS 파일 삭제
                        deleted_count += 1
                        logger.info(f"오래된 GCS 세션 파일 삭제: {blob.name}")
                        
                except Exception as e:
                    logger.warning(f"GCS 세션 파일 정리 중 오류 {blob.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"GCS 세션 정리 중 오류: {e}")
        
        logger.info(f"GCS 세션 정리 완료: {deleted_count}개 파일 삭제")
        return deleted_count

# 전역 인스턴스
conversation_logger = ConversationLogger()