# GraphRAG 프로젝트 설정 스크립트 분석

## 개요

이 문서는 `setup.py`를 중심으로 `modules/setup` 내 관련 모듈(`gcp_setup.py`, `firebase_setup.py`, `cicd_setup.py`)의 기능을 분석하고 설명합니다. 이 스크립트 모음은 GraphRAG 프로젝트에 필요한 Google Cloud Platform(GCP), Firebase, CI/CD 환경을 자동화하여 설정하는 역할을 합니다.

## 주요 파일

-   **`setup.py`**: 설정 프로세스 전체를 조율하는 메인 스크립트입니다. 커맨드 라인 인자를 파싱하고, 환경 변수를 로드하며, 각 설정 관리자 모듈을 호출합니다.
-   **`modules/setup/gcp_setup.py`**: GCP 리소스(Discovery Engine, Cloud Storage, Service Account 등)를 생성하고 관리합니다.
-   **`modules/setup/firebase_setup.py`**: Firebase 프로젝트를 활성화하고 호스팅 설정을 구성합니다.
-   **`modules/setup/cicd_setup.py`**: CI/CD 파이프라인을 위한 Artifact Registry 저장소와 Cloud Build 설정을 담당합니다.

## 실행 흐름

1.  **사전 요구사항 확인**: 스크립트는 시작 시 `.env` 파일의 존재 여부, 필요한 Python 패키지 설치 여부, `gcloud` CLI 인증 상태 등을 확인합니다.
2.  **환경변수 로드**: `.env` 파일에 정의된 `PROJECT_ID`와 같은 설정을 로드합니다. 필수 값이 누락된 경우, 기본값을 동적으로 생성합니다.
3.  **인수 기반 실행**: 사용자가 제공한 커맨드 라인 인수(`--gcp-only`, `--firebase-only` 등)에 따라 특정 설정 작업만 선택적으로 실행할 수 있습니다. `--dry-run` 옵션을 통해 실제 리소스를 생성하지 않고 설정값만 확인할 수도 있습니다.
4.  **리소스 생성**: 각 매니저가 담당하는 리소스를 순차적으로 생성합니다.
    -   **GCP**: 필수 API 활성화, 서비스 계정 생성 및 역할 부여, Cloud Storage 버킷, Discovery Engine 데이터스토어 및 엔진, Cloud Run 서비스를 생성합니다.
    -   **Firebase**: GCP 프로젝트에 Firebase를 추가하고, `firebase.json` 및 `.firebaserc` 파일을 생성하여 호스팅을 설정합니다.
    -   **CI/CD**: Docker 이미지를 저장할 Artifact Registry 저장소를 만들고, `cloudbuild.yaml` 설정 파일을 생성합니다.
5.  **설정 완료 및 요약**: 모든 과정이 성공적으로 완료되면, 업데이트된 설정값으로 새로운 `.env` 파일을 생성하고, 생성된 리소스 정보와 다음 단계(로컬 서버 실행 방법 등)를 요약하여 출력합니다.

## 주요 기능 상세

### `setup.py`

-   **역할**: 전체 설정 프로세스의 오케스트레이터.
-   **주요 기능**:
    -   `argparse`를 사용한 커맨드 라인 인터페이스 제공.
    -   `dotenv`를 사용해 `.env` 파일에서 설정을 로드하고 동적으로 기본값 할당.
    -   `GCPSetupManager`, `FirebaseSetupManager`, `CICDSetupManager` 클래스의 인스턴스를 생성하고, 조건에 따라 각 매니저의 메서드를 호출.
    -   성공적으로 리소스가 생성되면, `.env.backup`으로 기존 설정을 백업하고 새로운 `.env` 파일을 생성.
    -   설정 완료 후 사용자에게 다음 단계를 안내하는 요약 정보 출력.

### `GCPSetupManager` (`gcp_setup.py`)

-   **역할**: GCP 관련 리소스 생성 및 관리.
-   **주요 메서드**:
    -   `initialize()`: GCP API 클라이언트(Storage, Discovery Engine 등)를 초기화하고 인증을 처리.
    -   `enable_required_apis()`: `discoveryengine.googleapis.com`, `run.googleapis.com` 등 프로젝트에 필요한 API를 활성화.
    -   `create_service_account()`: `graphrag-service`라는 ID의 서비스 계정을 생성하고, Discovery Engine, Storage, Cloud Run, Firebase 등에 대한 포괄적인 권한을 부여한 후, 키 파일을 `keys/` 디렉토리에 저장.
    -   `create_storage_bucket()`: 문서 등을 저장할 Cloud Storage 버킷을 생성.
    -   `create_discovery_datastore()`: 검색 및 RAG 기능의 기반이 되는 Discovery Engine 데이터스토어를 생성.
    -   `create_discovery_engine()`: 데이터스토어를 사용하는 Discovery Engine을 생성.
    -   `create_cloud_run_service()`: 초기 배포를 위해 'hello' 이미지를 사용하는 Cloud Run 서비스를 생성. (이후 CI/CD 파이프라인을 통해 실제 애플리케이션 이미지로 업데이트됨)

### `FirebaseSetupManager` (`firebase_setup.py`)

-   **역할**: Firebase 프로젝트 설정 및 호스팅 구성.
-   **주요 메서드**:
    -   `initialize()`: Firebase Management API 클라이언트를 초기화.
    -   `enable_firebase_project()`: 기존 GCP 프로젝트에 Firebase 기능을 추가하고 활성화.
    -   `setup_firebase_hosting()`: 웹 애플리케이션 배포를 위한 `firebase.json`과 프로젝트 연결을 위한 `.firebaserc` 파일을 생성. `firebase.json`에는 Cloud Run 서비스로 API 요청을 리디렉션하는 `rewrites` 규칙이 포함됨.
    -   `check_firebase_cli()`: 로컬 환경에 Firebase CLI가 설치되고 로그인되어 있는지 확인.

### `CICDSetupManager` (`cicd_setup.py`)

-   **역할**: 지속적 통합 및 배포(CI/CD) 환경 구성.
-   **주요 메서드**:
    -   `initialize()`: Cloud Build API 클라이언트를 초기화.
    -   `create_artifact_repository()`: 빌드된 Docker 이미지를 저장하기 위한 Artifact Registry 저장소를 생성.
    -   `generate_cloudbuild_config()`: `cloudbuild.yaml.template` 파일을 기반으로 실제 `cloudbuild.yaml` 파일을 생성. 이 파일은 Docker 이미지 빌드, Artifact Registry에 푸시, Cloud Run 서비스 배포 과정을 정의.
    -   `print_cicd_setup_guide()`: Cloud Build 트리거 설정 등, 스크립트로 자동화하기 어려운 수동 설정 단계를 안내.

## 결론

`setup.py`와 관련 모듈들은 GraphRAG 애플리케이션을 GCP에 배포하고 운영하는 데 필요한 복잡한 초기 설정 과정을 자동화하는 강력한 도구입니다. 개발자는 이 스크립트를 실행함으로써 몇 가지 간단한 설정만으로 필요한 모든 클라우드 리소스를 일관성 있게 프로비저닝할 수 있습니다. 이는 개발 환경의 빠른 구축을 돕고, 수동 설정으로 인한 오류를 줄여줍니다.
