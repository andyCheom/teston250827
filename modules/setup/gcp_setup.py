"""Google Cloud Platform 리소스 자동 설정 모듈"""

import logging
import os
import time
from typing import Dict, List, Optional, Any
from google.cloud import storage
from google.cloud import discoveryengine_v1beta
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json

from ..config import Config
from ..auth import get_credentials

logger = logging.getLogger(__name__)

class GCPSetupManager:
    """GCP 리소스 자동 설정 관리자"""
    
    def __init__(self):
        self.credentials = None
        self.project_id = None
        self.storage_client = None
        self.service_management = None
        self.discovery_client = None
        
    def initialize(self) -> bool:
        """GCP 클라이언트 초기화"""
        try:
            # 먼저 인증 초기화
            from ..auth import initialize_auth
            if not initialize_auth():
                logger.error("❌ GCP 인증 초기화에 실패했습니다")
                return False
                
            self.credentials = get_credentials()
            if not self.credentials:
                logger.error("❌ GCP 인증 정보를 가져올 수 없습니다")
                return False
                
            self.project_id = Config.PROJECT_ID
            if not self.project_id:
                logger.error("❌ PROJECT_ID 환경변수가 설정되지 않았습니다")
                return False
                
            # 클라이언트 초기화
            self.storage_client = storage.Client(credentials=self.credentials, project=self.project_id)
            self.service_management = build('servicemanagement', 'v1', credentials=self.credentials)
            self.discovery_client = discoveryengine_v1beta.DataStoreServiceClient(credentials=self.credentials)
            
            logger.info(f"✅ GCP 클라이언트 초기화 완료 - Project: {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ GCP 클라이언트 초기화 실패: {e}")
            return False
    
    async def enable_required_apis(self) -> bool:
        """필요한 GCP API 활성화"""
        required_apis = [
            'discoveryengine.googleapis.com',
            'storage-api.googleapis.com',
            'storage-component.googleapis.com', 
            'cloudbuild.googleapis.com',
            'run.googleapis.com',
            'firebase.googleapis.com',
            'firebasehosting.googleapis.com',
            'firestore.googleapis.com',
            'appengine.googleapis.com',  # Firestore 기본 데이터베이스 생성에 필요
            'cloudresourcemanager.googleapis.com',
            'iam.googleapis.com',
            'cloudfunctions.googleapis.com',
        ]
        
        logger.info("📡 필요한 API 활성화 시작...")
        
        try:
            service_usage = build('serviceusage', 'v1', credentials=self.credentials)
            
            for api in required_apis:
                try:
                    # API 상태 확인
                    service_name = f"projects/{self.project_id}/services/{api}"
                    service = service_usage.services().get(name=service_name).execute()
                    
                    if service.get('state') == 'ENABLED':
                        logger.info(f"✅ {api} - 이미 활성화됨")
                        continue
                    
                    # API 활성화
                    logger.info(f"🔄 {api} 활성화 중...")
                    operation = service_usage.services().enable(
                        name=service_name,
                        body={}
                    ).execute()
                    
                    # 활성화 완료 대기 (최대 60초)
                    for _ in range(12):
                        time.sleep(5)
                        updated_service = service_usage.services().get(name=service_name).execute()
                        if updated_service.get('state') == 'ENABLED':
                            logger.info(f"✅ {api} 활성화 완료")
                            break
                    else:
                        logger.warning(f"⚠️ {api} 활성화 시간 초과")
                        
                except Exception as e:
                    logger.warning(f"⚠️ {api} 활성화 실패: {e}")
                    
            logger.info("✅ API 활성화 프로세스 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ API 활성화 실패: {e}")
            return False
    
    def create_storage_bucket(self, bucket_name: str, location: str = "asia-northeast3") -> bool:
        """Cloud Storage 버킷 생성"""
        try:
            # 버킷 존재 확인
            try:
                bucket = self.storage_client.get_bucket(bucket_name)
                logger.info(f"✅ 버킷 '{bucket_name}' 이미 존재함")
                return True
            except Exception:
                pass  # 버킷이 없으면 생성
            
            # 버킷 생성
            logger.info(f"🔄 버킷 '{bucket_name}' 생성 중...")
            bucket = self.storage_client.bucket(bucket_name)
            bucket.location = location
            
            # 버킷 생성 및 설정
            bucket = self.storage_client.create_bucket(bucket, location=location)
            
            # CORS 설정
            bucket.cors = [
                {
                    "origin": ["*"],
                    "method": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "responseHeader": ["Content-Type", "Authorization"],
                    "maxAgeSeconds": 3600
                }
            ]
            bucket.patch()
            
            # 공개 읽기 권한 설정 (선택적)
            policy = bucket.get_iam_policy(requested_policy_version=3)
            policy.bindings.append({
                "role": "roles/storage.objectViewer",
                "members": {"allUsers"}
            })
            bucket.set_iam_policy(policy)
            
            logger.info(f"✅ 버킷 '{bucket_name}' 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 버킷 생성 실패: {e}")
            return False
    
    def create_discovery_datastore(self, 
                                 datastore_id: str,
                                 display_name: str = None,
                                 location: str = "global") -> bool:
        """Discovery Engine 데이터스토어 생성"""
        try:
            if not display_name:
                display_name = f"{datastore_id.replace('-', ' ').title()} DataStore"
            
            # 데이터스토어 존재 확인
            try:
                parent = f"projects/{self.project_id}/locations/{location}/collections/default_collection"
                datastore_name = f"{parent}/dataStores/{datastore_id}"
                
                datastore = self.discovery_client.get_data_store(name=datastore_name)
                logger.info(f"✅ 데이터스토어 '{datastore_id}' 이미 존재함")
                return True
                
            except Exception:
                pass  # 데이터스토어가 없으면 생성
            
            # 데이터스토어 생성
            logger.info(f"🔄 데이터스토어 '{datastore_id}' 생성 중...")
            
            parent = f"projects/{self.project_id}/locations/{location}/collections/default_collection"
            
            # 데이터스토어 설정
            data_store = discoveryengine_v1beta.DataStore(
                display_name=display_name,
                industry_vertical=discoveryengine_v1beta.IndustryVertical.GENERIC,
                solution_types=[discoveryengine_v1beta.SolutionType.SOLUTION_TYPE_SEARCH],
                content_config=discoveryengine_v1beta.DataStore.ContentConfig.CONTENT_REQUIRED,
            )
            
            # 데이터스토어 생성 요청
            operation = self.discovery_client.create_data_store(
                parent=parent,
                data_store=data_store,
                data_store_id=datastore_id
            )
            
            # Operation 이름 안전하게 가져오기
            operation_name = getattr(operation, 'name', str(operation))
            logger.info(f"🔄 데이터스토어 생성 중... (Operation: {operation_name})")
            
            # 생성 완료 대기 (최대 10분)
            for i in range(60):
                time.sleep(10)
                try:
                    datastore = self.discovery_client.get_data_store(name=f"{parent}/dataStores/{datastore_id}")
                    logger.info(f"✅ 데이터스토어 '{datastore_id}' 생성 완료")
                    return True
                except Exception:
                    if i % 6 == 0:  # 1분마다 로그
                        logger.info(f"🔄 데이터스토어 생성 대기 중... ({i//6 + 1}/10분)")
                    continue
            
            logger.warning(f"⚠️ 데이터스토어 생성 시간 초과 - 백그라운드에서 계속 진행됩니다")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터스토어 생성 실패: {e}")
            return False
    
    def create_discovery_engine(self, 
                              engine_id: str,
                              datastore_ids: List[str],  # 다중 데이터스토어 지원
                              display_name: str = None,
                              location: str = "global") -> bool:
        """Discovery Engine 생성"""
        try:
            if not display_name:
                display_name = f"{engine_id.replace('-', ' ').title()} Engine"
            
            # 엔진 존재 확인
            try:
                parent = f"projects/{self.project_id}/locations/{location}/collections/default_collection"
                engine_name = f"{parent}/engines/{engine_id}"
                
                engine_client = discoveryengine_v1beta.EngineServiceClient(credentials=self.credentials)
                engine = engine_client.get_engine(name=engine_name)
                logger.info(f"✅ Discovery Engine '{engine_id}' 이미 존재함")
                return True
                
            except Exception:
                pass  # 엔진이 없으면 생성
            
            # 엔진 생성
            logger.info(f"🔄 Discovery Engine '{engine_id}' 생성 중...")
            logger.info(f"연결할 데이터스토어: {datastore_ids}")
            
            parent = f"projects/{self.project_id}/locations/{location}/collections/default_collection"
            
            # 데이터스토어 존재 확인
            validated_datastore_ids = []
            for ds_id in datastore_ids:
                datastore_path = f"{parent}/dataStores/{ds_id}"
                try:
                    # 데이터스토어 존재 확인
                    datastore = self.discovery_client.get_data_store(name=datastore_path)
                    validated_datastore_ids.append(ds_id)
                    logger.info(f"✅ 데이터스토어 '{ds_id}' 확인됨")
                except Exception as e:
                    logger.warning(f"⚠️ 데이터스토어 '{ds_id}' 확인 실패: {e}")
                    logger.info("데이터스토어가 존재하지 않거나 접근할 수 없습니다")
            
            if not validated_datastore_ids:
                logger.error("❌ 유효한 데이터스토어가 없습니다")
                return False
            
            logger.info(f"최종 연결 데이터스토어: {validated_datastore_ids}")
            
            # 엔진 설정 (다중 데이터스토어 지원을 위한 industry_vertical 설정)
            engine = discoveryengine_v1beta.Engine(
                display_name=display_name,
                solution_type=discoveryengine_v1beta.SolutionType.SOLUTION_TYPE_SEARCH,
                industry_vertical=discoveryengine_v1beta.IndustryVertical.GENERIC,  # 다중 데이터스토어 지원을 위해 필요
                search_engine_config=discoveryengine_v1beta.Engine.SearchEngineConfig(
                    search_tier=discoveryengine_v1beta.SearchTier.SEARCH_TIER_STANDARD,
                ),
                data_store_ids=validated_datastore_ids  # 다중 데이터스토어 연결
            )
            
            # 엔진 생성 요청
            engine_client = discoveryengine_v1beta.EngineServiceClient(credentials=self.credentials)
            operation = engine_client.create_engine(
                parent=parent,
                engine=engine,
                engine_id=engine_id
            )
            
            # Operation 이름 안전하게 가져오기
            operation_name = getattr(operation, 'name', str(operation))
            logger.info(f"🔄 엔진 생성 중... (Operation: {operation_name})")
            
            # 생성 완료 대기 (최대 10분)
            for i in range(60):
                time.sleep(10)
                try:
                    engine = engine_client.get_engine(name=f"{parent}/engines/{engine_id}")
                    logger.info(f"✅ Discovery Engine '{engine_id}' 생성 완료")
                    return True
                except Exception:
                    if i % 6 == 0:  # 1분마다 로그
                        logger.info(f"🔄 엔진 생성 대기 중... ({i//6 + 1}/10분)")
                    continue
            
            logger.warning(f"⚠️ 엔진 생성 시간 초과 - 백그라운드에서 계속 진행됩니다")
            return True
            
        except Exception as e:
            logger.error(f"❌ Discovery Engine 생성 실패: {e}")
            return False
    
    def create_service_account(self, 
                             service_account_id: str,
                             display_name: str = None,
                             description: str = None) -> Optional[str]:
        """서비스 계정 생성 및 키 파일 다운로드"""
        try:
            if not display_name:
                display_name = f"{service_account_id.replace('-', ' ').title()} Service Account"
            
            if not description:
                description = f"GraphRAG 프로젝트용 서비스 계정"
            
            # IAM 클라이언트
            iam_service = build('iam', 'v1', credentials=self.credentials)
            
            service_account_email = f"{service_account_id}@{self.project_id}.iam.gserviceaccount.com"
            
            # 서비스 계정 존재 확인
            try:
                existing_sa = iam_service.projects().serviceAccounts().get(
                    name=f"projects/{self.project_id}/serviceAccounts/{service_account_email}"
                ).execute()
                logger.info(f"✅ 서비스 계정 '{service_account_id}' 이미 존재함")
            except Exception:
                # 서비스 계정 생성
                logger.info(f"🔄 서비스 계정 '{service_account_id}' 생성 중...")
                
                service_account = {
                    'accountId': service_account_id,
                    'serviceAccount': {
                        'displayName': display_name,
                        'description': description
                    }
                }
                
                iam_service.projects().serviceAccounts().create(
                    name=f"projects/{self.project_id}",
                    body=service_account
                ).execute()
                
                logger.info(f"✅ 서비스 계정 '{service_account_id}' 생성 완료")
            
            # 필요한 역할 부여
            required_roles = [
                # Discovery Engine
                'roles/discoveryengine.editor',
                
                # Cloud Storage
                'roles/storage.admin',
                'roles/storage.objectCreator',
                'roles/storage.objectViewer',
                
                # Firestore / Datastore
                'roles/datastore.owner',
                'roles/datastore.viewer',
                'roles/datastore.user',

                # Firebase & Firestore
                'roles/firebase.admin',
                'roles/firebasehosting.admin',
                'roles/firebaseauth.admin',

                # App Engine (for Firestore creation)
                'roles/appengine.appAdmin',
                'roles/appengine.appCreator',
                
                # AI Platform & Vertex AI
                'roles/aiplatform.admin',
                'roles/aiplatform.user',
                'roles/ml.admin',
                'roles/ml.developer',
                
                # Project & Service Management
                'roles/resourcemanager.projectIamAdmin',
                'roles/serviceusage.serviceUsageAdmin',
                
                # Cloud Run
                'roles/run.admin',
                'roles/run.invoker',
                
                # Cloud Build (CI/CD)
                'roles/cloudbuild.builds.builder',
                'roles/source.reader',
                
                # Artifact Registry (CI/CD)
                'roles/artifactregistry.writer',
                'roles/artifactregistry.reader',
                
                # IAM (for service account management itself)
                'roles/iam.serviceAccountAdmin',
                'roles/iam.serviceAccountUser',
                'roles/iam.serviceAccountTokenCreator',
                
                # Logging & Monitoring
                'roles/logging.logWriter',
                'roles/monitoring.metricWriter',
                
                # Networking
                'roles/compute.networkUser'
            ]
            
            resource_manager = build('cloudresourcemanager', 'v1', credentials=self.credentials)
            
            for role in required_roles:
                try:
                    # 현재 IAM 정책 가져오기
                    policy = resource_manager.projects().getIamPolicy(
                        resource=self.project_id
                    ).execute()
                    
                    # 바인딩 추가
                    binding_exists = False
                    for binding in policy.get('bindings', []):
                        if binding['role'] == role:
                            if f"serviceAccount:{service_account_email}" not in binding['members']:
                                binding['members'].append(f"serviceAccount:{service_account_email}")
                            binding_exists = True
                            break
                    
                    if not binding_exists:
                        policy.setdefault('bindings', []).append({
                            'role': role,
                            'members': [f"serviceAccount:{service_account_email}"]
                        })
                    
                    # 정책 업데이트
                    resource_manager.projects().setIamPolicy(
                        resource=self.project_id,
                        body={'policy': policy}
                    ).execute()
                    
                    logger.info(f"✅ 역할 '{role}' 부여 완료")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 역할 '{role}' 부여 실패: {e}")
            
            # 키 파일 생성 시도 (개선된 로직)
            logger.info("🔄 서비스 계정 키 파일 생성 중...")
            
            max_retries = 3
            retry_count = 0
            key_file_path = None
            
            while retry_count < max_retries:
                try:
                    # 서비스 계정 상태 확인
                    service_account_resource = f"projects/{self.project_id}/serviceAccounts/{service_account_email}"
                    
                    sa_info = iam_service.projects().serviceAccounts().get(
                        name=service_account_resource
                    ).execute()
                    
                    if sa_info.get('disabled', False):
                        logger.warning("⚠️ 서비스 계정이 비활성화 상태입니다. 활성화 중...")
                        iam_service.projects().serviceAccounts().enable(
                            name=service_account_resource
                        ).execute()
                        import time
                        time.sleep(10)
                        continue
                    
                    # 키 생성 시도
                    key_creation_body = {
                        'privateKeyType': 'TYPE_GOOGLE_CREDENTIALS_FILE',
                        'keyAlgorithm': 'KEY_ALG_RSA_2048'
                    }
                    
                    key = iam_service.projects().serviceAccounts().keys().create(
                        name=service_account_resource,
                        body=key_creation_body
                    ).execute()
                    
                    # 키 디렉토리 생성
                    os.makedirs("keys", exist_ok=True)
                    
                    # 키 파일 저장
                    key_file_path = f"keys/{service_account_id}-{self.project_id}.json"
                    
                    import base64
                    key_data = base64.b64decode(key['privateKeyData']).decode('utf-8')
                    
                    with open(key_file_path, 'w', encoding='utf-8') as f:
                        f.write(key_data)
                    
                    # 파일 권한 설정 (읽기 전용)
                    import stat
                    os.chmod(key_file_path, stat.S_IRUSR | stat.S_IWUSR)
                    
                    logger.info(f"✅ 서비스 계정 키 파일 저장: {key_file_path}")
                    return key_file_path
                    
                except Exception as key_error:
                    retry_count += 1
                    error_msg = str(key_error)
                    
                    if "Precondition check failed" in error_msg:
                        if retry_count < max_retries:
                            wait_time = 10  # 30초에서 10초로 단축
                            logger.warning(f"⚠️ 사전 조건 확인 실패, {wait_time}초 후 재시도... ({retry_count}/{max_retries})")
                            logger.info("💡 Ctrl+C를 눌러 건너뛸 수 있습니다")
                            import time
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error("❌ 사전 조건 확인 지속 실패")
                            logger.info("💡 해결 방법:")
                            logger.info("   1. 서비스 계정이 완전히 생성될 때까지 대기")
                            logger.info("   2. IAM API가 활성화되어 있는지 확인")
                            logger.info("   3. 권한 전파 완료 대기 (최대 5분)")
                            logger.info(f"   4. 수동 키 생성: gcloud iam service-accounts keys create keys/{service_account_id}-{self.project_id}.json --iam-account={service_account_email}")
                            break
                    
                    elif "Permission 'iam.serviceAccountKeys.create' denied" in error_msg:
                        logger.warning(f"⚠️ 서비스 계정 키 생성 권한이 없습니다")
                        logger.info("💡 해결 방법:")
                        logger.info("   1. GCP 콘솔 → IAM & Admin → IAM")
                        logger.info(f"   2. 현재 사용자에게 'Service Account Key Admin' 역할 추가")
                        logger.info("   3. 또는 프로젝트 소유자가 다음 명령 실행:")
                        logger.info(f"      gcloud projects add-iam-policy-binding {self.project_id} \\")
                        logger.info(f"        --member=\"user:YOUR_EMAIL\" \\")
                        logger.info(f"        --role=\"roles/iam.serviceAccountKeyAdmin\"")
                        break
                    
                    elif "Service account does not exist" in error_msg:
                        logger.error("❌ 서비스 계정이 존재하지 않습니다")
                        break
                    
                    else:
                        if retry_count < max_retries:
                            logger.warning(f"⚠️ 키 생성 실패, 재시도 중... ({retry_count}/{max_retries}): {error_msg}")
                            import time
                            time.sleep(15)
                            continue
                        else:
                            logger.error(f"❌ 서비스 계정 키 생성 최종 실패: {error_msg}")
                            break
            
            # 키 생성 실패 시 안내
            logger.info("📝 서비스 계정은 생성되었지만 키 파일 생성에 실패했습니다.")
            logger.info("   다음 방법으로 수동 생성 가능:")
            logger.info(f"   gcloud iam service-accounts keys create keys/{service_account_id}-{self.project_id}.json \\")
            logger.info(f"     --iam-account={service_account_email}")
            logger.info(f"📄 생성된 서비스 계정: {service_account_email}")
            return None
            
        except Exception as e:
            logger.error(f"❌ 서비스 계정 생성 실패: {e}")
            return None
    
    def validate_setup(self) -> Dict[str, bool]:
        """설정 완료 상태 검증"""
        results = {}
        
        try:
            # Storage 버킷 확인
            bucket_name = Config.STORAGE_BUCKET or f"{self.project_id}-graphrag-storage"
            try:
                self.storage_client.get_bucket(bucket_name)
                results['storage_bucket'] = True
            except Exception:
                results['storage_bucket'] = False
            
            # Discovery Engine 데이터스토어 확인
            try:
                datastore_id = Config.DATASTORE_ID or "graphrag-datastore"
                parent = f"projects/{self.project_id}/locations/global/collections/default_collection"
                datastore_name = f"{parent}/dataStores/{datastore_id}"
                
                self.discovery_client.get_data_store(name=datastore_name)
                results['discovery_datastore'] = True
            except Exception:
                results['discovery_datastore'] = False
            
            # Discovery Engine 확인
            try:
                engine_id = Config.DISCOVERY_ENGINE_ID or "graphrag-engine"
                parent = f"projects/{self.project_id}/locations/global/collections/default_collection"
                engine_name = f"{parent}/engines/{engine_id}"
                
                engine_client = discoveryengine_v1beta.EngineServiceClient(credentials=self.credentials)
                engine_client.get_engine(name=engine_name)
                results['discovery_engine'] = True
            except Exception:
                results['discovery_engine'] = False
            
            logger.info(f"✅ 설정 검증 완료: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ 설정 검증 실패: {e}")
            return {}
    
    def create_cloud_run_service(self, 
                               service_name: str,
                               image_name: str,
                               location: str = "asia-northeast3",
                               cpu: str = "1",
                               memory: str = "2Gi",
                               max_instances: int = 100,
                               env_vars: Optional[Dict[str, str]] = None) -> bool:
        """Cloud Run 서비스 생성"""
        try:
            # Cloud Run Admin API 클라이언트
            cloudrun_service = build('run', 'v1', credentials=self.credentials)
            
            # 서비스 존재 확인
            try:
                service_path = f"projects/{self.project_id}/locations/{location}/services/{service_name}"
                existing_service = cloudrun_service.projects().locations().services().get(
                    name=service_path
                ).execute()
                logger.info(f"✅ Cloud Run 서비스 '{service_name}' 이미 존재함")
                return True
            except Exception:
                pass  # 서비스가 없으면 생성
            
            logger.info(f"🔄 Cloud Run 서비스 '{service_name}' 생성 중...")
            
            # 환경 변수 설정
            environment_vars = []
            if env_vars:
                for key, value in env_vars.items():
                    environment_vars.append({
                        'name': key,
                        'value': value
                    })
            
            # 서비스 설정
            service_spec = {
                'apiVersion': 'serving.knative.dev/v1',
                'kind': 'Service',
                'metadata': {
                    'name': service_name,
                    'annotations': {
                        'run.googleapis.com/ingress': 'all',
                        'run.googleapis.com/ingress-status': 'all'
                    }
                },
                'spec': {
                    'template': {
                        'metadata': {
                            'annotations': {
                                'autoscaling.knative.dev/maxScale': str(max_instances),
                                'run.googleapis.com/cpu-throttling': 'false',
                                'run.googleapis.com/execution-environment': 'gen2'
                            }
                        },
                        'spec': {
                            'containerConcurrency': 80,
                            'timeoutSeconds': 300,
                            'containers': [{
                                'image': image_name,
                                'ports': [{
                                    'name': 'http1',
                                    'containerPort': 8000
                                }],
                                'env': environment_vars,
                                'resources': {
                                    'limits': {
                                        'cpu': cpu,
                                        'memory': memory
                                    }
                                }
                            }]
                        }
                    },
                    'traffic': [{
                        'percent': 100,
                        'latestRevision': True
                    }]
                }
            }
            
            # 서비스 생성
            parent = f"projects/{self.project_id}/locations/{location}"
            operation = cloudrun_service.projects().locations().services().create(
                parent=parent,
                body=service_spec
            ).execute()
            
            logger.info(f"🔄 Cloud Run 서비스 배포 중... (Operation: {operation.get('name', 'N/A')})")
            
            # 배포 완료 대기 (최대 10분)
            for i in range(60):
                time.sleep(10)
                try:
                    service_path = f"projects/{self.project_id}/locations/{location}/services/{service_name}"
                    service = cloudrun_service.projects().locations().services().get(
                        name=service_path
                    ).execute()
                    
                    # 서비스 상태 확인
                    conditions = service.get('status', {}).get('conditions', [])
                    ready_condition = next((c for c in conditions if c.get('type') == 'Ready'), None)
                    
                    if ready_condition and ready_condition.get('status') == 'True':
                        service_url = service.get('status', {}).get('url', '')
                        logger.info(f"✅ Cloud Run 서비스 '{service_name}' 배포 완료")
                        logger.info(f"🔗 서비스 URL: {service_url}")
                        return True
                        
                except Exception as deploy_error:
                    if i % 6 == 0:  # 1분마다 로그
                        logger.info(f"🔄 서비스 배포 대기 중... ({i//6 + 1}/10분)")
                    continue
            
            logger.warning(f"⚠️ Cloud Run 서비스 배포 시간 초과")
            return False
            
        except Exception as e:
            logger.error(f"❌ Cloud Run 서비스 생성 실패: {e}")
            return False
    
    def create_firestore_database(self, location_id: str = "asia-northeast1") -> bool:
        """Firestore 네이티브 데이터베이스 생성"""
        try:
            logger.info("🔄 Firestore 데이터베이스 생성 중...")
            
            # Firestore Admin API 클라이언트
            firestore_admin = build('firestore', 'v1', credentials=self.credentials)
            
            # 기본 데이터베이스 존재 확인
            try:
                database_name = f"projects/{self.project_id}/databases/(default)"
                database = firestore_admin.projects().databases().get(name=database_name).execute()
                
                if database.get('type') == 'FIRESTORE_NATIVE':
                    logger.info("✅ Firestore 네이티브 데이터베이스가 이미 존재합니다")
                    return True
                elif database.get('type') == 'DATASTORE_MODE':
                    logger.warning("⚠️ 프로젝트에 Datastore 모드 데이터베이스가 존재합니다. Firestore로 마이그레이션이 필요할 수 있습니다.")
                    return False
                    
            except Exception:
                pass  # 데이터베이스가 없으면 생성
            
            # Firestore 네이티브 데이터베이스 생성
            logger.info(f"🔄 새로운 Firestore 데이터베이스 생성 중... (위치: {location_id})")
            
            database_config = {
                'type': 'FIRESTORE_NATIVE',
                'locationId': location_id,
                'concurrencyMode': 'OPTIMISTIC',
                'appEngineIntegrationMode': 'DISABLED'
            }
            
            operation = firestore_admin.projects().databases().create(
                parent=f"projects/{self.project_id}",
                databaseId='(default)',
                body=database_config
            ).execute()
            
            operation_name = operation.get('name')
            logger.info(f"🔄 Firestore 데이터베이스 생성 중... (Operation: {operation_name})")
            
            # ✅ Operation 상태 확인 (올바른 방식)
            for i in range(60):  # 최대 5분
                time.sleep(5)
                try:
                    # Operation 상태 확인
                    op_result = firestore_admin.projects().databases().operations().get(
                        name=operation_name
                    ).execute()
                    
                    # Operation 완료 확인
                    if op_result.get('done'):
                        if 'error' in op_result:
                            error = op_result['error']
                            error_msg = error.get('message', '알 수 없는 오류')
                            logger.error(f"❌ Firestore 데이터베이스 생성 실패: {error_msg}")
                            logger.error(f"   에러 코드: {error.get('code')}")
                            
                            # App Engine 관련 에러인지 확인
                            if "app does not exist" in error_msg.lower() or "enable the app engine admin api" in error_msg.lower():
                                logger.info("💡 App Engine 애플리케이션 생성을 시도합니다...")
                                return self._create_app_engine_application(location_id)
                            
                            return False
                        else:
                            # 성공 시 최종 데이터베이스 상태 확인
                            database_name = f"projects/{self.project_id}/databases/(default)"
                            database = firestore_admin.projects().databases().get(name=database_name).execute()
                            
                            if database.get('state') == 'ACTIVE':
                                logger.info("✅ Firestore 데이터베이스 생성 완료")
                                return True
                            else:
                                logger.warning(f"⚠️ Operation 완료되었지만 데이터베이스 상태가 예상과 다름: {database.get('state')}")
                                return False
                    
                    # Operation 진행 중인 경우 로그
                    if i % 12 == 0:  # 1분마다
                        logger.info(f"🔄 Firestore 데이터베이스 생성 대기 중... ({i//12 + 1}/5분)")
                        
                except Exception as e:
                    logger.error(f"❌ Operation 상태 확인 실패: {e}")
                    # Operation 상태 확인 실패 시 fallback으로 데이터베이스 직접 확인
                    try:
                        database_name = f"projects/{self.project_id}/databases/(default)"
                        database = firestore_admin.projects().databases().get(name=database_name).execute()
                        if database.get('state') == 'ACTIVE':
                            logger.info("✅ Firestore 데이터베이스 생성 완료 (직접 확인)")
                            return True
                    except:
                        pass
            
            logger.error("❌ Firestore 데이터베이스 생성 시간 초과")
            logger.info(f"💡 GCP 콘솔에서 수동 확인: https://console.firebase.google.com/project/{self.project_id}/firestore")
            return False
            
        except Exception as e:
            logger.error(f"❌ Firestore 데이터베이스 생성 실패: {e}")
            
            # App Engine 애플리케이션이 필요한 경우 안내
            if "Please enable the App Engine Admin API" in str(e) or "app does not exist" in str(e):
                logger.info("💡 App Engine 애플리케이션 생성을 시도합니다...")
                return self._create_app_engine_application(location_id)
            
            return False
    
    def _create_app_engine_application(self, location_id: str) -> bool:
        """App Engine 애플리케이션 생성 (Firestore를 위해 필요)"""
        try:
            logger.info("🔄 App Engine 애플리케이션 생성 중...")
            
            # App Engine Admin API 클라이언트
            appengine = build('appengine', 'v1', credentials=self.credentials)
            
            # 기존 애플리케이션 확인
            try:
                app = appengine.apps().get(appsId=self.project_id).execute()
                if app:
                    logger.info("✅ App Engine 애플리케이션이 이미 존재합니다")
                    # App Engine이 있으면 다시 Firestore 생성 시도
                    return self.create_firestore_database(location_id)
            except Exception:
                pass  # 애플리케이션이 없으면 생성
            
            # App Engine 애플리케이션 생성
            app_config = {
                'id': self.project_id,
                'locationId': location_id,
                'databaseType': 'CLOUD_FIRESTORE'
            }
            
            operation = appengine.apps().create(body=app_config).execute()
            logger.info(f"🔄 App Engine 애플리케이션 생성 중... (Operation: {operation.get('name')})")
            
            # 생성 완료 대기 (최대 10분)
            for i in range(120):
                time.sleep(5)
                try:
                    app = appengine.apps().get(appsId=self.project_id).execute()
                    if app and app.get('servingStatus') == 'SERVING':
                        logger.info("✅ App Engine 애플리케이션 생성 완료")
                        # 이제 Firestore 데이터베이스가 자동으로 생성되었을 것임
                        return True
                        
                except Exception:
                    pass
                
                if i % 12 == 0:  # 1분마다 로그
                    logger.info(f"🔄 App Engine 생성 대기 중... ({i//12 + 1}/10분)")
            
            logger.warning("⚠️ App Engine 애플리케이션 생성 시간 초과")
            return False
            
        except Exception as e:
            logger.error(f"❌ App Engine 애플리케이션 생성 실패: {e}")
            return False