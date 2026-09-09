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
    loader.remove();
}

function addToChat(msg) {
    var chat = document.getElementById('chat');
    var newMessage = addChatMessageBase()
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
                ${content.replace('MSG', msg.content).replace('TIME', msg.time)}
            </div>`;
        chat.appendChild(newMessage);
        scrollToBottom();
        return;
    }
    content = content.replace('MSG', msg.content);
    content = content.replace('TIME', msg.time)
    newMessage.innerHTML = content
    chat.appendChild(newMessage);
    scrollToBottom();
}

function getResponse(message) {
    let chatHistory = sessionStorage.getItem('chatHistory');
    let textHistory = '';
    if (chatHistory) {
        chatHistory = JSON.parse(chatHistory);
        chatHistory.slice(-4).forEach(function(data) {
            if (data.user) {
                textHistory += (textHistory ? 'Human: ' : '')+data.content.replace(/(<br\s?(\/)?>)+/, '')+ '\n\n';
            } else {
                textHistory += 'Assistant: '+data.content.replace(/(<br\s?(\/)?>)+/, '').replace(/<strong>(.+)$/, '\n\n');;
            }
        });
    }
    addLoader();
    $.ajax({
        url: 'https://buildabot.paygops.com/api/v1/simple/47453f96-f4fb63e8-b2ee51df',
        type: "POST",
        data: JSON.stringify({
            "question": textHistory + 'Human: '+message.content,
            "include_sources": true,
            "url": PAQUITA_SETTINGS.url,
            "user_name": PAQUITA_SETTINGS.name
        }),
        contentType: "application/json",
        success: function (result) {
            processResponse(message, result)
        },
        error: function (result, ajaxOptions, thrownError) {
            error_toast('Could not connect to AI assistant');
        }
    });
}

function processResponse(message, result, original_time) {
    removeLoader();
    var answer = result.answer.replace(/\n/g, "<br>")
    answer = answer.replace('Sources:', 'Relevant Articles:')
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