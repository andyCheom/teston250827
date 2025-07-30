// 더 안전한 DOM 로딩 확인
function initializeChat() {
  console.log("채팅 초기화 시작...");
  
  // DOM Elements
  const chatContainer = document.getElementById("chat-container");
  const promptForm = document.getElementById("prompt-form");
  const promptInput = document.getElementById("prompt-input");
  
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

  // --- Functions ---

  async function handleFormSubmit(e) {
    e.preventDefault();
    const userPrompt = promptInput.value.trim();

    if (!userPrompt) {
      return; // Do nothing if empty
    }

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
        
        displayModelMessageWithSources(modelResponseText, result);
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
    
    // 테스트용: related_questions가 없으면 더미 데이터 추가
    if (!result.related_questions || result.related_questions.length === 0) {
      console.log("related_questions가 없어서 테스트용 더미 데이터 추가");
      result.related_questions = [
        "처음서비스의 주요 기능은 무엇인가요?",
        "가격 정책은 어떻게 되나요?",
        "기술 지원은 어떻게 받을 수 있나요?"
      ];
    }
    
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

    // Related Questions 추가
    if (result.related_questions && result.related_questions.length > 0) {
      const questionsDiv = document.createElement("div");
      questionsDiv.style.marginTop = "1rem";
      questionsDiv.style.paddingTop = "1rem";
      questionsDiv.style.borderTop = "1px solid #e0e0e0";
      
      const questionsTitle = document.createElement("strong");
      questionsTitle.textContent = "🤔 관련 질문:";
      questionsDiv.appendChild(questionsTitle);
      
      const questionsList = document.createElement("ul");
      questionsList.style.marginTop = "0.5rem";
      questionsList.style.paddingLeft = "1.5rem";
      
      result.related_questions.slice(0, 3).forEach((question) => {
        const listItem = document.createElement("li");
        listItem.textContent = question;
        listItem.style.marginBottom = "0.25rem";
        questionsList.appendChild(listItem);
      });
      
      questionsDiv.appendChild(questionsList);
      messageElement.appendChild(questionsDiv);
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
