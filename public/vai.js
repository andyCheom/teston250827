// 더 안전한 DOM 로딩 확인
function initializeChat() {
  console.log("채팅 초기화 시작...");
  
  // DOM Elements
  const chatContainer = document.getElementById("chat-container");
  const promptForm = document.getElementById("prompt-form");
  const promptInput = document.getElementById("prompt-input");
  
  // Demo form elements
  const demoRequestBtn = document.getElementById("demo-request-btn");
  const demoFormContainer = document.getElementById("demo-form-container");
  const demoForm = document.getElementById("demo-form");
  const demoFormClose = document.getElementById("demo-form-close");
  const demoFormCancel = document.getElementById("demo-form-cancel");
  
  console.log("DOM 요소 확인:", {
    chatContainer: !!chatContainer,
    promptForm: !!promptForm,
    promptInput: !!promptInput
  });

  const submitButton = promptForm ? promptForm.querySelector(
    'button[type="submit"], input[type="submit"]'
  ) : null;

  // State
  let conversationHistory = [];
  let currentSessionId = generateSessionId();
  
  // Firestore 세션 관리
  function generateSessionId() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `session_${random}_${timestamp}`;
  }

  // --- Initial validation ---
  // Ensure essential elements exist before proceeding
  if (!chatContainer || !promptForm || !promptInput) {
    console.error(
      "Essential chat components not found in the DOM. Elements found:",
      {
        chatContainer: !!chatContainer,
        promptForm: !!promptForm, 
        promptInput: !!promptInput
      }
    );
    document.body.innerHTML =
      '<p style="color: red; text-align: center; margin-top: 2rem;">채팅 인터페이스를 불러오는 데 실패했습니다. 페이지의 HTML 요소를 확인해주세요.<br><small>개발자 도구 콘솔에서 자세한 정보를 확인하세요.</small></p>';
    return;
  }
  
  console.log("모든 DOM 요소가 정상적으로 로드되었습니다.");

  // --- UI Setup ---
  // Set input font to match chat window font for consistency
  const bodyFont = window.getComputedStyle(document.body).fontFamily;
  if (bodyFont) {
    promptInput.style.fontFamily = bodyFont;
  }

  // --- Event Listeners ---

  // Handle form submission (sending a message)
  promptForm.addEventListener("submit", handleFormSubmit);

  // Auto-resize textarea
  promptInput.addEventListener("input", () => {
    promptInput.style.height = "auto";
    promptInput.style.height = `${promptInput.scrollHeight}px`;
  });

  // Allow submitting with Enter key, but new line with Shift+Enter
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      promptForm.requestSubmit();
    }
  });

  // Demo form event listeners
  if (demoRequestBtn) {
    demoRequestBtn.addEventListener("click", showDemoForm);
  }
  
  if (demoFormClose) {
    demoFormClose.addEventListener("click", hideDemoForm);
  }
  
  if (demoFormCancel) {
    demoFormCancel.addEventListener("click", hideDemoForm);
  }
  
  if (demoForm) {
    demoForm.addEventListener("submit", handleDemoFormSubmit);
  }
  
  // Close demo form when clicking outside
  if (demoFormContainer) {
    demoFormContainer.addEventListener("click", (e) => {
      if (e.target === demoFormContainer) {
        hideDemoForm();
      }
    });
  }

  // --- Firestore Functions ---
  
  async function saveConversationToFirestore(userQuery, aiResponse, metadata = {}) {
    try {
      // Firebase가 로드되지 않았으면 스킵
      if (!window.firebaseDB || !window.firestoreFunctions) {
        console.log("Firebase가 로드되지 않아 로컬 저장만 사용합니다");
        return false;
      }
      
      const { collection, doc, setDoc, getDoc, updateDoc, arrayUnion, serverTimestamp } = window.firestoreFunctions;
      const db = window.firebaseDB;
      
      // 메시지 데이터 구성
      const messageData = {
        user_query: userQuery,
        ai_response: aiResponse,
        timestamp: serverTimestamp(),
        metadata: {
          ...metadata,
          user_agent: navigator.userAgent,
          response_length: aiResponse.length,
          query_length: userQuery.length
        }
      };
      
      // 세션 문서 참조
      const sessionRef = doc(collection(db, 'conversations'), currentSessionId);
      
      // 기존 세션 확인
      const sessionDoc = await getDoc(sessionRef);
      
      if (sessionDoc.exists()) {
        // 기존 세션에 메시지 추가
        await updateDoc(sessionRef, {
          messages: arrayUnion(messageData),
          message_count: sessionDoc.data().message_count + 1,
          updated_at: serverTimestamp(),
          last_activity: serverTimestamp()
        });
      } else {
        // 새 세션 생성
        await setDoc(sessionRef, {
          session_id: currentSessionId,
          created_at: serverTimestamp(),
          updated_at: serverTimestamp(),
          last_activity: serverTimestamp(),
          messages: [messageData],
          message_count: 1,
          user_info: {
            user_agent: navigator.userAgent,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
          }
        });
      }
      
      console.log(`✅ Firestore 대화 저장 성공 - 세션: ${currentSessionId}`);
      return true;
      
    } catch (error) {
      console.error("❌ Firestore 대화 저장 실패:", error);
      return false;
    }
  }
  
  async function loadConversationFromFirestore() {
    try {
      if (!window.firebaseDB || !window.firestoreFunctions) {
        return null;
      }
      
      const { collection, doc, getDoc } = window.firestoreFunctions;
      const db = window.firebaseDB;
      
      const sessionRef = doc(collection(db, 'conversations'), currentSessionId);
      const sessionDoc = await getDoc(sessionRef);
      
      if (sessionDoc.exists()) {
        const sessionData = sessionDoc.data();
        return sessionData.messages || [];
      }
      
      return null;
      
    } catch (error) {
      console.error("❌ Firestore 대화 로드 실패:", error);
      return null;
    }
  }
  
  async function updateMessageQuality(messageIndex, rating, feedback = "") {
    try {
      if (!window.firebaseDB || !window.firestoreFunctions) {
        return false;
      }
      
      // 백엔드 API를 통해 품질 업데이트
      const response = await fetch("/api/update-message-quality", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          message_index: messageIndex,
          rating: rating,
          feedback: feedback
        })
      });
      
      return response.ok;
      
    } catch (error) {
      console.error("❌ 메시지 품질 업데이트 실패:", error);
      return false;
    }
  }

  // --- Functions ---

  async function handleFormSubmit(e) {
    e.preventDefault();
    const userPrompt = promptInput.value.trim();

    if (!userPrompt) {
      return; // Do nothing if empty
    }

    // 응답 시간 측정 시작
    const startTime = Date.now();
    
    // 1. Display user's message in the chat
    displayUserMessage(userPrompt);

    // 2. Prepare for API call
    const formData = new FormData();
    formData.append("userPrompt", userPrompt);

    // conversationHistory가 항상 유효한 JSON 문자열이 되도록 보장합니다.
    let historyString;
    try {
      // stringify 하기 전에 history가 배열 형태인지 먼저 확인합니다.
      if (!Array.isArray(conversationHistory)) {
        console.warn(
          "conversationHistory가 배열이 아니므로 초기화합니다.",
          conversationHistory
        );
        conversationHistory = [];
      }
      historyString = JSON.stringify(conversationHistory);
    } catch (error) {
      console.error(
        "conversationHistory를 JSON 문자열로 변환하는 데 실패했습니다. 비어있는 기록을 전송합니다.",
        error
      );
      historyString = "[]"; // 순환 참조 등의 오류 발생 시, 안전하게 빈 배열을 보냅니다.
    }
    formData.append("conversationHistory", historyString);

    // 3. Reset input fields
    promptInput.value = "";
    promptInput.style.height = "auto";

    // 4. Show loading indicator inside the chat
    const loadingElement = showLoadingIndicator();
    scrollToBottom();

    // Disable form to prevent multiple submissions while waiting for a response
    if (submitButton) {
      submitButton.disabled = true;
    }
    promptInput.disabled = true;

    try {
      // 5. Call the API
      const response = await fetch("/api/generate", {
        method: "POST",
        body: formData,
      });

      // 6. Remove loading indicator
      loadingElement.remove();

      // 7. 응답을 한 번만 읽어서 처리
      let responseText;
      try {
        responseText = await response.text();
      } catch (error) {
        console.error("응답 읽기 실패:", error);
        throw new Error("서버 응답을 읽을 수 없습니다");
      }

      if (!response.ok) {
        let errorData;
        try {
          errorData = JSON.parse(responseText);
        } catch (jsonError) {
          console.error("서버 오류 응답이 유효한 JSON이 아닙니다:", jsonError);
          throw new Error(`서버 오류 (${response.status}): ${responseText.substring(0, 200)}`);
        }
        throw new Error(
          errorData.error?.message || errorData.detail || `API 요청 실패: ${response.status}`
        );
      }

      // 8. 성공 응답 처리
      let result;
      try {
        result = JSON.parse(responseText);
      } catch (jsonError) {
        console.error("성공 응답이 유효한 JSON이 아닙니다:", jsonError);
        throw new Error(`서버가 잘못된 형식의 응답을 반환했습니다: ${responseText.substring(0, 200)}`);
      }

      // Defensively update conversation history only if it's a valid array
      if (Array.isArray(result.updatedHistory)) {
        conversationHistory = result.updatedHistory;
      } else {
        console.warn(
          "Server returned invalid 'updatedHistory'. History will not be updated for this turn."
        );
      }

      // ✅ 1순위: summary_answer → 2순위: vertex_answer → fallback
      const modelResponseText =
        result.summary_answer ||
        result.answer ||
        result.vertex_answer ||
        result.vertexAiResponse?.candidates?.[0]?.content?.parts?.[0]?.text;

      if (modelResponseText) {
        // 디버깅을 위해 응답 데이터 로깅
        console.log("API 응답 전체:", result);
        console.log("Citations:", result.citations);
        console.log("Search Results:", result.search_results);
        console.log("Consultant needed:", result.consultant_needed);
        
        displayModelMessageWithSources(modelResponseText, result);
        
        // Firestore에 대화 저장 (비동기, 실패해도 UI에 영향 없음)
        saveConversationToFirestore(userPrompt, modelResponseText, {
          citations: result.citations,
          search_results: result.search_results,
          metadata: result.metadata,
          consultant_needed: result.consultant_needed,
          response_time_ms: Date.now() - startTime
        }).catch(error => {
          console.log("Firestore 저장 실패 (로컬에서는 정상):", error);
        });
      } else {
        displayModelMessage("죄송합니다, 답변을 생성하지 못했습니다.");
      }
    } catch (error) {
      // 이 블록은 네트워크 오류, 파싱 오류, 또는 !response.ok 확인에서 발생한 사용자 정의 오류를 처리합니다.
      if (loadingElement) loadingElement.remove();

      // 상세한 디버깅을 위해 전체 오류 객체를 로그에 기록합니다.
      console.error("API 호출 중 오류 발생:", error);

      let userMessage;
      if (error instanceof TypeError) {
        // 네트워크 오류일 가능성이 높습니다 (서버 다운, CORS, 인터넷 없음 등).
        console.error(
          "개발자 정보: TypeError가 발생했습니다. 네트워크 실패(CORS, DNS, 서버 다운)일 가능성이 높습니다."
        );
        userMessage =
          "서버에 연결할 수 없습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요.";
      } else if (error instanceof SyntaxError) {
        // response.json() 파싱 실패 시 발생합니다. 서버가 HTML 에러 페이지 등 비-JSON 응답을 보냈을 수 있습니다.
        console.error(
          "개발자 정보: SyntaxError가 발생했습니다. 서버 응답이 유효한 JSON이 아닙니다. 서버 로그에서 HTML 오류 페이지를 반환하는 충돌이 있는지 확인하세요."
        );
        userMessage =
          "서버로부터 잘못된 형식의 응답을 받았습니다. 서버에 문제가 있을 수 있습니다.";
      } else {
        // `!response.ok` 블록에서 발생시킨 사용자 정의 오류일 가능성이 높습니다.
        console.error(
          `개발자 정보: 처리된 API 오류입니다. 메시지: "${error.message}"`
        );
        userMessage = `오류가 발생했습니다: ${error.message}`;
      }

      displayModelMessage(userMessage);
    } finally {
      // Re-enable form regardless of success or failure
      if (submitButton) {
        submitButton.disabled = false;
      }
      promptInput.disabled = false;
      promptInput.focus();
      scrollToBottom();
    }
  }


  function displayUserMessage(text) {
    const messageElement = document.createElement("div");
    messageElement.className = "message user-message";

    const textNode = document.createElement("p");
    textNode.style.margin = "0";
    textNode.textContent = text;
    messageElement.appendChild(textNode);
    
    chatContainer.appendChild(messageElement);
  }

  function displayModelMessage(markdownText) {
    const messageElement = document.createElement("div");
    messageElement.className = "message model-message";

    // marked.parse()를 사용하여 마크다운을 HTML로 변환합니다.
    messageElement.innerHTML = marked.parse(markdownText);

    chatContainer.appendChild(messageElement);
  }

  function displayModelMessageWithSources(markdownText, result) {
    console.log("displayModelMessageWithSources 호출됨");
    console.log("Citations 존재 여부:", result.citations && result.citations.length > 0);
    console.log("Citations 내용:", result.citations);
    
    const messageElement = document.createElement("div");
    messageElement.className = "message model-message";

    // 메인 답변을 마크다운으로 파싱하여 HTML로 변환
    messageElement.innerHTML = marked.parse(markdownText);

    // Citations 섹션 제거 - 참조 문서 목록 출력하지 않음

    // Related Questions 추가
    console.log("응답 데이터 확인:", result);
    console.log("related_questions 확인:", result.related_questions);
    
    // 더미 데이터 제거 - 실제 related_questions만 표시
    
    if (result.related_questions && result.related_questions.length > 0) {
      console.log("Related Questions 섹션 생성 중...");
      const relatedDiv = document.createElement("div");
      relatedDiv.style.marginTop = "1rem";
      relatedDiv.style.paddingTop = "1rem";
      relatedDiv.style.borderTop = "1px solid #e0e0e0";
      
      const relatedTitle = document.createElement("strong");
      relatedTitle.textContent = "💡 연관 질문:";
      relatedTitle.style.display = "block";
      relatedTitle.style.marginBottom = "0.5rem";
      relatedDiv.appendChild(relatedTitle);
      
      const questionsList = document.createElement("div");
      questionsList.style.display = "flex";
      questionsList.style.flexDirection = "column";
      questionsList.style.gap = "0.5rem";
      
      result.related_questions.slice(0, 3).forEach((question, i) => {
        const questionButton = document.createElement("button");
        questionButton.textContent = `❓ ${question}`;
        questionButton.style.cssText = `
          background: #f5f5f5;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 8px 12px;
          text-align: left;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 14px;
          color: #333;
        `;
        
        // 호버 효과
        questionButton.onmouseenter = () => {
          questionButton.style.background = "#e3f2fd";
          questionButton.style.borderColor = "#1976d2";
          questionButton.style.color = "#1976d2";
        };
        
        questionButton.onmouseleave = () => {
          questionButton.style.background = "#f5f5f5";
          questionButton.style.borderColor = "#ddd";
          questionButton.style.color = "#333";
        };
        
        // 클릭 이벤트 - 해당 질문으로 새로운 요청 전송
        questionButton.onclick = () => {
          console.log("연관 질문 클릭:", question);
          const promptInput = document.getElementById('prompt-input');
          promptInput.value = question;
          
          // 자동으로 질문 전송
          const form = document.getElementById('prompt-form');
          if (form) {
            form.dispatchEvent(new Event('submit'));
          }
        };
        
        questionsList.appendChild(questionButton);
      });
      
      relatedDiv.appendChild(questionsList);
      messageElement.appendChild(relatedDiv);
    }

    // Search Results에서 추가 링크 정보 추가 (항상 표시)
    if (result.search_results && result.search_results.length > 0) {
      console.log("Search Results 섹션 생성 중...");
      const searchDiv = document.createElement("div");
      searchDiv.style.marginTop = "1rem";
      searchDiv.style.paddingTop = "1rem";
      searchDiv.style.borderTop = "1px solid #e0e0e0";
      
      const searchTitle = document.createElement("strong");
      searchTitle.textContent = "📚 관련 문서:";
      searchDiv.appendChild(searchTitle);
      
      const searchList = document.createElement("ol");
      searchList.style.marginTop = "0.5rem";
      searchList.style.paddingLeft = "1.5rem";
      
      result.search_results.slice(0, 3).forEach((searchResult, i) => {
        const doc = searchResult.document || {};
        const derivedData = doc.derivedStructData || {};
        const title = derivedData.title || `문서 ${i + 1}`;
        const link = derivedData.link || doc.uri || "";
        
        const listItem = document.createElement("li");
        listItem.style.marginBottom = "0.25rem";
        
        if (link) {
          const linkElement = document.createElement("a");
          linkElement.textContent = title;
          linkElement.style.color = "#1976d2";
          linkElement.style.textDecoration = "underline";
          linkElement.style.cursor = "pointer";
          
          // GCS 링크를 프록시 URL로 변환
          if (link.startsWith('gs://')) {
            const gcsPath = link.replace('gs://', '');
            const parts = gcsPath.split('/');
            const bucketName = parts[0];
            const filePath = parts.slice(1).join('/');
            linkElement.href = `/gcs/${bucketName}/${filePath}`;
            console.log(`Search Result GCS 링크 생성: ${link} -> ${linkElement.href}`);
          } else if (link.startsWith('http')) {
            linkElement.href = link;
            console.log(`Search Result HTTP 링크 생성: ${link}`);
          }
          
          linkElement.target = "_blank";
          linkElement.rel = "noopener noreferrer";
          
          // 링크 클릭 이벤트 추가 (디버깅용)
          linkElement.onclick = function(e) {
            console.log("Search Result 링크 클릭됨:", linkElement.href);
          };
          
          console.log("Search Result 링크 요소 생성됨:", linkElement);
          listItem.appendChild(linkElement);
        } else {
          console.log("Search Result에 링크가 없어서 텍스트로만 표시:", title);
          listItem.textContent = title;
        }
        
        searchList.appendChild(listItem);
      });
      
      searchDiv.appendChild(searchList);
      messageElement.appendChild(searchDiv);
    }

    // 상담사 연결 버튼 추가
    if (result.consultant_needed) {
      console.log("상담사 연결 버튼 섹션 생성 중...");
      const consultantDiv = document.createElement("div");
      consultantDiv.style.marginTop = "1rem";
      consultantDiv.style.paddingTop = "1rem";
      consultantDiv.style.borderTop = "1px solid #e0e0e0";
      consultantDiv.style.textAlign = "center";
      
      const consultantButton = document.createElement("button");
      consultantButton.textContent = "🎧 상담사와 연결하기";
      consultantButton.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      `;
      
      // 호버 효과
      consultantButton.onmouseenter = () => {
        consultantButton.style.transform = "translateY(-2px)";
        consultantButton.style.boxShadow = "0 6px 20px rgba(102, 126, 234, 0.6)";
      };
      
      consultantButton.onmouseleave = () => {
        consultantButton.style.transform = "translateY(0)";
        consultantButton.style.boxShadow = "0 4px 15px rgba(102, 126, 234, 0.4)";
      };
      
      // 클릭 이벤트
      consultantButton.onclick = async () => {
        await requestConsultant(result);
      };
      
      consultantDiv.appendChild(consultantButton);
      messageElement.appendChild(consultantDiv);
    }

    chatContainer.appendChild(messageElement);
  }

  function showLoadingIndicator() {
    const loadingElement = document.createElement("div");
    loadingElement.className = "message model-message";
    loadingElement.innerHTML = `<div class="loading-dots" style="display: flex; gap: 4px;"><span>●</span><span>●</span><span>●</span></div>`;

    const styleId = "loading-dots-style";
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.textContent = `
                .loading-dots span {
                    animation-name: blink;
                    animation-duration: 1.4s;
                    animation-iteration-count: infinite;
                    animation-fill-mode: both;
                }
                .loading-dots span:nth-child(2) { animation-delay: .2s; }
                .loading-dots span:nth-child(3) { animation-delay: .4s; }
                @keyframes blink { 0% { opacity: .2; } 20% { opacity: 1; } 100% { opacity: .2; } }
            `;
      document.head.appendChild(style);
    }

    chatContainer.appendChild(loadingElement);
    return loadingElement;
  }

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
  
  // Demo form functions
  function showDemoForm() {
    if (demoFormContainer) {
      demoFormContainer.style.display = "flex";
      // 폼 초기화
      if (demoForm) {
        demoForm.reset();
      }
      // 에러 메시지 숨김
      const errorContainer = document.getElementById("demo-form-errors");
      if (errorContainer) {
        errorContainer.style.display = "none";
      }
    }
  }
  
  function hideDemoForm() {
    if (demoFormContainer) {
      demoFormContainer.style.display = "none";
    }
  }
  
  async function handleDemoFormSubmit(e) {
    e.preventDefault();
    
    // 폼 데이터 수집
    const formData = new FormData(demoForm);
    
    // 제출 버튼 비활성화
    const submitBtn = document.getElementById("demo-form-submit");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "처리 중...";
    }
    
    // 에러 컨테이너 숨김
    const errorContainer = document.getElementById("demo-form-errors");
    if (errorContainer) {
      errorContainer.style.display = "none";
    }
    
    try {
      console.log("데모 신청 전송 중...");
      
      const response = await fetch("/api/request-demo", {
        method: "POST",
        body: formData,
      });
      
      const result = await response.json();
      
      if (result.success) {
        console.log("데모 신청 성공:", result);
        
        // 성공 메시지를 채팅에 표시
        displayModelMessage(`✅ **데모 신청이 완료되었습니다!**

**신청 번호**: ${result.request_id}
**신청 시간**: ${result.timestamp}

${result.message}

담당자가 빠른 시일 내에 연락드리겠습니다.`);
        
        // 경고사항이 있으면 추가로 표시
        if (result.warnings && result.warnings.length > 0) {
          const warningMessage = "📋 **참고사항**:\n" + result.warnings.map(w => `• ${w}`).join("\n");
          displayModelMessage(warningMessage);
        }
        
        // 폼 닫기
        hideDemoForm();
        
        // 채팅 하단으로 스크롤
        scrollToBottom();
        
      } else {
        console.error("데모 신청 실패:", result);
        
        // 에러 메시지 표시
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
      
    } catch (error) {
      console.error("데모 신청 중 네트워크 오류:", error);
      
      if (errorContainer) {
        errorContainer.innerHTML = "네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.";
        errorContainer.style.display = "block";
      }
    } finally {
      // 제출 버튼 다시 활성화
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "신청하기";
      }
    }
  }
  
  async function requestConsultant(apiResult) {
    console.log("상담사 연결 요청 시작...");
    
    try {
      // 현재 대화의 마지막 사용자 질문 추출
      const lastUserMessage = conversationHistory
        .filter(msg => msg.role === "user")
        .slice(-1)[0];
      
      const userPrompt = lastUserMessage?.parts?.[0]?.text || "";
      
      const formData = new FormData();
      formData.append("userPrompt", userPrompt);
      formData.append("conversationHistory", JSON.stringify(conversationHistory));
      formData.append("sessionId", apiResult.metadata?.session_id || "");
      formData.append("sensitiveCategories", JSON.stringify(apiResult.metadata?.sensitive_categories || []));
      
      // 로딩 메시지 표시
      displayModelMessage("상담사 연결 요청을 처리하고 있습니다... 🔄");
      
      const response = await fetch("/api/request-consultant", {
        method: "POST",
        body: formData,
      });
      
      const result = await response.json();
      
      if (result.success) {
        displayModelMessage(`✅ ${result.message}\n\n**문의 번호**: ${result.consultation_id}\n**요청 시간**: ${new Date(result.timestamp).toLocaleString('ko-KR')}`);
        console.log("상담사 연결 요청 성공:", result);
      } else {
        displayModelMessage(`❌ ${result.message || "상담 요청 처리 중 오류가 발생했습니다."}`);
        console.error("상담사 연결 요청 실패:", result);
      }
      
    } catch (error) {
      console.error("상담사 연결 요청 중 오류:", error);
      displayModelMessage("❌ 상담사 연결 요청 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
    }
    
    scrollToBottom();
  }
}

// DOM이 로드되면 채팅 초기화 함수 실행
document.addEventListener("DOMContentLoaded", initializeChat);

// 추가 안전장치: window.onload로도 시도
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeChat);
} else {
  // DOM이 이미 로드된 경우 즉시 실행
  initializeChat();
}
