# GraphRAG Chatbot API

![Diagram!](img/diagram.png)
---

## 개요 (Overview)

GraphRAG 기반의 지능형 챗봇 API 시스템입니다. Google Cloud Spanner의 Triple 데이터를 활용한 지식 그래프와 Vertex AI Gemini 모델을 결합하여 정확하고 맥락적인 답변을 생성합니다.

- **모듈화된 아키텍처**: 유지보수성과 확장성을 위한 체계적인 코드 구조
- **한국어 최적화**: 띄어쓰기 교정, 오타 수정, 불용어 처리 등 한국어 특화 텍스트 처리
- **고성능 검색**: 병렬 처리 및 다중 캐싱 전략으로 최적화된 응답 속도

---

## ✨ 주요 기능 (Features)

### 🧠 지능형 텍스트 처리
- **한국어 띄어쓰기 교정**: PyKoSpacing을 활용한 정확한 띄어쓰기 보정
- **오타 자동 수정**: 흔한 한국어/영어 오타 패턴 인식 및 교정
- **불용어 필터링**: 681개의 한국어/영어 불용어를 활용한 검색 키워드 최적화
- **스마트 키워드 추출**: 검색 효율성을 위한 지능형 키워드 분석

### 🚀 GraphRAG 검색 엔진
- **Triple 기반 검색**: Spanner 데이터베이스의 지식 그래프에서 정확한 정보 검색
- **다단계 폴백 검색**: 검색 결과가 없을 경우 자동으로 더 유연한 검색 수행
- **병렬 처리**: 여러 검색 작업을 동시에 수행하여 응답 속도 40-60% 향상
- **멀티레벨 캐싱**: 메모리, 데이터베이스 연결, API 헤더 단계별 캐싱

### 🔧 모듈화된 아키텍처
- **인증 관리**: 중앙화된 Google Cloud 인증 시스템
- **설정 관리**: 환경 변수 기반 동적 설정
- **라우터 분리**: FastAPI 라우터를 통한 API 엔드포인트 체계화
- **서비스 레이어**: Vertex AI API 통신 최적화

## ⚙️ 기술 스택 (Tech Stack)

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Database**: Google Cloud Spanner (Triple Store)
- **AI/ML**: Google Vertex AI Gemini, PyKoSpacing
- **Cloud**: Google Cloud Platform (Vertex AI, Spanner, Cloud Storage, Cloud Run)
- **Authentication**: Google Cloud IAM, Service Accounts

## 📁 프로젝트 구조 (Project Structure)

```
graphrag/
├── main.py                    # FastAPI 앱 엔트리포인트
├── requirements.txt           # Python 의존성
├── stopwords.txt             # 불용어 사전 (681개)
├── src/                      # 모듈화된 소스 코드
│   ├── auth.py              # Google Cloud 인증 관리
│   ├── config.py            # 환경 설정 관리
│   ├── cache.py             # 메모리 캐싱 시스템
│   ├── database.py          # Spanner 데이터베이스 연동
│   ├── text_processor.py    # 텍스트 전처리 엔진
│   ├── routers/
│   │   └── api.py          # API 라우터
│   └── services/
│       └── vertex_api.py   # Vertex AI API 클라이언트
└── public/                  # 정적 파일 (선택사항)
```

## 🔧 사전 준비 (Prerequisites)

- **Python 3.11+** 및 pip 패키지 관리자
- **Google Cloud SDK (gcloud CLI)**
- **Google Cloud 프로젝트** (Vertex AI, Spanner 서비스 활성화)
- **Spanner 인스턴스 및 데이터베이스** (Triple 데이터 저장용)
- **서비스 계정** (다음 권한 필요):
  - `roles/aiplatform.user` (Vertex AI 사용)
  - `roles/spanner.databaseUser` (Spanner 읽기)
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