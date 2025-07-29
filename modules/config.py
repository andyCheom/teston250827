"""설정 및 환경변수 관리 모듈"""
import os
from dotenv import load_dotenv

load_dotenv()


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
    
    # Datastore 설정
    DATASTORE_ID = os.getenv('DATASTORE_ID', '')
    DATASTORE_LOCATION = os.getenv('DATASTORE_LOCATION', '')
    
    # Discovery Engine 설정
    DISCOVERY_LOCATION = os.getenv('DISCOVERY_LOCATION', 'global')
    DISCOVERY_COLLECTION = os.getenv('DISCOVERY_COLLECTION', 'default_collection')
    DISCOVERY_ENGINE_ID = os.getenv('DISCOVERY_ENGINE_ID', '')
    DISCOVERY_SERVING_CONFIG = os.getenv('DISCOVERY_SERVING_CONFIG', 'default_search')
    
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
    def get_datastore_path(cls) -> str:
        project = cls._get_required_env('PROJECT_ID')
        location = cls._get_required_env('DATASTORE_LOCATION')
        datastore = cls._get_required_env('DATASTORE_ID')
        collection = cls.DISCOVERY_COLLECTION
        return f"projects/{project}/locations/{location}/collections/{collection}/dataStores/{datastore}"
    
    # 서비스 어카운트 키 경로
    SERVICE_ACCOUNT_PATH = "keys/cheom-kdb-test1-faf5cf87a1fd.json"
    
    @classmethod
    def load_system_instruction(cls) -> str:
        """시스템 프롬프트를 파일에서 로드"""
        try:
            with open(cls.SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"시스템 프롬프트 파일을 찾을 수 없습니다: {cls.SYSTEM_PROMPT_PATH}")