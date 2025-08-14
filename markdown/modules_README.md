# GraphRAG 프로젝트 모듈 구조 설명서

이 문서는 GraphRAG 프로젝트의 `modules` 폴더 안에 있는 파일들을 처음 접하는 개발자들을 위해 작성되었습니다. 각 파일의 역할과 주요 함수들에 대해 쉽게 설명합니다.

## 📁 전체 구조 개요

```
modules/
├── auth.py                     # Google Cloud 인증 관리
├── config.py                   # 환경 설정 관리 (다중 데이터스토어 지원)
├── routers/                    # 웹 API 엔드포인트들
│   ├── api.py                 # 메인 API (질의응답, 민감 질문 처리)
│   ├── conversation_api.py    # 대화 기록 관리 API (Firestore 연동)
│   ├── discovery_only_api.py  # Discovery Engine 테스트 API
│   └── multi_datastore_api.py # 다중 데이터스토어 API
├── services/                   # 핵심 비즈니스 로직
│   ├── conversation_logger.py # 대화 내용 저장 관리 (JSON 파일)
│   ├── discovery_engine_api.py# Google Discovery Engine 연동
│   ├── multi_datastore_manager.py # 다중 데이터스토어 관리
│   ├── sensitive_query_detector.py # 민감 질문 감지
│   ├── consultant_service.py  # 상담사 연결 서비스 (Google Chat)
│   ├── firestore_conversation.py # Firestore 대화 저장
│   └── demo_request_service.py # 데모 신청 처리
└── setup/                      # 자동 설정 도구들
    ├── gcp_setup.py           # Google Cloud 리소스 자동 생성
    ├── firebase_setup.py      # Firebase 설정 자동화
    └── cicd_setup.py          # 배포 파이프라인 설정
```

---

## 🔧 핵심 설정 파일들

### `config.py` - 환경 설정 관리자

**이게 뭐하는 파일인가요?**
- 프로젝트에서 사용하는 모든 설정값들을 한 곳에서 관리하는 파일입니다.
- `.env` 파일에서 환경변수를 읽어서 프로그램이 쓸 수 있게 만듭니다.

**주요 클래스:**
- `Config`: 모든 설정값들을 담고 있는 클래스

**주요 설정값들:**
```python
# Google Cloud 관련
PROJECT_ID = "your-project-name"         # 구글 클라우드 프로젝트 이름
LOCATION_ID = "asia-northeast3"          # 서버 위치 (서울)

# Discovery Engine 관련  
DISCOVERY_ENGINE_ID = "your-engine"      # 검색 엔진 이름
DATASTORE_ID = "your-datastore"          # 데이터 저장소 이름

# Storage 관련
STORAGE_BUCKET = "your-bucket"           # 파일 저장 공간 이름
CONVERSATION_BUCKET = "your-conversations" # 대화 저장 공간 이름
```

**주요 함수들:**
- `get_api_endpoint()`: Google API 주소를 만들어줍니다
- `get_datastore_path()`: 데이터 저장소 경로를 만들어줍니다
- `load_system_instruction()`: AI에게 줄 지시문을 파일에서 읽어옵니다

---

### `auth.py` - Google Cloud 인증 관리자

**이게 뭐하는 파일인가요?**
- Google Cloud 서비스를 사용하기 위한 로그인/인증을 처리합니다.
- 서비스 계정 키 파일이나 기본 인증을 사용해서 권한을 얻습니다.

**주요 함수들:**

#### `initialize_auth()` - 인증 초기화
```python
def initialize_auth() -> bool:
    """Google Cloud 인증을 설정합니다"""
```
- **하는 일**: 구글 클라우드에 로그인을 시도합니다
- **반환값**: 성공하면 True, 실패하면 False
- **언제 쓰나요**: 프로그램이 시작될 때 맨 처음 한 번

#### `get_credentials()` - 인증 정보 가져오기  
```python
def get_credentials():
    """인증 정보를 반환합니다"""
```
- **하는 일**: 다른 Google 서비스들이 쓸 수 있는 인증 정보를 줍니다
- **언제 쓰나요**: Discovery Engine이나 Storage를 쓸 때

#### `is_authenticated()` - 인증 상태 확인
```python  
def is_authenticated() -> bool:
    """현재 인증이 되어있는지 확인합니다"""
```
- **하는 일**: 지금 Google Cloud에 제대로 로그인되어 있는지 체크합니다
- **반환값**: 로그인 상태면 True, 아니면 False

#### `get_storage_client()` - 파일 저장소 클라이언트
```python
def get_storage_client():
    """Google Cloud Storage 클라이언트를 반환합니다"""
```
- **하는 일**: 파일을 Google Cloud에 저장하거나 읽을 수 있는 도구를 줍니다
- **언제 쓰나요**: 대화 내용을 JSON 파일로 저장할 때

---

## 🌐 API 엔드포인트들 (routers 폴더)

### `api.py` - 메인 API 엔드포인트

**이게 뭐하는 파일인가요?**
- 사용자가 질문을 보내고 AI가 답변을 주는 핵심 기능을 담고 있습니다.
- 웹브라우저나 앱에서 호출할 수 있는 API를 만듭니다.

**주요 API들:**

#### `POST /api/generate` - AI 질의응답
```python
async def generate_content(userPrompt: str, conversationHistory: str, sessionId: str):
    """사용자 질문에 대한 AI 답변을 생성합니다"""
```
- **받는 정보**: 
  - `userPrompt`: 사용자가 입력한 질문
  - `conversationHistory`: 이전 대화 내역
  - `sessionId`: 대화 세션 ID
- **하는 일**: 
  1. 민감 질문 감지 (가격, 할인, 계약 등)
  2. 민감 질문이면 상담사 연결 안내
  3. 일반 질문이면 Discovery Engine에서 답변 생성
  4. 대화 내용을 GCS와 Firestore에 저장
- **반환하는 것**: AI 답변, 참고자료, 관련 질문, 상담사 연결 필요 여부

#### `GET /api/health` - 서버 상태 확인
```python
async def health_check():
    """서버가 정상 작동하는지 확인합니다"""
```
- **하는 일**: 서버가 살아있는지 간단히 체크
- **언제 쓰나요**: 서버 모니터링할 때

#### `GET /gcs/{bucket_name}/{file_path}` - 파일 프록시
```python
async def proxy_gcs_file(bucket_name: str, file_path: str):
    """Google Cloud Storage 파일을 웹으로 제공합니다"""
```
- **하는 일**: GCS에 저장된 파일을 웹브라우저에서 볼 수 있게 해줍니다
- **언제 쓰나요**: 업로드된 문서를 사용자가 다운로드할 때

### `conversation_api.py` - 대화 기록 관리 API

**이게 뭐하는 파일인가요?**
- 저장된 대화 내용을 조회하고 관리하는 API들이 모여있습니다.

**주요 API들:**

#### `GET /api/conversations/sessions` - 대화 세션 목록
```python
async def list_conversation_sessions():
    """모든 대화 세션 목록을 가져옵니다"""
```
- **하는 일**: 지금까지 있었던 모든 대화방 목록을 보여줍니다
- **언제 쓰나요**: 관리자가 대화 현황을 확인할 때

#### `GET /api/conversations/sessions/{session_id}` - 특정 대화 내용 조회
```python
async def get_session_conversations(session_id: str):
    """특정 세션의 대화 내용을 가져옵니다"""
```
- **하는 일**: 특정 대화방의 모든 대화 내용을 보여줍니다
- **언제 쓰나요**: 특정 사용자의 대화 기록을 확인할 때

#### `DELETE /api/conversations/cleanup` - 오래된 대화 정리
```python  
async def cleanup_old_sessions(days: int):
    """오래된 대화 세션들을 삭제합니다"""
```
- **하는 일**: 오래된 대화 파일들을 자동으로 삭제해서 저장공간을 절약합니다
- **언제 쓰나요**: 주기적으로 데이터 정리할 때

### `discovery_only_api.py` - Discovery Engine 테스트 API

**이게 뭐하는 파일인가요?**
- Google Discovery Engine의 기능을 직접 테스트해볼 수 있는 API입니다.
- 개발자가 검색 엔진이 제대로 작동하는지 확인할 때 사용합니다.

---

## 🛠 비즈니스 로직들 (services 폴더)

### `discovery_engine_api.py` - Google Discovery Engine 연동

**이게 뭐하는 파일인가요?**
- Google의 검색 엔진과 대화하는 핵심 로직이 들어있습니다.
- 사용자 질문을 Google에 보내고 답변을 받아옵니다.

**주요 함수들:**

#### `get_complete_discovery_answer()` - 완전한 답변 생성
```python
async def get_complete_discovery_answer(user_prompt: str) -> dict:
    """사용자 질문에 대한 완전한 답변을 생성합니다"""
```
- **받는 정보**: 사용자의 질문
- **하는 일**:
  1. Discovery Engine의 Search API로 관련 문서 검색
  2. Answer API로 자연어 답변 생성
  3. 결과를 종합해서 완전한 답변 구성
- **반환하는 것**: 답변, 참고자료, 관련 질문, 메타데이터

#### `search_documents()` - 문서 검색
```python
def search_documents(query: str, session_id: str = None) -> dict:
    """관련 문서들을 검색합니다"""
```
- **하는 일**: 질문과 관련된 문서들을 찾아옵니다
- **언제 쓰나요**: 답변 생성 전에 참고자료를 찾을 때

#### `generate_answer()` - 답변 생성
```python  
def generate_answer(query: str, session_id: str = None) -> dict:
    """자연어 답변을 생성합니다"""
```
- **하는 일**: 검색된 정보를 바탕으로 자연스러운 답변을 만듭니다
- **언제 쓰나요**: 검색 결과를 사용자가 이해하기 쉬운 답변으로 바꿀 때

### 새로 추가된 서비스들

### `sensitive_query_detector.py` - 민감 질문 감지

**이게 뭐하는 파일인가요?**
- 가격, 할인, 계약 등 인간 상담사가 답변해야 할 민감한 질문들을 자동으로 감지합니다.

**주요 기능:**
- 민감 키워드 인식 (가격, 비용, 할인, 상담 등)
- 다단계 분류 시스템
- 신뢰도 점수 제공

### `consultant_service.py` - 상담사 연결 서비스

**이게 뭐하는 파일인가요?**
- 민감한 질문이 감지되면 Google Chat을 통해 인간 상담사에게 알림을 보냅니다.

**주요 기능:**
- Google Chat Webhook 연동
- 대화 컨텍스트와 함께 상담 요청 전송
- 상담 요청 ID 및 타임스탬프 관리

### `multi_datastore_manager.py` - 다중 데이터스토어 관리

**이게 뭐하는 파일인가요?**
- 여러 개의 Discovery Engine 데이터스토어에서 동시에 검색하고 결과를 통합합니다.

**주요 기능:**
- 다중 데이터스토어 병렬 검색
- 결과 통합 및 중요도 순 정렬
- 데이터스토어별 성공/실패 추적
- 동적 설정 관리

### `firestore_conversation.py` - Firestore 대화 저장

**이게 뭐하는 파일인가요?**
- 기존 GCS JSON 파일 저장에 추가로 Firestore에도 대화 내역을 저장하고 관리합니다.

**주요 기능:**
- 세션별 대화 내역 저장
- 사용자 품질 평가 기능
- 대화 분석 데이터 제공
- 세션 요약 및 통계

### `demo_request_service.py` - 데모 신청 처리

**이게 뭐하는 파일인가요?**
- 웹사이트에서 들어오는 데모 신청을 처리하고 관리합니다.

**주요 기능:**
- 데모 신청 양식 검증
- Google Chat으로 신청 내역 전송
- 신청 ID 및 타임스탬프 관리

### `conversation_logger.py` - 대화 내용 저장 관리 (GCS)

**이게 뭐하는 파일인가요?**
- 사용자와 AI의 대화 내용을 Google Cloud Storage에 JSON 파일로 저장하고 관리합니다.

**주요 클래스:**

#### `ConversationLogger` - 대화 로깅 관리자
```python
class ConversationLogger:
    """대화 세션별 GCS JSON 로깅 관리자"""
```

**주요 함수들:**

#### `log_conversation()` - 대화 내용 저장
```python
def log_conversation(session_id: str, user_question: str, 
                    ai_answer: str, metadata: dict) -> bool:
    """대화 내용을 GCS에 저장합니다"""
```
- **받는 정보**:
  - `session_id`: 대화방 ID
  - `user_question`: 사용자 질문  
  - `ai_answer`: AI 답변
  - `metadata`: 추가 정보 (참고자료 등)
- **하는 일**: 대화 내용을 JSON 파일로 구글 클라우드에 저장
- **반환값**: 저장 성공하면 True, 실패하면 False

#### `get_session_conversations()` - 세션 대화 조회
```python
def get_session_conversations(session_id: str) -> List[dict]:
    """특정 세션의 모든 대화를 가져옵니다"""
```
- **받는 정보**: 대화방 ID
- **반환하는 것**: 그 대화방의 모든 대화 내용 리스트

#### `list_sessions()` - 세션 목록 조회
```python  
def list_sessions() -> List[dict]:
    """모든 대화 세션 목록을 가져옵니다"""
```
- **하는 일**: GCS에 저장된 모든 대화방 목록을 조회
- **반환하는 것**: 세션 ID, 생성일시, 대화 개수 등의 정보

#### `cleanup_old_sessions()` - 오래된 대화 정리
```python
def cleanup_old_sessions(days_to_keep: int = 30) -> int:
    """오래된 대화 세션들을 삭제합니다"""
```
- **받는 정보**: 보관할 일수 (기본 30일)
- **하는 일**: 오래된 대화 파일들을 자동으로 삭제
- **반환하는 것**: 삭제된 파일 개수


---

## ⚙️ 자동 설정 도구들 (setup 폴더)

### `gcp_setup.py` - Google Cloud 리소스 자동 생성

**이게 뭐하는 파일인가요?**
- Google Cloud에서 필요한 모든 리소스들을 자동으로 만들어주는 도구입니다.
- 수동으로 하나씩 만들 필요 없이 스크립트 한 번 실행으로 모든 설정이 완료됩니다.

**주요 클래스:**

#### `GCPSetupManager` - GCP 리소스 설정 관리자
```python
class GCPSetupManager:
    """GCP 리소스 자동 설정 관리자"""
```

**주요 함수들:**

#### `enable_required_apis()` - 필요한 API 활성화
```python
async def enable_required_apis() -> bool:
    """프로젝트에 필요한 Google API들을 활성화합니다"""
```
- **하는 일**: Discovery Engine, Storage, Cloud Run 등 필요한 API들을 자동으로 켜줍니다
- **언제 쓰나요**: 새 프로젝트 설정할 때 맨 처음

#### `create_storage_bucket()` - Storage 버킷 생성
```python
def create_storage_bucket(bucket_name: str, location: str = "asia-northeast3") -> bool:
    """Google Cloud Storage 버킷을 생성합니다"""
```
- **하는 일**: 파일들을 저장할 수 있는 공간을 구글 클라우드에 만듭니다
- **받는 정보**: 버킷 이름, 위치 (기본: 서울)

#### `create_discovery_datastore()` - 검색 엔진 데이터스토어 생성
```python  
def create_discovery_datastore(datastore_id: str, display_name: str = None) -> bool:
    """Discovery Engine 데이터스토어를 생성합니다"""
```
- **하는 일**: AI가 검색할 수 있는 문서 저장소를 만듭니다
- **받는 정보**: 데이터스토어 ID, 화면에 표시될 이름

#### `create_discovery_engine()` - 검색 엔진 생성
```python
def create_discovery_engine(engine_id: str, datastore_id: str) -> bool:
    """Discovery Engine을 생성합니다"""
```
- **하는 일**: 실제로 검색 기능을 수행하는 엔진을 만듭니다
- **받는 정보**: 엔진 ID, 연결할 데이터스토어 ID

#### `create_service_account()` - 서비스 계정 생성
```python
def create_service_account(service_account_id: str) -> Optional[str]:
    """서비스 계정을 생성하고 키 파일을 다운로드합니다"""
```
- **하는 일**: 
  1. 프로그램이 Google Cloud를 사용할 수 있는 계정 생성
  2. 필요한 권한들을 자동으로 부여
  3. 인증키 파일을 다운로드
- **반환하는 것**: 생성된 키 파일의 경로

#### `create_cloud_run_service()` - Cloud Run 서비스 생성  
```python
def create_cloud_run_service(service_name: str, image_name: str) -> bool:
    """Cloud Run 서비스를 생성합니다"""
```
- **하는 일**: 웹 서버를 인터넷에 배포할 수 있는 환경을 만듭니다
- **받는 정보**: 서비스 이름, 사용할 Docker 이미지

### `firebase_setup.py` - Firebase 설정 자동화

**이게 뭐하는 파일인가요?**  
- 웹사이트를 인터넷에 무료로 올릴 수 있는 Firebase Hosting 설정을 자동화합니다.

**주요 클래스:**

#### `FirebaseSetupManager` - Firebase 설정 관리자
```python
class FirebaseSetupManager:
    """Firebase 프로젝트 설정 관리자"""  
```

**주요 함수들:**

#### `enable_firebase_project()` - Firebase 프로젝트 활성화
```python
def enable_firebase_project() -> bool:
    """GCP 프로젝트에서 Firebase를 활성화합니다"""
```
- **하는 일**: Google Cloud 프로젝트에 Firebase 기능을 추가합니다

#### `setup_firebase_hosting()` - Firebase Hosting 설정
```python  
def setup_firebase_hosting() -> bool:
    """Firebase Hosting을 설정합니다"""
```
- **하는 일**: 
  1. `firebase.json` 설정 파일 생성
  2. `.firebaserc` 프로젝트 연결 파일 생성  
  3. 웹사이트 배포 준비

#### `create_firebase_service_account()` - Firebase 서비스 계정 생성
```python
def create_firebase_service_account(service_account_id: str = None) -> Optional[str]:
    """Firebase 배포용 서비스 계정을 생성합니다"""
```
- **하는 일**:
  1. Firebase 배포 권한을 가진 계정 생성
  2. 필요한 권한들 자동 부여
  3. 배포용 키 파일 생성
- **언제 쓰나요**: GitHub Actions로 자동 배포할 때

### `cicd_setup.py` - 배포 파이프라인 설정

**이게 뭐하는 파일인가요?**
- 코드를 GitHub에 올리면 자동으로 배포되는 시스템을 설정하는 도구입니다.

**주요 클래스:**

#### `CICDSetupManager` - CI/CD 설정 관리자  
```python
class CICDSetupManager:
    """CICD 리소스 설정 관리자"""
```

**주요 함수들:**

#### `setup_github_actions()` - GitHub Actions 설정
```python
def setup_github_actions() -> bool:
    """GitHub Actions 워크플로우 파일들을 생성합니다"""
```
- **하는 일**: 
  1. 자동 배포 스크립트 파일들 생성
  2. 코드 푸시시 자동 테스트 및 배포 설정
- **언제 쓰나요**: 프로젝트 초기 설정할 때

#### `setup_cloud_build()` - Cloud Build 설정
```python  
def setup_cloud_build() -> bool:
    """Google Cloud Build 설정을 생성합니다"""
```
- **하는 일**: Google Cloud에서 자동으로 Docker 이미지를 빌드하는 설정을 만듭니다

---

## 🎯 사용 흐름 이해하기

### 1. 처음 프로젝트 설정할 때
```
setup.py 실행
    ↓
gcp_setup.py → Google Cloud 리소스들 자동 생성
    ↓  
firebase_setup.py → 웹사이트 호스팅 설정
    ↓
cicd_setup.py → 자동 배포 파이프라인 설정
```

### 2. 사용자가 질문할 때
```  
웹브라우저에서 질문 입력
    ↓
api.py → /api/generate 엔드포인트 호출
    ↓
sensitive_query_detector.py → 민감 질문 감지
    ↓
[민감 질문이면] consultant_service.py → 상담사 연결
[일반 질문이면] discovery_engine_api.py → 답변 생성
    ↓  
conversation_logger.py → GCS에 JSON 저장
firestore_conversation.py → Firestore에 구조화 저장
    ↓
사용자에게 답변 반환
```

### 3. 대화 기록 조회할 때
```
관리자가 대화 기록 요청
    ↓
conversation_api.py → 대화 관리 API 호출  
    ↓
firestore_conversation.py → Firestore에서 대화 내역 조회
    ↓
대화 기록 및 분석 데이터 반환
```

### 4. 다중 데이터스토어 검색할 때
```
사용자가 다중 데이터스토어 검색 요청
    ↓
multi_datastore_api.py → 다중 데이터스토어 API 호출
    ↓
multi_datastore_manager.py → 병렬 검색 수행
    ↓
통합된 검색 결과 반환
```

---

## 💡 핵심 개념 정리

**Google Discovery Engine이란?**
- Google이 만든 검색 엔진 서비스입니다.
- 문서들을 업로드하면 사용자 질문에 맞는 답변을 자동으로 찾아줍니다.

**Google Cloud Storage (GCS)란?**  
- Google의 클라우드 파일 저장소입니다.
- 대화 내용을 JSON 파일로 저장하는데 사용합니다.

**Firebase Hosting이란?**
- Google의 무료 웹사이트 호스팅 서비스입니다.
- HTML/CSS/JavaScript 파일들을 업로드하면 웹사이트가 됩니다.

**Cloud Run이란?**
- Google의 서버리스 컨테이너 플랫폼입니다.  
- Python 웹 API를 인터넷에 배포할 때 사용합니다.

**서비스 계정이란?**
- 프로그램이 Google Cloud 서비스를 사용할 때 필요한 계정입니다.
- 사람 계정이 아닌 프로그램 전용 계정입니다.

이 문서를 통해 GraphRAG 프로젝트의 전체 구조를 이해하고, 필요한 부분을 수정하거나 확장할 수 있기를 바랍니다!