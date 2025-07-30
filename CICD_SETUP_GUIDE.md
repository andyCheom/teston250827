# GitHub Actions CI/CD 사전 설정 가이드

이 문서는 GraphRAG 프로젝트의 CI/CD 파이프라인 (Cloud Run 및 Firebase Hosting 자동 배포)을 위한 GitHub 저장소 및 관련 서비스의 사전 설정 방법을 안내합니다. `DEPLOYMENT.md`에 명시된 워크플로우가 정상적으로 작동하기 위해 반드시 필요한 과정입니다.

---

## 1. Google Cloud 서비스 계정 키 등록

GitHub Actions가 Google Cloud 및 Firebase 프로젝트에 리소스를 배포하고 관리할 수 있도록 인증을 설정합니다.

### 1.1. 서비스 계정 준비

- `gcp_setting.md` 가이드에 따라 CI/CD용 서비스 계정을 생성했는지 확인합니다.
- 해당 서비스 계정에는 최소한 다음 역할이 부여되어야 합니다:
  - **Cloud Build 편집자**: 컨테이너 이미지를 빌드합니다.
  - **Cloud Run 관리자**: 새 버전을 배포하고 트래픽을 관리합니다.
  - **Firebase Hosting 관리자**: 웹 프론트엔드를 배포합니다.
  - **서비스 계정 사용자**: 다른 서비스에 자신의 권한으로 접근합니다.
  - **Storage 객체 뷰어/생성자**: Artifact Registry에 이미지를 푸시합니다.

### 1.2. 서비스 계정 키(JSON)를 GitHub Secrets에 등록

1.  GitHub 프로젝트 저장소에서 **Settings > Secrets and variables > Actions**로 이동합니다.
2.  **'New repository secret'** 버튼을 클릭합니다.
3.  `gcp_setting.md`를 따라 다운로드한 서비스 계정의 **JSON 키 파일 내용 전체를 복사**합니다.
4.  아래와 같이 Secret을 생성합니다.
    -   **Name**: `GCP_SA_KEY`
    -   **Secret**: 복사한 JSON 키 파일의 내용 전체를 붙여넣기
5.  **'Add secret'**을 클릭하여 저장합니다.

- **[중요]** `firebase-hosting.yml` 워크플로우는 별도의 Firebase 서비스 계정을 참조할 수 있습니다. 만약 Firebase 배포에 다른 서비스 계정을 사용한다면, 해당 키를 `FIREBASE_SERVICE_ACCOUNT`라는 이름의 Secret으로 추가 등록해야 합니다. 동일한 서비스 계정을 사용한다면 `GCP_SA_KEY` 하나만 등록해도 됩니다.

---

## 2. Slack 웹훅(Webhook) 설정 (선택 사항)

배포 성공, 실패 등의 CI/CD 상태 알림을 Slack으로 받기 위해 설정합니다.

### 2.1. Slack Incoming Webhook 생성

1.  [Slack App Directory](https://slack.com/apps)로 이동하여 **'Incoming WebHooks'**를 검색하고 설치합니다.
2.  알림을 수신할 채널을 선택하고 **'Add Incoming WebHooks integration'**을 클릭합니다.
3.  생성된 **Webhook URL**을 복사합니다. 이 URL은 `https://hooks.slack.com/services/...`와 같은 형태입니다.

### 2.2. Webhook URL을 GitHub Secrets에 등록

1.  다시 GitHub 저장소의 **Settings > Secrets and variables > Actions**로 이동합니다.
2.  **'New repository secret'** 버튼을 클릭합니다.
3.  아래와 같이 Secret을 생성합니다.
    -   **Name**: `SLACK_WEBHOOK_URL`
    -   **Secret**: 위에서 복사한 Slack Webhook URL을 붙여넣기
4.  **'Add secret'**을 클릭하여 저장합니다.

---

## 3. SSH 키 인증 설정 (필요 시)

현재 프로젝트의 배포 워크플로우는 Google Cloud 인증을 사용하므로 SSH 키가 필수는 아닙니다. 하지만 향후 CI/CD 과정에서 특정 서버(예: EC2 인스턴스)에 직접 파일을 복사하거나 명령을 실행해야 할 경우를 대비해 최신 암호화 방식으로 키를 생성하는 방법을 안내합니다.

### 3.1. SSH 키 생성 (Ed25519 방식)

보안과 성능이 뛰어난 **Ed25519** 방식을 사용하는 것을 적극 권장합니다.

```bash
# -t: 암호화 방식, -C: 주석(보통 이메일)
# 비밀번호(passphrase)는 비워두고 Enter를 누르면 CI/CD에서 사용하기 편리합니다.
ssh-keygen -t ed25519 -C "your_email@example.com"
```
- **장점**: 최신 타원 곡선 암호화 기술을 사용하여 RSA보다 빠르고 안전하며, 키 길이가 짧아 관리하기 용이합니다.
- **생성된 파일**: `id_ed25519` (비밀 키), `id_ed25519.pub` (공개 키)

### 3.2. GitHub Secrets 및 서버에 키 등록

1.  **비밀 키 등록**:
    - 위에서 생성한 **비밀 키** 파일(`id_ed25519`)의 내용을 복사합니다.
    - GitHub 저장소의 **Settings > Secrets and variables > Actions**에서 `SSH_PRIVATE_KEY`라는 이름의 Secret을 만들고 붙여넣습니다.

2.  **공개 키 등록**:
    - **공개 키** 파일(`id_ed25519.pub`)의 내용을 복사합니다.
    - SSH로 접근하려는 원격 서버의 `~/.ssh/authorized_keys` 파일에 해당 내용을 추가합니다.

---

## 4. GitHub 저장소 설정

안정적인 배포 파이프라인을 위해 `main` 및 `develop` 브랜치를 보호하는 것이 좋습니다.

1.  GitHub 저장소에서 **Settings > Branches**로 이동합니다.
2.  **'Add branch protection rule'** 버튼을 클릭합니다.
3.  **Branch name pattern**에 `main`을 입력하고 아래 규칙들을 활성화합니다.
    -   **Require a pull request before merging**: `main` 브랜치로의 직접적인 push를 막고, Pull Request(PR)를 통해서만 병합되도록 강제합니다.
    -   **Require status checks to pass before merging**: CI 빌드, 테스트 등의 검사가 모두 통과해야 병합이 가능하도록 설정합니다. (예: `build`, `test`)
4.  `develop` 브랜치에 대해서도 동일하게 보호 규칙을 설정합니다.

이 설정을 통해 코드 품질을 유지하고, 검증되지 않은 코드가 스테이징 및 프로덕션 환경에 배포되는 것을 방지할 수 있습니다.