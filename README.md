# Project Pipeline

![Diagram!](img/diagram.png)
---

## 개요 (Overview)

이 프로젝트는 Google Cloud Vertex AI의 Gemini 모델과 Vertex AI Search를 활용하여 RAG(검색 증강 생성, Retrieval-Augmented Generation)를 수행하는 Flask 기반 챗봇입니다.

- 백엔드 Flask에서 FastAPI로 수정되었습니다. (25.07.08)

고객 서비스(CS) 시나리오에 맞춰진 시스템 프롬프트를 기반으로 동작하며, 사용자의 텍스트 질문 뿐만 아니라 이미지 입력을 포함한 멀티모달 요청을 처리할 수 있습니다.

---

## ✨ 주요 기능 (Features)

- **Vertex AI Gemini 연동**: 최신 Gemini (2.5-flash) 모델을 통해 자연스러운 대화 생성
- **멀티모달 지원**: 텍스트와 이미지 입력을 동시에 처리
- **RAG (검색 증강 생성)**: Vertex AI Search 데이터 스토어와 연동하여 사내 매뉴얼 기반의 정확한 답변 제공
- **대화 기록 관리**: 이전 대화 내용을 기억하여 문맥에 맞는 답변 생성
- **견고한 API 오류 처리**: Vertex AI API 통신 시 발생할 수 있는 다양한 예외 상황 처리
- **환경 변수 기반 설정**: Google Cloud 프로젝트 ID, 모델 ID 등 주요 설정을 코드를 수정하지 않고 변경 가능
- **정적 파일 서빙**: React, Vue 등 SPA(Single Page Application) 프론트엔드 빌드 파일을 서빙하는 기능 포함
- **Cloud Run 최적화**: Gunicorn을 사용하여 프로덕션 환경의 Google Cloud Run에 손쉽게 배포 가능

## ⚙️ 기술 스택 (Tech Stack)

- **Backend**: Python, Flask, gunicorn
- **Cloud**: Google Cloud Platform (Vertex AI, Vertex AI Search, Cloud Run, Artifact Registry)

## 🔧 사전 준비 (Prerequisites)

- Python 3.11-slim 이상
- `pip` (Python 패키지 관리자)
- **Google Cloud SDK (gcloud CLI)**
- 서비스 배포를 위한 Google Cloud 프로젝트
- 질문-답변의 기반이 될 문서들이 등록된 Vertex AI Search 데이터스토어(RAG)
- **Vertex AI 사용자(roles/aiplatform.user)** 역할을 가진 서비스 계정 ~~(로컬 테스트 시에는 키 파일, Cloud Run 배포 시에는 서비스 자체의 서비스 계정)~~
    - Google Cloud Shell 편집기!

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
LOCATION_ID="us-central1"
MODEL_ID="gemini-2.5-flash"
DATASTORE_ID="your-datastore-id"
DATASTORE_LOCATION="global"

```

### 5. 로컬 서버 실행 (Run Local Server)

```bash

# 백엔드 서버 실행
uvicorn main:app --reload --port 8000

```

## 📦 API 명세 (API Specification)

### `POST /api/generate`

사용자의 입력(텍스트, 이미지)과 대화 기록을 받아 Gemini 모델의 답변을 반환합니다.

- **Request**: `multipart/form-data`
    - `userPrompt` (string, optional): 사용자의 텍스트 질문
    - `imageFile` (file, optional): 사용자가 첨부한 이미지 파일
    - `conversationHistory` (string, required): 이전 대화 기록을 담은 JSON 배열 문자열. (예: `'[{"role": "user", ...}, {"role": "model", ...}]'`)
- **Success Response (200 OK)**:
    
    ```json
    {
      "vertexAiResponse": { ... }, // Vertex AI API의 원본 응답
      "updatedHistory": [ ... ]    // 새로운 사용자/모델 응답이 추가된 전체 대화 기록
    }
    
    ```
    
- **Error Responses**:
    - `400 Bad Request`: 요청 형식이 잘못되었거나 필수 파라미터가 누락된 경우
    - `503 Service Unavailable`: 서버 인증 정보가 설정되지 않은 경우
    - 기타 `4xx`, `5xx`: Vertex AI API 호출 중 발생한 오류 (자세한 내용은 응답 메시지 참고)

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

# 2. 빌드된 이미지를 사용하여 Cloud Run에 서비스 배포ch
# --set-env-vars 플래그에 필요한 환경 변수를 모두 추가해야 합니다.
gcloud run deploy gemini-cs-chatbot \\
  --image="gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \\
  --platform=managed \\
  --region="${LOCATION_ID}" \\
  --allow-unauthenticated \\
  --set-env-vars="PROJECT_ID=${PROJECT_ID},LOCATION_ID=${LOCATION_ID},MODEL_ID=${MODEL_ID},DATASTORE_ID=${DATASTORE_ID},DATASTORE_LOCATION=${DATASTORE_LOCATION}"

```

**중요**: Cloud Run 서비스가 사용하는 서비스 계정에 **Vertex AI 사용자(roles/aiplatform.user)** 역할 부여 여부를 확인해야 합니다.

---

## ⚠️ 오류 코드 및 처리 방식

아래는 서비스 사용 중 발생할 수 있는 오류 코드입니다. 
Vertex AI API 문서 (https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/api-errors?hl=ko) 를 바탕으로 작성되었습니다.

| 오류 유형 | 상태 코드 | 발생 조건 | 테스트 방법 | 해결 방법 |
| --- | --- | --- | --- | --- |
| **입력 누락** | `400 Bad Request` | 질문과 이미지가 모두 없는 경우 | 아무것도 입력하지 않고 제출 | 프론트에서 입력 유효성 검사로 방지됨 |
| **JSON 파싱 오류** | `400 Bad Request` | `conversationHistory` 값이 JSON 파싱 불가한 문자열일 때 | 잘못된 JSON 문자열 삽입 | 항상 `JSON.stringify()` 사용 |
| **요청 포맷 오류 (Vertex API)** | `400 Bad Request` | API에 잘못된 필드 또는 비정상 입력 전송 | 모델 ID는 정상이나 payload 구조가 잘못된 경우 | payload 구조 확인 (`tools`, `contents`, `generationConfig` 등) |
| **권한 부족 (IAM 설정 누락)** | `403 Forbidden` | 서비스 계정에 Vertex AI 접근 권한이 없을 때 | Cloud Run에 적절한 IAM 역할 부여하지 않음 | `Vertex AI User`, `Storage Viewer` 등 권한 추가 |
| **리소스 없음** | `404 Not Found` | 모델 ID 또는 데이터스토어 ID가 잘못되었을 때 | 오타 입력 또는 삭제된 리소스 사용 | ID 확인 또는 새 리소스 생성 |
| **쿼터 초과** | `429 Too Many Requests` | Vertex API 할당량 초과 | 많은 요청 반복 호출 | GCP 콘솔에서 할당량 확인 후 증가 요청 |
| **Google 인증 설정 누락** | `503 Service Unavailable` | Cloud Run 또는 로컬 환경에서 인증 설정 실패 | `credentials = None` 상태로 실행 | 로컬은 `gcloud auth application-default login`, 서버는 서비스 계정 연결 |
| **Vertex AI 서버 내부 오류** | `500 Internal Server Error` | Vertex AI 서비스 자체의 문제 발생 | 예외적 상황이므로 인위적 유도 어려움 | 잠시 후 재시도 또는 GCP 상태 확인 |
| **타임아웃** | `504 Gateway Timeout` | Vertex AI 호출이 300초 이상 지연됨 | 응답 지연 유도 (ex. 큰 입력) | `maxOutputTokens` 감소 또는 응답 속도 개선 |
| **예상치 못한 서버 오류** | `500 Internal Server Error` | 위에서 처리되지 않은 모든 예외 | 파일 누락 등으로 인한 오류 발생 | 로그 확인 후 예외 분류하여 핸들링 추가 |