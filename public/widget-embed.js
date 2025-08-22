/**
 * GraphRAG 위젯 임베드 스크립트
 * 기존 위젯 파일들을 다른 웹사이트에서 사용할 수 있게 해주는 로더
 */
(function() {
    'use strict';
    
    // 동적 baseUrl 감지 함수
    function getBaseUrl() {
        // 1. 현재 스크립트의 src에서 도메인 추출
        const currentScript = document.currentScript;
        if (currentScript && currentScript.src) {
            const url = new URL(currentScript.src);
            return `${url.protocol}//${url.host}`;
        }
        
        // 2. 사용자 설정 확인
        if (window.GraphRAGWidgetConfig && window.GraphRAGWidgetConfig.baseUrl) {
            return window.GraphRAGWidgetConfig.baseUrl;
        }
        
        // 3. fallback URL (현재 배포된 URL)
        return 'https://widgettest-469800-graphrag-api-1056095201787.asia-northeast3.run.app';
    }
    
    
    // 설정
    const WIDGET_CONFIG = {
        baseUrl: getBaseUrl(),
        containerId: 'graphrag-widget-container',
        version: '1.0.0'
    };
    
    // 사용자 설정 병합
    const config = {
        ...WIDGET_CONFIG,
        ...(window.GraphRAGWidgetConfig || {})
    };
    
    // 이미 로드된 경우 중복 방지
    if (window.GraphRAGWidgetLoaded) {
        console.log('GraphRAG 위젯이 이미 로드되었습니다.');
        return;
    }
    
    window.GraphRAGWidgetLoaded = true;
    
    /**
     * CSS 파일 동적 로드
     */
    function loadCSS(href, id) {
        return new Promise((resolve, reject) => {
            if (document.getElementById(id)) {
                resolve();
                return;
            }
            
            const link = document.createElement('link');
            link.id = id;
            link.rel = 'stylesheet';
            link.type = 'text/css';
            link.href = href;
            link.onload = resolve;
            link.onerror = reject;
            document.head.appendChild(link);
        });
    }
    
    /**
     * JavaScript 파일 동적 로드
     */
    function loadJS(src, id) {
        return new Promise((resolve, reject) => {
            if (document.getElementById(id)) {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.id = id;
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    /**
     * 위젯 HTML을 동적으로 로드하고 삽입
     */
    async function loadWidgetHTML() {
        try {
            const response = await fetch(`${config.baseUrl}/widget.html`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const html = await response.text();
            
            // HTML에서 body 내용만 추출
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const bodyContent = doc.body.innerHTML;
            
            // 위젯 컨테이너 생성
            const container = document.createElement('div');
            container.id = config.containerId;
            container.innerHTML = bodyContent;
            
            // 위젯 컨테이너를 body에 추가
            document.body.appendChild(container);
            
            console.log('✅ GraphRAG 위젯 HTML 로드 완료');
            return true;
            
        } catch (error) {
            console.error('❌ 위젯 HTML 로드 실패:', error);
            return false;
        }
    }
    
    /**
     * 메인 로더 함수
     */
    async function loadWidget() {
        try {
            console.log('🚀 GraphRAG 위젯 로드 시작...');
            
            // 1. CSS 파일들 로드
            await Promise.all([
                loadCSS(`${config.baseUrl}/widget-style.css`, 'graphrag-widget-style'),
                // enhanced-chat.css는 없으므로 제외
            ]);
            console.log('✅ CSS 파일 로드 완료');
            
            // 2. 외부 의존성 로드 (marked.js)
            await loadJS('https://cdn.jsdelivr.net/npm/marked/marked.min.js', 'marked-js');
            console.log('✅ 외부 라이브러리 로드 완료');
            
            // 3. 위젯 HTML 로드 및 삽입
            const htmlLoaded = await loadWidgetHTML();
            if (!htmlLoaded) {
                throw new Error('위젯 HTML 로드 실패');
            }
            
            // 4. 위젯 스크립트 파일들 로드
            await Promise.all([
                loadJS(`${config.baseUrl}/widget-script.js`, 'graphrag-widget-script'),
                loadJS(`${config.baseUrl}/enhanced-chat.js`, 'graphrag-enhanced-chat')
            ]);
            console.log('✅ JavaScript 파일 로드 완료');
            
            // 5. 위젯 초기화 - 더 안전한 방식
            // 위젯 초기화 재시도 로직
            let initAttempts = 0;
            const maxAttempts = 10;
            
            const tryInitWidget = () => {
                initAttempts++;
                console.log(`위젯 초기화 시도 ${initAttempts}/${maxAttempts}`);
                
                if (window.initGraphRAGChatWidget) {
                    try {
                        window.initGraphRAGChatWidget({
                            apiBaseUrl: config.baseUrl
                        });
                        console.log('✅ 위젯 초기화 성공');
                        return true;
                    } catch (error) {
                        console.error('위젯 초기화 실패:', error);
                    }
                } else if (window.ChatbotWidget) {
                    try {
                        // 직접 위젯 클래스 인스턴스화
                        new window.ChatbotWidget({
                            apiBaseUrl: config.baseUrl
                        });
                        console.log('✅ 위젯 직접 초기화 성공');
                        return true;
                    } catch (error) {
                        console.error('위젯 직접 초기화 실패:', error);
                    }
                }
                
                // 재시도
                if (initAttempts < maxAttempts) {
                    setTimeout(tryInitWidget, 200);
                } else {
                    console.error('❌ 위젯 초기화 최대 재시도 초과');
                }
            };
            
            setTimeout(tryInitWidget, 100);
            
            console.log('🎉 GraphRAG 위젯 로드 완료!');
            
            // 사용자 정의 콜백 실행
            if (typeof window.onGraphRAGWidgetLoaded === 'function') {
                window.onGraphRAGWidgetLoaded();
            }
            
            // 커스텀 이벤트 발생
            window.dispatchEvent(new CustomEvent('graphrag:widget:loaded', {
                detail: { config, version: config.version }
            }));
            
        } catch (error) {
            console.error('❌ GraphRAG 위젯 로드 실패:', error);
            
            // 에러 이벤트 발생
            window.dispatchEvent(new CustomEvent('graphrag:widget:error', {
                detail: { error: error.message }
            }));
        }
    }
    
    /**
     * 스타일 충돌 방지를 위한 CSS 네임스페이스 추가
     */
    function addNamespaceStyles() {
        const namespaceStyles = `
            /* 컨테이너 기본 설정 */
            #${config.containerId} {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                position: relative !important;
                z-index: 2147483647 !important;
                all: initial !important;
            }
            
            #${config.containerId} * {
                box-sizing: border-box !important;
            }
            
            /* 토글 버튼 스타일 */
            #${config.containerId} .chatbot-toggle {
                all: unset !important;
                position: fixed !important;
                bottom: 120px !important;
                right: 24px !important;
                width: 60px !important;
                height: 60px !important;
                background: linear-gradient(135deg, #137546 0%, #115f3a 100%) !important;
                border-radius: 50% !important;
                cursor: pointer !important;
                z-index: 2147483647 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                visibility: visible !important;
                box-shadow: 0 8px 25px rgba(19, 117, 70, 0.3), 0 4px 12px rgba(0, 0, 0, 0.15) !important;
            }
            
            /* 위젯 컨테이너 */
            #${config.containerId} .chatbot-widget {
                all: unset !important;
                position: fixed !important;
                bottom: 200px !important;
                right: 24px !important;
                width: 380px !important;
                height: 600px !important;
                background: #ffffff !important;
                border-radius: 16px !important;
                z-index: 2147483647 !important;
                display: none !important;
                flex-direction: column !important;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 25px rgba(0, 0, 0, 0.1) !important;
                visibility: hidden !important;
                opacity: 0 !important;
                transform: translateY(20px) scale(0.95) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                overflow: hidden !important;
                border: 1px solid rgba(0, 0, 0, 0.05) !important;
                pointer-events: auto !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            #${config.containerId} .chatbot-widget.visible {
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
                transform: translateY(0) scale(1) !important;
                z-index: 2147483647 !important;
                pointer-events: auto !important;
            }
            
            /* 위젯 헤더 스타일 강화 */
            #${config.containerId} .widget-header {
                background: linear-gradient(135deg, #137546 0%, #115f3a 100%) !important;
                color: white !important;
                padding: 16px !important;
                border-radius: 16px 16px 0 0 !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            #${config.containerId} .brand-name {
                font-size: 16px !important;
                font-weight: 600 !important;
                color: white !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            #${config.containerId} .brand-status {
                font-size: 12px !important;
                color: rgba(255, 255, 255, 0.8) !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            /* 헤더 버튼들 */
            #${config.containerId} .action-btn {
                width: 32px !important;
                height: 32px !important;
                border: none !important;
                background: rgba(255, 255, 255, 0.1) !important;
                border-radius: 8px !important;
                cursor: pointer !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                color: white !important;
                transition: background-color 0.2s ease !important;
            }
            
            #${config.containerId} .action-btn:hover {
                background: rgba(255, 255, 255, 0.2) !important;
            }
            
            #${config.containerId} .action-btn svg {
                width: 16px !important;
                height: 16px !important;
                fill: currentColor !important;
            }
            
            /* 웰컴 메시지 스타일 */
            #${config.containerId} .welcome-message {
                background: #f8f9fa !important;
                border-radius: 12px !important;
                padding: 16px !important;
                margin: 16px !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            #${config.containerId} .welcome-message pre {
                white-space: pre-wrap !important;
                word-wrap: break-word !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                font-size: 14px !important;
                line-height: 1.5 !important;
                color: #333 !important;
                margin: 0 !important;
            }
            
            /* 데모 버튼 */
            #${config.containerId} .demo-button {
                background: #137546 !important;
                color: white !important;
                border: none !important;
                padding: 12px 24px !important;
                border-radius: 8px !important;
                cursor: pointer !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                margin-top: 16px !important;
                width: 100% !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            #${config.containerId} .demo-button:hover {
                background: #115f3a !important;
            }
            
            /* 입력 영역 */
            #${config.containerId} .input-section {
                padding: 16px !important;
                border-top: 1px solid #e9ecef !important;
                background: white !important;
            }
            
            #${config.containerId} .input-wrapper {
                display: flex !important;
                align-items: flex-end !important;
                gap: 8px !important;
            }
            
            #${config.containerId} #prompt-input {
                flex: 1 !important;
                border: 1px solid #e9ecef !important;
                border-radius: 12px !important;
                padding: 12px 16px !important;
                font-size: 14px !important;
                line-height: 1.4 !important;
                resize: none !important;
                outline: none !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                background: white !important;
                color: #333 !important;
            }
            
            #${config.containerId} .send-button {
                width: 40px !important;
                height: 40px !important;
                background: #137546 !important;
                border: none !important;
                border-radius: 50% !important;
                cursor: pointer !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                color: white !important;
            }
            
            #${config.containerId} .send-button svg {
                width: 18px !important;
                height: 18px !important;
                fill: currentColor !important;
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = 'graphrag-namespace-styles';
        styleSheet.textContent = namespaceStyles;
        document.head.appendChild(styleSheet);
    }
    
    // 네임스페이스 스타일 추가
    addNamespaceStyles();
    
    // DOM이 준비되면 위젯 로드
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadWidget);
    } else {
        // DOM이 이미 준비된 경우 즉시 실행
        setTimeout(loadWidget, 0);
    }
    
    // 전역 API 제공
    window.GraphRAGWidget = {
        version: config.version,
        config: config,
        reload: loadWidget,
        debug: function() {
            console.log('🔍 GraphRAG 위젯 디버깅 정보');
            console.log('컨테이너:', document.getElementById(config.containerId));
            console.log('토글 버튼:', document.querySelector(`#${config.containerId} #chatbot-toggle`));
            console.log('채팅창:', document.querySelector(`#${config.containerId} #chatbot-widget`));
            console.log('초기화 함수:', window.initGraphRAGChatWidget);
            console.log('위젯 클래스:', window.ChatbotWidget);
            console.log('설정:', config);
        },
        forceOpen: function() {
            const widget = document.querySelector(`#${config.containerId} #chatbot-widget`);
            if (widget) {
                widget.style.display = 'flex';
                widget.style.visibility = 'visible';
                widget.style.opacity = '1';
                console.log('강제로 위젯 열기 완료');
            }
        },
        forceClose: function() {
            // 모든 가능한 위젯 요소를 찾아서 닫기
            const widgets = document.querySelectorAll(`#${config.containerId} #chatbot-widget, #${config.containerId} .chatbot-widget, #chatbot-widget, .chatbot-widget`);
            widgets.forEach(widget => {
                widget.style.cssText = `
                    position: fixed !important;
                    bottom: 200px !important;
                    right: 24px !important;
                    z-index: 2147483647 !important;
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                `;
                widget.classList.remove('visible');
            });
            
            // ChatbotWidget 인스턴스를 통한 닫기도 시도
            if (window.chatbotWidgetInstance && typeof window.chatbotWidgetInstance.closeWidget === 'function') {
                window.chatbotWidgetInstance.closeWidget();
            }
            
            console.log('강제로 위젯 닫기 완료');
        },
        remove: function() {
            const container = document.getElementById(config.containerId);
            if (container) {
                container.remove();
            }
            
            // 스타일시트 제거
            const styles = document.querySelectorAll('#graphrag-widget-style, #graphrag-namespace-styles');
            styles.forEach(style => style.remove());
            
            // 스크립트 제거
            const scripts = document.querySelectorAll('#graphrag-widget-script, #graphrag-enhanced-chat');
            scripts.forEach(script => script.remove());
            
            window.GraphRAGWidgetLoaded = false;
        }
    };
    
})();