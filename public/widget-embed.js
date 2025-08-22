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
            
            // 5. 위젯 초기화
            // 잠시 대기 후 위젯 초기화 (스크립트 로드 완료 보장)
            setTimeout(() => {
                if (window.initGraphRAGChatWidget) {
                    window.initGraphRAGChatWidget({
                        apiBaseUrl: config.baseUrl
                    });
                }
            }, 500);
            
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
            #${config.containerId} {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                position: relative;
                z-index: 2147483647;
            }
            
            #${config.containerId} * {
                box-sizing: border-box;
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