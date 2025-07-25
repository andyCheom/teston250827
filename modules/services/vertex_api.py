"""Vertex AI API 호출 서비스"""
import time
import logging
from typing import Dict, Any
import aiohttp
import google.auth
import google.auth.transport.requests

from ..config import Config
from ..auth import get_credentials

logger = logging.getLogger(__name__)

# 공통 세션과 헤더 캐싱
_shared_session = None
_cached_headers = None
_headers_cache_time = 0

class VertexAIAPIError(Exception):
    """Vertex AI API 호출 오류"""
    def __init__(self, message: str, status_code: int, error_body: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_body = error_body

async def get_shared_session():
    """공유 HTTP 세션 관리"""
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        # 연결 풀 최적화 설정
        connector = aiohttp.TCPConnector(
            limit=100,  # 최대 연결 수
            limit_per_host=20,  # 호스트당 최대 연결 수
            keepalive_timeout=30,  # Keep-alive 타임아웃
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=300, connect=10)
        _shared_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return _shared_session

async def get_cached_headers():
    """인증 헤더 캐싱"""
    global _cached_headers, _headers_cache_time
    
    # 헤더를 5분간 캐시
    if _cached_headers is None or time.time() - _headers_cache_time > 300:
        credentials = get_credentials()
        if not credentials:
            raise ConnectionAbortedError("Server authentication is not configured.")
        
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        
        _cached_headers = {
            'Authorization': f'Bearer {credentials.token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        _headers_cache_time = time.time()
    
    return _cached_headers

async def call_vertex_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Vertex AI API 호출"""
    session = await get_shared_session()
    headers = await get_cached_headers()

    model_url = Config.get_model_endpoint_url()
    async with session.post(model_url, headers=headers, json=payload) as response:
        if not response.ok:
            error_body = await response.text()
            raise VertexAIAPIError(f"HTTP error {response.status}", response.status, error_body)
        return await response.json()

async def build_triple_only_payload(user_prompt: str, triples: list) -> Dict[str, Any]:
    """Triple 기반 응답 생성을 위한 페이로드"""
    triple_text = "\n".join(triples) if triples else "관련된 triple 정보를 찾을 수 없습니다."
    instruction = f"""당신은 사용자의 질문에 대해 제공된 triple 정보만으로 답변을 작성하는 AI입니다.
아래는 triple 정보입니다:
{triple_text}
사용자 질문: {user_prompt}"""
    
    return {
        "contents": [{"role": "user", "parts": [{"text": instruction}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 8192, "topP": 0.8}
    }

async def build_summary_payload(triple_answer: str, vertex_answer: str, user_prompt: str) -> Dict[str, Any]:
    """최종 요약 응답을 위한 페이로드"""
    summary_prompt = f"""사용자의 질문: {user_prompt}

[Spanner Triple 기반 응답]
{triple_answer}

[Vertex AI Search 기반 응답]
{vertex_answer}

위 두 응답을 참고하여 최종 응답을 생성하세요."""
    
    return {
        "contents": [{"role": "user", "parts": [{"text": summary_prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 16192, "topP": 0.8}
    }