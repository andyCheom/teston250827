"""인증 관리 모듈"""
import logging
from google.cloud import spanner, storage
from google.oauth2 import service_account

from .config import Config

logger = logging.getLogger(__name__)

# 전역 인증 상태
_credentials = None
_spanner_client = None
_storage_client = None
_is_initialized = False

def get_credentials():
    """인증 정보 반환"""
    if not _is_initialized:
        raise RuntimeError("인증이 초기화되지 않았습니다. initialize_auth()를 먼저 호출하세요.")
    return _credentials

def get_spanner_client():
    """Spanner 클라이언트 반환"""
    if not _is_initialized:
        raise RuntimeError("인증이 초기화되지 않았습니다. initialize_auth()를 먼저 호출하세요.")
    return _spanner_client

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
    global _credentials, _spanner_client, _storage_client, _is_initialized
    
    try:
        logger.info(f"서비스 계정 키 파일 확인: {Config.SERVICE_ACCOUNT_PATH}")
        
        # 파일 존재 확인
        import os
        if not os.path.exists(Config.SERVICE_ACCOUNT_PATH):
            raise FileNotFoundError(f"서비스 계정 키 파일을 찾을 수 없습니다: {Config.SERVICE_ACCOUNT_PATH}")
        
        _credentials = service_account.Credentials.from_service_account_file(
            Config.SERVICE_ACCOUNT_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        project_id = _credentials.project_id
        _storage_client = storage.Client(credentials=_credentials, project=project_id)
        _spanner_client = spanner.Client(credentials=_credentials, project=project_id)
        _is_initialized = True
        
        logger.info(f"✅ 인증 성공 - project_id: {project_id}")
        return True
        
    except Exception as e:
        logger.critical(f"❌ 인증 오류: {str(e)}", exc_info=True)
        _credentials = None
        _spanner_client = None
        _storage_client = None
        _is_initialized = False
        return False