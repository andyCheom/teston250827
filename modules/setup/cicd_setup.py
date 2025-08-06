"""CICD 환경 설정 모듈"""

import logging
import os
import json
import subprocess
from typing import Dict, Optional, Any, List
from googleapiclient.discovery import build
from google.oauth2 import service_account

from ..config import Config
from ..auth import get_credentials

logger = logging.getLogger(__name__)

class CICDSetupManager:
    """CICD 환경 설정 관리자"""
    
    def __init__(self):
        self.credentials = None
        self.project_id = None
        self.cloudbuild_service = None
        self.artifactregistry_service = None
        
        
    def initialize(self) -> bool:
        """CICD 클라이언트 초기화"""
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
            self.cloudbuild_service = build('cloudbuild', 'v1', credentials=self.credentials)
            
            logger.info(f"✅ CICD 클라이언트 초기화 완료 - Project: {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ CICD 클라이언트 초기화 실패: {e}")
            return False
    
    def create_artifact_repository(self, 
                                 repo_name: str = "graphrag-repo",
                                 location: str = "asia-northeast3") -> bool:
        """Artifact Registry 저장소 생성"""
        try:
            # Artifact Registry API 클라이언트
            from google.cloud import artifactregistry_v1
            
            client = artifactregistry_v1.ArtifactRegistryClient(credentials=self.credentials)
            
            # 저장소 존재 확인
            repository_name = f"projects/{self.project_id}/locations/{location}/repositories/{repo_name}"
            try:
                repository = client.get_repository(name=repository_name)
                logger.info(f"✅ Artifact Registry 저장소 '{repo_name}' 이미 존재함")
                return True
            except Exception:
                pass  # 저장소가 없으면 생성
            
            # 저장소 생성
            logger.info(f"🔄 Artifact Registry 저장소 '{repo_name}' 생성 중...")
            
            parent = f"projects/{self.project_id}/locations/{location}"
            repository = artifactregistry_v1.Repository(
                name=repository_name,
                format_=artifactregistry_v1.Repository.Format.DOCKER,
                description=f"GraphRAG 프로젝트 Docker 이미지 저장소"
            )
            
            operation = client.create_repository(
                parent=parent,
                repository=repository,
                repository_id=repo_name
            )
            
            # Operation 이름 안전하게 가져오기
            operation_name = getattr(operation, 'name', str(operation))
            logger.info(f"🔄 저장소 생성 중... (Operation: {operation_name})")
            
            # 생성 완료 대기
            import time
            for i in range(30):  # 최대 5분 대기
                time.sleep(10)
                try:
                    repository = client.get_repository(name=repository_name)
                    logger.info(f"✅ Artifact Registry 저장소 생성 완료: {repo_name}")
                    return True
                except Exception:
                    if i % 6 == 0:  # 1분마다 로그
                        logger.info(f"🔄 저장소 생성 대기 중... ({i//6 + 1}/5분)")
                    continue
            
            logger.warning(f"⚠️ 저장소 생성 시간 초과")
            return False
            

        except Exception as e:
            logger.error(f"❌ Artifact Registry 저장소 생성 실패: {e}")
            return False
    
    def setup_cloud_build_trigger(self,
                                trigger_name: str = "graphrag-deploy-trigger",
                                repo_owner: str = None,
                                repo_name: str = None,
                                branch_pattern: str = "^main$") -> bool:
        """Cloud Build 트리거 설정"""
        try:
            if not repo_owner or not repo_name:
                logger.warning("⚠️ GitHub 저장소 정보가 없어 트리거 생성을 건너뜁니다")
                logger.info("💡 수동으로 Cloud Build 트리거를 설정하세요")
                return True
            
            # 기존 트리거 확인
            triggers = self.cloudbuild_service.projects().triggers().list(
                projectId=self.project_id
            ).execute()
            
            for trigger in triggers.get('triggers', []):
                if trigger.get('name') == trigger_name:
                    logger.info(f"✅ Cloud Build 트리거 '{trigger_name}' 이미 존재함")
                    return True
            
            # 트리거 생성
            logger.info(f"🔄 Cloud Build 트리거 '{trigger_name}' 생성 중...")
            
            trigger_config = {
                'name': trigger_name,
                'description': 'GraphRAG 프로젝트 자동 배포 트리거',
                'github': {
                    'owner': repo_owner,
                    'name': repo_name,
                    'push': {
                        'branch': branch_pattern
                    }
                },
                'filename': 'cloudbuild.yaml',
                'substitutions': {
                    '_PROJECT_ID': self.project_id,
                    '_REGION': Config.LOCATION_ID or 'asia-northeast3',
                    '_SERVICE_NAME': f'{self.project_id}-graphrag-api',
                    '_REPO_NAME': f'{self.project_id}-graphrag-repo'
                }
            }
            
            operation = self.cloudbuild_service.projects().triggers().create(
                projectId=self.project_id,
                body=trigger_config
            ).execute()
            
            logger.info(f"✅ Cloud Build 트리거 생성 완료: {trigger_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cloud Build 트리거 설정 실패: {e}")
            return False
    
    def generate_cloudbuild_config(self) -> bool:
        """cloudbuild.yaml 설정 파일 생성"""
        try:
            template_path = "cloudbuild.yaml.template"
            target_path = "cloudbuild.yaml"

            logger.info(f"🔄 템플릿 파일({template_path})을 읽어 {target_path} 파일을 생성합니다...")

            if not os.path.exists(template_path):
                logger.error(f"❌ 템플릿 파일이 없습니다: {template_path}")
                return False

            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # .env 파일에서 설정값 가져오기
            project_id = Config.PROJECT_ID
            region = Config.LOCATION_ID or 'asia-northeast3'
            location_id = Config.LOCATION_ID or 'asia-northeast3'
            service_name = f"{project_id}-graphrag-api"
            repo_name = f"{project_id}-graphrag-repo"
            service_account = Config.SERVICE_ACCOUNT_EMAIL or f"graphrag-service@{project_id}.iam.gserviceaccount.com"
            datastore_id = Config.DATASTORE_ID or f"{project_id}-graphrag-datastore"
            discovery_engine_id = Config.DISCOVERY_ENGINE_ID or f"{project_id}-graphrag-engine"
            datastore_location = Config.DISCOVERY_LOCATION or 'global'
            discovery_location = Config.DISCOVERY_LOCATION or 'global'

            replacements = {
                '_PROJECT_ID_': project_id,
                '_REGION_': region,
                '_LOCATION_ID_': location_id,
                '_SERVICE_NAME_': service_name,
                '_REPO_NAME_': repo_name,
                '_SERVICE_ACCOUNT_': service_account,
                '_DATASTORE_ID_': datastore_id,
                '_DISCOVERY_ENGINE_ID_': discovery_engine_id,
                '_DATASTORE_LOCATION_': datastore_location,
                '_DISCOVERY_LOCATION_': discovery_location,
            }

            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"✅ {target_path} 파일 생성이 완료되었습니다.")
            return True

        except Exception as e:
            logger.error(f"❌ cloudbuild.yaml 생성 실패: {e}")
            return False
    
    def _generate_default_cloudbuild_config(self) -> Dict[str, Any]:
        """기본 Cloud Build 설정 생성"""
        # 프로젝트별 고유한 이름 생성
        repo_name = f"{self.project_id}-graphrag-repo"
        service_name = f"{self.project_id}-graphrag-api"
        
        return {
            'substitutions': {
                '_PROJECT_ID': self.project_id,
                '_REGION': Config.LOCATION_ID or 'asia-northeast3',
                '_REPO_NAME': repo_name,
                '_SERVICE_NAME': service_name,
                '_SERVICE_ACCOUNT': Config.SERVICE_ACCOUNT_EMAIL or f"graphrag-service@{self.project_id}.iam.gserviceaccount.com",
                '_ARTIFACT_REGISTRY': f"{Config.LOCATION_ID or 'asia-northeast3'}-docker.pkg.dev",
                '_MIN_INSTANCES': '0',
                '_MAX_INSTANCES': '10',
                '_CPU': '1',
                '_MEMORY': '2Gi',
                '_TIMEOUT': '300s',
                '_DATASTORE_ID': Config.DATASTORE_ID or f"{self.project_id}-graphrag-datastore",
                '_DISCOVERY_ENGINE_ID': Config.DISCOVERY_ENGINE_ID or f"{self.project_id}-graphrag-engine",
                '_MODEL_ID': 'gemini-pro',
                '_LOCATION_ID': Config.LOCATION_ID or 'asia-northeast3',
                '_DATASTORE_LOCATION': Config.DISCOVERY_LOCATION or 'global'
            },
            'steps': [
                {
                    'name': 'gcr.io/cloud-builders/docker',
                    'args': [
                        'build',
                        '-t', '${_ARTIFACT_REGISTRY}/${_PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}',
                        '-t', '${_ARTIFACT_REGISTRY}/${_PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:latest',
                        '.'
                    ],
                    'id': 'build-image'
                },
                {
                    'name': 'gcr.io/cloud-builders/docker',
                    'args': [
                        'push',
                        '--all-tags',
                        '${_ARTIFACT_REGISTRY}/${_PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}'
                    ],
                    'id': 'push-image',
                    'waitFor': ['build-image']
                },
                {
                    'name': 'gcr.io/google.com/cloudsdktool/cloud-sdk',
                    'entrypoint': 'gcloud',
                    'args': [
                        'run', 'deploy', '${_SERVICE_NAME}',
                        '--image=${_ARTIFACT_REGISTRY}/${_PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}',
                        '--region=${_REGION}',
                        '--platform=managed',
                        '--allow-unauthenticated',
                        '--service-account=${_SERVICE_ACCOUNT}',
                        '--min-instances=${_MIN_INSTANCES}',
                        '--max-instances=${_MAX_INSTANCES}',
                        '--cpu=${_CPU}',
                        '--memory=${_MEMORY}',
                        '--timeout=${_TIMEOUT}',
                        '--set-env-vars=PROJECT_ID=${_PROJECT_ID},LOCATION_ID=${_LOCATION_ID},MODEL_ID=${_MODEL_ID},DATASTORE_ID=${_DATASTORE_ID},DATASTORE_LOCATION=${_DATASTORE_LOCATION},DISCOVERY_ENGINE_ID=${_DISCOVERY_ENGINE_ID},DISCOVERY_LOCATION=${_DATASTORE_LOCATION},DISCOVERY_COLLECTION=default_collection,DISCOVERY_SERVING_CONFIG=default_config,SYSTEM_PROMPT_PATH=prompt/prompt.txt,USE_SECRET_MANAGER=True,SERVE_STATIC=false'
                    ],
                    'id': 'deploy-service',
                    'waitFor': ['push-image']
                }
            ],
            'options': {
                'logging': 'CLOUD_LOGGING_ONLY',
                'machineType': 'E2_HIGHCPU_4'
            },
            'serviceAccount': 'projects/${_PROJECT_ID}/serviceAccounts/${_SERVICE_ACCOUNT}',
            'images': [
                '${_ARTIFACT_REGISTRY}/${_PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:${SHORT_SHA}',
                '${_ARTIFACT_REGISTRY}/${_PROJECT_ID}/${_REPO_NAME}/${_SERVICE_NAME}:latest'
            ]
        }
    
    def validate_cicd_setup(self) -> Dict[str, bool]:
        """CICD 설정 검증"""
        results = {}
        
        try:
            # Artifact Registry 저장소 확인
            try:
                from google.cloud import artifactregistry_v1
                client = artifactregistry_v1.ArtifactRegistryClient(credentials=self.credentials)
                
                repo_name = f"projects/{self.project_id}/locations/{Config.LOCATION_ID or 'asia-northeast3'}/repositories/{self.project_id}-graphrag-repo"
                client.get_repository(name=repo_name)
                results['artifact_registry'] = True
            except Exception:
                results['artifact_registry'] = False
            
            # Cloud Build API 활성화 확인
            try:
                self.cloudbuild_service.projects().builds().list(
                    projectId=self.project_id,
                    pageSize=1
                ).execute()
                results['cloudbuild_api'] = True
            except Exception:
                results['cloudbuild_api'] = False
            
            # cloudbuild.yaml 파일 확인
            results['cloudbuild_config'] = os.path.exists('cloudbuild.yaml')
            
            # Cloud Build 트리거 확인 (선택사항)
            try:
                triggers = self.cloudbuild_service.projects().triggers().list(
                    projectId=self.project_id
                ).execute()
                results['build_triggers'] = len(triggers.get('triggers', [])) > 0
            except Exception:
                results['build_triggers'] = False
            
            logger.info(f"✅ CICD 설정 검증 완료: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ CICD 설정 검증 실패: {e}")
            return {}
    
    def print_cicd_setup_guide(self):
        """CICD 설정 가이드 출력"""
        logger.info("=" * 60)
        logger.info("🚀 CICD 환경 설정 가이드")
        logger.info("=" * 60)
        
        logger.info("📋 생성된 CICD 리소스:")
        logger.info(f"  • Artifact Registry: {self.project_id}-graphrag-repo")
        logger.info(f"  • Service Account: graphrag-service@{self.project_id}.iam.gserviceaccount.com")
        logger.info(f"  • Cloud Build 설정: cloudbuild.yaml")
        
        logger.info("")
        logger.info("🔧 수동 설정 필요:")
        logger.info("  1. GitHub 저장소 연결:")
        logger.info("     - Cloud Build > 트리거 > 저장소 연결")
        logger.info("     - GitHub 저장소 선택 및 권한 부여")
        
        logger.info("")
        logger.info("  2. 트리거 생성:")
        logger.info("     - 이벤트: Push to branch")
        logger.info("     - 소스: 연결된 저장소")
        logger.info("     - 브랜치: ^main$")
        logger.info("     - 구성: Cloud Build 구성 파일 (yaml 또는 json)")
        logger.info("     - 파일 위치: /cloudbuild.yaml")
        
        logger.info("")
        logger.info("  3. 환경변수 확인:")
        logger.info("     - cloudbuild.yaml의 substitutions 섹션")
        logger.info("     - 필요시 프로젝트별 값으로 수정")
        
        logger.info("")
        logger.info("🚀 배포 테스트:")
        logger.info("  1. 코드를 main 브랜치에 푸시")
        logger.info("  2. Cloud Build > 기록에서 빌드 진행 확인")
        logger.info("  3. Cloud Run > 서비스에서 배포 확인")
        
        logger.info("")
        logger.info("=" * 60)