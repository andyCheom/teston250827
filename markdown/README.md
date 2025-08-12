# GraphRAG Chatbot API
# 커밋 테스트
![Diagram!](img/diagram.png)
---

## 개요 (Overview)

Google Cloud Discovery Engine을 활용한 지능형 챗봇 API 시스템입니다. Discovery Engine Answer API와 Search API를 조합하여 정확하고 맥락적인 답변을 생성하며, 텍스트 기반 질의응답에 특화되어 있습니다.

- **Discovery Engine 활용**: Google Cloud의 고성능 검색 및 답변 생성 엔진 사용
- **텍스트 중심 설계**: 간결하고 효율적인 텍스트 기반 질의응답
- **모듈화된 아키텍처**: 유지보수성과 확장성을 위한 체계적인 코드 구조

---

## ✨ 주요 기능 (Features)

### 🔍 Discovery Engine 기반 검색
- **Answer API**: 구조화된 답변과 관련 질문 자동 생성
- **Search API**: 데이터스토어에서 관련 문서 검색 및 스니펫 제공
- **Citation 지원**: 답변의 출처와 참조 문서 정보 제공
- **한국어 최적화**: 한국어 검색 및 답변 생성에 특화

### 🎯 간결한 텍스트 인터페이스
- **텍스트 전용**: 이미지 처리 없이 텍스트 질의응답에 집중
- **실시간 채팅**: 웹 기반 채팅 인터페이스
- **대화 히스토리**: 컨텍스트를 유지하는 대화 관리
- **마크다운 지원**: 서식이 적용된 답변 렌더링

### 🔧 모듈화된 아키텍처
- **인증 관리**: 중앙화된 Google Cloud 인증 시스템
- **설정 관리**: 환경 변수 기반 동적 설정
- **라우터 분리**: FastAPI 라우터를 통한 API 엔드포인트 체계화
- **서비스 레이어**: Discovery Engine API 통신 최적화

## ⚙️ 기술 스택 (Tech Stack)

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Search Engine**: Google Cloud Discovery Engine (Answer API, Search API)
- **Cloud Platform**: Google Cloud Platform (Discovery Engine, Cloud Storage, Cloud Run)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Marked.js (마크다운 렌더링)
- **Authentication**: Google Cloud IAM, Service Accounts

## 📁 프로젝트 구조 (Project Structure)

```
graphrag/
├── main.py                              # FastAPI 앱 엔트리포인트
├── requirements.txt                     # Python 의존성
├── modules/                            # 모듈화된 소스 코드
│   ├── auth.py                        # Google Cloud 인증 관리
│   ├── config.py                      # 환경 설정 관리
│   ├── routers/
│   │   ├── api.py                    # 메인 API 라우터
│   │   └── discovery_only_api.py     # Discovery Engine 전용 API
│   └── services/
│       └── discovery_engine_api.py   # Discovery Engine API 클라이언트
├── public/                            # 웹 인터페이스 정적 파일
│   ├── index.html                    # 채팅 웹 인터페이스
│   ├── style.css                     # 스타일시트
│   └── vai.js                        # 채팅 JavaScript 로직
└── prompt/
    └── prompt.txt                    # 시스템 프롬프트 템플릿
```

## 🔧 사전 준비 (Prerequisites)

- **Python 3.11+** 및 pip 패키지 관리자
- **Google Cloud SDK (gcloud CLI)**
- **Google Cloud 프로젝트** (Discovery Engine 서비스 활성화)
- **Discovery Engine 데이터스토어** (검색 데이터 저장용)
- **서비스 계정** (다음 권한 필요):
  - `roles/discoveryengine.editor` (Discovery Engine 사용)
  - `roles/storage.objectViewer` (Cloud Storage 접근)
- **환경 변수 설정** (필수)

---

## 🚀 시작하기 (Getting Started)

- **Public**한 프로젝트가 아닌, **‘처음소프트’ 사내 프로젝트입니다.** 웹서비스 파일은 별도로 제공되지 않습니다.  OAuth 2.0 인증 방식을 사용해 Google API에 Access 합니다.
- 아래 내용은 배포 환경이 아닌 테스트 환경 기준입니다

### 1.  프로젝트 관리자 계정 로그인

```bash

# Google Cloud Shell - PM 계정 (결제 관리, 프로젝트 생성, 버킷 생성 ...)
gcloud auth login
```

### 2. 가상 환경 설정 (Setup Virtual Environment)

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\\Scripts\\activate

```

### 3. 의존성 설치 (Install Dependencies)

프로젝트 루트에 있는 `requirements.txt` 파일을 사용하여 필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt

```

### 4. 환경 변수 설정 (Configure Environment Variables)

`app.py`의 `Config` 클래스에서 사용하는 환경 변수를 설정해야 합니다. 로컬 개발 시에는 터미널에서 직접 export 하거나 `.env` 파일을 사용할 수 있습니다.


```bash
# 필수 환경 변수
PROJECT_ID="your-gcp-project-id"
DISCOVERY_LOCATION="global"
DISCOVERY_COLLECTION="default_collection"
DISCOVERY_ENGINE_ID="your-discovery-engine-id"
DISCOVERY_SERVING_CONFIG="default_config"

```

### 5. 로컬 서버 실행 (Run Local Server)

```bash

# 백엔드 서버 실행
uvicorn main:app --reload --port 8000

```

## 📦 API 명세 (API Specification)

### `POST /api/generate`

사용자의 텍스트 질문과 대화 기록을 받아 Discovery Engine 기반 답변을 반환합니다.

- **Request**: `application/x-www-form-urlencoded`
    - `userPrompt` (string, required): 사용자의 텍스트 질문
    - `conversationHistory` (string, required): 이전 대화 기록을 담은 JSON 배열 문자열. (예: `'[{"role": "user", ...}, {"role": "model", ...}]'`)
- **Success Response (200 OK)**:
    
    ```json
    {
      "answer": "답변 텍스트",
      "summary_answer": "요약 답변",
      "citations": [...],           // 인용 정보
      "search_results": [...],      // 검색 결과
      "related_questions": [...],   // 관련 질문
      "updatedHistory": [...],      // 업데이트된 대화 기록
      "metadata": {
        "engine_type": "discovery_engine_main",
        "query_id": "...",
        "session_id": "..."
      },
      "quality_check": {
        "has_answer": true,
        "discovery_success": true
      }
    }
    ```
    
- **Error Responses**:
    - `400 Bad Request`: 요청 형식이 잘못되었거나 필수 파라미터가 누락된 경우
    - `503 Service Unavailable`: 서버 인증 정보가 설정되지 않은 경우
    - 기타 `4xx`, `5xx`: Discovery Engine API 호출 중 발생한 오류

### `POST /api/discovery-answer`

Discovery Engine Answer API를 직접 테스트하는 엔드포인트입니다.

- **Request**: `application/x-www-form-urlencoded`
    - `userPrompt` (string, required): 사용자의 텍스트 질문
- **Success Response (200 OK)**:
    
    ```json
    {
      "answer": "답변 텍스트",
      "citations": [...],
      "search_results": [...],
      "related_questions": [...],
      "metadata": {
        "query_id": "...",
        "session_id": "...",
        "engine_type": "discovery_engine_answer",
        "final_query_used": "..."
      }
    }
    ```

## ☁️ 배포 (Deployment)

이 애플리케이션은 Google Cloud Run에 배포하기에 최적화되어 있습니다.

### 1. `requirements.txt` &`Dockerfile`

프로젝트에 필요한 Python 패키지 목록과 애플리케이션을 컨테이너화하기 위한 파일입니다. 

### 2. 작업 중인 프로젝트로 설정

```bash
# 1. 결제 계정 연동이 되어 있어야 합니다.
gcloud config set project {$PROJECT_ID}
```

### 3. Cloud Run 배포

아래 gcloud 명령어를 사용하여 Cloud Run에 배포할 수 있습니다.

```bash
# 1. Cloud Build를 사용하여 컨테이너 이미지(Dockerfile) 빌드 및 Artifact Registry에 푸시
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# 2. 빌드된 이미지를 사용하여 Cloud Run에 서비스 배포
# --set-env-vars 플래그에 필요한 환경 변수를 모두 추가해야 합니다.
gcloud run deploy discovery-chatbot \\
  --image="gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \\
  --platform=managed \\
  --region="${DISCOVERY_LOCATION}" \\
  --allow-unauthenticated \\
  --set-env-vars="PROJECT_ID=${PROJECT_ID},DISCOVERY_LOCATION=${DISCOVERY_LOCATION},DISCOVERY_COLLECTION=${DISCOVERY_COLLECTION},DISCOVERY_ENGINE_ID=${DISCOVERY_ENGINE_ID},DISCOVERY_SERVING_CONFIG=${DISCOVERY_SERVING_CONFIG}"

```

**중요**: Cloud Run 서비스가 사용하는 서비스 계정에 **Discovery Engine 편집자(roles/discoveryengine.editor)** 역할 부여 여부를 확인해야 합니다.

---

## ⚠️ 오류 코드 및 처리 방식

아래는 서비스 사용 중 발생할 수 있는 오류 코드입니다. 
Discovery Engine API 문서를 바탕으로 작성되었습니다.

| 오류 유형 | 상태 코드 | 발생 조건 | 테스트 방법 | 해결 방법 |
| --- | --- | --- | --- | --- |
| **입력 누락** | `400 Bad Request` | 텍스트 질문이 비어있는 경우 | 아무것도 입력하지 않고 제출 | 프론트에서 입력 유효성 검사로 방지됨 |
| **JSON 파싱 오류** | `400 Bad Request` | `conversationHistory` 값이 JSON 파싱 불가한 문자열일 때 | 잘못된 JSON 문자열 삽입 | 항상 `JSON.stringify()` ��용 |
| **요청 포맷 오류 (Discovery API)** | `400 Bad Request` | API에 잘못된 필드 또는 비정상 입력 전송 | Discovery Engine ID는 정상이나 payload 구조가 잘못된 경우 | payload 구조 확인 (`query`, `session`, `answerGenerationSpec` 등) |
| **권한 부족 (IAM 설정 누락)** | `403 Forbidden` | 서비스 계정에 Discovery Engine 접근 권한이 없을 때 | Cloud Run에 적절한 IAM 역할 부여하지 않음 | `Discovery Engine Editor`, `Storage Viewer` 등 권한 추가 |
| **리소스 없음** | `404 Not Found` | Discovery Engine ID 또는 데이터스토어 ID가 잘못되었을 때 | 오타 입력 또는 삭제된 리소스 사용 | ID 확인 또는 새 리소스 생성 |
| **쿼터 초과** | `429 Too Many Requests` | Discovery Engine API 할당량 초과 | 많은 요청 반복 호출 | GCP 콘솔에서 할당량 확인 후 증가 요청 |
| **Google 인증 설정 누락** | `503 Service Unavailable` | Cloud Run 또는 로컬 환경에서 인증 설정 실패 | `credentials = None` 상태로 실행 | 로컬은 `gcloud auth application-default login`, 서버는 서비스 계정 연결 |
| **Discovery Engine 서버 내부 오류** | `500 Internal Server Error` | Discovery Engine 서비스 자체의 문제 발생 | 예외적 상황이므로 인위적 유도 어려움 | 잠시 후 재시도 또는 GCP 상태 확인 |
| **타임아웃** | `504 Gateway Timeout` | Discovery Engine 호출이 300초 이상 지연됨 | 응답 지연 유도 (ex. 큰 입력) | 타임아웃 설정 조정 또는 응답 속도 개선 |
| **예상치 못한 서버 오류** | `500 Internal Server Error` | 위에서 처리되지 않은 모든 예외 | 파일 누락 등으로 인한 오류 발생 | 로그 확인 후 예외 분류하여 핸들링 추가 |

## 🌐 웹 인터페이스 (Web Interface)

이 프로젝트는 간단한 웹 기반 채팅 인터페이스를 포함합니다:

- **채팅 UI**: 실시간 텍스트 대화 인터페이스
- **마크다운 렌더링**: 답변의 서식 지원 (굵은 글씨, 목록, 링크 등)
- **반응형 디자인**: 모바일과 데스크톱 모두 지원
- **대화 히스토리**: 세션 동안 대화 맥락 유지

웹 인터페이스는 서버 실행 후 `http://localhost:8000/`에서 접근할 수 있습니다.