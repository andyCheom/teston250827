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
    
    if _is_initialized:
        return True

    try:
        import os
        from google.auth import default, exceptions

        project_id = Config.PROJECT_ID
        logger.info("인증 프로세스를 시작합니다...")

        # 1. gcloud auth application-default login 자격증명 시도
        try:
            logger.info("1. Application Default Credentials (ADC)를 사용하여 인증을 시도합니다.")
            creds, detected_project_id = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            
            if not creds or not creds.valid:
                logger.warning("ADC를 찾았지만 유효하지 않습니다. 서비스 계정 키 파일로 넘어갑니다.")
                raise exceptions.DefaultCredentialsError("Invalid ADC credentials.")

            logger.info("ADC 인증 정보가 유효합니다.")
            if detected_project_id:
                if project_id and detected_project_id != project_id:
                    logger.warning(f"ADC 프로젝트 ID '{detected_project_id}'가 .env의 프로젝트 ID '{project_id}'와 다릅니다. .env 설정을 우선합니다.")
                elif not project_id:
                    project_id = detected_project_id
            
            logger.info(f"Application Default Credentials를 사용하여 인증에 성공했습니다. (프로젝트: {project_id})")
            _credentials = creds

        except exceptions.DefaultCredentialsError:
            logger.info("Application Default Credentials를 찾을 수 없거나 유효하지 않습니다.")
            logger.info("2. 서비스 계정 키 파일로 인증을 시도합니다.")
            
            # 2. 서비스 계정 키 파일 시도
            service_account_path = Config.get_service_account_path()
            if not service_account_path or not os.path.exists(service_account_path):
                logger.error("서비스 계정 키 파일을 찾을 수 없습니다.")
                raise RuntimeError("인증 실패: 유효한 ADC도 없고, 서비스 계정 키 파일도 찾을 수 없습니다.")

            logger.info(f"서비스 계정 키 파일을 사용합니다: {service_account_path}")
            _credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            if not project_id:
                project_id = _credentials.project_id
            logger.info(f"서비스 계정 키 파일로 인증에 성공했습니다. (프로젝트: {project_id})")

        # 최종 인증 정보로 클라이언트 생성
        _storage_client = storage.Client(credentials=_credentials, project=project_id)
        _is_initialized = True
        logger.info(f"✅ 최종 인증 성공. Project ID: {project_id}")
        return True

    except Exception as e:
        logger.critical(f"❌ 인증 프로세스 중 심각한 오류 발생: {str(e)}", exc_info=True)
        _credentials = None
        _storage_client = None
        _is_initialized = False
        return False