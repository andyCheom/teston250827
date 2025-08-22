# 🚀 기존 GraphRAG 위젯을 다른 웹사이트에 임베드하는 방법

기존에 작성된 `/public` 폴더의 위젯 파일들을 다른 웹사이트에서 사용할 수 있게 하는 완벽한 가이드입니다.

## 📦 포함된 파일들

현재 위젯은 다음 파일들로 구성되어 있습니다:

- `widget.html` - 위젯 HTML 구조
- `widget-script.js` - 위젯 JavaScript 로직
- `enhanced-chat.js` - 고급 채팅 기능
- `widget-style.css` - 위젯 스타일
- `widget-embed.js` - **새로 생성된 임베드 로더**

## 🎯 3가지 사용 방법

### 방법 1: 원클릭 임베드 (가장 간단) ⭐

```html
<!-- 이 한 줄만 추가하면 끝! -->
<script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
```

### 방법 2: 사용자 정의 설정과 함께

```html
<script>
// 위젯 설정 (스크립트 로드 전에 정의)
window.GraphRAGWidgetConfig = {
    baseUrl: 'https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app',
    // 기타 사용자 정의 설정...
};
</script>
<script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
```

### 방법 3: 프로그래밍 방식 제어

```html
<script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
<script>
// 위젯 로드 완료 이벤트 감지
window.addEventListener('graphrag:widget:loaded', function(event) {
    console.log('위젯 로드 완료!', event.detail);
    
    // 위젯 제어
    if (window.GraphRAGWidget) {
        // window.GraphRAGWidget.remove(); // 위젯 제거
        // window.GraphRAGWidget.reload(); // 위젯 재로드
    }
});

// 위젯 로드 실패 이벤트 감지
window.addEventListener('graphrag:widget:error', function(event) {
    console.error('위젯 로드 실패:', event.detail.error);
});
</script>
```

## 🔧 작동 원리

### 1. 자동 파일 로드 과정

`widget-embed.js`가 다음 과정을 자동으로 수행합니다:

1. **CSS 로드**: `widget-style.css`
2. **외부 라이브러리 로드**: `marked.min.js` (CDN)
3. **HTML 구조 삽입**: `widget.html` 내용을 동적으로 삽입
4. **JavaScript 로드**: `widget-script.js`, `enhanced-chat.js`
5. **위젯 초기화**: 자동으로 위젯 인스턴스 생성

### 2. 네임스페이스 보호

모든 위젯 요소는 독립적인 컨테이너(`#graphrag-widget-container`)에 격리되어 기존 웹사이트와 충돌하지 않습니다.

## 🌐 사용 가능한 엔드포인트

다음 엔드포인트들이 CORS 허용으로 설정되어 외부에서 접근 가능합니다:

| 엔드포인트 | 설명 | 용도 |
|------------|------|------|
| `/widget.js` | 임베드 로더 스크립트 | 메인 임베드 파일 |
| `/widget.html` | 위젯 HTML 구조 | 동적 HTML 삽입용 |
| `/widget-script.js` | 위젯 JavaScript | 위젯 로직 |
| `/enhanced-chat.js` | 고급 채팅 기능 | 추가 기능 |
| `/widget-style.css` | 위젯 스타일 | CSS 스타일링 |
| `/widget-example` | 임베드 예제 페이지 | 사용법 참고 |

## ⚙️ 설정 옵션

### 기본 설정

```javascript
window.GraphRAGWidgetConfig = {
    baseUrl: 'https://your-api-domain.com',  // API 기본 URL
    containerId: 'graphrag-widget-container', // 컨테이너 ID
    version: '1.0.0'                         // 버전
};
```

### 고급 설정 (향후 지원 예정)

```javascript
window.GraphRAGWidgetConfig = {
    baseUrl: 'https://your-api-domain.com',
    
    // UI 커스터마이징
    theme: {
        primaryColor: '#667eea',
        backgroundColor: '#ffffff'
    },
    
    // 기능 토글
    features: {
        demoRequest: true,
        consultantRequest: true,
        messageRating: true
    },
    
    // 메시지 커스터마이징
    welcomeMessage: '안녕하세요! 무엇을 도와드릴까요?',
    
    // 디버그 모드
    debug: false
};
```

## 🎨 스타일 커스터마이징

### CSS 오버라이드

기존 사이트와 조화롭게 만들려면:

```css
/* 위젯 위치 조정 */
#graphrag-widget-container {
    bottom: 30px !important;
    right: 30px !important;
}

/* 토글 버튼 색상 변경 */
#graphrag-widget-container .chatbot-toggle {
    background: linear-gradient(135deg, #your-color1, #your-color2) !important;
}

/* 위젯 크기 조정 */
#graphrag-widget-container .chatbot-widget {
    width: 350px !important;
    height: 500px !important;
}
```

### 반응형 설정

모바일에서의 표시를 조정하려면:

```css
@media (max-width: 768px) {
    #graphrag-widget-container .chatbot-widget {
        width: calc(100vw - 20px) !important;
        height: calc(100vh - 100px) !important;
        bottom: 10px !important;
        right: 10px !important;
    }
}
```

## 🔄 JavaScript API

### 위젯 제어

```javascript
// 위젯이 로드된 후 사용 가능
if (window.chatbotWidget) {
    // 위젯 열기/닫기
    window.chatbotWidget.openWidget();
    window.chatbotWidget.closeWidget();
    window.chatbotWidget.toggleWidget();
    
    // 프로그래밍 방식 메시지 전송
    // window.chatbotWidget.sendMessage('안녕하세요');
}
```

### 이벤트 감지

```javascript
// 위젯 로드 완료
window.addEventListener('graphrag:widget:loaded', function(event) {
    console.log('위젯 준비됨');
});

// 위젯 상태 변경 (커스텀 이벤트 추가 필요)
window.addEventListener('graphrag:widget:opened', function() {
    console.log('위젯이 열렸습니다');
});

window.addEventListener('graphrag:widget:closed', function() {
    console.log('위젯이 닫혔습니다');
});
```

## 🚧 현재 제한사항 및 개선 방향

### 현재 제한사항

1. ❌ **Firebase 설정 하드코딩**: Firebase 프로젝트 ID가 하드코딩되어 있음
2. ❌ **테마 커스터마이징 미지원**: CSS 오버라이드로만 가능
3. ❌ **브랜딩 텍스트 고정**: "처음서비스" 브랜딩이 하드코딩됨

### 개선 방향

1. ✅ **동적 Firebase 설정**: 설정으로 Firebase 프로젝트 변경 가능하게
2. ✅ **테마 시스템**: CSS 변수 기반 테마 시스템 구축  
3. ✅ **브랜딩 커스터마이징**: 회사명, 로고, 메시지 등 동적 변경
4. ✅ **이벤트 시스템**: 더 풍부한 이벤트 시스템 구축

## 🔍 문제 해결

### 일반적인 문제

#### 1. 위젯이 표시되지 않음

```html
<!-- 디버그 모드로 확인 -->
<script>
window.GraphRAGWidgetConfig = { debug: true };
</script>
<script src="https://your-domain.com/widget.js"></script>
```

브라우저 개발자 도구 콘솔에서 오류 메시지를 확인하세요.

#### 2. API 호출 실패

- **CORS 오류**: 서버에서 해당 도메인을 허용했는지 확인
- **URL 오류**: `baseUrl` 설정이 올바른지 확인
- **네트워크 오류**: API 서버가 정상 작동하는지 확인

#### 3. Firebase 연결 실패

- Firebase 프로젝트 보안 규칙 확인
- 브라우저에서 JavaScript 활성화 확인
- 네트워크 연결 상태 확인

#### 4. 스타일 충돌

```css
/* 높은 z-index로 위젯을 최상위로 */
#graphrag-widget-container {
    z-index: 999999 !important;
}

/* 기존 CSS 리셋 방지 */
#graphrag-widget-container * {
    box-sizing: border-box !important;
}
```

### 디버깅 도구

```javascript
// 위젯 상태 확인
console.log('위젯 상태:', window.GraphRAGWidget);
console.log('채팅 인스턴스:', window.chatbotWidget);

// 네트워크 요청 확인
// 브라우저 개발자 도구 > Network 탭에서 실패한 요청 확인
```

## 📋 체크리스트

임베드하기 전에 확인할 사항들:

### 서버 설정
- [ ] CORS 설정이 올바른가?
- [ ] 모든 위젯 엔드포인트가 접근 가능한가?
- [ ] API 엔드포인트가 정상 작동하는가?

### 클라이언트 설정
- [ ] HTTPS 환경인가? (Firebase 사용 시 필수)
- [ ] JavaScript가 활성화되어 있는가?
- [ ] 다른 스크립트와 충돌하지 않는가?

### 기능 테스트
- [ ] 위젯이 정상적으로 표시되는가?
- [ ] 채팅 기능이 작동하는가?
- [ ] 데모 신청 기능이 작동하는가?
- [ ] 모바일에서도 정상 작동하는가?

## 🚀 실제 사용 예제

### 간단한 웹사이트에 추가

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>우리 회사 홈페이지</title>
</head>
<body>
    <h1>우리 회사에 오신 것을 환영합니다</h1>
    <p>최고의 서비스를 제공합니다.</p>
    
    <!-- GraphRAG 챗봇 위젯 추가 -->
    <script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
</body>
</html>
```

### WordPress 사이트에 추가

```php
// functions.php 또는 플러그인에 추가
function add_graphrag_widget() {
    ?>
    <script src="https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js"></script>
    <?php
}
add_action('wp_footer', 'add_graphrag_widget');
```

### React 앱에 추가

```jsx
import { useEffect } from 'react';

function App() {
    useEffect(() => {
        // 위젯 스크립트 로드
        const script = document.createElement('script');
        script.src = 'https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app/widget.js';
        document.body.appendChild(script);
        
        return () => {
            // 클린업
            document.body.removeChild(script);
            if (window.GraphRAGWidget) {
                window.GraphRAGWidget.remove();
            }
        };
    }, []);
    
    return (
        <div className="App">
            <h1>우리 React 앱</h1>
            {/* 위젯은 자동으로 body에 추가됩니다 */}
        </div>
    );
}
```

## 📞 지원

문제가 발생하거나 추가 기능이 필요한 경우:

- **GitHub Issues**: 버그 리포트 및 기능 요청
- **이메일**: 기술 지원 문의
- **문서**: 최신 사용법 및 API 문서

---

**버전**: 1.0.0  
**마지막 업데이트**: 2025-08-21  
**테스트 완료**: Chrome, Firefox, Safari, Edge (최신 버전)  
**모바일 지원**: iOS Safari, Android Chrome