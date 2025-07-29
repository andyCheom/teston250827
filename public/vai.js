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
        result.vertex_answer ||
        result.vertexAiResponse?.candidates?.[0]?.content?.parts?.[0]?.text;

      if (modelResponseText) {
        displayModelMessage(modelResponseText);
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
