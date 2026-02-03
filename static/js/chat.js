/* static/js/chat.js */

function initChat(config) {
    const sessionId = config.sessionId;
    const currentUserId = config.userId;
    const csrfToken = config.csrfToken;
    const uploadUrl = config.uploadUrl;
    
    let chatSocket = null;
    let reconnectInterval = null;

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socketUrl = protocol + window.location.host + '/ws/chat/' + sessionId + '/';
        
        console.log("Connecting to WebSocket...");
        chatSocket = new WebSocket(socketUrl);

        chatSocket.onopen = function(e) {
            console.log("Connected!");
            document.querySelector('.status-dot').style.color = '#28a745';
            if (reconnectInterval) {
                clearInterval(reconnectInterval);
                reconnectInterval = null;
            }
        };

        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            handleMessage(data); 
        };

        chatSocket.onclose = function(e) {
            console.error('Socket closed. Reconnecting...');
            document.querySelector('.status-dot').style.color = 'red';
            if (!reconnectInterval) {
                reconnectInterval = setInterval(connect, 3000);
            }
        };
        
        chatSocket.onerror = function(err) {
            console.error('Socket error:', err);
            chatSocket.close();
        };
    }

    // --- دالة جديدة لتنسيق الوقت (YYYY-MM-DD / HH:MM) ---
    function formatTime(isoString) {
        if (!isoString) return "";
        const date = new Date(isoString);
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');

        return `${year}-${month}-${day} / ${hours}:${minutes}`;
    }

    // === الدالة الذكية لمعالجة الرسائل (تحديث أو إنشاء) ===
    function handleMessage(data) {
        if (data.type === 'error_alert') {
            showError(data.error);
            return;
        }

        const msgElementId = `msg-${data.id}`;
        let existingMsgDiv = document.getElementById(msgElementId);

        let contentHtml = "";
        let msgClass = "";
        let senderLabel = "";

        // تحديد الاتجاه
        if (data.sender_id === currentUserId) {
            msgClass = "sent";
        } else {
            msgClass = "received";
            if (data.sender_id !== currentUserId) { 
                 senderLabel = '<span class="sender-label">Nurse 👩‍⚕️</span>';
            }
        }

        // بناء المحتوى
        let messageBody = "";
        
        if (data.image_url) {
            messageBody = `
                <a href="${data.image_url}" target="_blank">
                    <img src="${data.image_url}" class="chat-image">
                </a>
            `;
        } else {
            let displayText = "";
            
            if (data.sender_id === currentUserId) {
                displayText = data.text_original;
            } else {
                displayText = data.text_translated ? data.text_translated : 
                              (data.text_original ? data.text_original : '<i style="color:#888; font-size:0.8em;">... typing / oversetter ...</i>');
            }
            
            if (displayText) {
                displayText = displayText.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            }
            messageBody = displayText;
        }

        contentHtml = senderLabel + messageBody;

        // 🛑 استخدام دالة تنسيق الوقت هنا
        const formattedTime = formatTime(data.timestamp);
        const timeHtml = `<span class="time">${formattedTime}</span>`;

        // 2. القرار: تحديث أم إنشاء؟
        if (existingMsgDiv) {
            existingMsgDiv.innerHTML = contentHtml + timeHtml;
            existingMsgDiv.className = `message ${msgClass}`; // تحديث الكلاس أيضاً
        } else {
            const msgDiv = document.createElement('div');
            msgDiv.id = msgElementId;
            msgDiv.className = 'message ' + msgClass;
            msgDiv.innerHTML = contentHtml + timeHtml;
            
            const chatLog = document.querySelector('#chat-log');
            chatLog.appendChild(msgDiv);
            scrollToBottom();
        }
    }

    // === دوال مساعدة ===
    const imageBtn = document.getElementById('image-btn');
    const imageInput = document.getElementById('image-input');

    imageBtn.onclick = function() { imageInput.click(); };

    imageInput.onchange = function() {
        const file = imageInput.files[0];
        if (file) uploadImage(file);
    };

    function uploadImage(file) {
        const formData = new FormData();
        formData.append('image', file);
        formData.append('session_id', sessionId);

        imageBtn.innerHTML = "⏳"; 
        imageBtn.disabled = true;

        fetch(uploadUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) showError(data.error);
            imageBtn.innerHTML = "📎";
            imageBtn.disabled = false;
            imageInput.value = ""; 
        })
        .catch(error => {
            console.error('Error:', error);
            imageBtn.innerHTML = "📎";
            imageBtn.disabled = false;
        });
    }

    function showError(msg) {
        const errorBanner = document.getElementById('error-banner');
        errorBanner.innerText = "⚠️ " + msg;
        errorBanner.style.display = 'block';
        setTimeout(() => { errorBanner.style.display = 'none'; }, 5000);
    }

    document.querySelector('#chat-message-submit').onclick = function(e) {
        const messageInputDom = document.querySelector('#chat-message-input');
        const message = messageInputDom.value;
        if(message.trim() !== "" && chatSocket.readyState === WebSocket.OPEN) {
            document.getElementById('error-banner').style.display = 'none';
            chatSocket.send(JSON.stringify({'message': message}));
            messageInputDom.value = '';
        }
    };

    document.querySelector('#chat-message-input').onkeyup = function(e) {
        if (e.keyCode === 13) document.querySelector('#chat-message-submit').click();
    };

    function scrollToBottom() {
        const log = document.querySelector('#chat-log');
        log.scrollTop = log.scrollHeight;
    }

    connect();
    scrollToBottom();
}