"""Firebase Firestore 대화 저장 서비스"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from google.cloud import firestore
from google.cloud.exceptions import NotFound

from ..config import Config
from ..auth import get_credentials

logger = logging.getLogger(__name__)

class FirestoreConversationService:
    """Firebase Firestore를 이용한 대화 저장 및 분석 서비스"""
    
    def __init__(self):
        self.db = None
        self.project_id = Config.PROJECT_ID
        self._initialized = False
    
    def _initialize_firestore(self) -> bool:
        """Firestore 클라이언트 초기화 (지연 초기화)"""
        if self._initialized:
            return self.db is not None
            
        try:
            from ..auth import is_authenticated, get_credentials
            
            if not is_authenticated():
                logger.warning("인증이 초기화되지 않아 Firestore 초기화를 건너뜁니다")
                return False
                
            credentials = get_credentials()
            if credentials:
                self.db = firestore.Client(project=self.project_id, credentials=credentials)
            else:
                # 기본 인증 사용 (로컬 개발 환경)
                self.db = firestore.Client(project=self.project_id)
            
            self._initialized = True
            logger.info(f"✅ Firestore 클라이언트 초기화 완료 - Project: {self.project_id}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Firestore 초기화 실패 (정상적으로 건너뜀): {e}")
            self.db = None
            self._initialized = True  # 다시 시도하지 않음
            return False
    
    def generate_session_id(self) -> str:
        """세션 ID 생성"""
        return f"session_{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}"
    
    async def save_conversation(self, 
                              session_id: str,
                              user_query: str,
                              ai_response: str,
                              metadata: Optional[Dict[str, Any]] = None,
                              quality_metrics: Optional[Dict[str, Any]] = None) -> bool:
        """대화 내용을 Firestore에 저장"""
        if not self._initialize_firestore():
            logger.warning("Firestore가 초기화되지 않아 대화 저장을 건너뜁니다")
            return False
        
        try:
            # 메시지 데이터 구성
            message_data = {
                'user_query': user_query,
                'ai_response': ai_response,
                'timestamp': datetime.now(timezone.utc),
                'metadata': metadata or {},
                'quality_metrics': quality_metrics or {},
                'response_length': len(ai_response),
                'query_length': len(user_query)
            }
            
            # 세션 문서 참조
            session_ref = self.db.collection('conversations').document(session_id)
            
            # 기존 세션 확인
            session_doc = session_ref.get()
            
            if session_doc.exists:
                # 기존 세션 업데이트 - arrayUnion 사용으로 안전하게 추가
                session_ref.update({
                    'messages': firestore.ArrayUnion([message_data]),
                    'message_count': firestore.Increment(1),
                    'updated_at': datetime.now(timezone.utc),
                    'last_activity': datetime.now(timezone.utc)
                })
                updated_session = {'message_count': session_doc.to_dict().get('message_count', 0) + 1}
            else:
                # 새 세션 생성
                session_data = {
                    'session_id': session_id,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc),
                    'last_activity': datetime.now(timezone.utc),
                    'messages': [message_data],
                    'message_count': 1,
                    'user_info': {
                        'user_agent': metadata.get('user_agent', '') if metadata else '',
                        'ip_region': metadata.get('ip_region', '') if metadata else ''
                    }
                }
                session_ref.set(session_data)
                updated_session = session_data
            
            logger.info(f"✅ 대화 저장 성공 - 세션: {session_id}, 메시지 수: {updated_session['message_count']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 대화 저장 실패 - 세션: {session_id}, 오류: {e}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """세션의 대화 내역 조회"""
        if not self._initialize_firestore():
            return []
        
        try:
            session_ref = self.db.collection('conversations').document(session_id)
            session_doc = session_ref.get()
            
            if not session_doc.exists:
                return []
            
            session_data = session_doc.to_dict()
            messages = session_data.get('messages', [])
            
            # 최근 메시지부터 제한된 수만큼 반환
            return messages[-limit:] if len(messages) > limit else messages
            
        except Exception as e:
            logger.error(f"❌ 대화 내역 조회 실패 - 세션: {session_id}, 오류: {e}")
            return []
    
    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 요약 정보 조회"""
        if not self._initialize_firestore():
            return None
        
        try:
            session_ref = self.db.collection('conversations').document(session_id)
            session_doc = session_ref.get()
            
            if not session_doc.exists:
                return None
            
            session_data = session_doc.to_dict()
            
            return {
                'session_id': session_id,
                'created_at': session_data.get('created_at'),
                'updated_at': session_data.get('updated_at'),
                'message_count': session_data.get('message_count', 0),
                'last_activity': session_data.get('last_activity'),
                'user_info': session_data.get('user_info', {})
            }
            
        except Exception as e:
            logger.error(f"❌ 세션 요약 조회 실패 - 세션: {session_id}, 오류: {e}")
            return None
    
    async def update_session_quality(self, session_id: str, message_index: int, quality_score: float, feedback: str = "") -> bool:
        """특정 메시지의 품질 점수 업데이트"""
        if not self.db:
            logger.error("Firestore 데이터베이스가 초기화되지 않음")
            return False
        
        try:
            logger.info(f"품질 업데이트 시작 - 세션: {session_id}, 인덱스: {message_index}")
            
            session_ref = self.db.collection('conversations').document(session_id)
            session_doc = session_ref.get()
            
            if not session_doc.exists:
                logger.warning(f"⚠️ 세션을 찾을 수 없음 - 세션: {session_id}")
                
                # 대체 검색: conversations 컬렉션에서 세션 찾기
                conversations = self.db.collection('conversations').where('session_id', '==', session_id).limit(1).stream()
                found_doc = None
                for doc in conversations:
                    found_doc = doc
                    break
                
                if found_doc:
                    logger.info(f"대체 검색으로 세션 발견: {found_doc.id}")
                    session_ref = found_doc.reference
                    session_data = found_doc.to_dict()
                else:
                    logger.error(f"❌ 세션 완전히 찾을 수 없음 - 세션: {session_id}")
                    return False
            else:
                session_data = session_doc.to_dict()
                logger.info(f"세션 데이터 조회 성공 - 메시지 개수: {len(session_data.get('messages', []))}")
                
            messages = session_data.get('messages', [])
            logger.info(f"메시지 배열 크기: {len(messages)}, 요청 인덱스: {message_index}")
            
            if 0 <= message_index < len(messages):
                # 현재 메시지 확인
                current_message = messages[message_index]
                logger.info(f"업데이트할 메시지: {current_message.get('role', 'unknown')}")
                
                # 메시지 품질 정보 업데이트
                messages[message_index]['quality_metrics'] = {
                    'user_rating': quality_score,
                    'feedback': feedback,
                    'rated_at': firestore.SERVER_TIMESTAMP
                }
                
                # 문서 업데이트
                session_ref.update({
                    'messages': messages,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                logger.info(f"✅ 품질 점수 업데이트 성공 - 세션: {session_id}, 메시지: {message_index}, 점수: {quality_score}")
                return True
            else:
                logger.warning(f"⚠️ 품질 점수 업데이트 실패 - 유효하지 않은 메시지 인덱스: {message_index}, 총 메시지 수: {len(messages)}")
                return False
            
        except Exception as e:
            logger.error(f"❌ 품질 점수 업데이트 실패 - 세션: {session_id}, 오류: {e}")
            import traceback
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return False
    
    async def get_analytics_data(self, days: int = 30) -> Dict[str, Any]:
        """대화 분석 데이터 조회 (최근 N일)"""
        if not self.db:
            return {}
        
        try:
            # 날짜 범위 계산
            from datetime import timedelta
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # 기간 내 세션 조회
            sessions_query = (self.db.collection('conversations')
                            .where('created_at', '>=', start_date)
                            .where('created_at', '<=', end_date)
                            .limit(1000))  # 최대 1000개 세션
            
            sessions = sessions_query.stream()
            
            # 분석 데이터 수집
            total_sessions = 0
            total_messages = 0
            total_users = set()
            quality_scores = []
            common_queries = {}
            response_times = []
            
            for session_doc in sessions:
                session_data = session_doc.to_dict()
                total_sessions += 1
                
                messages = session_data.get('messages', [])
                total_messages += len(messages)
                
                # 사용자 정보 (익명화)
                user_agent = session_data.get('user_info', {}).get('user_agent', '')
                if user_agent:
                    # 사용자 구분을 위한 해시 (개인정보 보호)
                    import hashlib
                    user_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
                    total_users.add(user_hash)
                
                # 메시지 분석
                for msg in messages:
                    # 품질 점수
                    quality_metrics = msg.get('quality_metrics', {})
                    if 'user_rating' in quality_metrics:
                        quality_scores.append(quality_metrics['user_rating'])
                    
                    # 자주 묻는 질문
                    query = msg.get('user_query', '').strip().lower()
                    if query:
                        # 질문의 첫 10글자로 그룹화
                        query_key = query[:50] + "..." if len(query) > 50 else query
                        common_queries[query_key] = common_queries.get(query_key, 0) + 1
                    
                    # 응답 시간 (메타데이터에서)
                    metadata = msg.get('metadata', {})
                    if 'response_time_ms' in metadata:
                        response_times.append(metadata['response_time_ms'])
            
            # 통계 계산
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # 상위 질문 정렬
            top_queries = sorted(common_queries.items(), key=lambda x: x[1], reverse=True)[:10]
            
            analytics = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'overview': {
                    'total_sessions': total_sessions,
                    'total_messages': total_messages,
                    'unique_users': len(total_users),
                    'avg_messages_per_session': total_messages / total_sessions if total_sessions > 0 else 0
                },
                'quality': {
                    'avg_rating': round(avg_quality, 2),
                    'total_ratings': len(quality_scores),
                    'rating_distribution': self._calculate_rating_distribution(quality_scores)
                },
                'performance': {
                    'avg_response_time_ms': round(avg_response_time, 2),
                    'total_response_times': len(response_times)
                },
                'popular_queries': [{'query': q, 'count': c} for q, c in top_queries],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"✅ 분석 데이터 생성 완료 - {total_sessions}개 세션, {total_messages}개 메시지")
            return analytics
            
        except Exception as e:
            logger.error(f"❌ 분석 데이터 조회 실패: {e}")
            return {}
    
    def _calculate_rating_distribution(self, scores: List[float]) -> Dict[str, int]:
        """평점 분포 계산"""
        distribution = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
        for score in scores:
            if 1 <= score <= 5:
                distribution[str(int(score))] += 1
        return distribution
    
    async def cleanup_old_sessions(self, days_to_keep: int = 90) -> int:
        """오래된 세션 정리"""
        if not self.db:
            return 0
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # 오래된 세션 조회
            old_sessions = (self.db.collection('conversations')
                          .where('created_at', '<', cutoff_date)
                          .limit(100))  # 한 번에 100개씩 처리
            
            deleted_count = 0
            batch = self.db.batch()
            
            for session_doc in old_sessions.stream():
                batch.delete(session_doc.reference)
                deleted_count += 1
                
                # 배치 크기 제한 (Firestore 한계: 500개)
                if deleted_count % 100 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # 남은 삭제 작업 실행
            if deleted_count % 100 != 0:
                batch.commit()
            
            logger.info(f"✅ 오래된 세션 정리 완료: {deleted_count}개 삭제")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 세션 정리 실패: {e}")
            return 0

# 전역 인스턴스
firestore_conversation = FirestoreConversationService()