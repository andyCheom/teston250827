#!/usr/bin/env python3
"""
GraphRAG 프로젝트 초기 설정 스크립트 (로컬 환경 최적화)
.env 파일의 설정을 바탕으로 GCP 리소스를 자동 생성합니다.
"""

import asyncio
import logging
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from modules.setup.gcp_setup import GCPSetupManager
from modules.setup.firebase_setup import FirebaseSetupManager
from modules.setup.cicd_setup import CICDSetupManager
from modules.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class GraphRAGLocalSetup:
    """GraphRAG 프로젝트 로컬 설정 관리자"""
    
    def __init__(self):
        self.gcp_setup = GCPSetupManager()
        self.firebase_setup = FirebaseSetupManager()
        self.cicd_setup = CICDSetupManager()
        self.config_from_env = {}
        
    def load_env_config(self) -> Dict[str, str]:
        """환경변수에서 설정 로드"""
        try:
            from dotenv import load_dotenv
            
            # .env 파일 로드
            env_path = Path('.env')
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"✅ .env 파일 로드: {env_path.absolute()}")
            else:
                logger.warning("⚠️ .env 파일이 없습니다. 환경변수만 사용합니다.")
            
            config = {
                'PROJECT_ID': os.getenv('PROJECT_ID', ''),
                'LOCATION_ID': os.getenv('LOCATION_ID', 'asia-northeast3'),
                'DISCOVERY_LOCATION': os.getenv('DISCOVERY_LOCATION', 'global'),
                'DISCOVERY_COLLECTION': os.getenv('DISCOVERY_COLLECTION', 'default_collection'),
                'DISCOVERY_ENGINE_ID': os.getenv('DISCOVERY_ENGINE_ID', ''),
                'DISCOVERY_SERVING_CONFIG': os.getenv('DISCOVERY_SERVING_CONFIG', 'default_config'),
                'DATASTORE_ID': os.getenv('DATASTORE_ID', ''),
                'STORAGE_BUCKET': os.getenv('STORAGE_BUCKET', ''),
                'CONVERSATION_BUCKET': os.getenv('CONVERSATION_BUCKET', ''),
                'FIREBASE_PROJECT_ID': os.getenv('FIREBASE_PROJECT_ID', ''),
                'SERVICE_ACCOUNT_EMAIL': os.getenv('SERVICE_ACCOUNT_EMAIL', ''),
                'AUTO_SETUP': os.getenv('AUTO_SETUP', 'true').lower() == 'true',
                'SETUP_DISCOVERY_ENGINE': os.getenv('SETUP_DISCOVERY_ENGINE', 'true').lower() == 'true',
                'SETUP_STORAGE_BUCKET': os.getenv('SETUP_STORAGE_BUCKET', 'true').lower() == 'true',
                'SETUP_CONVERSATION_BUCKET': os.getenv('SETUP_CONVERSATION_BUCKET', 'true').lower() == 'true',
                'SETUP_FIREBASE': os.getenv('SETUP_FIREBASE', 'false').lower() == 'true',
                'SETUP_CICD': os.getenv('SETUP_CICD', 'false').lower() == 'true',
                'ENABLE_APIS': os.getenv('ENABLE_APIS', 'true').lower() == 'true',
            }
            
            # 기본값 생성
            if not config['PROJECT_ID']:
                logger.error("❌ PROJECT_ID 환경변수가 설정되지 않았습니다")
                logger.info("💡 .env 파일에 PROJECT_ID=your-project-id 를 추가하세요")
                return {}
            
            project_id = config['PROJECT_ID']
            
            if not config['DISCOVERY_ENGINE_ID']:
                config['DISCOVERY_ENGINE_ID'] = f"{project_id}-graphrag-engine"
            
            if not config['DATASTORE_ID']:
                config['DATASTORE_ID'] = f"{project_id}-graphrag-datastore"
            
            if not config['STORAGE_BUCKET']:
                config['STORAGE_BUCKET'] = f"{project_id}-graphrag-storage"
            
            if not config['CONVERSATION_BUCKET']:
                config['CONVERSATION_BUCKET'] = f"{project_id}-conversations"
            
            if not config['FIREBASE_PROJECT_ID']:
                config['FIREBASE_PROJECT_ID'] = project_id
            
            if not config['SERVICE_ACCOUNT_EMAIL']:
                config['SERVICE_ACCOUNT_EMAIL'] = f"graphrag-service@{project_id}.iam.gserviceaccount.com"
            
            self.config_from_env = config
            logger.info(f"✅ 환경변수 설정 로드 완료 - Project: {project_id}")
            return config
            
        except ImportError:
            logger.error("❌ python-dotenv 패키지가 필요합니다")
            logger.info("💡 설치 방법: pip install python-dotenv")
            return {}
        except Exception as e:
            logger.error(f"❌ 환경변수 설정 로드 실패: {e}")
            return {}
    
    def validate_prerequisites(self) -> bool:
        """사전 요구사항 확인 (로컬 환경 최적화)"""
        logger.info("🔍 로컬 환경 사전 요구사항 확인 중...")
        
        # .env 파일 확인
        if not os.path.exists('.env'):
            logger.error("❌ .env 파일이 없습니다")
            logger.info("💡 .env.example을 .env로 복사하고 PROJECT_ID를 설정하세요")
            return False
        
        # 환경변수 로드
        config = self.load_env_config()
        if not config or not config.get('PROJECT_ID'):
            return False
        
        # Python 패키지 확인
        required_packages = {
            'google-cloud-storage': 'google.cloud.storage',
            'google-cloud-discoveryengine': 'google.cloud.discoveryengine', 
            'google-api-python-client': 'googleapiclient',
            'python-dotenv': 'dotenv'
        }
        
        missing_packages = []
        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(package_name)
        
        if missing_packages:
            logger.error(f"❌ 필요한 패키지가 설치되지 않았습니다: {', '.join(missing_packages)}")
            logger.info("💡 설치 방법: pip install -r requirements.txt")
            return False
        
        logger.info("✅ Python 패키지 확인 완료")
        
        # gcloud CLI 확인 (선택사항)
        try:
            import subprocess
            import shutil
            
            gcloud_path = shutil.which('gcloud')
            if gcloud_path:
                result = subprocess.run([gcloud_path, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"✅ gcloud CLI 확인됨: {gcloud_path}")
                    
                    # 인증 확인
                    auth_result = subprocess.run([gcloud_path, 'auth', 'list', '--filter=status:ACTIVE'], 
                                                capture_output=True, text=True, timeout=30)
                    if auth_result.returncode == 0 and 'ACTIVE' in auth_result.stdout:
                        logger.info("✅ gcloud 인증 확인됨")
                    else:
                        logger.warning("⚠️ gcloud 인증이 필요할 수 있습니다")
                        logger.info("💡 인증 방법: gcloud auth application-default login")
                else:
                    logger.warning("⚠️ gcloud CLI가 제대로 동작하지 않습니다")
            else:
                logger.warning("⚠️ gcloud CLI를 찾을 수 없습니다")
                logger.info("💡 서비스 계정 키 파일을 사용하거나 gcloud CLI를 설치하세요")
                
        except Exception as e:
            logger.warning(f"⚠️ gcloud CLI 확인 실패: {e}")
            logger.info("💡 서비스 계정 키 파일을 사용하거나 gcloud CLI를 설치하세요")
        
        logger.info("✅ 로컬 환경 사전 요구사항 확인 완료")
        return True
    
    async def setup_gcp_resources(self) -> bool:
        """GCP 리소스 설정"""
        logger.info("🚀 GCP 리소스 설정 시작...")
        
        # GCP 설정 관리자 초기화
        if not self.gcp_setup.initialize():
            logger.error("❌ GCP 인증 실패. 다음 중 하나를 시도하세요:")
            logger.info("💡 1. gcloud auth application-default login")
            logger.info("💡 2. 서비스 계정 키 파일을 keys/ 디렉토리에 배치")
            logger.info("💡 3. GOOGLE_APPLICATION_CREDENTIALS 환경변수 설정")
            return False
        
        config = self.config_from_env
        success_count = 0
        total_count = 0
        
        # API 활성화
        if config.get('ENABLE_APIS', True):
            total_count += 1
            logger.info("🔄 필요한 API 활성화 중...")
            if await self.gcp_setup.enable_required_apis():
                success_count += 1
                logger.info("✅ API 활성화 완료")
            else:
                logger.error("❌ API 활성화 실패")
        
        # Storage 버킷 생성
        if config.get('SETUP_STORAGE_BUCKET', True):
            total_count += 1
            bucket_name = config['STORAGE_BUCKET']
            logger.info(f"🔄 Storage 버킷 '{bucket_name}' 생성 중...")
            if self.gcp_setup.create_storage_bucket(bucket_name, config['LOCATION_ID']):
                success_count += 1
                logger.info(f"✅ Storage 버킷 생성 완료: {bucket_name}")
            else:
                logger.error(f"❌ Storage 버킷 생성 실패: {bucket_name}")
        
        # 대화 저장용 버킷 생성 
        if config.get('SETUP_CONVERSATION_BUCKET', True):
            total_count += 1
            conversation_bucket_name = config.get('CONVERSATION_BUCKET', f"{config['PROJECT_ID']}-conversations")
            logger.info(f"🔄 대화 저장용 버킷 '{conversation_bucket_name}' 생성 중...")
            if self.gcp_setup.create_storage_bucket(conversation_bucket_name, config['LOCATION_ID']):
                success_count += 1
                logger.info(f"✅ 대화 저장용 버킷 생성 완료: {conversation_bucket_name}")
                # 환경변수에 추가
                self.config_from_env['CONVERSATION_BUCKET'] = conversation_bucket_name
            else:
                logger.error(f"❌ 대화 저장용 버킷 생성 실패: {conversation_bucket_name}")
        
        # Discovery Engine 데이터스토어 생성
        if config.get('SETUP_DISCOVERY_ENGINE', True):
            total_count += 1
            datastore_id = config['DATASTORE_ID']
            logger.info(f"🔄 Discovery Engine 데이터스토어 '{datastore_id}' 생성 중...")
            if self.gcp_setup.create_discovery_datastore(
                datastore_id=datastore_id,
                display_name=f"{config['PROJECT_ID']} GraphRAG DataStore",
                location=config['DISCOVERY_LOCATION']
            ):
                success_count += 1
                logger.info(f"✅ 데이터스토어 생성 완료: {datastore_id}")
            else:
                logger.error(f"❌ 데이터스토어 생성 실패: {datastore_id}")
        
        # Discovery Engine 생성
        if config.get('SETUP_DISCOVERY_ENGINE', True):
            total_count += 1
            engine_id = config['DISCOVERY_ENGINE_ID']
            datastore_id = config['DATASTORE_ID']
            logger.info(f"🔄 Discovery Engine '{engine_id}' 생성 중...")
            if self.gcp_setup.create_discovery_engine(
                engine_id=engine_id,
                datastore_id=datastore_id,
                display_name=f"{config['PROJECT_ID']} GraphRAG Engine",
                location=config['DISCOVERY_LOCATION']
            ):
                success_count += 1
                logger.info(f"✅ Discovery Engine 생성 완료: {engine_id}")
            else:
                logger.error(f"❌ Discovery Engine 생성 실패: {engine_id}")
        
        # 서비스 계정 생성
        service_account_id = "graphrag-service"
        total_count += 1
        logger.info(f"🔄 서비스 계정 '{service_account_id}' 생성 중...")
        key_file_path = self.gcp_setup.create_service_account(
            service_account_id=service_account_id,
            display_name="GraphRAG Service Account",
            description="GraphRAG 프로젝트용 서비스 계정"
        )
        if key_file_path:
            success_count += 1
            logger.info(f"✅ 서비스 계정 생성 완료: {key_file_path}")
        else:
            logger.error(f"❌ 서비스 계정 생성 실패")
        
        # Cloud Run 서비스 생성
        total_count += 1
        service_name = f"{config['PROJECT_ID']}-graphrag-api"
        # 초기 이미지는 gcr.io/cloudrun/hello를 사용합니다.
        # CI/CD 파이프라인이 실제 애플리케이션 이미지로 업데이트합니다.
        image_name = "gcr.io/cloudrun/hello"
        logger.info(f"🔄 Cloud Run 서비스 '{service_name}' 생성 중 (초기 이미지: {image_name})...")
        if self.gcp_setup.create_cloud_run_service(
            service_name=service_name,
            location=config['LOCATION_ID'],
            image_name=image_name
        ):
            success_count += 1
            logger.info(f"✅ Cloud Run 서비스 생성 완료: {service_name}")
        else:
            logger.error(f"❌ Cloud Run 서비스 생성 실패: {service_name}")

        logger.info(f"🎯 GCP 리소스 설정 완료: {success_count}/{total_count} 성공")
        return success_count > 0
    
    def setup_firebase_resources(self) -> bool:
        """Firebase 리소스 설정"""
        if not self.config_from_env.get('SETUP_FIREBASE', False):
            logger.info("⏭️ Firebase 설정이 비활성화됨")
            return True
        
        logger.info("🚀 Firebase 리소스 설정 시작...")
        
        # Firebase 설정 관리자 초기화
        if not self.firebase_setup.initialize():
            return False
        
        config = self.config_from_env
        success_count = 0
        total_count = 0
        
        # Firebase 프로젝트 활성화
        total_count += 1
        logger.info("🔄 Firebase 프로젝트 활성화 중...")
        if self.firebase_setup.enable_firebase_project():
            success_count += 1
            logger.info("✅ Firebase 프로젝트 활성화 완료")
        else:
            logger.error("❌ Firebase 프로젝트 활성화 실패")
        
        # Firebase Hosting 설정
        total_count += 1
        logger.info("🔄 Firebase Hosting 설정 중...")
        if self.firebase_setup.setup_firebase_hosting():
            success_count += 1
            logger.info("✅ Firebase Hosting 설정 완료")
        else:
            logger.error("❌ Firebase Hosting 설정 실패")
        
        # Firebase 서비스 계정 생성
        total_count += 1
        logger.info("🔄 Firebase 서비스 계정 생성 중...")
        firebase_key_file = self.firebase_setup.create_firebase_service_account()
        if firebase_key_file:
            success_count += 1
            logger.info(f"✅ Firebase 서비스 계정 키 파일 생성 완료: {firebase_key_file}")
        else:
            logger.error("❌ Firebase 서비스 계정 생성 실패")
        
        logger.info(f"🎯 Firebase 리소스 설정 완료: {success_count}/{total_count} 성공")
        return success_count > 0
    
    def setup_cicd_resources(self, force_run: bool = False) -> bool:
        """CICD 리소스 설정"""
        if not self.config_from_env.get('SETUP_CICD', False) and not force_run:
            logger.info("⏭️ CICD 설정이 비활성화됨")
            return True
        
        logger.info("🚀 CICD 리소스 설정 시작...")
        
        # CICD 설정 관리자 초기화
        if not self.cicd_setup.initialize():
            return False
        
        config = self.config_from_env
        success_count = 0
        total_count = 0
        
        # Artifact Registry 저장소 생성
        total_count += 1
        repo_name = f"{config['PROJECT_ID']}-graphrag-repo"
        logger.info(f"🔄 Artifact Registry 저장소 '{repo_name}' 생성 중...")
        if self.cicd_setup.create_artifact_repository(
            repo_name=repo_name,
            location=config['LOCATION_ID']
        ):
            success_count += 1
            logger.info("✅ Artifact Registry 저장소 생성 완료")
        else:
            logger.error("❌ Artifact Registry 저장소 생성 실패")
        
        # Cloud Build 설정 파일 생성
        total_count += 1
        logger.info("🔄 Cloud Build 설정 파일 생성 중...")
        if self.cicd_setup.generate_cloudbuild_config():
            success_count += 1
            logger.info("✅ Cloud Build 설정 파일 생성 완료")
        else:
            logger.error("❌ Cloud Build 설정 파일 생성 실패")
        
        logger.info(f"🎯 CICD 리소스 설정 완료: {success_count}/{total_count} 성공")
        
        # CICD 설정 가이드 출력
        if success_count > 0:
            self.cicd_setup.print_cicd_setup_guide()
        
        return success_count > 0
    
    def generate_updated_env(self) -> bool:
        """업데이트된 .env 파일 생성"""
        try:
            config = self.config_from_env
            
            # 현재 .env 파일 백업
            if os.path.exists('.env'):
                import shutil
                shutil.copy2('.env', '.env.backup')
                logger.info("📄 기존 .env 파일을 .env.backup으로 백업했습니다")
            
            # 새로운 .env 파일 생성
            env_content = f"""# GraphRAG 프로젝트 환경변수
# 자동 설정 스크립트에 의해 생성됨

# ============================
# GCP 프로젝트 기본 설정
# ============================
PROJECT_ID={config['PROJECT_ID']}
LOCATION_ID={config['LOCATION_ID']}
DISCOVERY_LOCATION={config['DISCOVERY_LOCATION']}

# ============================
# Discovery Engine 설정
# ============================
DISCOVERY_COLLECTION={config['DISCOVERY_COLLECTION']}
DISCOVERY_ENGINE_ID={config['DISCOVERY_ENGINE_ID']}
DISCOVERY_SERVING_CONFIG={config['DISCOVERY_SERVING_CONFIG']}

# 데이터스토어 설정
DATASTORE_ID={config['DATASTORE_ID']}
DATASTORE_LOCATION={config['DISCOVERY_LOCATION']}

# ============================
# Cloud Storage 설정
# ============================
STORAGE_BUCKET={config['STORAGE_BUCKET']}
CONVERSATION_BUCKET={config.get('CONVERSATION_BUCKET', config['PROJECT_ID'] + '-conversations')}

# ============================
# Firebase 설정
# ============================
FIREBASE_PROJECT_ID={config['FIREBASE_PROJECT_ID']}

# ============================
# Service Account 설정
# ============================
SERVICE_ACCOUNT_EMAIL={config['SERVICE_ACCOUNT_EMAIL']}

# ============================
# 기존 호환성 설정
# ============================
MODEL_ID=gemini-pro
SYSTEM_PROMPT_PATH=prompt/prompt.txt

# ============================
# 자동 설정 옵션
# ============================
SETUP_CICD={str(config.get('SETUP_CICD', 'false')).lower()}
SETUP_FIREBASE={str(config.get('SETUP_FIREBASE', 'false')).lower()}
SETUP_CONVERSATION_BUCKET={str(config.get('SETUP_CONVERSATION_BUCKET', 'true')).lower()}

# ============================
# 정적 파일 서빙 (로컬 개발용)
# ============================
SERVE_STATIC=true
"""
            
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            logger.info("✅ 업데이트된 .env 파일 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ .env 파일 생성 실패: {e}")
            return False
    
    def print_setup_summary(self):
        """설정 완료 요약 출력"""
        logger.info("=" * 60)
        logger.info("🎉 GraphRAG 프로젝트 로컬 설정 완료!")
        logger.info("=" * 60)
        
        config = self.config_from_env
        
        logger.info("📋 생성된 리소스:")
        logger.info(f"  • GCP 프로젝트: {config['PROJECT_ID']}")
        logger.info(f"  • Discovery Engine: {config['DISCOVERY_ENGINE_ID']}")
        logger.info(f"  • 데이터스토어: {config['DATASTORE_ID']}")
        logger.info(f"  • Storage 버킷: {config['STORAGE_BUCKET']}")
        logger.info(f"  • 서비스 계정: {config['SERVICE_ACCOUNT_EMAIL']}")
        
        if config.get('SETUP_FIREBASE'):
            logger.info(f"  • Firebase 프로젝트: {config['FIREBASE_PROJECT_ID']}")
        
        if config.get('SETUP_CICD'):
            logger.info(f"  • Artifact Registry: {config['PROJECT_ID']}-graphrag-repo")
        
        logger.info("")
        logger.info("🚀 다음 단계:")
        logger.info("  1. 로컬 개발 서버 실행:")
        logger.info("     uvicorn main:app --reload --port 8000")
        logger.info("")
        logger.info("  2. 웹 인터페이스 접속:")
        logger.info("     http://localhost:8000")
        logger.info("")
        logger.info("  3. API 테스트:")
        logger.info("     curl -X POST http://localhost:8000/api/generate \\")
        logger.info("       -F \"userPrompt=안녕하세요\" \\")
        logger.info("       -F \"conversationHistory=[]\"")
        logger.info("")
        logger.info("💡 로컬 개발 팁:")
        logger.info("  • 서비스 계정 키 파일이 keys/ 디렉토리에 생성되었습니다")
        logger.info("  • .env 파일이 업데이트되었습니다")
        logger.info("  • gcloud auth application-default login 으로 인증하면 더 편리합니다")
        logger.info("")
        logger.info("=" * 60)

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='GraphRAG 프로젝트 로컬 초기 설정')
    parser.add_argument('--skip-validation', action='store_true', 
                       help='사전 요구사항 검증 건너뛰기')
    parser.add_argument('--gcp-only', action='store_true', 
                       help='GCP 리소스만 설정')
    parser.add_argument('--firebase-only', action='store_true', 
                       help='Firebase 리소스만 설정')
    parser.add_argument('--cicd-only', action='store_true', 
                       help='CICD 리소스만 설정')
    parser.add_argument('--dry-run', action='store_true', 
                       help='실제 리소스를 생성하지 않고 설정만 확인')
    
    args = parser.parse_args()
    
    logger.info("🚀 GraphRAG 프로젝트 로컬 설정 시작")
    logger.info("=" * 60)
    
    setup = GraphRAGLocalSetup()
    
    # 환경변수 로드 (모든 모드에서 필요)
    config = setup.load_env_config()
    if not config:
        logger.error("❌ 환경변수 로드 실패")
        sys.exit(1)
    
    # 사전 요구사항 확인
    if not args.skip_validation:
        if not setup.validate_prerequisites():
            logger.error("❌ 사전 요구사항 확인 실패")
            logger.info("💡 --skip-validation 옵션을 사용하거나 문제를 해결하세요")
            sys.exit(1)
    
    # Dry run 모드
    if args.dry_run:
        logger.info("🔍 Dry run 모드 - 설정만 확인합니다")
        logger.info("✅ 설정 확인 완료")
        for key, value in config.items():
            logger.info(f"  {key}: {value}")
        return
    
    success = True
    
    # GCP 리소스 설정
    if args.gcp_only or (not args.firebase_only and not args.cicd_only):
        if not await setup.setup_gcp_resources():
            logger.error("❌ GCP 리소스 설정 실패")
            success = False
    
    # Firebase 리소스 설정
    if args.firebase_only or (not args.gcp_only and not args.cicd_only):
        if not setup.setup_firebase_resources():
            logger.error("❌ Firebase 리소스 설정 실패")
            success = False
    
    # CICD 리소스 설정
    if args.cicd_only or (not args.gcp_only and not args.firebase_only):
        if not setup.setup_cicd_resources(force_run=args.cicd_only):
            logger.error("❌ CICD 리소스 설정 실패")
            success = False
    
    # 설정 파일 업데이트
    if success:
        setup.generate_updated_env()
        setup.print_setup_summary()
    else:
        logger.error("❌ 설정 과정에서 오류가 발생했습니다")
        logger.info("💡 개별 옵션으로 다시 시도하거나 수동 설정을 고려하세요")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}", exc_info=True)
        sys.exit(1)