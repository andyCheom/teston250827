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
            'firebasehosting.googleapis.com'
            'cloudfunctions.googleapis.com'
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
                              datastore_id: str,
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
            
            parent = f"projects/{self.project_id}/locations/{location}/collections/default_collection"
            datastore_path = f"{parent}/dataStores/{datastore_id}"
            
            # 엔진 설정
            engine = discoveryengine_v1beta.Engine(
                display_name=display_name,
                solution_type=discoveryengine_v1beta.SolutionType.SOLUTION_TYPE_SEARCH,
                search_engine_config=discoveryengine_v1beta.Engine.SearchEngineConfig(
                    search_tier=discoveryengine_v1beta.SearchTier.SEARCH_TIER_STANDARD,
                ),
                data_store_ids=[datastore_id]
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
                # Discovery Engine 권한
                'roles/discoveryengine.editor',
                
                # Storage 권한
                'roles/storage.objectViewer',
                'roles/storage.objectCreator',
                'roles/storage.admin',  # 버킷 관리용
                
                # Cloud Run 배포 권한
                'roles/run.admin',
                'roles/run.invoker',
                
                # Cloud Build 권한 (CICD용)
                'roles/cloudbuild.builds.builder',
                'roles/source.reader',
                
                # Artifact Registry 권한 (Docker 이미지용)
                'roles/artifactregistry.writer',
                'roles/artifactregistry.reader',
                
                # Container Registry 권한 (호환성)
                'roles/storage.admin',  # GCR 이미지 저장용
                
                # IAM 권한 (서비스 계정 관리용)
                'roles/iam.serviceAccountUser',
                'roles/iam.serviceAccountTokenCreator',
                
                # 로깅 및 모니터링
                'roles/logging.logWriter',
                'roles/monitoring.metricWriter',
                
                # 네트워킹 (VPC 관련)
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
            
            # 키 파일 생성
            logger.info("🔄 서비스 계정 키 파일 생성 중...")
            
            key = iam_service.projects().serviceAccounts().keys().create(
                name=f"projects/{self.project_id}/serviceAccounts/{service_account_email}",
                body={'keyAlgorithm': 'KEY_ALG_RSA_2048'}
            ).execute()
            
            # 키 디렉토리 생성
            os.makedirs("keys", exist_ok=True)
            
            # 키 파일 저장
            key_file_path = f"keys/{service_account_id}-{self.project_id}.json"
            with open(key_file_path, 'w') as f:
                import base64
                key_data = base64.b64decode(key['privateKeyData']).decode('utf-8')
                f.write(key_data)
            
            logger.info(f"✅ 서비스 계정 키 파일 저장: {key_file_path}")
            return key_file_path
            
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