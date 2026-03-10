from flask import Flask, render_template_string, request, jsonify, session, Response
import requests
import json
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import threading
import base64

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

# إعدادات NVIDIA API الجديدة
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-397b-a17b"

# تخزين المحادثات والتدفقات النشطة
conversations = {}
active_streams = {}

def generate_professional_response(messages, stream_id):
    """توليد ردود احترافية كاملة بدون تقطع"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    system_prompt = {
        "role": "system",
        "content": """أنت Abdo AI Pro - خبير محترف في جميع المجالات.

القواعد الذهبية للإجابات الاحترافية:

1. **البداية المباشرة**: ابدأ الإجابة فوراً بدون مقدمات أو ترحيب

2. **الهيكل التنظيمي**:
   - استخدم عناوين رئيسية (##) للأقسام الرئيسية
   - استخدم عناوين فرعية (###) للتفاصيل
   - استخدم القوائم النقطية والرقمية

3. **للعروض والتحليلات**:
   - استخدم جداول منسقة للبيانات
   - أضف إحصائيات دقيقة
   - قارن بين الخيارات

4. **للبرمجة**:
   - قدم كود كامل ومتكامل
   - أضف تعليقات بالعربية
   - اشرح كل جزء بالتفصيل

5. **للمقارنات**:
   - استخدم جدول مقارنة من 3 أعمدة
   - قارن من جميع النواحي
   - قدم توصيات نهائية

6. **ضمان الاكتمال**:
   - أكمل جميع الأفكار حتى النهاية
   - لا تتوقف قبل إكمال الموضوع
   - قسّم الإجابات الطويلة لأقسام

7. **الدقة**:
   - استخدم أرقام وإحصائيات حقيقية
   - قدم أمثلة واقعية
   - استشهد بالمصادر الموثوقة"""
    }
    
    full_messages = [system_prompt] + messages[-20:]
    
    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "max_tokens": 16384,
        "temperature": 0.60,
        "top_p": 0.95,
        "top_k": 20,
        "presence_penalty": 0,
        "repetition_penalty": 1,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": True}
    }
    
    try:
        response = requests.post(
            NVIDIA_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=300
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if stream_id in active_streams and active_streams[stream_id].get('stopped', False):
                    yield "data: " + json.dumps({"choices": [{"delta": {"content": "\n\n**[تم إيقاف التوليد]**"}}]}) + "\n\n"
                    break
                    
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data = line_text[6:]
                        if data and data != '[DONE]':
                            yield line_text + "\n\n"
                        elif data == '[DONE]':
                            yield "data: [DONE]\n\n"
                            break
            else:
                yield "data: " + json.dumps({"choices": [{"delta": {"content": "\n\n⚠️ حدث خطأ في الاتصال. جاري إعادة المحاولة.."}}]}) + "\n\n"
        else:
            error_msg = f"data: " + json.dumps({"choices": [{"delta": {"content": f"\n\n⚠️ خطأ في الاتصال بالخادم: {response.status_code}"}}]}) + "\n\n"
            yield error_msg
            
    except Exception as e:
        error_msg = f"data: " + json.dumps({"choices": [{"delta": {"content": f"\n\n⚠️ عذراً، حدث خطأ في الاتصال. جاري إعادة المحاولة..\n\nتفاصيل الخطأ: {str(e)}"}}]}) + "\n\n"
        yield error_msg

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    html = '''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Abdo AI Pro - المحادثة المتقدمة</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .chat-container {
                width: 100%;
                max-width: 1200px;
                height: 90vh;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                display: flex;
                overflow: hidden;
            }
            
            .sidebar {
                width: 280px;
                background: #f8f9fa;
                border-left: 1px solid #e9ecef;
                display: flex;
                flex-direction: column;
                padding: 20px;
            }
            
            .new-chat-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin-bottom: 20px;
                transition: transform 0.2s;
            }
            
            .new-chat-btn:hover {
                transform: scale(1.02);
            }
            
            .conversations-list {
                flex: 1;
                overflow-y: auto;
            }
            
            .conversation-item {
                padding: 12px;
                background: white;
                border-radius: 8px;
                margin-bottom: 8px;
                cursor: pointer;
                border: 1px solid #e9ecef;
                transition: all 0.2s;
            }
            
            .conversation-item:hover {
                background: #f1f3f4;
                border-color: #667eea;
            }
            
            .conversation-item.active {
                background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
                border-color: #667eea;
            }
            
            .main-chat {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            
            .chat-header {
                padding: 20px;
                border-bottom: 1px solid #e9ecef;
                background: white;
            }
            
            .chat-title {
                font-size: 20px;
                font-weight: bold;
                color: #333;
            }
            
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #f8f9fa;
            }
            
            .message {
                margin-bottom: 20px;
                display: flex;
                flex-direction: column;
            }
            
            .message.user {
                align-items: flex-end;
            }
            
            .message.assistant {
                align-items: flex-start;
            }
            
            .message-content {
                max-width: 80%;
                padding: 15px;
                border-radius: 15px;
                position: relative;
                word-wrap: break-word;
            }
            
            .message.user .message-content {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-bottom-left-radius: 5px;
            }
            
            .message.assistant .message-content {
                background: white;
                border: 1px solid #e9ecef;
                border-bottom-right-radius: 5px;
            }
            
            .message-time {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
                margin-right: 10px;
            }
            
            .chat-input-container {
                padding: 20px;
                background: white;
                border-top: 1px solid #e9ecef;
            }
            
            .input-wrapper {
                display: flex;
                gap: 10px;
            }
            
            textarea {
                flex: 1;
                padding: 15px;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                font-size: 16px;
                resize: none;
                font-family: inherit;
                transition: border-color 0.2s;
            }
            
            textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0 30px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.2s;
            }
            
            button:hover:not(:disabled) {
                transform: scale(1.02);
            }
            
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .stop-btn {
                background: #dc3545;
            }
            
            .typing-indicator {
                display: flex;
                gap: 5px;
                padding: 10px;
            }
            
            .typing-indicator span {
                width: 8px;
                height: 8px;
                background: #667eea;
                border-radius: 50%;
                animation: typing 1s infinite ease-in-out;
            }
            
            .typing-indicator span:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .typing-indicator span:nth-child(3) {
                animation-delay: 0.4s;
            }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
            
            .message pre {
                background: #f4f4f4;
                padding: 10px;
                border-radius: 8px;
                overflow-x: auto;
                direction: ltr;
            }
            
            .message code {
                font-family: 'Courier New', monospace;
            }
            
            .message table {
                border-collapse: collapse;
                width: 100%;
                margin: 10px 0;
            }
            
            .message th, .message td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: right;
            }
            
            .message th {
                background: #667eea20;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="sidebar">
                <button class="new-chat-btn" onclick="newConversation()">+ محادثة جديدة</button>
                <div class="conversations-list" id="conversationsList"></div>
            </div>
            
            <div class="main-chat">
                <div class="chat-header">
                    <div class="chat-title" id="chatTitle">Abdo AI Pro</div>
                </div>
                
                <div class="chat-messages" id="chatMessages"></div>
                
                <div class="chat-input-container">
                    <div class="input-wrapper">
                        <textarea id="userInput" placeholder="اكتب سؤالك هنا..." rows="3"></textarea>
                        <button id="sendBtn" onclick="sendMessage()">إرسال</button>
                        <button id="stopBtn" class="stop-btn" onclick="stopGeneration()" style="display: none;">إيقاف</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let currentConversationId = null;
            let eventSource = null;
            let isGenerating = false;
            let currentStreamId = null;
            
            function loadConversations() {
                fetch('/get_conversations')
                    .then(response => response.json())
                    .then(data => {
                        const list = document.getElementById('conversationsList');
                        list.innerHTML = '';
                        
                        data.conversations.forEach(conv => {
                            const div = document.createElement('div');
                            div.className = 'conversation-item' + (conv.id === currentConversationId ? ' active' : '');
                            div.onclick = () => switchConversation(conv.id);
                            div.innerHTML = `
                                <div><strong>${conv.title || 'محادثة جديدة'}</strong></div>
                                <div style="font-size: 12px; color: #666;">${new Date(conv.created).toLocaleString('ar-EG')}</div>
                            `;
                            list.appendChild(div);
                        });
                    });
            }
            
            function newConversation() {
                fetch('/new_conversation', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        currentConversationId = data.conversation_id;
                        document.getElementById('chatTitle').textContent = 'محادثة جديدة';
                        document.getElementById('chatMessages').innerHTML = '';
                        loadConversations();
                    });
            }
            
            function switchConversation(convId) {
                currentConversationId = convId;
                loadConversations();
                
                fetch(`/get_conversation/${convId}`)
                    .then(response => response.json())
                    .then(data => {
                        const messagesDiv = document.getElementById('chatMessages');
                        messagesDiv.innerHTML = '';
                        
                        document.getElementById('chatTitle').textContent = data.title || 'محادثة';
                        
                        data.messages.forEach(msg => {
                            addMessageToChat(msg.role, msg.content);
                        });
                    });
            }
            
            function addMessageToChat(role, content) {
                const messagesDiv = document.getElementById('chatMessages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                
                const time = new Date().toLocaleTimeString('ar-EG');
                
                messageDiv.innerHTML = `
                    <div class="message-content">${formatMessage(content)}</div>
                    <div class="message-time">${time}</div>
                `;
                
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            function formatMessage(content) {
                // تحويل النص إلى HTML مع دعم Markdown بسيط
                let formatted = content
                    .replace(/## (.*?)(?:\n|$)/g, '<h2>$1</h2>')
                    .replace(/### (.*?)(?:\n|$)/g, '<h3>$1</h3>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>')
                    .replace(/`(.*?)`/g, '<code>$1</code>')
                    .replace(/\n/g, '<br>');
                
                return formatted;
            }
            
            function sendMessage() {
                const input = document.getElementById('userInput');
                const message = input.value.trim();
                
                if (!message || !currentConversationId || isGenerating) return;
                
                // إضافة رسالة المستخدم
                addMessageToChat('user', message);
                input.value = '';
                
                // إظهار مؤشر الكتابة
                const messagesDiv = document.getElementById('chatMessages');
                const typingDiv = document.createElement('div');
                typingDiv.className = 'message assistant';
                typingDiv.id = 'typingIndicator';
                typingDiv.innerHTML = `
                    <div class="message-content">
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                `;
                messagesDiv.appendChild(typingDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                
                // إخفاء زر الإرسال وإظهار زر الإيقاف
                document.getElementById('sendBtn').style.display = 'none';
                document.getElementById('stopBtn').style.display = 'block';
                isGenerating = true;
                
                // إنشاء معرف فريد للتدفق
                currentStreamId = Date.now() + '-' + Math.random();
                
                // بدء التدفق
                eventSource = new EventSource(`/stream_chat?conversation_id=${currentConversationId}&message=${encodeURIComponent(message)}&stream_id=${currentStreamId}`);
                
                let responseContent = '';
                let responseDiv = null;
                
                eventSource.onmessage = function(event) {
                    if (event.data === '[DONE]') {
                        eventSource.close();
                        document.getElementById('typingIndicator')?.remove();
                        document.getElementById('sendBtn').style.display = 'block';
                        document.getElementById('stopBtn').style.display = 'none';
                        isGenerating = false;
                        loadConversations();
                        return;
                    }
                    
                    try {
                        const data = JSON.parse(event.data);
                        const content = data.choices?.[0]?.delta?.content || '';
                        
                        if (content) {
                            responseContent += content;
                            
                            // إزالة مؤشر الكتابة وإضافة رسالة الرد
                            const typingEl = document.getElementById('typingIndicator');
                            if (typingEl) {
                                typingEl.remove();
                                responseDiv = document.createElement('div');
                                responseDiv.className = 'message assistant';
                                responseDiv.innerHTML = `
                                    <div class="message-content">${formatMessage(responseContent)}</div>
                                    <div class="message-time">${new Date().toLocaleTimeString('ar-EG')}</div>
                                `;
                                document.getElementById('chatMessages').appendChild(responseDiv);
                            } else if (responseDiv) {
                                responseDiv.querySelector('.message-content').innerHTML = formatMessage(responseContent);
                            }
                            
                            document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
                        }
                    } catch (e) {
                        console.log('Event data:', event.data);
                    }
                };
                
                eventSource.onerror = function() {
                    eventSource.close();
                    document.getElementById('typingIndicator')?.remove();
                    document.getElementById('sendBtn').style.display = 'block';
                    document.getElementById('stopBtn').style.display = 'none';
                    isGenerating = false;
                    
                    if (!responseDiv) {
                        addMessageToChat('assistant', '⚠️ عذراً، حدث خطأ في الاتصال. جاري إعادة المحاولة..');
                    }
                };
            }
            
            function stopGeneration() {
                if (currentStreamId) {
                    fetch('/stop_generation', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({stream_id: currentStreamId})
                    });
                    
                    if (eventSource) {
                        eventSource.close();
                    }
                    
                    document.getElementById('typingIndicator')?.remove();
                    document.getElementById('sendBtn').style.display = 'block';
                    document.getElementById('stopBtn').style.display = 'none';
                    isGenerating = false;
                }
            }
            
            // إنشاء محادثة جديدة عند التحميل
            window.onload = function() {
                newConversation();
                
                // دعم إرسال الرسالة بالضغط على Enter + Ctrl
                document.getElementById('userInput').addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && e.ctrlKey) {
                        e.preventDefault();
                        sendMessage();
                    }
                });
            };
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    """إنشاء محادثة جديدة"""
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = {
        'id': conversation_id,
        'title': 'محادثة جديدة',
        'messages': [],
        'created': datetime.now().isoformat(),
        'updated': datetime.now().isoformat()
    }
    session['current_conversation'] = conversation_id
    return jsonify({'conversation_id': conversation_id})

@app.route('/get_conversations')
def get_conversations():
    """الحصول على قائمة المحادثات"""
    conv_list = []
    for conv_id, conv in conversations.items():
        conv_list.append({
            'id': conv_id,
            'title': conv['title'],
            'created': conv['created'],
            'preview': conv['messages'][-1]['content'][:50] + '...' if conv['messages'] else ''
        })
    return jsonify({'conversations': sorted(conv_list, key=lambda x: x['created'], reverse=True)})

@app.route('/get_conversation/<conversation_id>')
def get_conversation(conversation_id):
    """الحصول على محادثة محددة"""
    if conversation_id in conversations:
        return jsonify(conversations[conversation_id])
    return jsonify({'error': 'المحادثة غير موجودة'}), 404

@app.route('/stream_chat')
def stream_chat():
    """بث الردود بشكل مباشر"""
    conversation_id = request.args.get('conversation_id')
    message = request.args.get('message', '')
    stream_id = request.args.get('stream_id', str(uuid.uuid4()))
    
    if not conversation_id or conversation_id not in conversations:
        return jsonify({'error': 'محادثة غير صالحة'}), 400
    
    # حفظ رسالة المستخدم
    conversations[conversation_id]['messages'].append({
        'role': 'user',
        'content': message,
        'timestamp': datetime.now().isoformat()
    })
    
    # تحديث عنوان المحادثة إذا كانت جديدة
    if len(conversations[conversation_id]['messages']) == 1:
        conversations[conversation_id]['title'] = message[:50] + ('...' if len(message) > 50 else '')
    
    # تسجيل التدفق النشط
    active_streams[stream_id] = {
        'conversation_id': conversation_id,
        'started': datetime.now().isoformat(),
        'stopped': False
    }
    
    # تجهيز رسائل المحادثة
    messages = []
    for msg in conversations[conversation_id]['messages'][-10:]:  # آخر 10 رسائل فقط للسياق
        messages.append({
            'role': msg['role'],
            'content': msg['content']
        })
    
    def generate():
        full_response = ""
        try:
            for chunk in generate_professional_response(messages, stream_id):
                yield chunk
                
                # تجميع الرد الكامل
                if chunk.startswith('data: ') and '[DONE]' not in chunk:
                    try:
                        data = json.loads(chunk[6:])
                        content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            full_response += content
                    except:
                        pass
            
            # حفظ رد المساعد بعد اكتماله
            if full_response and conversation_id in conversations:
                conversations[conversation_id]['messages'].append({
                    'role': 'assistant',
                    'content': full_response,
                    'timestamp': datetime.now().isoformat()
                })
                conversations[conversation_id]['updated'] = datetime.now().isoformat()
        
        except Exception as e:
            error_msg = f"data: " + json.dumps({"choices": [{"delta": {"content": f"\n\n⚠️ عذراً، حدث خطأ: {str(e)}"}}]}) + "\n\n"
            yield error_msg
        finally:
            if stream_id in active_streams:
                del active_streams[stream_id]
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/stop_generation', methods=['POST'])
def stop_generation():
    """إيقاف التوليد"""
    data = request.json
    stream_id = data.get('stream_id')
    
    if stream_id in active_streams:
        active_streams[stream_id]['stopped'] = True
    
    return jsonify({'status': 'stopped'})

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
