// Vertex AI 채팅 인터페이스 스크립트

document.addEventListener("DOMContentLoaded", function () {
  const chatContainer = document.getElementById("chat-container");
  const promptInput = document.getElementById("prompt");
  const submitButton = document.getElementById("submit");
  const form = document.getElementById("chat-form");

  let conversationHistory = [];
  let sessionId = generateSessionId();

  // 세션 ID 생성 함수
  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // 초기화
  init();

  function init() {
    // 환영 메시지 표시
    displayModelMessage("안녕하세요! 궁금한 것이 있으시면 언제든 물어보세요. 😊");

    // 폼 제출 이벤트
    form.addEventListener("submit", handleFormSubmit);

    // 입력 필드에 포커스
    promptInput.focus();

    // 엔터키 처리 (Shift+Enter는 줄바꿈)
    promptInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleFormSubmit(e);
      }
    });

    

    // 자동 크기 조정
    promptInput.addEventListener("input", autoResizeTextarea);
  }

  function autoResizeTextarea() {
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + 'px';
  }

  async function handleFormSubmit(e) {
    e.preventDefault();

    const userPrompt = promptInput.value.trim();
    if (!userPrompt) return;

    const startTime = Date.now();

    // 사용자 메시지 표시
    displayUserMessage(userPrompt);

    // 폼 데이터 준비
    const formData = new FormData();
    formData.append("userPrompt", userPrompt);
    formData.append("conversationHistory", JSON.stringify(conversationHistory));
    formData.append("sessionId", sessionId);

    // 입력 필드 초기화 및 비활성화
    promptInput.value = "";
    autoResizeTextarea();
    promptInput.disabled = true;
    submitButton.disabled = true;

    // 로딩 표시
    const loadingElement = showLoadingIndicator();
    scrollToBottom();

    try {
      // API 호출
      const response = await fetch("/api/generate", {
        method: "POST",
        body: formData,
      });

      // 로딩 제거
      if (loadingElement) loadingElement.remove();

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.error?.message || errorData.detail || `API 요청 실패: ${response.status}`;
        } catch (jsonError) {
          errorMessage = `서버 오류 (${response.status}): ${errorText.substring(0, 200)}`;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();

      // 대화 기록 업데이트
      if (Array.isArray(result.updatedHistory)) {
        conversationHistory = result.updatedHistory;
      }

      // 응답 표시
      const modelResponseText = result.summary_answer || 
                              result.answer || 
                              result.vertex_answer || 
                              result.vertexAiResponse?.candidates?.[0]?.content?.parts?.[0]?.text;

      if (modelResponseText) {
        // 인용 정보가 있는 경우 특별한 표시 방식 사용
        if (result.citations && result.citations.length > 0) {
          displayModelMessageWithSources(modelResponseText, result);
        } else {
          displayModelMessage(modelResponseText);
        }
      } else {
        displayModelMessage('죄송합니다, 답변을 생성하지 못했습니다.');
      }

    } catch (error) {
      if (loadingElement) loadingElement.remove();
      
      console.error('API 호출 오류:', error);
      displayModelMessage(`❌ 오류가 발생했습니다: ${error.message}`);
    } finally {
      // 입력 필드 재활성화
      promptInput.disabled = false;
      submitButton.disabled = false;
      promptInput.focus();
      scrollToBottom();
    }
  }

  function displayUserMessage(message) {
    const messageElement = document.createElement("div");
    messageElement.className = "message user-message";
    messageElement.innerHTML = `<pre>${escapeHtml(message)}</pre>`;
    chatContainer.appendChild(messageElement);
    scrollToBottom();
  }

  function showLoadingIndicator() {
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "message model-message loading";
    loadingDiv.innerHTML = `
      <div class="loading-dots">
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
      </div>
      <span>AI가 응답을 생성하고 있습니다...</span>
    `;
    chatContainer.appendChild(loadingDiv);
    return loadingDiv;
  }

  function escapeHtml(text) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
  }

  // 동적 도메인 링크 처리 함수 
  function getBaseDomain() {
    // 위젯 설정에서 베이스 도메인 가져오기
    if (window.GraphRAGWidgetConfig?.baseDomain) {
      return window.GraphRAGWidgetConfig.baseDomain;
    }
    
    // API URL에서 도메인 추출 (위젯 인스턴스 확인)
    if (window.chatbotWidgetInstance?.apiBaseUrl) {
      const apiUrl = window.chatbotWidgetInstance.apiBaseUrl;
      // Cloud Run URL에서 Firebase Hosting 도메인 추출
      const match = apiUrl.match(/https:\/\/([^-]+)-[^-]+-[^-]+-[^.]+\.([^.]+)\.run\.app/);
      if (match) {
        return `https://${match[1]}.web.app`; // Firebase Hosting 도메인 형식
      }
    }
    
    // 기본 도메인 (cheomservice.com)
    return 'https://cheomservice.com';
  }

  function displayModelMessage(markdownText) {
    const messageElement = document.createElement("div");
    messageElement.className = "message model-message";

    // marked.parse()를 사용하여 마크다운을 HTML로 변환합니다.
    let htmlContent = marked.parse(markdownText);
    
    // 문서 출처 링크 수정
    htmlContent = fixDocumentLinks(htmlContent);
    
    messageElement.innerHTML = htmlContent;
    
    // 모든 링크를 새 탭에서 열리도록 설정 및 접근성 향상
    const links = messageElement.querySelectorAll('a');
    links.forEach(link => {
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      
      // 링크 접근성 및 오류 처리 개선
      link.addEventListener('click', function(e) {
        const href = link.href;
        console.log('🔗 링크 클릭됨:', href);
        
        // 링크 유효성 검사
        if (href.includes('/gcs/')) {
          // GCS 링크인 경우 접근성 체크
          console.log('📁 GCS 문서 링크 접근 시도:', href);
          
          // Firebase Hosting 리라우팅을 통해 처리되는 링크인지 확인
          const baseDomain = getBaseDomain();
          if (!href.startsWith(baseDomain)) {
            console.warn('⚠️ 잘못된 도메인의 GCS 링크:', href);
            e.preventDefault();
            
            if (window.enhancedChat) {
              window.enhancedChat.showNotification('문서 링크가 올바르지 않습니다. 페이지를 새로고침해주세요.', 'warning');
            } else {
              // 기본 알림 표시
              const notification = document.createElement('div');
              notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ff9800;
                color: white;
                padding: 12px 16px;
                border-radius: 8px;
                z-index: 10000;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
              `;
              notification.textContent = '⚠️ 문서 링크가 올바르지 않습니다. 페이지를 새로고침해주세요.';
              document.body.appendChild(notification);
              
              setTimeout(() => {
                notification.remove();
              }, 5000);
            }
            return false;
          }
        }
        
        // 문서 접근 로그 기록
        console.log('📄 문서 접근:', {
          url: href,
          timestamp: new Date().toISOString(),
          referrer: window.location.href
        });
      });
    });

    // 메시지 반응 버튼 추가
    addMessageReactions(messageElement);

    chatContainer.appendChild(messageElement);
  }

  // 문서 출처 링크 수정 함수
  function fixDocumentLinks(htmlContent) {
    console.log('링크 수정 전 확인:', htmlContent.substring(0, 500));
    
    let fixedContent = htmlContent;
    const baseDomain = getBaseDomain();
    console.log('🌐 사용할 베이스 도메인:', baseDomain);
    
    // Firebase Hosting 리라우팅 구조를 고려한 링크 처리
    // firebase.json에서 /gcs/** 경로는 Cloud Run으로 프록시됨
    
    // 1. GCS 스토리지 경로 패턴 수정
    // 예: https://cheomservice.com/gcs/sampleprojects-468223-graphrag-storage/IT사업부 문서.../web_html/file.html
    // → https://cheomservice.com/gcs/web_html/file.html (Firebase 리라우팅 활용)
    fixedContent = fixedContent.replace(
      /https:\/\/[^/]+\/gcs\/sampleprojects-468223-graphrag-storage\/[^/]+\/([^"'\s\)>]+)/g,
      function(match, path) {
        console.log('📁 GCS 링크 매칭됨:', match);
        console.log('📄 추출된 경로:', path);
        const fixedUrl = `${baseDomain}/gcs/${path}`;
        console.log('🔗 수정된 링크:', fixedUrl);
        return fixedUrl;
      }
    );
    
    // 2. URL 인코딩된 경로 처리 (한글 파일명 등)
    fixedContent = fixedContent.replace(
      /https:\/\/[^/]+\/gcs\/[^/]+\/[^"'\s\)>]*%[0-9A-Fa-f]{2}[^"'\s\)>]*\/([^"'\s\)>]+)/g,
      function(match, path) {
        console.log('🈳 인코딩된 링크 매칭됨:', match);
        const decodedPath = decodeURIComponent(path);
        const fixedUrl = `${baseDomain}/gcs/${decodedPath}`;
        console.log('🔗 디코딩 후 수정된 링크:', fixedUrl);
        return fixedUrl;
      }
    );
    
    // 3. 일반적인 다중 세그먼트 GCS 경로 처리 (백업용)
    fixedContent = fixedContent.replace(
      /https:\/\/[^/]+\/gcs\/[^/]+\/[^/]+\/[^/]+\/([^"'\s\)>]+)/g,
      function(match, path) {
        console.log('📂 다중 세그먼트 GCS 링크 매칭됨:', match);
        const fixedUrl = `${baseDomain}/gcs/${path}`;
        console.log('🔗 수정된 링크:', fixedUrl);
        return fixedUrl;
      }
    );
    
    // 4. 기타 잘못된 도메인 패턴 수정
    fixedContent = fixedContent.replace(
      /https:\/\/[^/]+\/([^"'\s\)>]*\.html?)/g,
      function(match, path) {
        // 이미 올바른 도메인인 경우 패스
        if (match.startsWith(baseDomain)) {
          return match;
        }
        console.log('🌐 도메인 수정 대상:', match);
        const fixedUrl = `${baseDomain}/gcs/${path}`;
        console.log('🔗 도메인 수정 완료:', fixedUrl);
        return fixedUrl;
      }
    );
    
    if (fixedContent !== htmlContent) {
      console.log('✅ 링크 수정 완료');
      console.log('📋 수정 후 미리보기:', fixedContent.substring(0, 500));
    } else {
      console.log('🔍 수정할 링크를 찾지 못했습니다');
    }
    
    return fixedContent;
  }

  function displayModelMessageWithSources(markdownText, result) {
    console.log("Citations 존재 여부:", result.citations && result.citations.length > 0);
    console.log("Citations 내용:", result.citations);
    
    const messageElement = document.createElement("div");
    messageElement.className = "message model-message";

    // 메인 답변을 마크다운으로 파싱하여 HTML로 변환
    let htmlContent = marked.parse(markdownText);
    
    // 문서 출처 링크 수정
    htmlContent = fixDocumentLinks(htmlContent);
    
    messageElement.innerHTML = htmlContent;

    // Citations 섹션 제거 - 참조 문서 목록 출력하지 않음

    // Related Questions 추가
    console.log("응답 데이터 확인:", result);
    console.log("related_questions 확인:", result.related_questions);
    
    // 더미 데이터 제거 - 실제 related_questions만 표시
    if (result.related_questions && Array.isArray(result.related_questions) && result.related_questions.length > 0) {
      // 실제 데이터인지 확인 (더미 데이터가 아닌지)
      const realQuestions = result.related_questions.filter(q => 
        q && q.trim() && 
        !q.includes('sample') && 
        !q.includes('더미') &&
        q.length > 5
      );
      
      if (realQuestions.length > 0) {
        const relatedQuestionsDiv = document.createElement("div");
        relatedQuestionsDiv.className = "related-questions";
        relatedQuestionsDiv.innerHTML = `
          <h4>💡 관련 질문들</h4>
          <div class="question-buttons">
            ${realQuestions.slice(0, 3).map(question => 
              `<button class="related-question-btn" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`
            ).join('')}
          </div>
        `;

        // 관련 질문 버튼 이벤트 리스너 추가
        relatedQuestionsDiv.addEventListener('click', function(e) {
          if (e.target.classList.contains('related-question-btn')) {
            const question = e.target.dataset.question;
            promptInput.value = question;
            promptInput.focus();
            autoResizeTextarea();
            // 바로 전송하지 않고 사용자가 확인할 수 있도록 함
          }
        });

        messageElement.appendChild(relatedQuestionsDiv);
      }
    }

    // 상담사 연결 버튼 추가 (consultant_needed가 true인 경우)
    if (result.consultant_needed || 
        (result.metadata && result.metadata.consultant_needed) || 
        (result.metadata && result.metadata.sensitive_categories && result.metadata.sensitive_categories.length > 0)) {
      
      console.log("상담사 연결 필요 감지:", {
        consultant_needed: result.consultant_needed,
        metadata_consultant_needed: result.metadata?.consultant_needed,
        sensitive_categories: result.metadata?.sensitive_categories
      });
      
      const consultantDiv = document.createElement("div");
      consultantDiv.className = "consultant-section";
      consultantDiv.innerHTML = `
        <div class="consultant-notice">
          <p>🔒 민감한 정보나 전문적인 상담이 필요한 내용입니다.</p>
          <button class="consultant-btn" data-api-result='${JSON.stringify(result)}'>
            🎧 상담사와 연결하기
          </button>
        </div>
      `;

      // 상담사 연결 버튼 이벤트
      const consultantButton = consultantDiv.querySelector('.consultant-btn');
      consultantButton.addEventListener('click', function() {
        const apiResult = JSON.parse(this.dataset.apiResult);
        requestConsultant(apiResult);
      });

      messageElement.appendChild(consultantDiv);
    }

    // 모든 링크를 새 탭에서 열리도록 설정
    const links = messageElement.querySelectorAll('a');
    links.forEach(link => {
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      
      // 링크 접근성 및 오류 처리 개선
      link.addEventListener('click', function(e) {
        const href = link.href;
        console.log('🔗 링크 클릭됨:', href);
        
        // 링크 유효성 검사
        if (href.includes('/gcs/')) {
          // GCS 링크인 경우 접근성 체크
          console.log('📁 GCS 문서 링크 접근 시도:', href);
          
          // Firebase Hosting 리라우팅을 통해 처리되는 링크인지 확인
          const baseDomain = getBaseDomain();
          if (!href.startsWith(baseDomain)) {
            console.warn('⚠️ 잘못된 도메인의 GCS 링크:', href);
            e.preventDefault();
            
            if (window.enhancedChat) {
              window.enhancedChat.showNotification('문서 링크가 올바르지 않습니다. 페이지를 새로고침해주세요.', 'warning');
            } else {
              // 기본 알림 표시
              const notification = document.createElement('div');
              notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ff9800;
                color: white;
                padding: 12px 16px;
                border-radius: 8px;
                z-index: 10000;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
              `;
              notification.textContent = '⚠️ 문서 링크가 올바르지 않습니다. 페이지를 새로고침해주세요.';
              document.body.appendChild(notification);
              
              setTimeout(() => {
                notification.remove();
              }, 5000);
            }
            return false;
          }
        }
        
        // 문서 접근 로그 기록
        console.log('📄 문서 접근:', {
          url: href,
          timestamp: new Date().toISOString(),
          referrer: window.location.href
        });
      });
    });

    // 메시지 반응 버튼 추가
    addMessageReactions(messageElement);

    chatContainer.appendChild(messageElement);
  }

  async function requestConsultant(apiResult) {
    console.log('상담사 연결 요청 시작...');
    
    try {
      const lastUserMessage = conversationHistory
        .filter(msg => msg.role === 'user')
        .slice(-1)[0];
      
      const userPrompt = lastUserMessage?.parts?.[0]?.text || '';
      
      const formData = new FormData();
      formData.append('userPrompt', userPrompt);
      formData.append('conversationHistory', JSON.stringify(conversationHistory));
      formData.append('sessionId', apiResult.metadata?.session_id || sessionId);
      formData.append('sensitiveCategories', JSON.stringify(apiResult.metadata?.sensitive_categories || []));
      
      displayModelMessage('상담사 연결 요청을 처리하고 있습니다... 🔄');
      
      const response = await fetch('/api/request-consultant', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      
      if (result.success) {
        displayModelMessage(`✅ ${result.message}\n\n**문의 번호**: ${result.consultation_id}\n**요청 시간**: ${new Date(result.timestamp).toLocaleString('ko-KR')}`);
        console.log('상담사 연결 요청 성공:', result);
      } else {
        displayModelMessage(`❌ ${result.message || "상담 요청 처리 중 오류가 발생했습니다."}`);
        console.error('상담사 연결 요청 실패:', result);
      }
      
    } catch (error) {
      console.error('상담사 연결 요청 중 오류:', error);
      displayModelMessage('❌ 상담사 연결 요청 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    }
    
    scrollToBottom();
  }

  function addMessageReactions(messageElement) {
    const reactionsDiv = document.createElement("div");
    reactionsDiv.className = "message-reactions";
    reactionsDiv.innerHTML = `
      <button class="reaction-btn helpful" title="도움됨">👍</button>
      <button class="reaction-btn not-helpful" title="도움되지 않음">👎</button>
      <button class="reaction-btn copy" title="복사">📋</button>
    `;

    // 반응 버튼 이벤트 리스너
    reactionsDiv.addEventListener('click', function(e) {
      if (e.target.classList.contains('reaction-btn')) {
        handleReaction(e.target, messageElement);
      }
    });

    messageElement.appendChild(reactionsDiv);
  }

  function handleReaction(button, messageElement) {
    const reaction = button.classList.contains('helpful') ? 'helpful' : 
                    button.classList.contains('not-helpful') ? 'not-helpful' : 'copy';
    
    switch (reaction) {
      case 'helpful':
        button.classList.toggle('active');
        console.log('도움됨 피드백');
        break;
      case 'not-helpful':
        button.classList.toggle('active');
        console.log('도움되지 않음 피드백');
        break;
      case 'copy':
        copyMessageText(messageElement);
        showNotification('메시지가 복사되었습니다');
        break;
    }
  }

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

  function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
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
    }, 2000);
  }

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

});