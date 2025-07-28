# 📝 GraphRAG 프로젝트 초기 설정 가이드

새로운 구글 및 깃허브 계정으로 `GraphRAG` 프로젝트를 시작하는 사용자를 위한 설정 문서입니다. 이 문서는 프로젝트 실행에 필요한 모든 API 활성화, 권한 설정 및 로컬 환경 구성 단계를 안내합니다.

##  사전 준비 사항

- **GitHub 계정**: 코드 저장소에 접근하기 위해 필요합니다.
- **Google Cloud 계정**: 프로젝트에서 사용하는 Google Cloud 서비스에 접근하기 위해 필요합니다.
- **Git**: 코드를 로컬 컴퓨터로 복제하기 위해 설치되어 있어야 합니다.
- **Python (3.x 버전)**: 프로젝트를 실행하기 위해 필요합니다.
- **Node.js 및 npm**: Firebase CLI 설치를 위해 필요합니다.

---

## 1. GitHub Repository 설정

프로젝트 코드를 로컬 환경으로 가져옵니다.

```bash
git clone <YOUR_REPOSITORY_URL>
cd graphrag
```

- **[참고]** `.github/workflows` 디렉토리에 `deploy.yml`과 `firebase-hosting.yml` 파일이 있습니다. 이는 GitHub Actions를 통해 Google Cloud 및 Firebase로 자동 배포가 설정되어 있음을 의미합니다. 배포를 위해서는 GitHub 저장소 설정에 GCP 서비스 계정 키를 Secret으로 등록해야 합니다. (후반부에서 설명)

---

## 2. Google Cloud Platform (GCP) 프로젝트 설정

이 프로젝트는 Google Cloud의 여러 서비스를 사용합니다. (`cloudbuild.yaml`, `modules/services/discovery_engine_api.py`, `modules/services/vertex_api.py` 파일 참고)

### 2.1. GCP 프로젝트 생성 및 선택

1.  [Google Cloud Console](https://console.cloud.google.com/)에 로그인합니다.
2.  새로운 GCP 프로젝트를 생성하거나 기존 프로젝트를 선택합니다.

### 2.2. 필요한 API 활성화

프로젝트 실행을 위해 다음 API들을 활성화해야 합니다.
`IAM 및 관리자` > `API 및 서비스` > `라이브러리` 메뉴에서 아래 API를 검색하여 **'사용 설정'** 버튼을 클릭하세요.

- **Vertex AI API**: 핵심 AI/ML 기능을 위해 필요합니다.
- **Cloud Build API**: `cloudbuild.yaml`을 이용한 자동 빌드 및 배포에 필요합니다.
- **Identity and Access Management (IAM) API**: 서비스 계정 관리를 위해 필요합니다.
- **Vertex AI Search and Conversation API** (또는 이전 명칭인 **Discovery Engine API**): `discovery_engine_api.py`에서 사용되므로 활성화가 필요합니다.

### 2.3. 서비스 계정(Service Account) 생성 및 키 발급

애플리케이션이 GCP 서비스에 안전하게 접근하려면 서비스 계정이 필요합니다.

1.  `IAM 및 관리자` > `서비스 계정`으로 이동합니다.
2.  **'+ 서비스 계정 만들기'** 를 클릭합니다.
3.  서비스 계정 이름(예: `graphrag-runner`)을 입력하고 '만들기 및 계속'을 클릭합니다.
4.  **역할 부여**: 이 서비스 계정에 다음 역할을 부여하여 필요한 권한을 제공합니다.
    - `Vertex AI 사용자`
    - `Discovery Engine 관리자` (또는 `Vertex AI Search and Conversation 관리자`)
    - `Cloud Build 편집자`
    - `서비스 계정 사용자`
5.  '계속' 및 '완료'를 클릭하여 서비스 계정 생성을 마칩니다.
6.  생성된 서비스 계정의 이메일 주소를 클릭한 후, **'키'** 탭으로 이동합니다.
7.  **'키 추가'** > **'새 키 만들기'** 를 선택합니다.
8.  키 유형은 **JSON**으로 선택하고 '만들기'를 클릭하면 키 파일(`.json`)이 컴퓨터에 다운로드됩니다.

**[중요]** 이 JSON 키 파일은 매우 중요한 비밀 정보입니다. 절대로 Git 저장소에 직접 커밋해서는 안 됩니다. `.gitignore`에 `keys/` 디렉토리가 포함되어 있는지 확인하세요.

---

## 3. Firebase 프로젝트 설정

이 프로젝트는 `firebase.json` 및 `.firebaserc` 파일을 통해 Firebase Hosting을 사용합니다.

1.  [Firebase Console](https://console.firebase.google.com/)로 이동하여 **'프로젝트 추가'** 를 클릭합니다.
2.  위에서 생성한 **GCP 프로젝트**를 선택하여 Firebase에 연결합니다.
3.  프로젝트 대시보드에서 웹 앱을 추가하고 설정을 완료합니다.

---

## 4. 로컬 개발 환경 설정

이제 로컬에서 프로젝트를 실행할 준비를 합니다.

1.  **서비스 계정 키 배치**:
    - 2.3 단계에서 다운로드한 **서비스 계정 JSON 키 파일**의 이름을 `gcp_credentials.json` (또는 `config.py`에 명시된 이름)으로 변경합니다.
    - 이 파일을 프로젝트 내 `keys/` 디렉토리로 이동시킵니다.

2.  **Python 가상 환경 및 의존성 설치**:
    ```bash
    # Python 가상환경 생성 및 활성화
    python3 -m venv .venv
    source .venv/bin/activate

    # requirements.txt에 명시된 라이브러리 설치
    pip install -r requirements.txt
    ```

3.  **Firebase CLI 설치 및 로그인**:
    ```bash
    # Firebase Command Line Interface 설치
    npm install -g firebase-tools

    # Google 계정으로 로그인
    firebase login
    ```

4.  **프로젝트 실행**:
    이제 모든 설정이 완료되었습니다. `main.py`를 실행하여 애플리케이션을 시작할 수 있습니다.
    ```bash
    python main.py
    ```

---

이 가이드의 단계를 모두 완료하면, 당신의 로컬 환경에서 `GraphRAG` 프로젝트를 문제없이 실행하고 Google Cloud 및 Firebase의 모든 기능을 활용할 수 있습니다.
