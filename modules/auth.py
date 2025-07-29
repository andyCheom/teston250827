"""인증 관리 모듈"""
import logging
from google.cloud import storage
from google.oauth2 import service_account

from .config import Config

logger = logging.getLogger(__name__)

# 전역 인증 상태
_credentials = None
_storage_client = None
_is_initialized = False

def get_credentials():
    """인증 정보 반환"""
    if not _is_initialized:
        raise RuntimeError("인증이 초기화되지 않았습니다. initialize_auth()를 먼저 호출하세요.")
    return _credentials

# Spanner 클라이언트는 더 이상 사용하지 않음 - Discovery Engine 사용

def get_storage_client():
    """Storage 클라이언트 반환"""
    if not _is_initialized:
        raise RuntimeError("인증이 초기화되지 않았습니다. initialize_auth()를 먼저 호출하세요.")
    return _storage_client

def is_authenticated() -> bool:
    """인증 상태 확인"""
    return _is_initialized and _credentials is not None

def initialize_auth() -> bool:
    """Google Cloud 인증 초기화"""
    global _credentials, _storage_client, _is_initialized
    
    try:
        import os
        import json
        from google.auth import default
        
        # Cloud Run 환경에서는 기본 인증을 시도
        use_secret_manager = os.getenv('USE_SECRET_MANAGER', 'false').lower() == 'true'
        
        if use_secret_manager and 'SERVICE_ACCOUNT_JSON' in os.environ:
            # Cloud Run에서 시크릿으로 설정된 서비스 계정 JSON 사용
            logger.info("서비스 계정 JSON 시크릿 사용")
            service_account_json = os.environ['SERVICE_ACCOUNT_JSON']
            service_account_info = json.loads(service_account_json)
            
            _credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            project_id = _credentials.project_id
            
        elif os.path.exists(Config.SERVICE_ACCOUNT_PATH):
            # 로컬 개발환경에서 키 파일 사용
            logger.info(f"서비스 계정 키 파일 사용: {Config.SERVICE_ACCOUNT_PATH}")
            _credentials = service_account.Credentials.from_service_account_file(
                Config.SERVICE_ACCOUNT_PATH,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            project_id = _credentials.project_id
            
        else:
            # Cloud Run에서 기본 서비스 계정 사용 (메타데이터 서버)
            logger.info("Cloud Run 기본 서비스 계정 사용")
            _credentials, project_id = default()
        
        _storage_client = storage.Client(credentials=_credentials, project=project_id)
        _is_initialized = True
        
        logger.info(f"✅ 인증 성공 - project_id: {project_id}")
        return True
        
    except Exception as e:
        logger.critical(f"❌ 인증 오류: {str(e)}", exc_info=True)
        _credentials = None
        _storage_client = None
        _is_initialized = False
        return False