# GitHub Secrets 설정 가이드

GitHub Actions에서 Google Chat 웹훅을 사용하기 위한 시크릿 설정 방법입니다.

## 📋 필요한 GitHub Secrets

### 1. GOOGLE_CHAT_WEBHOOK_URL
- **설명**: Google Chat 웹훅 URL (배포 알림용)
- **형식**: `https://chat.googleapis.com/v1/spaces/YOUR_SPACE_ID/messages?key=YOUR_KEY&token=YOUR_TOKEN`

### 2. 기존 GCP 관련 Secrets (이미 설정되어 있다면 그대로 사용)
- `GCP_SA_KEY`: Google Cloud Service Account JSON 키
- `FIREBASE_SA_KEY`: Firebase Service Account JSON 키

## 🔧 GitHub Secrets 설정 방법

### 1. Repository Secrets 페이지 접속
1. GitHub 저장소로 이동
2. **Settings** 탭 클릭
3. 좌측 메뉴에서 **Secrets and variables** > **Actions** 클릭

### 2. Google Chat 웹훅 URL 추가
1. **New repository secret** 클릭
2. **Name**: `GOOGLE_CHAT_WEBHOOK_URL` 입력
3. **Secret**: Google Chat 웹훅 URL 전체를 붙여넣기
4. **Add secret** 클릭

## 🎯 Google Chat 웹훅 URL 생성 방법

### 1. Google Chat Space 생성
```
1. Google Chat (https://chat.google.com) 접속
2. 새로운 Space 만들기
3. Space 이름: "GraphRAG 배포 알림" (원하는 이름)
4. 필요한 팀원들 초대
```

### 2. Incoming Webhook 앱 추가
```
1. 생성한 Space 입장
2. Space 이름 옆 ▼ 클릭
3. "Apps & integrations" 선택
4. "Find apps" 검색창에 "Incoming Webhook" 입력
5. "Incoming Webhook" 앱 선택 후 "Add" 클릭
```

### 3. 웹훅 설정 및 URL 복사
```
1. "Configure" 버튼 클릭
2. 웹훅 이름: "GraphRAG 배포 알림" (원하는 이름)
3. 아바타 이미지 설정 (선택사항)
4. "Save" 버튼 클릭
5. 생성된 웹훅 URL 복사
```

## 📝 설정 확인 방법

### 1. 웹훅 테스트
로컬에서 다음 명령으로 웹훅이 작동하는지 테스트:

```bash
# 환경변수 설정
export GOOGLE_CHAT_WEBHOOK_URL="여기에_실제_웹훅_URL_입력"

# 테스트 메시지 전송
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🧪 GitHub Actions 웹훅 테스트",
    "cards": [{
      "sections": [{
        "widgets": [{
          "keyValue": {
            "topLabel": "상태",
            "content": "테스트 성공"
          }
        }]
      }]
    }]
  }' \
  "$GOOGLE_CHAT_WEBHOOK_URL"
```

### 2. GitHub Actions 워크플로우 테스트
1. 코드를 main 또는 develop 브랜치에 push
2. GitHub Actions 탭에서 워크플로우 실행 확인
3. Google Chat Space에서 배포 알림 수신 확인

## 🔒 보안 고려사항

### 1. 웹훅 URL 보호
- ✅ GitHub Secrets에만 저장
- ❌ 코드나 로그에 노출 금지
- ❌ 공개 저장소에서 URL 하드코딩 금지

### 2. Space 권한 관리
- 배포 알림을 받을 사람만 Space에 초대
- 필요 시 Space 접근 권한 제한

### 3. 웹훅 순환 (필요 시)
- 보안상 필요하면 주기적으로 웹훅 재생성
- 새 웹훅 생성 후 GitHub Secrets 업데이트

## 📋 GitHub Secrets 체크리스트

- [ ] `GOOGLE_CHAT_WEBHOOK_URL` 추가됨
- [ ] `GCP_SA_KEY` 설정됨 (GCP 배포용)
- [ ] `FIREBASE_SA_KEY` 설정됨 (Firebase 배포용)
- [ ] 웹훅 테스트 완료
- [ ] 실제 배포 시 알림 수신 확인

## 🚨 문제 해결

### 1. 알림이 오지 않는 경우
```bash
# GitHub Actions 로그 확인
- "⚠️ GOOGLE_CHAT_WEBHOOK_URL이 설정되지 않았습니다" 메시지 확인
- curl 명령의 응답 코드 확인 (200이어야 정상)
```

### 2. 403/401 오류 발생 시
- Google Chat 웹훅 URL이 올바른지 확인
- Space에서 Incoming Webhook 앱이 활성화되어 있는지 확인
- 웹훅이 삭제되지 않았는지 확인

### 3. JSON 파싱 오류 시
- 페이로드의 JSON 형식이 올바른지 확인
- 특수문자나 이스케이프 문자 확인

## 📞 지원

문제가 계속 발생하면:
1. GitHub Actions 워크플로우 로그 확인
2. Google Chat Space의 웹훅 설정 재확인
3. 웹훅 URL 재생성 후 GitHub Secrets 업데이트 시도