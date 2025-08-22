# 🤖 GraphRAG 위젯 통합 가이드

GraphRAG 챗봇 위젯을 다른 웹사이트에 쉽게 임베드할 수 있는 완전한 가이드입니다.

## 📋 목차

1. [빠른 시작](#빠른-시작)
2. [설정 옵션](#설정-옵션)
3. [API 엔드포인트](#api-엔드포인트)
4. [사용자 정의](#사용자-정의)
5. [문제 해결](#문제-해결)

## 🚀 빠른 시작

### 기본 임베드

가장 간단한 방법으로 위젯을 추가하려면 다음 코드를 HTML의 `</body>` 태그 직전에 추가하세요:

```html
<!-- GraphRAG 챗봇 위젯 -->
<script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
```

### 사용자 정의 설정과 함께 임베드

```html
<script>
// 위젯 설정 (스크립트 로드 전에 정의)
window.GraphRAGWidgetConfig = {
    apiBaseUrl: 'https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app',
    firebaseProjectId: 'sampleprojects-468223',
    version: '1.0.0'
};
</script>
<script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
```

## ⚙️ 설정 옵션

### 기본 설정

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `apiBaseUrl` | Cloud Run URL | GraphRAG API의 기본 URL |
| `firebaseProjectId` | `sampleprojects-468223` | Firebase 프로젝트 ID |
| `version` | `1.0.0` | 위젯 버전 |

### 고급 설정 예제

```javascript
window.GraphRAGWidgetConfig = {
    // API 설정
    apiBaseUrl: 'https://your-api-domain.com',
    firebaseProjectId: 'your-firebase-project',
    
    // UI 설정
    theme: {
        primaryColor: '#667eea',
        backgroundColor: '#ffffff',
        textColor: '#2d3748'
    },
    
    // 기능 설정
    features: {
        fileUpload: false,
        voiceInput: false,
        typing: true
    },
    
    // 메시지 설정
    welcomeMessage: '안녕하세요! 무엇을 도와드릴까요?',
    placeholder: '메시지를 입력하세요...',
    
    // 디버그
    debug: false
};
```

## 📡 API 엔드포인트

### 위젯 관련 엔드포인트

| 엔드포인트 | 설명 | 방법 |
|------------|------|------|
| `/widget.js` | 위젯 스크립트 파일 | GET |
| `/widget-example` | 임베드 예제 페이지 | GET |
| `/api/generate` | 챗봇 응답 생성 | POST |

### 챗봇 API 사용법

```javascript
// POST /api/generate
{
    "userPrompt": "사용자 메시지",
    "conversationHistory": [
        {
            "user": "이전 사용자 메시지",
            "bot": "이전 봇 응답"
        }
    ]
}

// 응답
{
    "response": "AI 생성 응답",
    "status": "success"
}
```

## 🎨 사용자 정의

### CSS 커스터마이징

위젯은 독립적인 CSS 네임스페이스를 사용하므로 기존 사이트 스타일과 충돌하지 않습니다. 
하지만 필요한 경우 다음과 같이 스타일을 오버라이드할 수 있습니다:

```css
/* 위젯 컨테이너 위치 조정 */
#graphrag-chatbot-container {
    bottom: 30px !important;
    right: 30px !important;
}

/* 토글 버튼 색상 변경 */
#graphrag-toggle {
    background: linear-gradient(135deg, #your-color1, #your-color2) !important;
}

/* 위젯 크기 조정 */
#graphrag-widget {
    width: 350px !important;
    height: 500px !important;
}
```

### JavaScript 이벤트

위젯은 사용자 정의 이벤트를 발생시킵니다:

```javascript
// 위젯 열림/닫힘 이벤트 감지
document.addEventListener('graphrag:widget:opened', function() {
    console.log('위젯이 열렸습니다');
});

document.addEventListener('graphrag:widget:closed', function() {
    console.log('위젯이 닫혔습니다');
});

// 메시지 전송 이벤트 감지
document.addEventListener('graphrag:message:sent', function(event) {
    console.log('메시지 전송:', event.detail.message);
});

document.addEventListener('graphrag:message:received', function(event) {
    console.log('응답 수신:', event.detail.response);
});
```

## 🔧 프로그래밍 방식 제어

### 수동 초기화

```javascript
// 위젯을 수동으로 제어하고 싶은 경우
<script src="https://your-domain.com/widget.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    const widget = window.initGraphRAGWidget({
        apiBaseUrl: 'https://your-api-domain.com'
    });
    
    // 위젯 제어
    widget.open();     // 위젯 열기
    widget.close();    // 위젯 닫기
    widget.toggle();   // 위젯 토글
    widget.sendMessage('안녕하세요'); // 프로그래밍 방식 메시지 전송
});
</script>
```

### 동적 설정 변경

```javascript
// 런타임에 설정 변경
if (window.graphragWidget) {
    window.graphragWidget.updateConfig({
        welcomeMessage: '새로운 환영 메시지'
    });
}
```

## 🌐 멀티 도메인 배포

### CORS 설정

서버에서 CORS를 적절히 설정해야 합니다:

```python
# main.py
allowed_origins = [
    "https://your-website.com",
    "https://www.your-website.com",
    "https://subdomain.your-website.com"
]
```

환경변수로 설정:

```bash
export ALLOWED_ORIGINS="https://site1.com,https://site2.com,https://site3.com"
```

### Firebase 보안 규칙

Firestore 보안 규칙을 업데이트하여 외부 도메인에서의 접근을 허용:

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /conversations/{sessionId} {
      allow read, write: if request.auth == null; // 익명 접근 허용
    }
  }
}
```

## 📱 반응형 디자인

위젯은 자동으로 반응형으로 동작합니다:

- **데스크톱**: 400px × 600px 고정 크기
- **태블릿**: 유연한 크기 조정
- **모바일**: 전체 화면 - 여백 (40px)

### 모바일 최적화

```css
/* 모바일에서 위젯 위치 조정 */
@media (max-width: 480px) {
    #graphrag-chatbot-container {
        bottom: 10px !important;
        right: 10px !important;
        left: 10px !important;
    }
}
```

## 🔍 문제 해결

### 일반적인 문제

#### 1. 위젯이 표시되지 않음

```javascript
// 디버그 모드 활성화
window.GraphRAGWidgetConfig = {
    debug: true,
    // ... 기타 설정
};
```

브라우저 콘솔에서 오류 메시지를 확인하세요.

#### 2. API 호출 실패

- CORS 설정 확인
- API 엔드포인트 URL 확인
- 네트워크 연결 상태 확인

#### 3. Firebase 연결 실패

- Firebase 프로젝트 ID 확인
- 보안 규칙 설정 확인
- 브라우저의 JavaScript 활성화 상태 확인

#### 4. 스타일 충돌

위젯은 독립적인 CSS를 사용하지만, 필요한 경우:

```css
/* 위젯 z-index 조정 */
#graphrag-chatbot-container {
    z-index: 2147483647 !important;
}
```

### 디버깅 도구

```javascript
// 위젯 상태 확인
console.log('위젯 상태:', window.graphragWidget?.getState());

// 설정 확인
console.log('위젯 설정:', window.graphragWidget?.getConfig());

// 대화 히스토리 확인
console.log('대화 히스토리:', window.graphragWidget?.getHistory());
```

## 📊 성능 최적화

### 지연 로딩

```html
<!-- 사용자 인터랙션 후 로딩 -->
<script>
function loadChatWidget() {
    const script = document.createElement('script');
    script.src = 'https://your-domain.com/widget.js';
    document.head.appendChild(script);
}

// 스크롤이나 클릭 시 로딩
window.addEventListener('scroll', loadChatWidget, { once: true });
</script>
```

### CDN 사용

```html
<!-- CDN을 통한 빠른 로딩 (예시) -->
<script src="https://cdn.your-domain.com/widget.js"></script>
```

## 🔐 보안 고려사항

### 1. API 키 보호

클라이언트에서는 공개 API만 사용하고, 민감한 API 키는 서버에서 관리하세요.

### 2. 입력 검증

사용자 입력에 대한 적절한 검증과 sanitization이 서버에서 수행됩니다.

### 3. HTTPS 필수

위젯은 HTTPS 환경에서만 정상적으로 작동합니다.

## 📞 지원

문제가 발생하거나 추가 기능이 필요한 경우:

- **이메일**: support@your-domain.com
- **문서**: https://your-domain.com/docs
- **예제**: https://your-domain.com/widget-example

---

**버전**: 1.0.0  
**마지막 업데이트**: 2025-08-21  
**호환성**: 모든 최신 브라우저 (Chrome, Firefox, Safari, Edge)