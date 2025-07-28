document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatContainer = document.getElementById("chat-container");
  const promptForm = document.getElementById("prompt-form");
  const promptInput = document.getElementById("prompt-input");
  const imageInput = document.getElementById("image-input");
  const imagePreview = document.getElementById("image-preview");
  const removeImageBtn = document.getElementById("remove-image-btn");
  const submitButton = promptForm.querySelector(
    'button[type="submit"], input[type="submit"]'
  );

  // State
  let conversationHistory = [];
  let attachedImageFile = null;

  // --- Initial validation ---
  // Ensure essential elements exist before proceeding
  if (!chatContainer || !promptForm || !promptInput || !imageInput) {
    console.error(
      "Essential chat components not found in the DOM. Aborting script."
    );
    document.body.innerHTML =
      '<p style="color: red; text-align: center; margin-top: 2rem;">채팅 인터페이스를 불러오는 데 실패했습니다. 페이지의 HTML 요소를 확인해주세요.</p>';
    return;
  }

  // --- UI Setup ---
  // Set input font to match chat window font for consistency
  const bodyFont = window.getComputedStyle(document.body).fontFamily;
  if (bodyFont) {
    promptInput.style.fontFamily = bodyFont;
  }

  // --- Event Listeners ---

  // Handle form submission (sending a message)
  promptForm.addEventListener("submit", handleFormSubmit);

  // Handle image selection for preview
  imageInput.addEventListener("change", handleImageSelection);

  // Handle image removal
  removeImageBtn.addEventListener("click", clearImageAttachment);

  // Handle test buttons
  document.getElementById("test-discovery-btn").addEventListener("click", () => testAPI("discovery"));
  document.getElementById("test-compare-btn").addEventListener("click", () => testAPI("compare"));
  document.getElementById("test-original-btn").addEventListener("click", () => testAPI("original"));

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

    if (!userPrompt && !attachedImageFile) {
      return; // Do nothing if both are empty
    }

    // 1. Display user's message in the chat
    displayUserMessage(userPrompt, attachedImageFile);

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

    if (attachedImageFile) {
      formData.append("imageFile", attachedImageFile);
    }

    // 3. Reset input fields
    promptInput.value = "";
    promptInput.style.height = "auto";
    clearImageAttachment();

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

  
  function handleImageSelection() {
    const file = imageInput.files[0];
    if (file) {
      attachedImageFile = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreview.src = e.target.result;
        imagePreview.style.display = "block";
        removeImageBtn.style.display = "block";
      };
      reader.onerror = () => {
        console.error("FileReader failed to read the file.");
        displayModelMessage("오류: 선택한 이미지 파일을 읽는 데 실패했습니다.");
        clearImageAttachment();
      };
      reader.readAsDataURL(file);
    }
  }

  function clearImageAttachment() {
    imageInput.value = ""; // Reset file input
    imagePreview.src = "";
    imagePreview.style.display = "none";
    removeImageBtn.style.display = "none";
    attachedImageFile = null;
  }

  function displayUserMessage(text, imageFile) {
    const messageElement = document.createElement("div");
    messageElement.className = "message user-message";

    if (imageFile) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(imageFile);
      img.style.maxWidth = "100%";
      img.style.borderRadius = "0.75rem";
      img.style.marginBottom = text ? "0.5rem" : "0";
      messageElement.appendChild(img);
    }
    if (text) {
      const textNode = document.createElement("p");
      textNode.style.margin = "0";
      textNode.textContent = text;
      messageElement.appendChild(textNode);
    }
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

  // Test API functions
  async function testAPI(type) {
    const testQuery = document.getElementById("test-query").value.trim();
    if (!testQuery) {
      alert("테스트할 질문을 입력해주세요!");
      return;
    }

    // Disable all test buttons during request
    const testButtons = document.querySelectorAll(".test-button");
    testButtons.forEach(btn => btn.disabled = true);

    // Show loading indicator
    const loadingElement = showLoadingIndicator();
    scrollToBottom();

    try {
      let endpoint, title;
      switch(type) {
        case "discovery":
          endpoint = "/api/discovery-answer";
          title = "🔵 Discovery Engine 답변";
          break;
        case "compare":
          endpoint = "/api/compare-answers";
          title = "🟢 비교 테스트 결과";
          break;
        case "original":
          endpoint = "/api/generate";
          title = "🔴 기존 방식 답변";
          break;
      }

      // Display test query as user message
      displayUserMessage(`[${title}] ${testQuery}`);

      const formData = new FormData();
      formData.append("userPrompt", testQuery);
      formData.append("conversationHistory", "[]");

      const response = await fetch(endpoint, {
        method: "POST",
        body: formData
      });

      loadingElement.remove();

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `API 요청 실패: ${response.status}`);
      }

      const result = await response.json();
      
      // Format and display results based on API type
      if (type === "discovery") {
        displayDiscoveryResult(result);
      } else if (type === "compare") {
        displayCompareResult(result);
      } else {
        // Original API result
        const modelResponseText = result.summary_answer || result.vertex_answer || "답변을 생성하지 못했습니다.";
        displayModelMessage(`**${title}**\n\n${modelResponseText}`);
      }

    } catch (error) {
      if (loadingElement) loadingElement.remove();
      console.error(`${type} API 테스트 오류:`, error);
      displayModelMessage(`❌ **${type} 테스트 오류**: ${error.message}`);
    } finally {
      // Re-enable test buttons
      testButtons.forEach(btn => btn.disabled = false);
      scrollToBottom();
    }
  }

  function displayDiscoveryResult(result) {
    let message = "**🔵 Discovery Engine 답변**\n\n";
    
    if (result.answer) {
      message += `${result.answer}\n\n`;
    }
    
    // 검색 결과에서 링크 정보 추출 및 표시
    if (result.search_results && result.search_results.length > 0) {
      message += "**📚 참고 문서:**\n";
      result.search_results.slice(0, 3).forEach((searchResult, i) => {
        const doc = searchResult.document || {};
        const derivedData = doc.derivedStructData || {};
        const title = derivedData.title || `문서 ${i + 1}`;
        const link = derivedData.link || doc.uri || "";
        
        if (link) {
          // GCS 링크를 프록시 URL로 변환
          if (link.startsWith('gs://')) {
            const gcsPath = link.replace('gs://', '');
            const parts = gcsPath.split('/');
            const bucketName = parts[0];
            const filePath = parts.slice(1).join('/');
            const proxyUrl = `/gcs/${bucketName}/${filePath}`;
            message += `${i + 1}. [${title}](${proxyUrl})\n`;
          } else if (link.startsWith('http')) {
            message += `${i + 1}. [${title}](${link})\n`;
          } else {
            message += `${i + 1}. ${title}\n`;
          }
        } else {
          message += `${i + 1}. ${title}\n`;
        }
      });
      message += "\n";
    }
    
    // Citation 정보가 있으면 추가 표시
    if (result.citations && result.citations.length > 0) {
      message += "**📖 인용 정보:**\n";
      result.citations.slice(0, 3).forEach((citation, i) => {
        const title = citation.title || citation.displayName || `인용 ${i + 1}`;
        const uri = citation.uri || "";
        
        if (uri) {
          message += `${i + 1}. [${title}](${uri})\n`;
        } else {
          message += `${i + 1}. ${title}\n`;
        }
      });
      message += "\n";
    }
    
    if (result.related_questions && result.related_questions.length > 0) {
      message += "**🤔 관련 질문:**\n";
      result.related_questions.slice(0, 3).forEach((q) => {
        message += `• ${q}\n`;
      });
    }
    
    message += `\n*검색 결과: ${result.search_results?.length || 0}건*`;
    
    displayModelMessage(message);
  }

  function displayCompareResult(result) {
    let message = "**🟢 비교 테스트 결과**\n\n";
    message += `**질문:** ${result.user_prompt}\n`;
    message += `**테스트 시간:** ${new Date(result.timestamp).toLocaleString()}\n\n`;
    
    // Original method result
    message += "### 🔴 기존 방식\n";
    if (result.original_method.status === "success") {
      message += `**요약 답변:** ${result.original_method.summary_answer?.substring(0, 200)}${result.original_method.summary_answer?.length > 200 ? '...' : ''}\n`;
      message += `**품질 검증:** ${result.original_method.quality_check?.relevance_passed ? '✅ 통과' : '❌ 실패'}\n`;
    } else {
      message += `❌ **오류:** ${result.original_method.error}\n`;
    }
    
    message += "\n### 🔵 Discovery Engine\n";
    if (result.discovery_method.status === "success") {
      message += `**답변:** ${result.discovery_method.answer?.substring(0, 200)}${result.discovery_method.answer?.length > 200 ? '...' : ''}\n`;
      message += `**인용 수:** ${result.discovery_method.citations_count}개\n`;
      message += `**검색 결과:** ${result.discovery_method.search_results_count}건\n`;
    } else {
      message += `❌ **오류:** ${result.discovery_method.error}\n`;
    }
    
    displayModelMessage(message);
  }
});
