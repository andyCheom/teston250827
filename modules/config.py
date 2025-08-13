"""설정 및 환경변수 관리 모듈"""
import os
import logging
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 파일 로드
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """애플리케이션 설정 클래스"""
    
    @staticmethod
    def get_env(name: str) -> str:
        """환경변수를 가져오고 없으면 예외 발생"""
        if name not in os.environ:
            raise EnvironmentError(f"❌ 환경변수 '{name}'가 설정되어 있지 않습니다.")
        return os.environ[name]

    # Google Cloud 설정
    PROJECT_ID = os.getenv('PROJECT_ID', '')
    LOCATION_ID = os.getenv('LOCATION_ID', '')
    MODEL_ID = os.getenv('MODEL_ID', '')
    
    # Datastore 설정 (다중 데이터스토어 지원)
    DATASTORE_ID = os.getenv('DATASTORE_ID', '')  # 기본 데이터스토어
    DATASTORE_LOCATION = os.getenv('DATASTORE_LOCATION', '')
    
    # 다중 데이터스토어 설정
    DATASTORES = {
        'default': {
            'id': os.getenv('DATASTORE_ID', ''),
            'location': os.getenv('DATASTORE_LOCATION', 'global'),
            'type': 'unstructured',
            'enabled': True
        }
    }
    
    # 추가 데이터스토어들 (환경변수로 동적 설정)
    @classmethod
    def get_datastores_config(cls) -> Dict[str, Dict[str, str]]:
        """환경변수에서 다중 데이터스토어 설정 로드"""
        datastores = cls.DATASTORES.copy()
        
        # DATASTORES_CONFIG 환경변수에서 JSON 형태로 추가 설정 로드
        extra_config = os.getenv('DATASTORES_CONFIG', '{}')
        try:
            import json
            extra_datastores = json.loads(extra_config)
            for name, config in extra_datastores.items():
                datastores[name] = {
                    'id': config.get('id', f"{cls.PROJECT_ID}-{name}-datastore"),
                    'location': config.get('location', 'global'),
                    'type': config.get('type', 'unstructured'),
                    'enabled': config.get('enabled', True)
                }
        except json.JSONDecodeError:
            logger.warning("DATASTORES_CONFIG 파싱 실패, 기본 설정 사용")
        
        return datastores
    
    # Discovery Engine 설정
    DISCOVERY_LOCATION = os.getenv('DISCOVERY_LOCATION', 'global')
    DISCOVERY_COLLECTION = os.getenv('DISCOVERY_COLLECTION', 'default_collection')
    DISCOVERY_ENGINE_ID = os.getenv('DISCOVERY_ENGINE_ID', '')
    DISCOVERY_SERVING_CONFIG = os.getenv('DISCOVERY_SERVING_CONFIG', 'default_search')
    
    # Service Account 설정
    SERVICE_ACCOUNT_EMAIL = os.getenv('SERVICE_ACCOUNT_EMAIL', '')
    
    # Storage 설정
    STORAGE_BUCKET = os.getenv('STORAGE_BUCKET', '')
    CONVERSATION_BUCKET = os.getenv('CONVERSATION_BUCKET', '')
    
    # Spanner 설정은 더 이상 사용하지 않음 - Discovery Engine 사용
    
    # 프롬프트 설정
    SYSTEM_PROMPT_PATH = os.getenv('SYSTEM_PROMPT_PATH', 'prompt/prompt.txt')
    
    @classmethod
    def _get_required_env(cls, name: str) -> str:
        """필수 환경변수 확인 및 반환"""
        value = os.getenv(name)
        if not value:
            raise EnvironmentError(f"❌ 환경변수 '{name}'가 설정되어 있지 않습니다.")
        return value
    
    # 파생 설정 (실제 사용 시점에 생성)
    @classmethod
    def get_api_endpoint(cls) -> str:
        location = cls._get_required_env('LOCATION_ID')
        return f"https://{location}-aiplatform.googleapis.com"
    
    @classmethod 
    def get_model_endpoint_url(cls) -> str:
        project = cls._get_required_env('PROJECT_ID')
        location = cls._get_required_env('LOCATION_ID')
        model = cls._get_required_env('MODEL_ID')
        api_endpoint = cls.get_api_endpoint()
        return f"{api_endpoint}/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent"
    
    @classmethod
    def get_datastore_path(cls, datastore_name: str = 'default') -> str:
        """지정된 데이터스토어의 경로 반환"""
        datastores = cls.get_datastores_config()
        if datastore_name not in datastores:
            raise ValueError(f"데이터스토어 '{datastore_name}'을 찾을 수 없습니다")
        
        datastore_config = datastores[datastore_name]
        project = cls._get_required_env('PROJECT_ID')
        location = datastore_config['location']
        datastore_id = datastore_config['id']
        collection = cls.DISCOVERY_COLLECTION
        
        return f"projects/{project}/locations/{location}/collections/{collection}/dataStores/{datastore_id}"
    
    @classmethod
    def get_active_datastores(cls) -> Dict[str, str]:
        """활성화된 데이터스토어들의 이름과 경로 반환"""
        datastores = cls.get_datastores_config()
        return {
            name: cls.get_datastore_path(name)
            for name, config in datastores.items()
            if config.get('enabled', True)
        }
    

    
    # 서비스 어카운트 키 경로 (동적 검색)
    @classmethod
    def get_service_account_path(cls) -> Optional[str]:
        """keys/ 디렉토리에서 서비스 계정 키 파일을 자동으로 찾기"""
        import glob
        
        # 환경변수로 직접 지정된 경우
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            if os.path.exists(path):
                logger.info(f"환경변수에서 서비스 계정 키 파일 사용: {path}")
                return path
            else:
                logger.warning(f"환경변수의 서비스 계정 키 파일이 존재하지 않음: {path}")
        
        # keys/ 디렉토리에서 JSON 파일 찾기
        key_patterns = [
            "keys/*service*.json",
            "keys/*graphrag*.json", 
            "keys/*.json"
        ]
        
        for pattern in key_patterns:
            try:
                files = glob.glob(pattern)
                if files:
                    # 가장 최근 파일 사용
                    latest_file = max(files, key=os.path.getctime)
                    logger.info(f"패턴 '{pattern}'에서 서비스 계정 키 파일 발견: {latest_file}")
                    return latest_file
            except Exception as e:
                logger.warning(f"패턴 '{pattern}' 검색 중 오류: {e}")
        
        # 기본 경로들 시도
        default_paths = [
            "keys/service-account.json",
            "keys/graphrag-service.json"
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                logger.info(f"기본 경로에서 서비스 계정 키 파일 발견: {path}")
                return path
        
        logger.warning("서비스 계정 키 파일을 찾을 수 없음")
        return None
    
    # 동적 프로퍼티로 설정
    @property
    def SERVICE_ACCOUNT_PATH(self):
        return self.get_service_account_path()
    
    @classmethod
    def load_system_instruction(cls) -> str:
        """시스템 프롬프트를 파일에서 로드"""
        try:
            prompt_path = Path(cls.SYSTEM_PROMPT_PATH)
            if not prompt_path.exists():
                logger.warning(f"시스템 프롬프트 파일이 존재하지 않음: {cls.SYSTEM_PROMPT_PATH}")
                return "기본 시스템 프롬프트"
            
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.warning("시스템 프롬프트 파일이 비어있음")
                    return "기본 시스템 프롬프트"
                
                logger.info(f"시스템 프롬프트 로드 완료: {len(content)}자")
                return content
                
        except FileNotFoundError:
            logger.error(f"시스템 프롬프트 파일을 찾을 수 없습니다: {cls.SYSTEM_PROMPT_PATH}")
            return "기본 시스템 프롬프트"
        except Exception as e:
            logger.error(f"시스템 프롬프트 로드 중 오류: {e}")
            return "기본 시스템 프롬프트"
    
    @staticmethod
    def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
        """환경변수 안전하게 가져오기"""
        value = os.getenv(name, default)
        if value is None and default is None:
            logger.warning(f"환경변수 '{name}'이 설정되지 않음")
        return value
    
    @classmethod
    def validate_config(cls) -> bool:
        """필수 설정값들이 올바르게 설정되었는지 검증"""
        required_vars = ['PROJECT_ID', 'LOCATION_ID', 'DISCOVERY_ENGINE_ID']
        missing_vars = []
        
        for var in required_vars:
            value = getattr(cls, var, None)
            if not value:
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"필수 환경변수가 누락됨: {', '.join(missing_vars)}")
            return False
        
        logger.info("필수 설정값 검증 완료")
        return True