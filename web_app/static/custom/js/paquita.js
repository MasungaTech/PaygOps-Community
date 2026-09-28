function sendMessage() {
    var message = document.getElementById('messageInput').value;
    document.getElementById('messageInput').value = "";
    var msg = {content: message, user: true, time: getTime()}
    // Add message to chat
    addToChat(msg);
    // Call API
    getResponse(msg);
}

function getTime() {
    var d = new Date();
    return d.toLocaleTimeString("en-UK", {hour12: false, timeStyle: "short"})
}

var questionMessageTemplate = '<div class="d-flex overflow-hidden"><div class="chat-message-wrapper flex-grow-1 mx-1 mb-2"><div class="chat-message-text"><p class="mb-0">MSG</p></div><div class="text-muted mt-1 float-end"><small>TIME</small></div></div></div>'
var answerMessageTemplate = '<div class="d-flex overflow-hidden"><div class="chat-message-wrapper flex-grow-1 mx-1 mb-2"><div class="chat-message-text"><p class="mb-0">MSG</p></div><div class="text-muted mt-1"><small>TIME</small></div></div></div>'
var answerMessageTemplateFeedback = '<div class="d-flex overflow-hidden"><div class="chat-message-wrapper flex-grow-1 mx-1 mb-2"><div class="chat-message-text"><p class="mb-0">MSG</p></div><div class="chat-message-text feedback-container"><p class="mb-0 mx-auto">Was this answer good? <a href="#" onclick="sendFeedback(this, \'UUID\', true)">Yes</a> / <a href="#" onclick="sendFeedback(this, \'UUID\', false)">No</a></p></div><div class="text-muted mt-1"><small>TIME</small></div></div></div>'

var loaderTemplate = '<div id="chat-message-loader" class="d-flex overflow-hidden"><div class="chat-message-wrapper flex-grow-1 mx-1 mb-2"><div class="chat-message-text"><p class="mb-0 dot-loader mx-auto"></p></div></div></div>'

function addChatMessageBase() {
    var newMessage = document.createElement('li');
    newMessage.classList.add('chat-message');
    newMessage.classList.add('list-group-item');
    newMessage.classList.add('p-0');
    return newMessage
}

function addLoader() {
    var chat = document.getElementById('chat');
    var newMessage = addChatMessageBase()
    newMessage.innerHTML = loaderTemplate
    chat.appendChild(newMessage);
    scrollToBottom();
}

function removeLoader() {
    var loader = document.getElementById('chat-message-loader');
    if (loader) {
        loader.remove();
    }
}

function escapeHtmlAttr(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function renderPaquitaMarkdown(text) {
    if (text == null) {
        return '';
    }
    text = String(text);
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/gi, function(_match, label, url) {
        return '<a href="' + escapeHtmlAttr(url) + '" target="_blank" rel="noopener noreferrer">' + label + '</a>';
    });
    return text.split(/(<[^>]+>)/g).map(function(part) {
        if (!part || part.charAt(0) === '<') {
            return part;
        }
        part = part.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        part = part.replace(/__(.+?)__/g, '<strong>$1</strong>');
        part = part.replace(/\*(.+?)\*/g, '<em>$1</em>');
        part = part.replace(/(^|[\s(])_([^_\n]+?)_(?=[\s).,!?:;]|$)/g, '$1<em>$2</em>');
        part = part.replace(/\n/g, '<br>');
        return part;
    }).join('');
}

function addToChat(msg) {
    var chat = document.getElementById('chat');
    var newMessage = addChatMessageBase()
    var formattedContent = renderPaquitaMarkdown(msg.content);
    if(msg.user) {
        var content = questionMessageTemplate
        newMessage.classList.add('chat-message-right');
    } else {
        if(msg.feedback_uuid) {
            var content = answerMessageTemplateFeedback
            content = content.replace('UUID', msg.feedback_uuid);
            content = content.replace('UUID', msg.feedback_uuid);
        } else {
            var content = answerMessageTemplate
        }
        // Add avatar wrapper div before the message content
        newMessage.innerHTML = `
            <div class="d-flex">
                <div class="flex-shrink-0 avatar-wrapper" style="margin-right: 8px;">
                    <img src="/static/img/paquita_profile_pic.jpeg" alt="Paquita Profile Picture" class="w-px-40 h-auto rounded-circle">
                </div>
                ${content.replace('MSG', formattedContent).replace('TIME', msg.time)}
            </div>`;
        chat.appendChild(newMessage);
        scrollToBottom();
        return;
    }
    content = content.replace('MSG', formattedContent);
    content = content.replace('TIME', msg.time)
    newMessage.innerHTML = content
    chat.appendChild(newMessage);
    scrollToBottom();
}

var PAYGOPS_MCP_TOOLS = [
    'lookup_client',
    'get_client',
    'get_contract',
    'get_repayments',
    'get_payments',
    'get_device',
    'get_issues',
    'get_lead',
    'get_offer',
    'get_user',
    'get_role',
    'get_settings',
    'get_outgoing_messages'
];

var PAQUITA_NEW_CONVERSATION_KEY = 'paquitaNewConversation';
var paquitaRequestId = 0;

function getPaygopsMcpUrl() {
    var baseUrl = (PAQUITA_SETTINGS.url || '').replace(/\/+$/, '');
    return baseUrl + '/mcp';
}

function getLocalTimezone() {
    var timeZone = PAQUITA_SETTINGS.timezone;
    if (!timeZone) {
        try {
            timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch (e) {
            timeZone = '';
        }
    }
    return timeZone;
}

function getTodayDateContext() {
    var timeZone = getLocalTimezone();
    var dateTimeOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    var now;
    try {
        now = new Date().toLocaleString('en-CA', timeZone ? Object.assign({ timeZone: timeZone }, dateTimeOptions) : dateTimeOptions);
    } catch (e) {
        now = new Date().toLocaleString('en-CA', dateTimeOptions);
        timeZone = '';
    }
    if (timeZone) {
        return "[Today's date and time in the local timezone (" + timeZone + ") is " + now + ".]";
    }
    return "[Today's date and time in the local timezone is " + now + ".]";
}

function getResponse(message) {
    var requestId = ++paquitaRequestId;
    addLoader();
    var payload = {
        "question": message.content + "\n\n" + getTodayDateContext(),
        "user_id": String(PAQUITA_SETTINGS.user_id),
        "include_sources": true,
        "url": PAQUITA_SETTINGS.url,
        "user_name": PAQUITA_SETTINGS.name,
        "mcp_servers": [{
            "name": "paygops",
            "url": getPaygopsMcpUrl(),
            "authorization_token": JWTKey,
            "allowed_tools": PAYGOPS_MCP_TOOLS
        }]
    };
    if (sessionStorage.getItem(PAQUITA_NEW_CONVERSATION_KEY) === 'true') {
        payload.new_conversation = true;
    }
    $.ajax({
        url: 'https://buildabot.paygops.com/api/v1/simple/4192e105-e7b39fb8-f48cbe8a',
        type: "POST",
        data: JSON.stringify(payload),
        contentType: "application/json",
        success: function (result) {
            if (requestId !== paquitaRequestId) {
                return;
            }
            sessionStorage.removeItem(PAQUITA_NEW_CONVERSATION_KEY);
            processResponse(message, result)
        },
        error: function (result, ajaxOptions, thrownError) {
            error_toast('Could not connect to AI assistant');
        }
    });
}

function processResponse(message, result, original_time) {
    removeLoader();
    var answer = result.answer.replace('Sources:', 'Relevant Articles:')
    var ans = { content: answer, user: false, time: getTime(), feedback_uuid: result.uuid}
    addToChat(ans);  
    // Store the question and answer
    storeConversation(message);
    storeConversation(ans);
}


function sendFeedback(el, uuid, positive) {
    $(el).parent().parent().remove();
    $.ajax({
        url: 'https://buildabot.paygops.com/api/v1/simple/questions/'+uuid+'/rate',
        type: "POST",
        data: JSON.stringify({ "positive": positive }),
        contentType: "application/json",
        success: function (result) {
            storeFeedbackGiven(uuid)
            success_toast('Thanks for your feedback!');
        },
        error: function (result, ajaxOptions, thrownError) {
            error_toast('Could not connect to AI assistant');
        }
    });
}

var chatLoaded = false; 
function toggleChat() {
    if (!chatLoaded) {
        chatLoaded = true;
        loadConversation();
    }
    var chatContainer = document.getElementById('chatContainer');
    if (chatContainer.style.display === "none") {
        chatContainer.style.display = "block";
    } else {
        chatContainer.style = "display: none !important;";
    }

    captureEvent(
        event_name='ai_assistant_launched',
        event_data={
                    data: { ...PAQUITA_SETTINGS, 
                            ...{"current_page": window.location.href}
                        }
        }
    )
}

function updateChatInput(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
}

function storeFeedbackGiven(feedback_uuid) {
    var chatHistory = loadChatHistory()
    chatHistory.forEach(item => {
        if (item.feedback_uuid === feedback_uuid) {
            delete item.feedback_uuid;
        }
    });
    sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

function loadChatHistory() {
    var chatHistory = sessionStorage.getItem('chatHistory');
    if (!chatHistory) {
        chatHistory = [];
    } else {
        chatHistory = JSON.parse(chatHistory);
    }
    return chatHistory
}

function storeConversation(message) {
    var chatHistory = loadChatHistory()
    chatHistory.push(message);
    sessionStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

function startNewConversation() {
    paquitaRequestId++;
    sessionStorage.removeItem('chatHistory');
    sessionStorage.setItem(PAQUITA_NEW_CONVERSATION_KEY, 'true');
    document.getElementById('chat').innerHTML = '';
    var messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.value = '';
    }
    addWelcomeMessage();
}

function loadConversation() {
    var chatHistory = sessionStorage.getItem('chatHistory');
    if (chatHistory) {
        chatHistory = JSON.parse(chatHistory);
        if (chatHistory.length > 0) {
            chatHistory.forEach(function(message) {
                addToChat(message);
            });
        } else {
            addWelcomeMessage();
        }
    } else {
        addWelcomeMessage();
    }
    scrollToBottom();
}

function scrollToBottom() {
    setTimeout(function() {
        var chatbox = document.getElementById('chat-box');
        $(chatbox).animate({
            scrollTop: chatbox.scrollHeight
        }, {
            duration: 100,
            specialEasing: {
              width: "linear",
              height: "easeOutBounce"
            }
        });
    }, 50);
}

function addWelcomeMessage() {
    message = {
        "content": "Hello, I'm the PaygOps AI assistant, ask me anything about PaygOps?",
        "user": false,
        "time": getCurrentTime()
    }

    addToChat(message);
}