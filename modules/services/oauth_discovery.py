"""OAuth 2.0을 사용한 Discovery Engine 접근"""
import os
import json
import aiohttp
from typing import Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import logging

logger = logging.getLogger(__name__)

# OAuth 2.0 설정 (실제 운영에서는 환경변수로 관리)
OAUTH_CONFIG = {
    "web": {
        "client_id": "your-oauth-client-id.googleusercontent.com",
        "client_secret": "your-oauth-client-secret", 
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080/oauth/callback"]
    }
}

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

class OAuthDiscoveryEngine:
    """OAuth 2.0 인증을 사용하는 Discovery Engine 클라이언트"""
    
    def __init__(self):
        self.credentials = None
        self.session = None
    
    def get_auth_url(self) -> str:
        """OAuth 2.0 인증 URL 생성"""
        flow = Flow.from_client_config(
            OAUTH_CONFIG, 
            scopes=SCOPES,
            redirect_uri=OAUTH_CONFIG["web"]["redirect_uris"][0]
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url
    
    def exchange_code_for_token(self, code: str) -> bool:
        """인증 코드를 액세스 토큰으로 교환"""
        try:
            flow = Flow.from_client_config(
                OAUTH_CONFIG, 
                scopes=SCOPES,
                redirect_uri=OAUTH_CONFIG["web"]["redirect_uris"][0]
            )
            flow.fetch_token(code=code)
            self.credentials = flow.credentials
            return True
        except Exception as e:
            logger.error(f"OAuth 토큰 교환 실패: {e}")
            return False
    
    async def search_with_oauth(self, query: str) -> Dict[str, Any]:
        """OAuth 인증을 사용한 Discovery Engine 검색"""
        if not self.credentials:
            raise ValueError("OAuth 인증이 필요합니다. get_auth_url()로 먼저 인증하세요.")
        
        # 토큰 갱신 확인
        if self.credentials.expired:
            self.credentials.refresh(Request())
        
        url = "https://discoveryengine.googleapis.com/v1alpha/projects/580360941782/locations/global/collections/default_collection/engines/test_1753406039510/servingConfigs/default_search:search"
        
        payload = {
            "query": query,
            "pageSize": 10,
            "session": "projects/580360941782/locations/global/collections/default_collection/engines/test_1753406039510/sessions/-",
            "spellCorrectionSpec": {"mode": "AUTO"},
            "languageCode": "ko",
            "userInfo": {"timeZone": "Asia/Seoul"},
            "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}
        }
        
        headers = {
            'Authorization': f'Bearer {self.credentials.token}',
            'Content-Type': 'application/json'
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.post(url, headers=headers, json=payload) as response:
            if not response.ok:
                error_body = await response.text()
                logger.error(f"OAuth Discovery Engine 검색 실패: {response.status} - {error_body}")
                raise Exception(f"Search failed: {response.status}")
            
            return await response.json()

# 전역 OAuth 클라이언트 인스턴스
oauth_client = OAuthDiscoveryEngine()

async def get_oauth_auth_url() -> str:
    """OAuth 인증 URL 반환"""
    return oauth_client.get_auth_url()

async def handle_oauth_callback(code: str) -> bool:
    """OAuth 콜백 처리"""
    return oauth_client.exchange_code_for_token(code)

async def search_with_oauth(query: str) -> Dict[str, Any]:
    """OAuth 인증을 사용한 검색"""
    return await oauth_client.search_with_oauth(query)