"""인증 관리 모듈"""
import logging
import threading
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account
from google.auth.credentials import Credentials

from .config import Config

logger = logging.getLogger(__name__)

# 전역 인증 상태 (스레드 안전)
_auth_lock = threading.RLock()
_credentials: Optional[Credentials] = None
_storage_client: Optional[storage.Client] = None
_is_initialized = False

def get_credentials() -> Optional[Credentials]:
    """인증 정보 반환"""
    with _auth_lock:
        if not _is_initialized:
            raise RuntimeError("인증이 초기화되지 않았습니다. initialize_auth()를 먼저 호출하세요.")
        return _credentials



# Spanner 클라이언트는 더 이상 사용하지 않음 - Discovery Engine 사용

def get_storage_client() -> Optional[storage.Client]:
    """Storage 클라이언트 반환"""
    with _auth_lock:
        if not _is_initialized:
            raise RuntimeError("인증이 초기화되지 않았습니다. initialize_auth()를 먼저 호출하세요.")
        return _storage_client

def is_authenticated() -> bool:
    """인증 상태 확인"""
    return _is_initialized and _credentials is not None

def initialize_auth() -> bool:
    """Google Cloud 인증 초기화"""
    global _credentials, _storage_client, _is_initialized
    
    with _auth_lock:
        if _is_initialized:
            return True

    try:
        import os
        from google.auth import default, exceptions

        project_id = Config.PROJECT_ID
        logger.info("인증 프로세스를 시작합니다...")

        # 1. Google Cloud 기본 자격증명 시도 (Cloud Run 환경 포함)
        try:
            logger.info("1. Google Cloud 기본 자격증명을 사용하여 인증을 시도합니다.")
            creds, detected_project_id = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            
            # Cloud Run 환경에서는 자격증명이 유효하지 않다고 표시될 수 있지만 실제로는 작동함
            logger.info(f"기본 자격증명 획득 완료. 유효성: {creds.valid if creds else 'None'}")
            
            # Cloud Run에서는 자격증명이 바로 유효하지 않을 수 있으므로 유효성 검사 건너뜀
            if creds is None:
                logger.warning("자격증명이 None입니다.")
                raise exceptions.DefaultCredentialsError("자격증명을 획득할 수 없습니다.")
            
            if detected_project_id:
                if project_id and detected_project_id != project_id:
                    logger.warning(f"감지된 프로젝트 ID '{detected_project_id}'가 설정된 프로젝트 ID '{project_id}'와 다릅니다. 설정값을 우선합니다.")
                elif not project_id:
                    project_id = detected_project_id
                    logger.info(f"프로젝트 ID를 자동 감지했습니다: {project_id}")
            
            logger.info(f"Google Cloud 기본 자격증명 인증 성공 (프로젝트: {project_id})")
            _credentials = creds

        except exceptions.DefaultCredentialsError:
            logger.info("Application Default Credentials를 찾을 수 없거나 유효하지 않습니다.")
            logger.info("2. 서비스 계정 키 파일로 인증을 시도합니다.")
            
            # 2. 서비스 계정 키 파일 시도 (로컬 개발 환경용)
            service_account_path = Config.get_service_account_path()
            if not service_account_path or not os.path.exists(service_account_path):
                logger.warning("서비스 계정 키 파일을 찾을 수 없습니다.")
                
                # Cloud Run 환경에서는 키 파일이 없어도 Metadata Service를 통해 인증 가능
                if os.getenv('K_SERVICE'):  # Cloud Run 환경 감지
                    logger.info("Cloud Run 환경이 감지되었습니다. Metadata Service를 통한 인증을 시도합니다.")
                    try:
                        # Cloud Run에서는 기본 자격증명을 다시 시도
                        creds, detected_project_id = default()
                        if creds:
                            logger.info("Cloud Run Metadata Service를 통한 인증 성공")
                            _credentials = creds
                            if not project_id and detected_project_id:
                                project_id = detected_project_id
                        else:
                            raise RuntimeError("Cloud Run 환경에서 Metadata Service 인증 실패")
                    except Exception as e:
                        logger.error(f"Cloud Run Metadata Service 인증 실패: {e}")
                        raise RuntimeError(f"Cloud Run 환경에서 인증 실패: {e}")
                else:
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