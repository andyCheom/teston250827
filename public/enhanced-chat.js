// Enhanced Chat UI Functions

// 타이핑 인디케이터 표시
function showTypingIndicator() {
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
    
    const chatContainer = document.getElementById('chat-container');
    chatContainer.appendChild(typingDiv);
    scrollToBottom();
}

// 타이핑 인디케이터 제거
function hideTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// 로딩 인디케이터 표시
function showLoadingIndicator(message = '처리 중...') {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    loadingDiv.innerHTML = `
        <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        </div>
        <span>${message}</span>
    `;
    
    const chatContainer = document.getElementById('chat-container');
    chatContainer.appendChild(loadingDiv);
    scrollToBottom();
    
    return loadingDiv;
}

// 메시지에 반응 버튼 추가
function addMessageActions(messageElement, messageType, messageIndex) {
    if (messageType === 'user') return; // 사용자 메시지에는 반응 버튼 없음
    
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';
    actionsDiv.innerHTML = `
        <button class="reaction-btn" data-reaction="helpful" data-index="${messageIndex}">
            👍 도움됨
        </button>
        <button class="reaction-btn" data-reaction="not-helpful" data-index="${messageIndex}">
            👎 도움안됨
        </button>
        <button class="reaction-btn" data-reaction="copy" data-index="${messageIndex}">
            📋 복사
        </button>
    `;
    
    messageElement.appendChild(actionsDiv);
    
    // 반응 버튼 이벤트 리스너
    actionsDiv.addEventListener('click', handleMessageReaction);
}

// 메시지 반응 처리
function handleMessageReaction(event) {
    const button = event.target.closest('.reaction-btn');
    if (!button) return;
    
    const reaction = button.dataset.reaction;
    const messageIndex = parseInt(button.dataset.index);
    
    switch (reaction) {
        case 'helpful':
            button.classList.toggle('active');
            // API 호출로 피드백 전송
            sendFeedback(messageIndex, 5.0, '도움이 되었습니다');
            break;
        case 'not-helpful':
            button.classList.toggle('active');
            // API 호출로 피드백 전송
            sendFeedback(messageIndex, 1.0, '도움이 되지 않았습니다');
            break;
        case 'copy':
            copyMessageText(button.closest('.message'));
            showNotification('메시지가 복사되었습니다');
            break;
    }
}

// 메시지 텍스트 복사
function copyMessageText(messageElement) {
    const textElement = messageElement.querySelector('pre') || messageElement;
    const text = textElement.textContent;
    
    navigator.clipboard.writeText(text).catch(err => {
        console.error('복사 실패:', err);
        // 폴백: 텍스트 선택
        const range = document.createRange();
        range.selectNodeContents(textElement);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    });
}

// 피드백 전송
async function sendFeedback(messageIndex, rating, feedback) {
    try {
        // 위젯 인스턴스에서 apiBaseUrl 가져오기
        const apiBaseUrl = window.chatbotWidgetInstance?.apiBaseUrl || 
                          window.GraphRAGWidgetConfig?.baseUrl || 
                          'https://sampleprojects-468223-graphrag-api-975882305117.asia-northeast3.run.app';
        
        const sessionId = localStorage.getItem('graphrag_session_id');
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('message_index', messageIndex);
        formData.append('rating', rating);
        formData.append('feedback', feedback);
        
        const response = await fetch(`${apiBaseUrl}/api/update-message-quality`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            console.log('피드백 전송 성공:', { messageIndex, rating, feedback });
            
            // Firestore에 직접 피드백 저장
            await saveFeedbackToFirestore(sessionId, messageIndex, rating, feedback);
            
            showNotification('피드백이 전송되었습니다', 'success');
        } else {
            console.error('피드백 전송 실패 - 응답 오류:', response.status);
            
            // API 실패 시 Firestore에만 저장
            await saveFeedbackToFirestore(sessionId, messageIndex, rating, feedback);
            
            showNotification('피드백이 저장되었습니다', 'warning');
        }
    } catch (error) {
        console.error('피드백 전송 실패:', error);
        
        // 네트워크 오류 시에도 Firestore에 저장 시도
        try {
            await saveFeedbackToFirestore(sessionId, messageIndex, rating, feedback);
            showNotification('피드백이 저장되었습니다 (오프라인)', 'info');
        } catch (firestoreError) {
            console.error('Firestore 저장도 실패:', firestoreError);
            showNotification('피드백 전송에 실패했습니다', 'error');
        }
    }
}

// Firestore에 피드백 직접 저장
async function saveFeedbackToFirestore(sessionId, messageIndex, rating, feedback) {
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

// 상태 인디케이터 표시
function showStatusIndicator(status, message) {
    let indicator = document.querySelector('.status-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.className = 'status-indicator';
        document.body.appendChild(indicator);
    }
    
    indicator.className = `status-indicator status-${status}`;
    indicator.textContent = message;
    
    // 자동 숨김 (에러가 아닌 경우)
    if (status !== 'error') {
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.remove();
            }
        }, 3000);
    }
}

// 알림 표시
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 1rem;
        left: 50%;
        transform: translateX(-50%);
        background: var(--primary-600);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        animation: slideDown 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideUp 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 2000);
}

// 부드러운 스크롤
function scrollToBottom(smooth = true) {
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }
}

// 텍스트 애니메이션 효과
function typewriterEffect(element, text, speed = 30) {
    element.textContent = '';
    let i = 0;
    
    const typeInterval = setInterval(() => {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            scrollToBottom();
        } else {
            clearInterval(typeInterval);
        }
    }, speed);
    
    return typeInterval;
}

// 향상된 메시지 생성
function createEnhancedMessage(content, type, includeActions = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    // 메시지 내용
    const contentElement = document.createElement('pre');
    contentElement.textContent = content;
    messageDiv.appendChild(contentElement);
    
    // 타임스탬프 추가
    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = new Date().toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit'
    });
    messageDiv.appendChild(timestamp);
    
    // 반응 버튼 추가 (AI 메시지에만)
    if (includeActions && type === 'model') {
        const messageIndex = document.querySelectorAll('.model-message').length;
        addMessageActions(messageDiv, type, messageIndex);
    }
    
    return messageDiv;
}

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideDown {
        from {
            transform: translateX(-50%) translateY(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
    }
    
    @keyframes slideUp {
        from {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
        to {
            transform: translateX(-50%) translateY(-100%);
            opacity: 0;
        }
    }
    
    .notification {
        font-size: 0.875rem;
        font-weight: 500;
    }
`;

document.head.appendChild(style);

// 전역 함수로 내보내기
window.enhancedChat = {
    showTypingIndicator,
    hideTypingIndicator,
    showLoadingIndicator,
    showStatusIndicator,
    showNotification,
    scrollToBottom,
    typewriterEffect,
    createEnhancedMessage,
    addMessageActions,
    copyMessageText
};