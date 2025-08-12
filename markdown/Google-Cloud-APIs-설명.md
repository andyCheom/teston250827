# GraphRAG 프로젝트에서 사용하는 Google Cloud APIs 설명

이 문서는 GraphRAG 프로젝트에서 사용하는 Google Cloud APIs들이 각각 어떤 용도로 사용되는지 설명합니다.

## 📋 API 목록 및 용도

### 🔍 **discoveryengine.googleapis.com**
**용도**: AI 기반 검색 및 답변 생성
```
📍 사용 위치: modules/services/discovery_engine_api.py
📝 주요 기능:
  • 사용자 질문에 대한 지능형 검색
  • 업로드된 문서들에서 관련 정보 추출
  • 자연어 답변 자동 생성
  • 관련 질문 추천
```
**실제 사용 예시**: 사용자가 "GraphRAG가 뭐야?"라고 질문하면, Discovery Engine이 관련 문서를 찾아서 답변을 생성해줍니다.

---

### 💾 **storage-api.googleapis.com**
**용도**: Google Cloud Storage 파일 관리
```
📍 사용 위치: 
  • modules/services/conversation_logger.py (대화 내용 저장)
  • modules/routers/api.py (파일 업로드/다운로드)
📝 주요 기능:
  • 대화 내용을 JSON 파일로 저장
  • 문서 파일 업로드/다운로드
  • 파일 권한 관리
```

### 🔧 **storage-component.googleapis.com** 
**용도**: Cloud Storage 내부 구성 요소
```
📝 주요 기능:
  • Storage API의 핵심 기능 지원
  • 버킷 생성 및 관리
  • CORS 설정 등 고급 기능
```
**참고**: storage-api.googleapis.com과 함께 사용되는 보조 API입니다.

---

### 🏗️ **cloudbuild.googleapis.com**
**용도**: Docker 이미지 자동 빌드
```
📍 사용 위치: 
  • cloudbuild.yaml (CI/CD 파이프라인)
  • .github/workflows/deploy.yml (GitHub Actions)
📝 주요 기능:
  • Python 코드를 Docker 이미지로 패키지화
  • 자동 빌드 파이프라인 실행
  • Artifact Registry에 이미지 저장
```
**실제 사용 예시**: 코드를 GitHub에 푸시하면 Cloud Build가 자동으로 Docker 이미지를 만들어서 배포 준비를 해줍니다.

---

### 🚀 **run.googleapis.com**
**용도**: 서버리스 컨테이너 배포 및 관리
```
📍 사용 위치:
  • cloudbuild.yaml (자동 배포)
  • modules/setup/gcp_setup.py (초기 설정)
📝 주요 기능:
  • FastAPI 백엔드 서버 배포
  • 무중단 블루-그린 배포
  • 자동 스케일링 (트래픽에 따라 서버 개수 조절)
  • HTTPS 자동 설정
```
**실제 사용 예시**: 사용자가 많아지면 자동으로 서버를 늘리고, 적어지면 줄여서 비용을 절약합니다.

---

### 🔥 **firebase.googleapis.com**
**용도**: Firebase 프로젝트 기본 관리
```
📍 사용 위치: modules/setup/firebase_setup.py
📝 주요 기능:
  • Firebase 프로젝트 활성화
  • Firebase 서비스 전반적인 관리
  • 프로젝트 설정 및 구성
```

### 🌐 **firebasehosting.googleapis.com**
**용도**: 무료 웹사이트 호스팅
```
📍 사용 위치: 
  • .github/workflows/firebase-hosting.yml
  • modules/setup/firebase_setup.py
📝 주요 기능:
  • public/ 폴더의 HTML, CSS, JS 파일들을 웹사이트로 배포
  • CDN을 통한 전 세계 빠른 접속
  • 커스텀 도메인 설정
  • SSL 인증서 자동 적용
```
**실제 사용 예시**: public/index.html을 수정하고 푸시하면 자동으로 웹사이트가 업데이트됩니다.

---

### ⚡ **cloudfunctions.googleapis.com**
**용도**: 서버리스 함수 (현재 사용하지 않음)
```
📝 주요 기능:
  • 이벤트 기반 서버리스 함수 실행
  • Firebase와 연동 가능
📍 현재 상태: 
  • GraphRAG 프로젝트에서는 실제로 사용하지 않음
  • Cloud Run으로 모든 백엔드 처리를 하고 있음
  • 향후 확장 가능성을 위해 활성화해둔 상태
```

---

## 🔄 API들이 함께 작동하는 흐름

### 사용자가 질문할 때:
```
1. 🌐 사용자가 웹사이트 접속 (Firebase Hosting)
2. 📝 질문 입력 후 전송
3. 🚀 Cloud Run 서버가 요청 받음
4. 🔍 Discovery Engine이 답변 생성
5. 💾 Cloud Storage에 대화 내용 저장
6. 📱 사용자에게 답변 전달
```

### 개발자가 코드 수정할 때:
```
1. 💻 개발자가 git push
2. 🏗️ Cloud Build가 Docker 이미지 생성
3. 🚀 Cloud Run에 새 버전 배포
4. 🌐 Firebase Hosting에 웹사이트 업데이트
```

## 📊 비용 및 사용량 모니터링

각 API의 사용량은 Google Cloud Console에서 확인할 수 있습니다:

| API | 무료 한도 | 과금 시점 |
|-----|-----------|-----------|
| **Discovery Engine** | 월 1,000회 쿼리 | 초과 시 쿼리당 과금 |
| **Cloud Storage** | 5GB 저장공간 | 초과 시 GB당 과금 |
| **Cloud Run** | 월 200만 요청 | 초과 시 요청당 과금 |
| **Firebase Hosting** | 10GB 전송량 | 초과 시 GB당 과금 |
| **Cloud Build** | 일 120분 빌드시간 | 초과 시 분당 과금 |

**💡 팁**: 개인 프로젝트나 소규모 테스트라면 대부분 무료 한도 내에서 사용 가능합니다!

---

## 🛠️ API 활성화 확인 방법

```bash
# 현재 활성화된 API 확인
gcloud services list --enabled --project=YOUR_PROJECT_ID

# 특정 API 상태 확인
gcloud services list --filter="name:discoveryengine.googleapis.com"

# API 수동 활성화 (필요시)
gcloud services enable discoveryengine.googleapis.com
```

---

## ❌ 사용하지 않는 API 정리

현재 GraphRAG 프로젝트에서 **실제로 사용하지 않는 API**:
- `cloudfunctions.googleapis.com` - Cloud Functions 미사용

**삭제 가능한가요?**
- ✅ 삭제 가능하지만, 향후 확장성을 위해 유지하는 것을 추천
- 비활성화해도 비용은 발생하지 않음 (실제 사용 시에만 과금)

이제 각 API가 프로젝트에서 어떤 역할을 하는지 완전히 이해하셨을 것입니다! 🎉