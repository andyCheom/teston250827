(function() {
    const originalSend = window.XMLHttpRequest.prototype.send;
    window.XMLHttpRequest.prototype.send = function(body) {
        this.addEventListener("load", function() {
            if (this.responseURL.includes("/api/chat")) {
                try {
                    const response = JSON.parse(this.responseText);
                    if (response.answer) {
                        handleSpecialResponses(response.answer);
                    }
                } catch (e) {
                    // console.error("Error parsing chat response:", e);
                }
            }
        });
        originalSend.apply(this, arguments);
    };

    function handleSpecialResponses(answer) {
        if (answer.includes("데모 신청을 원하시면")) {
            showDemoRequestButton();
        }
    }

    function showDemoRequestButton() {
        const chatMessages = document.getElementById('chat-messages');
        const button = document.createElement('button');
        button.innerText = '데모 신청하기';
        button.className = 'demo-request-btn';
        button.onclick = function() {
            showDemoForm();
            button.style.display = 'none';
        };
        chatMessages.appendChild(button);
    }

    function showDemoForm() {
        const chatMessages = document.getElementById('chat-messages');
        const demoFormContainer = document.createElement('div');
        demoFormContainer.id = 'demo-form-container';
        demoFormContainer.innerHTML = `
            <form id="demo-form">
                <h3>데모 신청</h3>
                <input type="text" id="company-name" placeholder="회사명" required>
                <input type="text" id="contact-person" placeholder="담당자명" required>
                <input type="email" id="email" placeholder="이메일" required>
                <input type="tel" id="phone" placeholder="연락처" required>
                <button type="submit">신청하기</button>
            </form>
        `;
        chatMessages.appendChild(demoFormContainer);

        // The event listener is now handled by widget-script.js
    }

    function appendMessage(sender, text) {
        const chatMessages = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${sender}`;
        messageElement.innerText = text;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
})();