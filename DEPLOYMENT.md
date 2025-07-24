# GraphRAG 챗봇 API - 지속적 배포 가이드

## 📋 개요

이 문서는 GraphRAG 챗봇 API의 지속적 배포(CI/CD) 설정 방법을 설명합니다.

## 🚀 배포 방식

### 1. Cloud Build (권장)
- **Blue-Green 배포**: 무중단 배포
- **자동 헬스 체크**: 배포 후 자동 검증
- **롤백 지원**: 문제 발생 시 즉시 이전 버전으로 복구

### 2. GitHub Actions
- **브랜치 기반 배포**: main(production), develop(staging)
- **보안 스캔**: Trivy를 통한 취약점 검사
- **Slack 알림**: 배포 결과 실시간 알림

## ⚙️ 설정 방법

### Cloud Build 트리거 설정

1. **Google Cloud Console**에서 Cloud Build > 트리거로 이동
2. **트리거 만들기** 클릭
3. 다음 설정 적용:

```yaml
name: graphrag-api-deploy
description: GraphRAG API 자동 배포
github:
  owner: [GITHUB_USERNAME]
  name: [REPOSITORY_NAME]
  push:
    branch: ^main$|^develop$
  
configuration:
  type: Cloud Build configuration file
  path: cloudbuild.yaml

substitutions:
  _PROJECT_ID: cheom-kdb-test1
  _REGION: asia-northeast3
  _SERVICE_NAME: testing0724
```

### GitHub Secrets 설정

GitHub 리포지토리 > Settings > Secrets and variables > Actions에서 다음 설정:

```
GCP_SA_KEY: [서비스 계정 JSON 키]
SLACK_WEBHOOK_URL: [선택사항 - Slack 알림용]
```

## 📊 배포 단계

### Cloud Build 파이프라인

1. **사전 검증** (1분)
   - Dockerfile, requirements.txt 존재 확인
   - 환경 변수 검증

2. **이미지 빌드** (5-8분)
   - Docker 이미지 생성
   - 캐시 활용으로 빌드 시간 단축

3. **이미지 푸시** (1-2분)
   - Artifact Registry에 이미지 업로드
   - latest, SHA 태그 동시 생성

4. **보안 스캔** (2-3분)
   - 취약점 검사 실행
   - 심각한 문제 발견 시 배포 중단

5. **후보 배포** (2-3분)
   - 새 버전을 candidate 태그로 배포
   - 트래픽 전환 없이 대기

6. **헬스 체크** (2-5분)
   - /api/health 엔드포인트 검증
   - /api/generate 기능 테스트
   - 최대 5회 재시도

7. **트래픽 전환** (30초)
   - Blue-Green 방식으로 트래픽 100% 전환
   - 즉시 서비스 제공 시작

8. **정리 작업** (1분)
   - 이전 버전 태그 제거
   - 오래된 리비전 삭제 (최근 5개만 유지)

## 🔧 환경 설정

### 개발 환경 (develop 브랜치)
```yaml
SERVICE_NAME: testing0724
MIN_INSTANCES: 0
MAX_INSTANCES: 10
MEMORY: 2Gi
CPU: 1
```

### 프로덕션 환경 (main 브랜치)
```yaml
SERVICE_NAME: graphrag-api
MIN_INSTANCES: 1
MAX_INSTANCES: 20
MEMORY: 4Gi
CPU: 2
```

## 🛠️ 수동 배포

### Cloud Build 직접 실행
```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD)
```

### 긴급 롤백
```bash
# 이전 버전으로 트래픽 전환
gcloud run services update-traffic testing0724 \
  --to-revisions=[PREVIOUS_REVISION]=100 \
  --region=asia-northeast3
```

## 📱 모니터링

### Cloud Run 메트릭
- **요청 지연시간**: 평균 < 2초
- **오류율**: < 1%
- **CPU 사용률**: < 70%
- **메모리 사용률**: < 80%

### 알림 설정
```bash
# 오류율 5% 초과 시 알림
gcloud alpha monitoring policies create \
  --policy-from-file=monitoring-policy.yaml
```

## 🔍 문제 해결

### 배포 실패 시
1. **Cloud Build 로그 확인**
   ```bash
   gcloud builds log [BUILD_ID]
   ```

2. **Cloud Run 로그 확인**
   ```bash
   gcloud logs read "resource.type=cloud_run_revision" \
     --limit=100 --format="value(textPayload)"
   ```

3. **헬스 체크 실패**
   - `/api/health` 엔드포인트 응답 확인
   - 환경 변수 설정 검증
   - 서비스 계정 권한 확인

### 자주 발생하는 문제

| 문제 | 원인 | 해결방법 |
|------|------|----------|
| 빌드 실패 | requirements.txt 누락 패키지 | 의존성 추가 |
| 헬스 체크 실패 | Cold start 지연 | timeout 증가 |
| 권한 오류 | 서비스 계정 권한 부족 | IAM 역할 확인 |
| 메모리 부족 | 메모리 할당 부족 | 메모리 설정 증가 |

## 📈 성능 최적화

### 빌드 최적화
- **멀티스테이지 빌드**: Dockerfile 최적화
- **레이어 캐싱**: 자주 변경되지 않는 부분을 먼저 복사
- **병렬 빌드**: 고사양 빌드 머신 사용

### 런타임 최적화
- **최소 인스턴스**: Cold start 최소화
- **동시성 설정**: 요청 처리 효율성 증대
- **리소스 튜닝**: CPU/메모리 적절한 할당

## 🔐 보안 고려사항

1. **컨테이너 보안**
   - 정기적인 베이스 이미지 업데이트
   - 취약점 스캔 결과 모니터링

2. **접근 제어**
   - 서비스 계정 최소 권한 원칙
   - VPC 네트워크 보안 규칙

3. **데이터 보호**
   - 환경 변수 암호화
   - Secret Manager 활용

## 📞 지원

배포 관련 문제가 발생하면:
1. 이 문서의 문제 해결 섹션 참조
2. Cloud Build 로그 및 Cloud Run 로그 확인
3. 필요시 롤백 후 원인 분석