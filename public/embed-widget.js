/**
 * GraphRAG 챗봇 위젯 - 임베드 가능한 버전
 * 다른 웹사이트에 삽입하여 사용할 수 있는 독립적인 위젯
 */
(function() {
    'use strict';
    
    // 위젯 설정
    const WIDGET_CONFIG = {
        apiBaseUrl: 'https://sampleprojects-468223-graphrag-api-4n6zl3mafq-du.a.run.app',
        firebaseProjectId: 'sampleprojects-468223',
        version: '1.0.0'
    };
    
    // CSS 스타일 주입
    function injectStyles() {
        if (document.getElementById('graphrag-widget-styles')) return;
        
        const styles = `
            /* GraphRAG Widget Embed Styles */
            #graphrag-chatbot-container {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 2147483647;
                font-size: 14px;
                line-height: 1.4;
            }
            
            #graphrag-toggle {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                color: white;
            }
            
            #graphrag-toggle:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2);
            }
            
            #graphrag-widget {
                position: absolute;
                bottom: 80px;
                right: 0;
                width: 400px;
                height: 600px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 8px 40px rgba(0, 0, 0, 0.12);
                display: none;
                flex-direction: column;
                overflow: hidden;
                border: 1px solid #e1e5e9;
            }
            
            @media (max-width: 480px) {
                #graphrag-widget {
                    width: calc(100vw - 40px);
                    height: calc(100vh - 100px);
                    bottom: 10px;
                    right: 10px;
                }
            }
            
            .graphrag-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .graphrag-header h3 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
            }
            
            .graphrag-close {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                font-size: 18px;
            }
            
            .graphrag-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                background: #f8fafc;
            }
            
            .graphrag-message {
                margin-bottom: 16px;
                display: flex;
                align-items: flex-start;
                gap: 8px;
            }
            
            .graphrag-message.user {
                flex-direction: row-reverse;
            }
            
            .graphrag-message-content {
                max-width: 85%;
                padding: 12px 16px;
                border-radius: 18px;
                word-wrap: break-word;
            }
            
            .graphrag-message.bot .graphrag-message-content {
                background: white;
                border: 1px solid #e1e5e9;
                border-bottom-left-radius: 4px;
            }
            
            .graphrag-message.user .graphrag-message-content {
                background: #667eea;
                color: white;
                border-bottom-right-radius: 4px;
            }
            
            .graphrag-input-area {
                padding: 16px;
                border-top: 1px solid #e1e5e9;
                background: white;
            }
            
            .graphrag-input-wrapper {
                display: flex;
                gap: 8px;
                align-items: flex-end;
            }
            
            .graphrag-input {
                flex: 1;
                border: 1px solid #e1e5e9;
                border-radius: 20px;
                padding: 12px 16px;
                resize: none;
                outline: none;
                font-family: inherit;
                font-size: 14px;
                max-height: 100px;
            }
            
            .graphrag-send-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: #667eea;
                border: none;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }
            
            .graphrag-send-btn:hover:not(:disabled) {
                background: #5a67d8;
                transform: scale(1.05);
            }
            
            .graphrag-send-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .graphrag-loading {
                display: flex;
                gap: 4px;
                padding: 12px 16px;
            }
            
            .graphrag-loading-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #667eea;
                animation: graphrag-loading 1.4s ease-in-out infinite both;
            }
            
            .graphrag-loading-dot:nth-child(1) { animation-delay: -0.32s; }
            .graphrag-loading-dot:nth-child(2) { animation-delay: -0.16s; }
            .graphrag-loading-dot:nth-child(3) { animation-delay: 0; }
            
            @keyframes graphrag-loading {
                0%, 80%, 100% { transform: scale(0); }
                40% { transform: scale(1); }
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = 'graphrag-widget-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
    
    // Firebase 초기화
    function initFirebase() {
        return new Promise((resolve) => {
            if (window.firebase) {
                resolve(window.firebase);
                return;
            }
            
            // Firebase SDK 동적 로드
            const script = document.createElement('script');
            script.type = 'module';
            script.innerHTML = `
                import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
                import { getFirestore, collection, doc, setDoc, getDoc, updateDoc, arrayUnion, serverTimestamp } 
                        from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js';
                
                const firebaseConfig = {
                    projectId: "${WIDGET_CONFIG.firebaseProjectId}",
                };
                
                const app = initializeApp(firebaseConfig);
                const db = getFirestore(app);
                
                window.graphragFirebase = {
                    db,
                    collection, doc, setDoc, getDoc, updateDoc, arrayUnion, serverTimestamp
                };
                
                window.dispatchEvent(new CustomEvent('graphragFirebaseReady'));
            `;
            document.head.appendChild(script);
            
            window.addEventListener('graphragFirebaseReady', () => {
                resolve(window.graphragFirebase);
            });
        });
    }
    
    // 위젯 클래스
    class GraphRAGWidget {
        constructor(config = {}) {
            this.config = { ...WIDGET_CONFIG, ...config };
            this.isOpen = false;
            this.conversationHistory = [];
            this.currentSessionId = this.generateSessionId();
            this.isLoading = false;
            
            this.init();
        }
        
        async init() {
            injectStyles();
            await initFirebase();
            this.createWidget();
            this.setupEventListeners();
            console.log('GraphRAG Widget 초기화 완료');
        }
        
        createWidget() {
            // 위젯 컨테이너 생성
            const container = document.createElement('div');
            container.id = 'graphrag-chatbot-container';
            container.innerHTML = `
                <button id="graphrag-toggle" aria-label="챗봇 열기">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/>
                    </svg>
                </button>
                
                <div id="graphrag-widget">
                    <div class="graphrag-header">
                        <h3>AI 고객지원</h3>
                        <button class="graphrag-close" id="graphrag-close-btn">×</button>
                    </div>
                    
                    <div class="graphrag-messages" id="graphrag-messages">
                        <div class="graphrag-message bot">
                            <div class="graphrag-message-content">
                                안녕하세요! 😊<br>
                                AI 고객지원 챗봇입니다.<br><br>
                                궁금하신 내용을 언제든지 입력해 주세요.
                            </div>
                        </div>
                    </div>
                    
                    <div class="graphrag-input-area">
                        <div class="graphrag-input-wrapper">
                            <textarea 
                                id="graphrag-input" 
                                class="graphrag-input" 
                                placeholder="메시지를 입력하세요..."
                                rows="1"
                            ></textarea>
                            <button id="graphrag-send-btn" class="graphrag-send-btn" type="button">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(container);
            
            // 요소 참조 저장
            this.elements = {
                toggle: document.getElementById('graphrag-toggle'),
                widget: document.getElementById('graphrag-widget'),
                closeBtn: document.getElementById('graphrag-close-btn'),
                messages: document.getElementById('graphrag-messages'),
                input: document.getElementById('graphrag-input'),
                sendBtn: document.getElementById('graphrag-send-btn')
            };
        }
        
        setupEventListeners() {
            // 토글 버튼
            this.elements.toggle.addEventListener('click', () => this.toggleWidget());
            
            // 닫기 버튼
            this.elements.closeBtn.addEventListener('click', () => this.closeWidget());
            
            // 전송 버튼
            this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
            
            // 입력 필드
            this.elements.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // 입력 필드 자동 크기 조정
            this.elements.input.addEventListener('input', () => {
                this.elements.input.style.height = 'auto';
                this.elements.input.style.height = Math.min(this.elements.input.scrollHeight, 100) + 'px';
            });
        }
        
        toggleWidget() {
            this.isOpen = !this.isOpen;
            this.elements.widget.style.display = this.isOpen ? 'flex' : 'none';
            
            if (this.isOpen) {
                this.elements.input.focus();
            }
        }
        
        closeWidget() {
            this.isOpen = false;
            this.elements.widget.style.display = 'none';
        }
        
        async sendMessage() {
            const message = this.elements.input.value.trim();
            if (!message || this.isLoading) return;
            
            // 사용자 메시지 추가
            this.addMessage(message, 'user');
            this.elements.input.value = '';
            this.elements.input.style.height = 'auto';
            
            // 로딩 표시
            this.showLoading();
            
            try {
                // API 호출
                const response = await this.callAPI(message);
                this.hideLoading();
                
                // AI 응답 추가
                this.addMessage(response, 'bot');
                
                // 대화 저장
                await this.saveConversation(message, response);
                
            } catch (error) {
                console.error('메시지 전송 실패:', error);
                this.hideLoading();
                this.addMessage('죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'bot');
            }
        }
        
        addMessage(content, type) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `graphrag-message ${type}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'graphrag-message-content';
            contentDiv.innerHTML = content.replace(/\\n/g, '<br>');
            
            messageDiv.appendChild(contentDiv);
            this.elements.messages.appendChild(messageDiv);
            
            // 스크롤을 맨 아래로
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        }
        
        showLoading() {
            this.isLoading = true;
            this.elements.sendBtn.disabled = true;
            
            const loadingDiv = document.createElement('div');
            loadingDiv.id = 'graphrag-loading-indicator';
            loadingDiv.className = 'graphrag-message bot';
            loadingDiv.innerHTML = `
                <div class="graphrag-message-content">
                    <div class="graphrag-loading">
                        <div class="graphrag-loading-dot"></div>
                        <div class="graphrag-loading-dot"></div>
                        <div class="graphrag-loading-dot"></div>
                    </div>
                </div>
            `;
            
            this.elements.messages.appendChild(loadingDiv);
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        }
        
        hideLoading() {
            this.isLoading = false;
            this.elements.sendBtn.disabled = false;
            
            const loadingIndicator = document.getElementById('graphrag-loading-indicator');
            if (loadingIndicator) {
                loadingIndicator.remove();
            }
        }
        
        async callAPI(message) {
            const response = await fetch(`${this.config.apiBaseUrl}/api/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    userPrompt: message,
                    conversationHistory: this.conversationHistory
                })
            });
            
            if (!response.ok) {
                throw new Error(`API 호출 실패: ${response.status}`);
            }
            
            const data = await response.json();
            return data.response || '응답을 처리할 수 없습니다.';
        }
        
        async saveConversation(userMessage, botResponse) {
            try {
                if (!window.graphragFirebase) return;
                
                const { db, doc, setDoc, getDoc, updateDoc, arrayUnion, serverTimestamp } = window.graphragFirebase;
                
                const conversationRef = doc(db, 'conversations', this.currentSessionId);
                const conversationDoc = await getDoc(conversationRef);
                
                const messageData = {
                    user_message: userMessage,
                    bot_response: botResponse,
                    timestamp: serverTimestamp()
                };
                
                if (conversationDoc.exists()) {
                    await updateDoc(conversationRef, {
                        messages: arrayUnion(messageData),
                        last_activity: serverTimestamp(),
                        message_count: (conversationDoc.data().message_count || 0) + 1
                    });
                } else {
                    await setDoc(conversationRef, {
                        session_id: this.currentSessionId,
                        messages: [messageData],
                        created_at: serverTimestamp(),
                        last_activity: serverTimestamp(),
                        message_count: 1,
                        widget_version: this.config.version
                    });
                }
                
                // 대화 히스토리 업데이트
                this.conversationHistory.push({
                    user: userMessage,
                    bot: botResponse
                });
                
                // 히스토리 길이 제한 (최근 10개만 유지)
                if (this.conversationHistory.length > 10) {
                    this.conversationHistory = this.conversationHistory.slice(-10);
                }
                
            } catch (error) {
                console.error('대화 저장 실패:', error);
            }
        }
        
        generateSessionId() {
            return 'widget_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
        }
    }
    
    // 자동 초기화 또는 수동 초기화 지원
    if (typeof window.GraphRAGWidgetConfig !== 'undefined') {
        // 설정이 미리 정의된 경우 즉시 초기화
        new GraphRAGWidget(window.GraphRAGWidgetConfig);
    } else {
        // 전역 초기화 함수 제공
        window.initGraphRAGWidget = function(config) {
            return new GraphRAGWidget(config);
        };
        
        // DOM이 준비되면 자동 초기화 (설정이 없으면 기본값 사용)
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => {
                    if (!window.graphragWidgetInitialized) {
                        new GraphRAGWidget();
                        window.graphragWidgetInitialized = true;
                    }
                }, 100);
            });
        } else {
            setTimeout(() => {
                if (!window.graphragWidgetInitialized) {
                    new GraphRAGWidget();
                    window.graphragWidgetInitialized = true;
                }
            }, 100);
        }
    }
    
})();