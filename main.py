import os
from flask import Flask, render_template_string, request, jsonify, session, Response
import requests
import json
import uuid
from datetime import datetime
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-2024'

# إعدادات NVIDIA API المحسنة للسرعة القصوى
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "deepseek-ai/deepseek-v3.2"

# تخزين المحادثات
conversations = {}

def generate_response(messages):
    """توليد ردود سريعة بدون مقدمات"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    # نظام مختصر جداً للسرعة
    system_prompt = {
        "role": "system",
        "content": """أنت مساعد ذكي. أجب مباشرة بدون مقدمات. إذا كان السؤال برمجي، أعط الكود فوراً. كن دقيقاً ومختصراً في الردود العادية، وطويلاً ومفصلاً في البرمجة."""
    }
    
    full_messages = [system_prompt] + messages[-10:]
    
    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "max_tokens": 8192,
        "temperature": 0.5,
        "top_p": 0.9,
        "stream": True
    }
    
    try:
        response = requests.post(
            NVIDIA_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data = line_text[6:]
                        if data and data != '[DONE]':
                            try:
                                json_data = json.loads(data)
                                if 'choices' in json_data:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                            except:
                                continue
        else:
            yield f"⚠️ خطأ: {response.status_code}"
            
    except Exception as e:
        yield f"❌ خطأ: {str(e)}"

@app.route('/')
def index():
    """الصفحة الرئيسية - سريعة ومتجاوبة"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
        conversations[session['conversation_id']] = []
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>AI Expert - سريع ومباشر</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        :root {
            --primary: #2563eb;
            --bg: #0f172a;
            --bg-light: #1e293b;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            overflow: hidden;
        }

        .app {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Header بسيط */
        .header {
            background: var(--bg-light);
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 60px;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .logo i {
            font-size: 1.5rem;
            color: var(--primary);
        }

        .logo span {
            font-weight: 600;
            font-size: 1.1rem;
        }

        .badge {
            background: var(--primary);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .menu-btn {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
            width: 40px;
            height: 40px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1.2rem;
        }

        /* Main */
        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        /* Sidebar متحرك */
        .sidebar {
            position: fixed;
            top: 60px;
            right: -280px;
            width: 280px;
            bottom: 0;
            background: var(--bg-light);
            border-left: 1px solid var(--border);
            transition: right 0.3s ease;
            z-index: 1000;
        }

        .sidebar.open {
            right: 0;
        }

        .sidebar-header {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .new-chat {
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 10px;
            margin: 1rem;
            width: calc(100% - 2rem);
            font-weight: 500;
            cursor: pointer;
        }

        .conv-list {
            padding: 0.5rem;
            overflow-y: auto;
            height: calc(100vh - 150px);
        }

        .conv-item {
            background: var(--bg);
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 8px;
            cursor: pointer;
            border: 1px solid var(--border);
        }

        .conv-item.active {
            border-color: var(--primary);
        }

        .conv-title {
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conv-time {
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        /* Chat Area */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg);
            width: 100%;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            -webkit-overflow-scrolling: touch;
        }

        .message {
            display: flex;
            gap: 8px;
            margin-bottom: 1rem;
            max-width: 100%;
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background: var(--primary);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .message.user .avatar {
            background: #dc2626;
        }

        .bubble {
            max-width: calc(100% - 50px);
            padding: 12px 16px;
            border-radius: 16px;
            background: var(--bg-light);
            border: 1px solid var(--border);
            line-height: 1.5;
            word-wrap: break-word;
        }

        .message.user .bubble {
            background: var(--primary);
            border: none;
        }

        /* أكواد البرمجة */
        pre {
            background: #1a1a1a;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
            font-size: 13px;
        }

        code {
            font-family: monospace;
            color: #fff;
        }

        /* Input Area */
        .input-area {
            background: var(--bg-light);
            border-top: 1px solid var(--border);
            padding: 0.75rem;
        }

        .input-wrapper {
            display: flex;
            gap: 8px;
            background: var(--bg);
            border-radius: 25px;
            padding: 4px 4px 4px 16px;
            border: 1px solid var(--border);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            padding: 10px 0;
            color: var(--text);
            font-family: 'Cairo', sans-serif;
            font-size: 1rem;
            resize: none;
            max-height: 100px;
            outline: none;
        }

        .input-actions {
            display: flex;
            gap: 4px;
        }

        .input-btn {
            width: 44px;
            height: 44px;
            border: none;
            border-radius: 22px;
            background: transparent;
            color: var(--text);
            cursor: pointer;
            font-size: 1.2rem;
        }

        .input-btn.send {
            background: var(--primary);
            color: white;
        }

        .input-btn.stop {
            background: #dc2626;
            color: white;
        }

        .typing {
            padding: 0 1rem 0.5rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .dots {
            display: flex;
            gap: 3px;
        }

        .dots span {
            width: 6px;
            height: 6px;
            background: var(--primary);
            border-radius: 50%;
            animation: wave 1s infinite;
        }

        .dots span:nth-child(2) { animation-delay: 0.2s; }
        .dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes wave {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }

        /* Overlay للجوال */
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 999;
            display: none;
        }

        .overlay.show {
            display: block;
        }

        @media (max-width: 768px) {
            .badge { display: none; }
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Header -->
        <div class="header">
            <div class="logo">
                <i class="fas fa-bolt"></i>
                <span>AI Expert</span>
                <span class="badge">سريع</span>
            </div>
            <button class="menu-btn" onclick="toggleSidebar()">
                <i class="fas fa-bars"></i>
            </button>
        </div>

        <!-- Sidebar -->
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <span><i class="fas fa-history"></i> المحادثات</span>
                <button class="menu-btn" onclick="toggleSidebar()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <button class="new-chat" onclick="newChat()">
                <i class="fas fa-plus"></i> محادثة جديدة
            </button>
            <div class="conv-list" id="convList"></div>
        </div>

        <!-- Overlay -->
        <div class="overlay" id="overlay" onclick="toggleSidebar()"></div>

        <!-- Chat Area -->
        <div class="chat-area">
            <div class="messages" id="messages"></div>

            <div class="typing" id="typing" style="display: none;">
                <div class="dots">
                    <span></span><span></span><span></span>
                </div>
                <span>AI يكتب...</span>
            </div>

            <div class="input-area">
                <div class="input-wrapper">
                    <textarea 
                        id="input" 
                        placeholder="اكتب سؤالك..."
                        rows="1"
                        oninput="autoResize(this)"
                    ></textarea>
                    <div class="input-actions">
                        <button class="input-btn stop" id="stopBtn" onclick="stopGeneration()" style="display: none;">
                            <i class="fas fa-stop"></i>
                        </button>
                        <button class="input-btn send" id="sendBtn" onclick="sendMessage()">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentId = '{{ session.conversation_id }}';
        let isGenerating = false;
        let currentStream = null;
        let eventSource = null;

        // التحميل الأولي
        document.addEventListener('DOMContentLoaded', function() {
            loadConversations();
            loadMessages();
            
            document.getElementById('input').addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
        });

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('show');
        }

        function loadMessages() {
            fetch(`/api/conversation/${currentId}`)
                .then(res => res.json())
                .then(data => {
                    const container = document.getElementById('messages');
                    container.innerHTML = '';
                    
                    if (data.messages && data.messages.length > 0) {
                        data.messages.forEach(msg => {
                            addMessage(msg.content, msg.role === 'user');
                        });
                    }
                });
        }

        function loadConversations() {
            fetch('/api/conversations')
                .then(res => res.json())
                .then(list => {
                    const container = document.getElementById('convList');
                    container.innerHTML = '';
                    
                    list.forEach(conv => {
                        const div = document.createElement('div');
                        div.className = `conv-item ${conv.id === currentId ? 'active' : ''}`;
                        div.onclick = () => loadConversation(conv.id);
                        
                        const date = new Date(conv.timestamp);
                        div.innerHTML = `
                            <div class="conv-title">${escapeHtml(conv.preview)}</div>
                            <div class="conv-time">${date.toLocaleTimeString('ar-EG')}</div>
                        `;
                        
                        container.appendChild(div);
                    });
                });
        }

        function loadConversation(id) {
            currentId = id;
            toggleSidebar();
            loadMessages();
            loadConversations();
        }

        function newChat() {
            fetch('/api/conversations', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    currentId = data.id;
                    document.getElementById('messages').innerHTML = '';
                    toggleSidebar();
                    loadConversations();
                });
        }

        function addMessage(text, isUser = false) {
            const container = document.getElementById('messages');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${isUser ? 'user' : 'ai'}`;
            
            msgDiv.innerHTML = `
                <div class="avatar">
                    <i class="fas fa-${isUser ? 'user' : 'robot'}"></i>
                </div>
                <div class="bubble">${formatMessage(text)}</div>
            `;
            
            container.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
        }

        function formatMessage(text) {
            // تحويل الكود
            text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, function(match, lang, code) {
                return `<pre><code>${escapeHtml(code)}</code></pre>`;
            });
            
            // تحويل النص العادي
            return text.replace(/\n/g, '<br>');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function sendMessage() {
            if (isGenerating) return;
            
            const input = document.getElementById('input');
            const message = input.value.trim();
            if (!message) return;
            
            // عرض رسالة المستخدم
            addMessage(message, true);
            input.value = '';
            autoResize(input);
            
            // بدء التوليد
            isGenerating = true;
            document.getElementById('sendBtn').style.display = 'none';
            document.getElementById('stopBtn').style.display = 'flex';
            document.getElementById('typing').style.display = 'flex';
            
            // إنشاء معرف فريد للتيار
            const streamId = Date.now().toString();
            currentStream = streamId;
            
            // الاتصال بالتدفق
            eventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}&stream_id=${streamId}`);
            
            let aiMessage = null;
            let fullResponse = '';
            
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                if (data.chunk) {
                    document.getElementById('typing').style.display = 'none';
                    
                    if (!aiMessage) {
                        aiMessage = document.createElement('div');
                        aiMessage.className = 'message ai';
                        aiMessage.innerHTML = `
                            <div class="avatar">
                                <i class="fas fa-robot"></i>
                            </div>
                            <div class="bubble"></div>
                        `;
                        document.getElementById('messages').appendChild(aiMessage);
                    }
                    
                    fullResponse += data.chunk;
                    aiMessage.querySelector('.bubble').innerHTML = formatMessage(fullResponse);
                    aiMessage.scrollIntoView({ behavior: 'smooth' });
                }
                
                if (data.done) {
                    eventSource.close();
                    isGenerating = false;
                    document.getElementById('sendBtn').style.display = 'flex';
                    document.getElementById('stopBtn').style.display = 'none';
                    document.getElementById('typing').style.display = 'none';
                    loadConversations();
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                isGenerating = false;
                document.getElementById('sendBtn').style.display = 'flex';
                document.getElementById('stopBtn').style.display = 'none';
                document.getElementById('typing').style.display = 'none';
                
                if (!aiMessage) {
                    addMessage('⚠️ حدث خطأ، حاول مرة أخرى');
                }
            };
        }

        function stopGeneration() {
            if (currentStream) {
                fetch('/api/chat/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ stream_id: currentStream })
                }).then(() => {
                    if (eventSource) {
                        eventSource.close();
                    }
                    isGenerating = false;
                    document.getElementById('sendBtn').style.display = 'flex';
                    document.getElementById('stopBtn').style.display = 'none';
                    document.getElementById('typing').style.display = 'none';
                });
            }
        }

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/chat/stream')
def chat_stream():
    message = request.args.get('message', '').strip()
    conversation_id = session.get('conversation_id')
    stream_id = request.args.get('stream_id')
    
    if not message:
        return jsonify({'error': 'No message'}), 400
    
    def generate():
        try:
            # حفظ رسالة المستخدم
            user_msg = {'role': 'user', 'content': message, 'timestamp': datetime.now().isoformat()}
            if conversation_id not in conversations:
                conversations[conversation_id] = []
            conversations[conversation_id].append(user_msg)
            
            # تحضير الرسائل
            messages = [{'role': m['role'], 'content': m['content']} for m in conversations[conversation_id]]
            
            full = ""
            
            # توليد الرد
            for chunk in generate_response(messages):
                full += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # حفظ الرد
            ai_msg = {'role': 'assistant', 'content': full, 'timestamp': datetime.now().isoformat()}
            conversations[conversation_id].append(ai_msg)
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'chunk': f'❌ {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/api/chat/stop', methods=['POST'])
def stop_chat():
    return jsonify({'success': True})

@app.route('/api/conversations')
def list_conversations():
    result = []
    for cid, msgs in conversations.items():
        if msgs:
            result.append({
                'id': cid,
                'preview': msgs[0]['content'][:30] + '...',
                'timestamp': msgs[0]['timestamp']
            })
    return jsonify(sorted(result, key=lambda x: x['timestamp'], reverse=True))

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    new_id = str(uuid.uuid4())
    conversations[new_id] = []
    session['conversation_id'] = new_id
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/conversation/<conversation_id>')
def get_conversation(conversation_id):
    return jsonify({'messages': conversations.get(conversation_id, [])})

if __name__ == '__main__':
    print('='*50)
    print('🚀 AI Expert - النسخة السريعة')
    print('='*50)
    print('✅ المميزات:')
    print('   • سرعة فائقة في الاستجابة')
    print('   • متجاوب 100% مع الجوال')
    print('   • إجابات مباشرة بدون مقدمات')
    print('   • لا يتوقف في منتصف الإجابة')
    print('   • تصميم خفيف وسريع')
    print('='*50)
    print('🌐 http://localhost:5000')
    print('='*50)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
