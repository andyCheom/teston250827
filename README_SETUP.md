# GraphRAG 프로젝트 자동 설정 가이드

이 가이드는 GraphRAG 프로젝트를 처음 시작하는 사람들을 위한 자동 설정 기능에 대해 설명합니다.

## 🚀 빠른 시작

### 1. 환경 설정 파일 준비

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일을 편집하여 실제 값 입력
# 최소한 PROJECT_ID는 반드시 설정해야 합니다
```

**.env 파일 필수 설정:**
```bash
PROJECT_ID=your-actual-project-id
```

### 2. 사전 요구사항

- **Google Cloud SDK (gcloud CLI)** 설치 및 로그인
- **Python 3.11+** 및 pip
- **적절한 GCP 권한** (프로젝트 편집자 이상)

### 3. 자동 설정 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 자동 설정 실행
python setup.py
```

## 📋 자동 설정 기능

### 생성되는 GCP 리소스

1. **필요한 API 자동 활성화**
   - Discovery Engine API
   - Cloud Storage API
   - Cloud Build API
   - Cloud Run API
   - Firebase API (선택사항)

2. **Cloud Storage 버킷**
   - 이름: `{PROJECT_ID}-graphrag-storage`
   - 위치: `asia-northeast3` (기본값)
   - CORS 설정 자동 구성

3. **Discovery Engine 데이터스토어**
   - 이름: `{PROJECT_ID}-graphrag-datastore`
   - 위치: `global`
   - 검색 및 답변 생성용 구성

4. **Discovery Engine**
   - 이름: `{PROJECT_ID}-graphrag-engine`
   - 데이터스토어와 자동 연결
   - Answer API 활성화

5. **서비스 계정**
   - 이름: `graphrag-service@{PROJECT_ID}.iam.gserviceaccount.com`
   - 필요한 권한 자동 부여:
     - `roles/discoveryengine.editor`
     - `roles/storage.objectViewer`
     - `roles/storage.objectCreator`
   - 키 파일 자동 생성: `keys/graphrag-service-{PROJECT_ID}.json`

6. **Firebase 설정** (선택사항)
   - Firebase 프로젝트 활성화
   - Firebase Hosting 설정
   - `firebase.json` 및 `.firebaserc` 자동 생성

## ⚙️ 설정 옵션

### 환경변수로 설정 제어

```bash
# 자동 설정 비활성화
AUTO_SETUP=false

# 개별 리소스 설정 제어
SETUP_DISCOVERY_ENGINE=true    # Discovery Engine 생성
SETUP_STORAGE_BUCKET=true      # Storage 버킷 생성
SETUP_FIREBASE=false           # Firebase 설정 (기본값: false)
ENABLE_APIS=true               # 필요한 API 활성화
```

### 리소스 이름 커스터마이징

```bash
# 기본값 대신 커스텀 이름 사용
DISCOVERY_ENGINE_ID=my-custom-engine
DATASTORE_ID=my-custom-datastore
STORAGE_BUCKET=my-custom-bucket
SERVICE_ACCOUNT_EMAIL=my-service@project.iam.gserviceaccount.com
```

## 🛠️ 고급 사용법

### 명령행 옵션

```bash
# 사전 요구사항 검증 건너뛰기
python setup.py --skip-validation

# GCP 리소스만 설정
python setup.py --gcp-only

# Firebase 리소스만 설정
python setup.py --firebase-only

# 설정 확인만 하고 실제 생성하지 않음
python setup.py --dry-run
```

### 개별 설정 모듈 사용

```python
from modules.setup.gcp_setup import GCPSetupManager
from modules.setup.firebase_setup import FirebaseSetupManager

# GCP 리소스만 설정
gcp_setup = GCPSetupManager()
gcp_setup.initialize()
await gcp_setup.enable_required_apis()
gcp_setup.create_storage_bucket("my-bucket")

# Firebase 리소스만 설정
firebase_setup = FirebaseSetupManager()
firebase_setup.initialize()
firebase_setup.enable_firebase_project()
```

## 🔍 문제 해결

### 일반적인 오류

1. **인증 오류**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **권한 부족**
   - GCP 콘솔에서 프로젝트 편집자 권한 확인
   - 결제 계정 연결 확인

3. **API 활성화 실패**
   - 수동으로 필요한 API 활성화:
   ```bash
   gcloud services enable discoveryengine.googleapis.com
   gcloud services enable storage-api.googleapis.com
   ```

4. **타임아웃 오류**
   - Discovery Engine 생성은 최대 10분 소요
   - 백그라운드에서 계속 진행되므로 잠시 후 확인

### 설정 검증

```python
# 설정 완료 상태 확인
python -c "
from modules.setup.gcp_setup import GCPSetupManager
setup = GCPSetupManager()
setup.initialize()
print(setup.validate_setup())
"
```

## 📁 생성되는 파일들

설정 완료 후 다음 파일들이 생성됩니다:

```
graphrag/
├── .env                           # 업데이트된 환경설정
├── .env.backup                    # 기존 설정 백업
├── keys/
│   └── graphrag-service-{PROJECT_ID}.json  # 서비스 계정 키
├── firebase.json                  # Firebase 설정 (SETUP_FIREBASE=true인 경우)
└── .firebaserc                    # Firebase 프로젝트 설정
```

## 🚀 설정 완료 후 다음 단계

1. **개발 서버 실행**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

2. **웹 인터페이스 접속**
   ```
   http://localhost:8000
   ```

3. **API 테스트**
   ```bash
   curl -X POST http://localhost:8000/api/generate \
     -F "userPrompt=안녕하세요" \
     -F "conversationHistory=[]"
   ```

4. **Firebase 배포** (선택사항)
   ```bash
   firebase deploy --only hosting
   ```

## ⚠️ 주의사항

- **비용**: GCP 리소스 사용에 따른 요금이 발생할 수 있습니다
- **보안**: 생성된 서비스 계정 키 파일을 안전하게 관리하세요
- **백업**: 설정 전 기존 `.env` 파일이 자동 백업됩니다
- **권한**: 충분한 GCP 권한이 필요합니다 (프로젝트 편집자 이상)

## 🔗 관련 문서

- [GraphRAG 프로젝트 메인 README](README.md)
- [Google Cloud Discovery Engine 문서](https://cloud.google.com/discovery-engine)
- [Firebase Hosting 문서](https://firebase.google.com/docs/hosting)