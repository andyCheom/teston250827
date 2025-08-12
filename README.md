# GraphRAG Chatbot API

![Diagram](img/diagram.png)

---

## 1. 프로젝트 개요 (Overview)

이 프로젝트는 Google Cloud Discovery Engine을 활용한 지능형 챗봇 API 시스템입니다. Discovery Engine의 Answer API와 Search API를 조합하여, 사용자의 텍스트 기반 질문에 대해 정확하고 맥락에 맞는 답변을 생성합니다. 특히 한국어 질의응답에 최적화되어 있으며, 모듈화된 아키텍처를 통해 유지보수와 확장성을 높였습니다.

### 주요 기능
- **Discovery Engine 기반 검색**: AI 기반의 지능형 검색, 자연어 답변 생성, 관련 질문 추천
- **간결한 텍스트 인터페이스**: 실시간 웹 채팅 및 마크다운 형식의 답변 렌더링
- **체계적인 아키텍처**: 인증, 설정, API 라우팅, 서비스 로직의 명확한 분리

---

## 2. 기술 스택 (Tech Stack)

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Search Engine**: Google Cloud Discovery Engine (Answer API, Search API)
- **Cloud Platform**: Google Cloud Platform (Cloud Run, Cloud Storage, Cloud Build, Artifact Registry)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3, Marked.js
- **CI/CD**: GitHub Actions, Google Cloud Build
- **Hosting**: Firebase Hosting

---

## 3. 시작하기 (Getting Started)

### 3.1. 자동 설정 (권장)

이 프로젝트는 복잡한 GCP 및 Firebase 설정을 자동화하는 스크립트를 제공합니다.

**사전 요구사항:**
- Python 3.11+ 및 pip
- Google Cloud SDK (gcloud CLI) 설치 및 로그인 (`gcloud auth login`)
- GCP 프로젝트에 대한 편집자 이상의 권한

**실행 절차:**
1.  **.env 파일 준비**:
    ```bash
    cp .env.example .env
    ```
    `.env` 파일을 열어 `PROJECT_ID`를 실제 GCP 프로젝트 ID로 수정합니다.

2.  **의존성 설치**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **자동 설정 스크립트 실행**:
    ```bash
    python setup.py
    ```
    이 스크립트는 필요한 모든 GCP 리소스(API 활성화, 서비스 계정, Storage 버킷, Discovery Engine 등)와 Firebase 호스팅 설정을 자동으로 구성합니다.

### 3.2. 로컬 서버 실행

설정이 완료되면 아래 명령어로 로컬에서 테스트 서버를 실행할 수 있습니다.

```bash
# 가상 환경 활성화 (Windows)
venv\Scripts\activate

# FastAPI 서버 실행
uvicorn main:app --reload --port 8000
```
서버 실행 후 `http://localhost:8000` 주소로 접속하여 웹 인터페이스를 확인할 수 있습니다.

---

## 4. CI/CD 자동 배포

이 프로젝트는 GitHub Actions를 통해 백엔드와 프론트엔드 배포를 자동화합니다.

### 배포 흐름
- **백엔드 (API)**: `main.py`, `modules/**` 등 백엔드 관련 파일이 `main` 또는 `develop` 브랜치에 푸시되면 `deploy.yml` 워크플로우가 실행됩니다.
  1.  GitHub Actions가 Google Cloud Build를 트리거합니다.
  2.  `cloudbuild.yaml` 설정에 따라 Docker 이미지가 빌드됩니다.
  3.  빌드된 이미지는 Artifact Registry에 저장됩니다.
  4.  새 이미지를 사용하여 Cloud Run에 무중단 배포(Blue-Green)가 진행됩니다.

- **프론트엔드 (웹)**: `public/**` 등 프론트엔드 파일이 변경되면 `firebase-hosting.yml` 워크플로우가 실행되어 Firebase Hosting에 직접 배포됩니다.

### GitHub Secrets 설정
자동 배포 및 알림을 위해 GitHub 저장소에 다음 Secrets를 설정해야 합니다.
- `GCP_SA_KEY`: GCP 서비스 계정 키 (JSON)
- `FIREBASE_SA_KEY`: Firebase 서비스 계정 키 (JSON)
- `GOOGLE_CHAT_WEBHOOK_URL`: 배포 알림을 받을 Google Chat 웹훅 URL

---

## 5. 프로젝트 구조 및 모듈 설명

```
graphrag/
├── main.py              # FastAPI 앱 엔트리포인트
├── setup.py             # 프로젝트 자동 설정 스크립트
├── requirements.txt     # Python 의존성
├── markdown/            # 모든 원본 .md 문서 보관
├── modules/             # 핵심 소스 코드
│   ├── auth.py          # Google Cloud 인증 관리
│   ├── config.py        # 환경 설정 관리
│   ├── routers/         # API 엔드포인트 정의
│   └── services/        # 비즈니스 로직 (Discovery Engine 연동 등)
├── public/              # 웹 인터페이스 정적 파일
└── .github/workflows/   # CI/CD 워크플로우 (YAML)
```

### `modules` 폴더 상세
- **`auth.py`**: Google Cloud 서비스 사용에 필요한 인증을 처리합니다.
- **`config.py`**: `.env` 파일에서 환경 변수를 로드하여 프로젝트 전반의 설정을 관리합니다.
- **`routers/`**: FastAPI를 사용하여 API 엔드포인트를 정의합니다.
  - `api.py`: 메인 질의응답 API (`/api/generate`)
  - `conversation_api.py`: 대화 기록 조회 및 관리 API
- **`services/`**: 핵심 비즈니스 로직을 구현합니다.
  - `discovery_engine_api.py`: Discovery Engine 검색 및 답변 생성 로직
  - `conversation_logger.py`: 대화 내용을 Cloud Storage에 저장하는 로직
- **`setup/`**: `setup.py`에서 호출하는 자동 설정 모듈들입니다.
  - `gcp_setup.py`: GCP 리소스(Discovery Engine, Storage, Cloud Run 등) 생성
  - `firebase_setup.py`: Firebase 프로젝트 및 호스팅 설정
  - `cicd_setup.py`: CI/CD 관련 설정 파일 생성

---

## 6. API 명세 (주요 엔드포인트)

### `POST /api/generate`
사용자의 질문과 대화 기록을 받아 Discovery Engine 기반의 답변을 반환합니다.

- **Request Body** (`application/x-www-form-urlencoded`):
  - `userPrompt` (string, required): 사용자 질문
  - `conversationHistory` (string, required): 이전 대화 기록 (JSON 배열 문자열)
- **Success Response** (200 OK):
  ```json
  {
    "answer": "생성된 답변 텍스트",
    "citations": [...],
    "search_results": [...],
    "related_questions": [...],
    "updatedHistory": [...]
  }
  ```

---

## 7. 사용된 Google Cloud APIs

- **Discovery Engine API**: AI 기반 검색 및 답변 생성
- **Cloud Storage API**: 대화 기록 및 문서 파일 저장
- **Cloud Run API**: 서버리스 컨테이너 배포 및 관리
- **Cloud Build API**: Docker 이미지 자동 빌드
- **Artifact Registry API**: 빌드된 Docker 이미지 저장
- **Firebase Hosting API**: 정적 웹사이트 호스팅

자세한 내용은 `markdown/Google-Cloud-APIs-설명.md` 문서를 참고하세요.
