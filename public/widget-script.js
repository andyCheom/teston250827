// 위젯 초기화 및 이벤트 핸들러
class ChatbotWidget {
    constructor(config = {}) {
        this.isOpen = false;
        this.messageCounter = 0;
        this.conversationHistory = [];
        this.currentSessionId = this.getOrCreateSessionId();
        this.isToggling = false; // 디바운싱을 위한 플래그
        
        // API 기본 URL 설정 (외부 사이트에서 사용시 명시적 Cloud Run URL 사용)
        this.apiBaseUrl = config.apiBaseUrl || 
                         window.GraphRAGWidgetConfig?.baseUrl || 
                         'https://sampleprojects-468223-graphrag-api-975882305117.asia-northeast3.run.app';
        
        this.init();
    }

    // getCurrentDomainUrl 함수 제거됨 - 항상 Cloud Run URL 사용

    init() {
        // 위젯 요소들이 존재하는지 확인
        if (!document.getElementById('chatbot-toggle') || !document.getElementById('chatbot-widget')) {
            console.log('위젯 요소들이 없어 위젯 초기화를 건너뜁니다.');
            return;
        }
        
        this.setupElements();
        this.setupEventListeners();
        this.setupEnhancedFeatures();
        this.showNotificationBadge();
        
        console.log('챗봇 위젯 초기화 완료');
        console.log('API Base URL:', this.apiBaseUrl);
        console.log('주요 엘리먼트 확인:', {
            toggle: !!this.toggle,
            widget: !!this.widget,
            promptForm: !!this.promptForm,
            promptInput: !!this.promptInput,
            submitButton: !!this.submitButton
        });
    }

    setupElements() {
        this.toggle = document.getElementById('chatbot-toggle');
        this.widget = document.getElementById('chatbot-widget');
        this.chatContainer = document.getElementById('chat-container');
        this.promptForm = document.getElementById('prompt-form');
        this.promptInput = document.getElementById('prompt-input');
        this.submitButton = document.getElementById('submit-button');
        this.closeBtn = document.getElementById('close-widget');
        this.notificationBadge = document.getElementById('notification-badge');
        
        // 디버깅용 로그
        console.log('요소 설정 완료:', {
            toggle: !!this.toggle,
            widget: !!this.widget,
            chatContainer: !!this.chatContainer,
            promptForm: !!this.promptForm,
            promptInput: !!this.promptInput,
            submitButton: !!this.submitButton
        });
        
        // 데모 폼 요소들
        this.demoRequestBtn = document.getElementById('demo-request-btn');
        this.demoFormContainer = document.getElementById('demo-form-container');
        this.demoForm = document.getElementById('demo-form');
        this.demoFormClose = document.getElementById('demo-form-close');
        this.demoFormCancel = document.getElementById('demo-form-cancel');
    }

    setupEventListeners() {
        // 토글 버튼 - 단일 이벤트만 사용
        if (this.toggle) {
            // 기존 이벤트 핸들러 제거 (중복 방지)
            this.toggle.onclick = null;
            
            // addEventListener만 사용
            this.toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                console.log('토글 버튼 클릭됨');
                this.toggleWidget();
            });
            
            console.log('토글 버튼 이벤트 리스너 설정 완료');
        } else {
            console.error('토글 버튼을 찾을 수 없습니다');
        }
        
        // 위젯 컨트롤 - 강화된 이벤트 리스너
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeWidget();
                console.log('닫기 버튼 클릭됨');
            });
            
            // 추가 안전장치: 동적으로 버튼 재연결
            const retryCloseBtn = () => {
                const closeBtn = document.querySelector('#close-widget, .close-btn');
                if (closeBtn && !closeBtn.hasAttribute('data-listener-attached')) {
                    closeBtn.setAttribute('data-listener-attached', 'true');
                    closeBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.closeWidget();
                        console.log('동적 닫기 버튼 클릭됨');
                    });
                }
            };
            
            setTimeout(retryCloseBtn, 1000);
        }
        
        // 새 대화 버튼 제거됨 (최소화 버튼 삭제)
        
        // 채팅 폼
        if (this.promptForm) {
            this.promptForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
        
        // 입력 필드 자동 크기 조정
        if (this.promptInput) {
            this.promptInput.addEventListener('input', () => this.autoResizeInput());
        }
        
        // Enter 키 처리
        if (this.promptInput) {
            this.promptInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (this.promptForm) {
                        this.promptForm.requestSubmit();
                    }
                }
            });
        }

        // 데모 폼 이벤트
        if (this.demoRequestBtn) {
            this.demoRequestBtn.addEventListener('click', () => this.showDemoForm());
        }
        
        if (this.demoFormClose) {
            this.demoFormClose.addEventListener('click', () => this.hideDemoForm());
        }
        
        if (this.demoFormCancel) {
            this.demoFormCancel.addEventListener('click', () => this.hideDemoForm());
        }
        
        if (this.demoForm) {
            this.demoForm.addEventListener('submit', (e) => this.handleDemoFormSubmit(e));
        }
        
        if (this.demoFormContainer) {
            this.demoFormContainer.addEventListener('click', (e) => {
                if (e.target === this.demoFormContainer) {
                    this.hideDemoForm();
                }
            });
        }

        // 위젯 외부 클릭 시 닫기 (옵션)
        document.addEventListener('click', (e) => {
            if (this.isOpen && !this.widget.contains(e.target) && !this.toggle.contains(e.target)) {
                // 데모 폼이 열려있으면 닫지 않음
                if (!this.demoFormContainer || this.demoFormContainer.style.display === 'none') {
                    // this.closeWidget(); // 주석 처리하여 자동 닫기 비활성화
                }
            }
        });
    }

    setupEnhancedFeatures() {
        // Enhanced Chat 기능들을 전역 객체로 설정
        window.enhancedChat = {
            showTypingIndicator: () => this.showTypingIndicator(),
            hideTypingIndicator: () => this.hideTypingIndicator(),
            showLoadingIndicator: (message) => this.showLoadingIndicator(message),
            showNotification: (message, type) => this.showNotification(message, type),
            scrollToBottom: () => this.scrollToBottom(),
            createEnhancedMessage: (content, type, includeActions) => this.createEnhancedMessage(content, type, includeActions),
            addMessageActions: (element, type, index) => this.addMessageActions(element, type, index),
            copyMessageText: (element) => this.copyMessageText(element)
        };
    }

    // 세션 관리
    getOrCreateSessionId() {
        // 세션 스토리지 사용으로 브라우저 탭별 독립적 세션 관리
        let sessionId = sessionStorage.getItem('widget_session_id');
        
        // 세션이 없거나 페이지 새로고침인 경우 새 세션 생성
        if (!sessionId || this.shouldCreateNewSession()) {
            sessionId = this.generateSessionId();
            sessionStorage.setItem('widget_session_id', sessionId);
            sessionStorage.setItem('widget_session_created', Date.now().toString());
            console.log('새 위젯 세션 ID 생성:', sessionId);
        } else {
            console.log('기존 위젯 세션 ID 사용:', sessionId);
        }
        return sessionId;
    }
    
    shouldCreateNewSession() {
        // 대화 기록이 없으면 새 세션으로 간주
        const hasMessages = this.conversationHistory && this.conversationHistory.length > 0;
        
        // 또는 세션이 24시간 이상 오래된 경우
        const sessionCreated = sessionStorage.getItem('widget_session_created');
        const isOldSession = sessionCreated && (Date.now() - parseInt(sessionCreated) > 24 * 60 * 60 * 1000);
        
        return !hasMessages || isOldSession;
    }

    generateSessionId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substr(2, 9);
        return `widget_${random}_${timestamp}`;
    }
    
    // 새 대화 시작
    startNewConversation() {
        // 기존 세션 정리
        sessionStorage.removeItem('widget_session_id');
        sessionStorage.removeItem('widget_session_created');
        
        // 새 세션 ID 생성
        this.currentSessionId = this.generateSessionId();
        sessionStorage.setItem('widget_session_id', this.currentSessionId);
        sessionStorage.setItem('widget_session_created', Date.now().toString());
        
        // 대화 기록 초기화
        this.conversationHistory = [];
        
        // 채팅 컨테이너 초기화
        if (this.chatContainer) {
            // 웰컴 메시지만 남기고 나머지 제거
            const welcomeMessage = this.chatContainer.querySelector('.welcome-message');
            this.chatContainer.innerHTML = '';
            if (welcomeMessage) {
                this.chatContainer.appendChild(welcomeMessage);
            }
        }
        
        console.log('새 대화 시작:', this.currentSessionId);
        this.showNotification('새 대화가 시작되었습니다', 'info');
    }

    // 위젯 제어 (디바운싱 적용)
    toggleWidget() {
        // 이미 토글 중이면 무시
        if (this.isToggling) {
            console.log('토글 중이므로 무시됨');
            return;
        }
        
        this.isToggling = true;
        console.log('toggleWidget 호출됨, 현재 상태:', this.isOpen);
        console.log('위젯 요소:', this.widget);
        
        if (this.isOpen) {
            console.log('위젯 닫기 시도');
            this.closeWidget();
        } else {
            console.log('위젯 열기 시도');
            this.openWidget();
        }
        
        // 300ms 후 토글 가능하도록 설정
        setTimeout(() => {
            this.isToggling = false;
        }, 300);
    }

    openWidget() {
        console.log('openWidget 시작');
        this.isOpen = true;
        
        if (this.widget) {
            // 강제 스타일 적용 - 무조건 최상위 표시
            this.widget.style.cssText = `
                position: fixed !important;
                bottom: 200px !important;
                right: 24px !important;
                width: 380px !important;
                height: 600px !important;
                background: #ffffff !important;
                border-radius: 16px !important;
                z-index: 2147483647 !important;
                display: flex !important;
                flex-direction: column !important;
                visibility: visible !important;
                opacity: 1 !important;
                transform: translateY(0) scale(1) !important;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 25px rgba(0, 0, 0, 0.1) !important;
                overflow: hidden !important;
                border: 1px solid rgba(0, 0, 0, 0.05) !important;
                pointer-events: auto !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            `;
            
            this.widget.classList.add('visible');
            console.log('위젯 강제 표시됨');
        } else {
            console.error('위젯 요소를 찾을 수 없습니다');
        }
        
        if (this.toggle) {
            this.toggle.classList.add('active');
        }
        
        this.hideNotificationBadge();
        
        if (this.promptInput) {
            setTimeout(() => {
                this.promptInput.focus();
            }, 100);
        }
        
        this.scrollToBottom();
        
        // 위젯이 처음 열릴 때 한 번만 환영 메시지 로드
        if (!this.hasLoadedWelcome) {
            this.hasLoadedWelcome = true;
        }
    }

    closeWidget() {
        this.isOpen = false;
        
        // 1. 클래스 제거
        if (this.widget) {
            this.widget.classList.remove('visible');
        }
        if (this.toggle) {
            this.toggle.classList.remove('active');
        }
        
        // 2. 강제로 위젯 완전히 숨기기 - z-index를 -1로 설정
        if (this.widget) {
            this.widget.style.cssText = `
                position: fixed !important;
                bottom: 200px !important;
                right: 24px !important;
                z-index: -1 !important;
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                transform: translateY(100px) scale(0.8) !important;
                pointer-events: none !important;
                width: 0 !important;
                height: 0 !important;
            `;
        }
        
        // 3. 모든 위젯 요소 완전히 제거
        const widgetElements = document.querySelectorAll('#chatbot-widget, .chatbot-widget');
        widgetElements.forEach(element => {
            element.style.cssText = `
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                z-index: -1 !important;
                width: 0 !important;
                height: 0 !important;
                pointer-events: none !important;
                position: fixed !important;
                top: -9999px !important;
                left: -9999px !important;
            `;
            element.classList.remove('visible');
            element.setAttribute('aria-hidden', 'true');
        });
        
        // 4. 0.3초 후 추가 확인
        setTimeout(() => {
            const stillVisible = document.querySelectorAll('#chatbot-widget, .chatbot-widget');
            stillVisible.forEach(element => {
                if (element.style.display !== 'none') {
                    element.style.display = 'none';
                    element.style.visibility = 'hidden';
                    element.style.zIndex = '-1';
                }
            });
        }, 300);
        
        console.log('위젯 닫기 완료');
        
        // 알림 배지 표시
        this.showNotificationBadge();
    }

    // 알림 배지
    showNotificationBadge() {
        if (this.notificationBadge && !this.isOpen) {
            this.notificationBadge.style.display = 'flex';
        }
    }

    hideNotificationBadge() {
        if (this.notificationBadge) {
            this.notificationBadge.style.display = 'none';
        }
    }

    // 입력 필드 자동 크기 조정
    autoResizeInput() {
        this.promptInput.style.height = 'auto';
        this.promptInput.style.height = Math.min(this.promptInput.scrollHeight, 120) + 'px';
    }

    // 폼 제출 처리
    async handleFormSubmit(e) {
        e.preventDefault();
        const userPrompt = this.promptInput.value.trim();

        if (!userPrompt) return;

        const startTime = Date.now();
        
        // 사용자 메시지 표시
        this.displayUserMessage(userPrompt);

        // 폼 데이터 준비
        const formData = new FormData();
        formData.append('userPrompt', userPrompt);
        formData.append('conversationHistory', JSON.stringify(this.conversationHistory));
        formData.append('sessionId', this.currentSessionId);

        // 입력 필드 초기화
        this.promptInput.value = '';
        this.autoResizeInput();

        // 로딩 표시
        const loadingElement = this.showLoadingIndicator();
        this.scrollToBottom();

        // 버튼 비활성화
        this.submitButton.disabled = true;
        this.promptInput.disabled = true;

        try {
            // API 호출
            const response = await fetch(`${this.apiBaseUrl}/api/generate`, {
                method: 'POST',
                body: formData,
            });

            // 로딩 제거
            if (loadingElement) loadingElement.remove();

            const responseText = await response.text();

            if (!response.ok) {
                let errorData;
                try {
                    errorData = JSON.parse(responseText);
                } catch (jsonError) {
                    throw new Error(`서버 오류 (${response.status}): ${responseText.substring(0, 200)}`);
                }
                throw new Error(errorData.error?.message || errorData.detail || `API 요청 실패: ${response.status}`);
            }

            const result = JSON.parse(responseText);

            // 대화 기록 업데이트
            if (Array.isArray(result.updatedHistory)) {
                this.conversationHistory = result.updatedHistory;
            }

            // 응답 표시
            const modelResponseText = result.summary_answer || 
                                    result.answer || 
                                    result.vertex_answer || 
                                    result.vertexAiResponse?.candidates?.[0]?.content?.parts?.[0]?.text;

            if (modelResponseText) {
                this.displayModelMessageWithSources(modelResponseText, result);
                
                // Firestore에 저장 (비동기)
                this.saveConversationToFirestore(userPrompt, modelResponseText, {
                    citations: result.citations,
                    search_results: result.search_results,
                    metadata: result.metadata,
                    consultant_needed: result.consultant_needed,
                    response_time_ms: Date.now() - startTime
                }).catch(error => {
                    console.log('Firestore 저장 실패 (위젯):', error);
                });
            } else {
                this.displayModelMessage('죄송합니다, 답변을 생성하지 못했습니다.');
            }

        } catch (error) {
            if (loadingElement) loadingElement.remove();
            
            console.error('API 호출 오류:', error);
            
            let userMessage;
            if (error instanceof TypeError) {
                userMessage = '서버에 연결할 수 없습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요.';
            } else if (error instanceof SyntaxError) {
                userMessage = '서버로부터 잘못된 형식의 응답을 받았습니다.';
            } else {
                userMessage = `오류가 발생했습니다: ${error.message}`;
            }
            
            this.displayModelMessage(userMessage);
        } finally {
            // 버튼 재활성화
            this.submitButton.disabled = false;
            this.promptInput.disabled = false;
            if (this.promptInput) {
            this.promptInput.focus();
        }
            this.scrollToBottom();
        }
    }

    // 메시지 표시
    displayUserMessage(text) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        
        const textNode = document.createElement('p');
        textNode.style.margin = '0';
        textNode.textContent = text;
        messageElement.appendChild(textNode);
        
        this.chatContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    displayModelMessage(markdownText) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message model-message';
        
        messageElement.innerHTML = marked.parse(markdownText);
        
        this.addMessageReactions(messageElement);
        this.chatContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    displayModelMessageWithSources(markdownText, result) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message model-message';

        // 메인 답변
        messageElement.innerHTML = marked.parse(markdownText);

        // 연관 질문 추가
        if (result.related_questions && result.related_questions.length > 0) {
            const relatedDiv = document.createElement('div');
            relatedDiv.style.cssText = `
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid var(--gray-200);
            `;
            
            const relatedTitle = document.createElement('strong');
            relatedTitle.textContent = '💡 연관 질문:';
            relatedTitle.style.cssText = `
                display: block;
                margin-bottom: 8px;
                font-size: 13px;
                color: var(--gray-600);
            `;
            relatedDiv.appendChild(relatedTitle);
            
            const questionsList = document.createElement('div');
            questionsList.style.cssText = `
                display: flex;
                flex-direction: column;
                gap: 6px;
            `;
            
            result.related_questions.slice(0, 3).forEach((question) => {
                const questionButton = document.createElement('button');
                questionButton.textContent = `❓ ${question}`;
                questionButton.style.cssText = `
                    background: var(--gray-100);
                    border: 1px solid var(--gray-200);
                    border-radius: 12px;
                    padding: 8px 12px;
                    text-align: left;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 12px;
                    color: var(--gray-700);
                `;
                
                questionButton.addEventListener('mouseenter', () => {
                    questionButton.style.background = '#e3f2fd';
                    questionButton.style.borderColor = '#1976d2';
                    questionButton.style.color = '#1976d2';
                });
                
                questionButton.addEventListener('mouseleave', () => {
                    questionButton.style.background = 'var(--gray-100)';
                    questionButton.style.borderColor = 'var(--gray-200)';
                    questionButton.style.color = 'var(--gray-700)';
                });
                
                questionButton.addEventListener('click', () => {
                    this.promptInput.value = question;
                    this.promptForm.dispatchEvent(new Event('submit'));
                });
                
                questionsList.appendChild(questionButton);
            });
            
            relatedDiv.appendChild(questionsList);
            messageElement.appendChild(relatedDiv);
        }

        // 관련 문서 링크
        if (result.search_results && result.search_results.length > 0) {
            const searchDiv = document.createElement('div');
            searchDiv.style.cssText = `
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid var(--gray-200);
            `;
            
            const searchTitle = document.createElement('strong');
            searchTitle.textContent = '📚 관련 문서:';
            searchTitle.style.cssText = `
                display: block;
                margin-bottom: 8px;
                font-size: 13px;
                color: var(--gray-600);
            `;
            searchDiv.appendChild(searchTitle);
            
            const searchList = document.createElement('ol');
            searchList.style.cssText = `
                margin: 0;
                padding-left: 16px;
                font-size: 12px;
            `;
            
            result.search_results.slice(0, 3).forEach((searchResult, i) => {
                const doc = searchResult.document || {};
                const derivedData = doc.derivedStructData || {};
                const title = derivedData.title || `문서 ${i + 1}`;
                const link = derivedData.link || doc.uri || '';
                
                const listItem = document.createElement('li');
                listItem.style.marginBottom = '4px';
                
                if (link) {
                    const linkElement = document.createElement('a');
                    linkElement.textContent = title;
                    linkElement.style.cssText = `
                        color: var(--primary-600);
                        text-decoration: underline;
                        font-size: 12px;
                    `;
                    
                    if (link.startsWith('gs://')) {
                        const gcsPath = link.replace('gs://', '');
                        const parts = gcsPath.split('/');
                        const bucketName = parts[0];
                        const filePath = parts.slice(1).join('/');
                        linkElement.href = `/gcs/${bucketName}/${filePath}`;
                    } else if (link.startsWith('http')) {
                        linkElement.href = link;
                    }
                    
                    linkElement.target = '_blank';
                    linkElement.rel = 'noopener noreferrer';
                    
                    listItem.appendChild(linkElement);
                } else {
                    listItem.textContent = title;
                    listItem.style.fontSize = '12px';
                }
                
                searchList.appendChild(listItem);
            });
            
            searchDiv.appendChild(searchList);
            messageElement.appendChild(searchDiv);
        }

        // 상담사 연결 버튼
        if (result.consultant_needed) {
            const consultantDiv = document.createElement('div');
            consultantDiv.style.cssText = `
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid var(--gray-200);
                text-align: center;
            `;
            
            const consultantButton = document.createElement('button');
            consultantButton.textContent = '🎧 상담사와 연결하기';
            consultantButton.style.cssText = `
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            `;
            
            consultantButton.addEventListener('mouseenter', () => {
                consultantButton.style.transform = 'translateY(-2px)';
                consultantButton.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
            });
            
            consultantButton.addEventListener('mouseleave', () => {
                consultantButton.style.transform = 'translateY(0)';
                consultantButton.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
            });
            
            consultantButton.addEventListener('click', () => this.requestConsultant(result));
            
            consultantDiv.appendChild(consultantButton);
            messageElement.appendChild(consultantDiv);
        }

        this.addMessageReactions(messageElement);
        this.chatContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    // 로딩 인디케이터
    showLoadingIndicator(message = 'AI가 응답을 생성하고 있습니다...') {
        const loadingElement = document.createElement('div');
        loadingElement.className = 'loading-indicator';
        loadingElement.innerHTML = `
            <div class="loading-dots">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
            <span class="typing-text">${message}</span>
        `;
        
        this.chatContainer.appendChild(loadingElement);
        this.scrollToBottom();
        return loadingElement;
    }

    // 타이핑 인디케이터
    showTypingIndicator() {
        if (document.querySelector('.typing-indicator')) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="loading-dots">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
            <span class="typing-text">AI가 응답을 생성하고 있습니다...</span>
        `;
        
        this.chatContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // 스크롤
    scrollToBottom() {
        requestAnimationFrame(() => {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        });
    }

    // 메시지 반응 버튼
    addMessageReactions(messageElement) {
        this.messageCounter++;
        const messageIndex = this.messageCounter;
        
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        const buttons = [
            { icon: '👍', text: '도움됨', action: 'helpful', rating: 5.0 },
            { icon: '👎', text: '도움안됨', action: 'not-helpful', rating: 1.0 },
            { icon: '📋', text: '복사', action: 'copy', rating: null }
        ];
        
        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.className = 'reaction-btn';
            button.innerHTML = `${btn.icon} ${btn.text}`;
            
            button.addEventListener('click', () => this.handleReaction(btn, button, messageIndex, messageElement));
            actionsDiv.appendChild(button);
        });
        
        messageElement.appendChild(actionsDiv);
    }

    async handleReaction(btnInfo, buttonElement, messageIndex, messageElement) {
        switch (btnInfo.action) {
            case 'helpful':
            case 'not-helpful':
                const isActive = buttonElement.classList.contains('active');
                
                // 다른 평가 버튼들 비활성화
                const otherButtons = messageElement.querySelectorAll('.reaction-btn');
                otherButtons.forEach(btn => {
                    if (btn !== buttonElement && (btn.textContent.includes('👍') || btn.textContent.includes('👎'))) {
                        btn.classList.remove('active');
                    }
                });
                
                if (!isActive) {
                    buttonElement.classList.add('active');
                    try {
                        await this.sendMessageFeedback(messageIndex, btnInfo.rating, btnInfo.text);
                        this.showNotification(`${btnInfo.text} 피드백이 전송되었습니다`);
                    } catch (error) {
                        console.error('피드백 전송 실패:', error);
                        this.showNotification('피드백 전송에 실패했습니다', 'error');
                    }
                } else {
                    buttonElement.classList.remove('active');
                }
                break;
                
            case 'copy':
                try {
                    const textContent = this.getMessageText(messageElement);
                    await navigator.clipboard.writeText(textContent);
                    this.showNotification('메시지가 복사되었습니다');
                    
                    buttonElement.style.background = 'var(--success)';
                    buttonElement.style.borderColor = 'var(--success)';
                    buttonElement.style.color = 'white';
                    
                    setTimeout(() => {
                        buttonElement.style.background = 'none';
                        buttonElement.style.borderColor = 'var(--gray-300)';
                        buttonElement.style.color = 'var(--gray-600)';
                    }, 1000);
                    
                } catch (error) {
                    console.error('복사 실패:', error);
                    this.showNotification('복사에 실패했습니다', 'error');
                }
                break;
        }
    }

    getMessageText(messageElement) {
        const clone = messageElement.cloneNode(true);
        const actionsDiv = clone.querySelector('.message-actions');
        if (actionsDiv) actionsDiv.remove();
        return clone.textContent.trim();
    }

    async sendMessageFeedback(messageIndex, rating, feedback) {
        try {
            // 데이터 타입 검증 및 변환
            const sessionId = String(this.currentSessionId || localStorage.getItem('graphrag_session_id') || '');
            const msgIndex = parseInt(messageIndex, 10);
            const userRating = parseFloat(rating);
            const feedbackText = String(feedback || '');
            
            console.log('피드백 전송 데이터 (상세):', {
                session_id: sessionId,
                message_index: msgIndex,
                rating: userRating,
                feedback: feedbackText,
                currentSessionId: this.currentSessionId,
                storageSessionId: localStorage.getItem('graphrag_session_id'),
                conversationHistory: this.conversationHistory?.length || 0
            });
            
            // 필수 데이터 검증
            if (!sessionId) {
                console.error('세션 ID가 없습니다. 새로운 세션을 생성합니다.');
                this.currentSessionId = this.getOrCreateSessionId();
                const newSessionId = String(this.currentSessionId);
                
                console.log('새로 생성된 세션 ID:', newSessionId);
                
                // 로컬 스토리지에 피드백 저장 (권한 문제 회피)
                const feedbackKey = `feedback_${newSessionId}_${msgIndex}_${Date.now()}`;
                const feedbackData = {
                    sessionId: newSessionId,
                    messageIndex: msgIndex,
                    rating: userRating,
                    feedback: feedbackText,
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    status: 'session_recreated'
                };
                
                localStorage.setItem(feedbackKey, JSON.stringify(feedbackData));
                this.showNotification('피드백이 저장되었습니다 (세션 재생성)', 'info');
                return { success: true, message: '세션 재생성 후 저장됨' };
            }
            
            if (isNaN(msgIndex) || msgIndex < 0) {
                console.error('메시지 인덱스가 유효하지 않습니다:', messageIndex);
                
                // 안전한 인덱스 사용 (대화 기록 길이 기반)
                const safeIndex = Math.max(0, (this.conversationHistory?.length || 1) - 1);
                console.log('인덱스 보정:', messageIndex, '→', safeIndex);
                
                // 로컬 스토리지에 저장 (권한 문제 회피)
                const feedbackKey = `feedback_${sessionId}_${safeIndex}_${Date.now()}`;
                const feedbackData = {
                    sessionId: sessionId,
                    messageIndex: safeIndex,
                    originalIndex: messageIndex,
                    rating: userRating,
                    feedback: feedbackText,
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    status: 'index_corrected'
                };
                
                localStorage.setItem(feedbackKey, JSON.stringify(feedbackData));
                this.showNotification('피드백이 저장되었습니다 (인덱스 보정)', 'info');
                return { success: true, message: '인덱스 보정 후 저장됨' };
            }
            
            if (isNaN(userRating)) {
                throw new Error('피드백 평점이 유효하지 않습니다');
            }
            
            const formData = new FormData();
            formData.append('session_id', sessionId);
            formData.append('message_index', msgIndex.toString());
            formData.append('rating', userRating.toString());
            formData.append('feedback', feedbackText);
            
            const response = await fetch(`${this.apiBaseUrl}/api/update-message-quality`, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                console.log('피드백 API 전송 성공');
                
                // API 성공 시에도 Firestore에 백업 저장
                try {
                    await this.saveFeedbackToFirestore(sessionId, msgIndex, userRating, feedbackText);
                    this.showNotification('피드백이 전송되었습니다', 'success');
                } catch (firestoreError) {
                    console.warn('Firestore 저장 실패했지만 API는 성공:', firestoreError);
                    this.showNotification('피드백이 전송되었습니다 (서버만)', 'success');
                }
                return await response.json();
            } else {
                // API 실패 상세 로그
                const errorText = await response.text();
                console.error('피드백 API 전송 실패:', {
                    status: response.status,
                    statusText: response.statusText,
                    error: errorText,
                    url: response.url,
                    headers: Object.fromEntries(response.headers.entries())
                });
                
                // API 실패 시 Firestore에 저장
                try {
                    await this.saveFeedbackToFirestore(sessionId, msgIndex, userRating, feedbackText);
                    this.showNotification('피드백이 저장되었습니다 (오프라인)', 'info');
                    return { success: true, message: 'Firestore에 저장됨 (API 실패)' };
                } catch (firestoreError) {
                    console.error('Firestore 저장도 실패:', firestoreError);
                    this.showNotification('피드백 저장에 실패했습니다', 'error');
                    throw new Error(`API와 Firestore 모두 실패: API(${response.status}), Firestore(${firestoreError.message})`);
                }
            }
        } catch (error) {
            console.error('피드백 전송 실패:', error);
            
            // 네트워크 오류 시에도 간단한 로컬 저장 시도 (Firestore 권한 문제 회피)
            try {
                // 세션 ID 재확인
                const fallbackSessionId = this.currentSessionId || localStorage.getItem('graphrag_session_id') || 'unknown';
                
                // 로컬 스토리지에 피드백 저장 (백업)
                const feedbackKey = `feedback_${fallbackSessionId}_${messageIndex}_${Date.now()}`;
                const feedbackData = {
                    sessionId: fallbackSessionId,
                    messageIndex: messageIndex,
                    rating: rating,
                    feedback: feedback,
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    status: 'local_backup'
                };
                
                localStorage.setItem(feedbackKey, JSON.stringify(feedbackData));
                console.log('로컬 스토리지 백업 저장 성공:', feedbackKey);
                
                this.showNotification('피드백이 임시 저장되었습니다', 'info');
                return { success: true, message: '로컬 백업 저장됨' };
            } catch (localError) {
                console.error('로컬 저장도 실패:', localError);
                this.showNotification('피드백 저장에 실패했습니다', 'error');
                return { success: false, message: '모든 저장 방법 실패' };
            }
        }
    }

    // 구글챗 웹훅으로 상담사 연결 요청 전송
    async sendConsultantRequestToGoogleChat(requestData) {
        try {
            // 구글챗 웹훅 URL (위젯 설정에서 가져오기)
            const GOOGLE_CHAT_WEBHOOK = window.GraphRAGWidgetConfig?.googleChatWebhook || 
                                       this.googleChatWebhook || 
                                       'https://chat.googleapis.com/v1/spaces/AAAA_YOUR_SPACE_ID/messages?key=YOUR_KEY&token=YOUR_TOKEN';
            
            const isSuccess = !requestData.error;
            const statusIcon = isSuccess ? '✅' : '❌';
            const statusText = isSuccess ? '상담사 연결 요청' : '상담사 연결 요청 실패';
            
            // 구글챗 메시지 포맷
            let messageText = `${statusIcon} *${statusText}*\n\n`;
            messageText += `📅 *요청시간*: ${new Date().toLocaleString('ko-KR')}\n`;
            messageText += `💬 *고객 질문*: ${requestData.userPrompt.substring(0, 100)}${requestData.userPrompt.length > 100 ? '...' : ''}\n`;
            messageText += `🔑 *세션 ID*: ${requestData.sessionId}\n`;
            
            if (requestData.sensitiveCategories && requestData.sensitiveCategories.length > 0) {
                messageText += `⚠️ *민감 카테고리*: ${requestData.sensitiveCategories.join(', ')}\n`;
            }
            
            if (isSuccess && requestData.consultation_id) {
                messageText += `📋 *문의 번호*: ${requestData.consultation_id}\n`;
            }
            
            if (requestData.error) {
                messageText += `❌ *오류 내용*: ${requestData.error}\n`;
            }
            
            messageText += `🌐 *접속 URL*: ${window.location.href}\n\n`;
            messageText += isSuccess ? 
                '담당 상담사는 고객에게 빠르게 연락해주세요! 📞' : 
                '시스템 관리자가 문제를 확인해주세요! 🔧';
            
            const chatMessage = {
                text: messageText
            };

            console.log('상담사 요청 구글챗 웹훅 전송 시작:', {
                sessionId: requestData.sessionId,
                isSuccess,
                timestamp: requestData.timestamp
            });
            
            const webhookResponse = await fetch(GOOGLE_CHAT_WEBHOOK, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(chatMessage)
            });

            if (webhookResponse.ok) {
                console.log('✅ 상담사 요청 구글챗 웹훅 전송 성공');
            } else {
                console.warn('⚠️ 상담사 요청 구글챗 웹훅 전송 실패:', webhookResponse.status, webhookResponse.statusText);
            }
            
        } catch (error) {
            console.error('❌ 상담사 요청 구글챗 웹훅 전송 실패:', error);
            throw error;
        }
    }

    // 구글챗 웹훅으로 데모 신청 전송
    async sendDemoRequestToGoogleChat(formData, isSuccess = false) {
        try {
            // 구글챗 웹훅 URL (위젯 설정에서 가져오기)
            const GOOGLE_CHAT_WEBHOOK = window.GraphRAGWidgetConfig?.googleChatWebhook || 
                                       this.googleChatWebhook || 
                                       'https://chat.googleapis.com/v1/spaces/AAAA_YOUR_SPACE_ID/messages?key=YOUR_KEY&token=YOUR_TOKEN';
            
            // 데모 신청 데이터 구성
            const demoData = {
                companyName: formData.get('companyName') || '',
                customerName: formData.get('customerName') || '',
                email: formData.get('email') || '',
                phone: formData.get('phone') || '',
                sendType: formData.get('sendType') || '',
                usagePurpose: formData.get('usagePurpose') || '',
                timestamp: new Date().toISOString(),
                url: window.location.href
            };

            // 성공/실패 상태에 따른 메시지 구성
            const statusIcon = isSuccess ? '✅' : '🎯';
            const statusText = isSuccess ? '데모 신청 API 처리 완료' : '새로운 데모 신청이 접수되었습니다';
            const note = isSuccess ? 
                '정상적으로 API를 통해 처리되었습니다.' : 
                '시스템 문제로 대체 경로를 통해 접수되었습니다.';

            // 구글챗 메시지 포맷
            const chatMessage = {
                text: `${statusIcon} *${statusText}*\n\n` +
                      `📅 *신청시간*: ${new Date().toLocaleString('ko-KR')}\n` +
                      `🏢 *회사명*: ${demoData.companyName}\n` +
                      `👤 *고객명*: ${demoData.customerName}\n` +
                      `📧 *이메일*: ${demoData.email}\n` +
                      `📞 *전화번호*: ${demoData.phone}\n` +
                      `📋 *발송타입*: ${demoData.sendType || '미선택'}\n` +
                      `💭 *사용목적*: ${demoData.usagePurpose || '미작성'}\n` +
                      `🌐 *접속 URL*: ${demoData.url}\n\n` +
                      `${note}\n\n` +
                      `담당자는 빠른 시일 내에 고객에게 연락해주세요! 📞`
            };

            // 1차: 구글챗 웹훅으로 전송
            console.log('구글챗 웹훅 전송 시작:', {
                company: demoData.companyName,
                customer: demoData.customerName,
                timestamp: demoData.timestamp
            });
            
            try {
                const webhookResponse = await fetch(GOOGLE_CHAT_WEBHOOK, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(chatMessage)
                });

                if (webhookResponse.ok) {
                    console.log('✅ 구글챗 웹훅 전송 성공:', demoData.companyName);
                } else {
                    console.warn('⚠️ 구글챗 웹훅 전송 실패:', webhookResponse.status, webhookResponse.statusText);
                    // 웹훅 실패해도 계속 진행 (Firestore 백업 저장)
                }
            } catch (webhookError) {
                console.warn('⚠️ 구글챗 웹훅 오류:', webhookError.message);
                // 웹훅 오류해도 계속 진행
            }

            // 2차: Firestore에 백업 저장
            if (window.firebaseDB && window.firestoreFunctions) {
                const { collection, doc, setDoc, serverTimestamp } = window.firestoreFunctions;
                
                const firestoreData = {
                    ...demoData,
                    timestamp: serverTimestamp(),
                    status: 'webhook_submitted'
                };

                const demoRef = doc(collection(window.firebaseDB, 'demo_requests'), `demo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
                await setDoc(demoRef, firestoreData);
                
                console.log('✅ Firestore 백업 저장 성공');
            } else {
                console.warn('⚠️ Firebase가 초기화되지 않아 백업 저장 실패');
            }
            
        } catch (error) {
            console.error('❌ 데모 신청 전송 실패:', error);
            throw error;
        }
    }

    // Firestore에 피드백 직접 저장
    async saveFeedbackToFirestore(sessionId, messageIndex, rating, feedback) {
        try {
            if (!window.firebaseDB || !window.firestoreFunctions) {
                console.warn('Firebase가 초기화되지 않았습니다');
                return;
            }

            const { collection, doc, setDoc, serverTimestamp } = window.firestoreFunctions;
            
            // 피드백 데이터 구성
            const feedbackData = {
                sessionId: sessionId,
                messageIndex: messageIndex,
                rating: rating,
                feedback: feedback,
                timestamp: serverTimestamp(),
                userAgent: navigator.userAgent,
                url: window.location.href
            };

            // Firestore에 피드백 저장
            const feedbackRef = doc(collection(window.firebaseDB, 'feedback'), `${sessionId}_${messageIndex}_${Date.now()}`);
            await setDoc(feedbackRef, feedbackData);
            
            console.log('Firestore 피드백 저장 성공:', feedbackData);
            
        } catch (error) {
            console.error('Firestore 피드백 저장 실패:', error);
            throw error;
        }
    }

    // 알림 표시
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? 'var(--error)' : 'var(--success)'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: var(--shadow);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
            max-width: 300px;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, 3000);
    }

    // 데모 폼 관리
    showDemoForm() {
        if (this.demoFormContainer) {
            this.demoFormContainer.style.display = 'flex';
            if (this.demoForm) {
                this.demoForm.reset();
            }
            const errorContainer = document.getElementById('demo-form-errors');
            if (errorContainer) {
                errorContainer.style.display = 'none';
            }
        }
    }

    hideDemoForm() {
        if (this.demoFormContainer) {
            this.demoFormContainer.style.display = 'none';
        }
    }

    async handleDemoFormSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.demoForm);
        const submitBtn = document.getElementById('demo-form-submit');
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = '처리 중...';
        }
        
        const errorContainer = document.getElementById('demo-form-errors');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
        
        try {
            console.log('데모 신청 전송 중...');
            
            const response = await fetch(`${this.apiBaseUrl}/api/request-demo`, {
                method: 'POST',
                body: formData,
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('데모 신청 성공:', result);
                
                this.displayModelMessage(`✅ **데모 신청이 완료되었습니다!**

**신청 번호**: ${result.request_id}
**신청 시간**: ${result.timestamp}

${result.message}

담당자가 빠른 시일 내에 연락드리겠습니다.`);
                
                if (result.warnings && result.warnings.length > 0) {
                    const warningMessage = "📋 **참고사항**:\n" + result.warnings.map(w => `• ${w}`).join("\n");
                    this.displayModelMessage(warningMessage);
                }
                
                // API 성공 시에는 웹훅 전송하지 않음 (중복 방지)
                console.log('데모 신청 API 성공 - 웹훅 전송 생략');
                
                this.hideDemoForm();
                this.scrollToBottom();
                
            } else {
                console.error('데모 신청 API 실패:', result);
                
                // API 실패 시 구글챗 웹훅으로 전송 (중복 메시지 방지)
                console.log('API 실패로 인한 웹훅 전송 시도...');
                
                try {
                    await this.sendDemoRequestToGoogleChat(formData, false);
                    console.log('웹훅 전송 성공 - 사용자에게 알림');
                    
                    this.displayModelMessage(`📤 **데모 신청이 접수되었습니다**

시스템 문제로 인해 대체 경로를 통해 담당팀에 전달되었습니다.

**접수된 정보**:
• 회사명: ${formData.get('companyName')}
• 고객명: ${formData.get('customerName')}
• 이메일: ${formData.get('email')}

담당자가 확인 후 연락드리겠습니다. 🙏`);

                    this.hideDemoForm();
                    this.scrollToBottom();
                    
                } catch (firestoreError) {
                    console.error('데모 신청 Firestore 저장도 실패:', firestoreError);
                    
                    if (errorContainer) {
                        let errorHtml = "";
                        
                        if (result.errors && result.errors.length > 0) {
                            errorHtml += "<ul>";
                            result.errors.forEach(error => {
                                errorHtml += `<li>${error}</li>`;
                            });
                            errorHtml += "</ul>";
                        } else {
                            errorHtml = result.message || "데모 신청 중 오류가 발생했습니다.";
                        }
                        
                        errorContainer.innerHTML = errorHtml;
                        errorContainer.style.display = "block";
                    }
                }
            }
            
        } catch (error) {
            console.error('데모 신청 중 네트워크 오류:', error);
            
            // 네트워크 오류 시에도 구글챗 웹훅 시도 (중복 메시지 방지)
            console.log('네트워크 오류로 인한 웹훅 전송 시도...');
            
            try {
                await this.sendDemoRequestToGoogleChat(formData, false);
                console.log('네트워크 오류 상황에서 웹훅 전송 성공');
                
                this.displayModelMessage(`🌐 **데모 신청이 접수되었습니다**

네트워크 문제가 있었지만 대체 경로를 통해 담당팀에 전달되었습니다.

**접수된 정보**:
• 회사명: ${formData.get('companyName')}
• 고객명: ${formData.get('customerName')}
• 이메일: ${formData.get('email')}

담당자가 확인 후 연락드리겠습니다. 🔄`);

                this.hideDemoForm();
                this.scrollToBottom();
                
            } catch (webhookError) {
                console.error('구글챗 웹훅도 실패:', webhookError);
                
                if (errorContainer) {
                    errorContainer.innerHTML = "일시적인 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
                    errorContainer.style.display = "block";
                }
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "신청하기";
            }
        }
    }

    async requestConsultant(apiResult) {
        console.log('상담사 연결 요청 시작...');
        
        try {
            const lastUserMessage = this.conversationHistory
                .filter(msg => msg.role === 'user')
                .slice(-1)[0];
            
            const userPrompt = lastUserMessage?.parts?.[0]?.text || '';
            
            const formData = new FormData();
            formData.append('userPrompt', userPrompt);
            formData.append('conversationHistory', JSON.stringify(this.conversationHistory));
            formData.append('sessionId', apiResult.metadata?.session_id || '');
            formData.append('sensitiveCategories', JSON.stringify(apiResult.metadata?.sensitive_categories || []));
            
            this.displayModelMessage('상담사 연결 요청을 처리하고 있습니다... 🔄');
            
            const response = await fetch(`${this.apiBaseUrl}/api/request-consultant`, {
                method: 'POST',
                body: formData,
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.displayModelMessage(`✅ ${result.message}\n\n**문의 번호**: ${result.consultation_id}\n**요청 시간**: ${new Date(result.timestamp).toLocaleString('ko-KR')}`);
                console.log('상담사 연결 요청 성공:', result);
                
                // 성공 시 구글챗 웹훅으로 알림 전송
                this.sendConsultantRequestToGoogleChat({
                    userPrompt,
                    sessionId: apiResult.metadata?.session_id || '',
                    sensitiveCategories: apiResult.metadata?.sensitive_categories || [],
                    consultation_id: result.consultation_id,
                    timestamp: result.timestamp
                }).catch(error => {
                    console.warn('상담사 요청 웹훅 전송 실패:', error);
                });
                
            } else {
                this.displayModelMessage(`❌ ${result.message || "상담 요청 처리 중 오류가 발생했습니다."}`);
                console.error('상담사 연결 요청 실패:', result);
                
                // 실패 시에도 구글챗으로 알림 (실패 상태로)
                this.sendConsultantRequestToGoogleChat({
                    userPrompt,
                    sessionId: apiResult.metadata?.session_id || '',
                    sensitiveCategories: apiResult.metadata?.sensitive_categories || [],
                    consultation_id: null,
                    timestamp: new Date().toISOString(),
                    error: result.message || "상담 요청 처리 중 오류가 발생했습니다."
                }).catch(error => {
                    console.warn('상담사 요청 실패 웹훅 전송 실패:', error);
                });
            }
            
        } catch (error) {
            console.error('상담사 연결 요청 중 오류:', error);
            this.displayModelMessage('❌ 상담사 연결 요청 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            
            // 네트워크 오류 시에도 구글챗으로 알림
            this.sendConsultantRequestToGoogleChat({
                userPrompt: this.conversationHistory
                    .filter(msg => msg.role === 'user')
                    .slice(-1)[0]?.parts?.[0]?.text || '',
                sessionId: apiResult.metadata?.session_id || '',
                sensitiveCategories: apiResult.metadata?.sensitive_categories || [],
                consultation_id: null,
                timestamp: new Date().toISOString(),
                error: '네트워크 오류로 인한 상담사 연결 요청 실패'
            }).catch(webhookError => {
                console.warn('상담사 요청 네트워크 오류 웹훅 전송 실패:', webhookError);
            });
        }
        
        this.scrollToBottom();
    }

    // Firestore 저장
    async saveConversationToFirestore(userQuery, aiResponse, metadata = {}) {
        try {
            if (!window.firebaseDB || !window.firestoreFunctions) {
                console.log('Firebase가 로드되지 않아 로컬 저장만 사용합니다');
                return false;
            }
            
            const { collection, doc, setDoc, getDoc, updateDoc, arrayUnion, serverTimestamp } = window.firestoreFunctions;
            const db = window.firebaseDB;
            
            const messageData = {
                user_query: userQuery,
                ai_response: aiResponse,
                timestamp: serverTimestamp(),
                metadata: {
                    ...metadata,
                    user_agent: navigator.userAgent,
                    response_length: aiResponse.length,
                    query_length: userQuery.length,
                    widget_version: '1.0'
                }
            };
            
            const sessionRef = doc(collection(db, 'widget_conversations'), this.currentSessionId);
            const sessionDoc = await getDoc(sessionRef);
            
            if (sessionDoc.exists()) {
                await updateDoc(sessionRef, {
                    messages: arrayUnion(messageData),
                    message_count: sessionDoc.data().message_count + 1,
                    updated_at: serverTimestamp(),
                    last_activity: serverTimestamp()
                });
            } else {
                await setDoc(sessionRef, {
                    session_id: this.currentSessionId,
                    created_at: serverTimestamp(),
                    updated_at: serverTimestamp(),
                    last_activity: serverTimestamp(),
                    messages: [messageData],
                    message_count: 1,
                    widget_version: '1.0',
                    user_info: {
                        user_agent: navigator.userAgent,
                        language: navigator.language,
                        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }
                });
            }
            
            console.log(`✅ Widget Firestore 대화 저장 성공 - 세션: ${this.currentSessionId}`);
            return true;
            
        } catch (error) {
            console.error('❌ Widget Firestore 대화 저장 실패:', error);
            return false;
        }
    }
}

// DOM 로드 후 위젯 초기화
// 위젯 초기화 함수
function initChatbotWidget(config = {}) {
    // 위젯 요소가 존재할 때만 초기화
    if (document.getElementById('chatbot-toggle') && document.getElementById('chatbot-widget')) {
        const widgetInstance = new ChatbotWidget(config);
        window.chatbotWidget = widgetInstance;
        window.chatbotWidgetInstance = widgetInstance; // 외부 접근용
        return window.chatbotWidget;
    }
    return null;
}

// 외부에서 사용할 수 있는 전역 함수
window.initGraphRAGChatWidget = initChatbotWidget;

// 자동 초기화 (기존 동작 유지)
document.addEventListener('DOMContentLoaded', () => {
    initChatbotWidget();
});

// 추가 안전장치
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.chatbotWidget) {
            initChatbotWidget();
        }
    });
} else {
    if (!window.chatbotWidget) {
        // 지연 실행으로 외부 로더가 설정할 시간 제공
        setTimeout(() => {
            if (!window.chatbotWidget) {
                initChatbotWidget();
            }
        }, 100);
    }
}