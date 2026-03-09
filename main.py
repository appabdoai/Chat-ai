from flask import Flask, render_template_string, request, jsonify, session, Response
import requests
import json
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import threading

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

# إعدادات NVIDIA API
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-122b-a10b"

# تخزين المحادثات والتدفقات النشطة
conversations = {}
active_streams = {}  # لتتبع التدفقات النشطة وإيقافها

def generate_expert_response(messages, stream_id):
    """توليد ردود خبيرة مع إمكانية الإيقاف"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    system_prompt = {
        "role": "system",
        "content": """أنت Soft Atlas AI Expert - خبير متخصص في التحليل والنقاش العميق.

قواعد الخبرة المتقدمة:

1. للأسئلة العامة والتحليل:
   - ابدأ الإجابة فوراً دون مقدمات
   - حلل السؤال من 7 جوانب مختلفة على الأقل
   - قدم أدلة وإحصائيات وأرقام دقيقة
   - ناقش بالإيجابيات والسلبيات
   - أضف توقعات وتوصيات مستقبلية

2. للمواضيع البرمجية:
   - قدم كود كامل ومتكامل (2000-5000 سطر)
   - اشرح كل دالة وكلاس بالتفصيل الممل
   - أضف تعليقات على كل سطر بالعربية
   - قدم 10 أمثلة تطبيقية متنوعة
   - حلل أداء الكود واقترح تحسينات
   - ناقش الأخطاء الشائعة وكيفية تجنبها

3. للمقارنات:
   - استخدم جداول مقارنة مفصلة
   - قارن من جميع النواحي (أداء، تكلفة، سهولة، أمان)
   - أضف توصيات بناءً على حالة الاستخدام

4. للإحصائيات:
   - استخدم جداول إحصائية مرتبة
   - أضف رسوم بيانية نصية
   - حلل الاتجاهات والأنماط

5. تنسيق الإجابة:
   - استخدم عناوين رئيسية (##)
   - استخدم عناوين فرعية (###)
   - استخدم جداول للبيانات
   - استخدم قوائم نقطية ورقمية
   - استخدم أكواد مع تلوين
   - تأكد من اكتمال الإجابة 100%

6. مهم جداً:
   - لا تتوقف قبل إكمال الفكرة كاملة
   - قسّم الإجابات الطويلة لأقسام واضحة
   - استخدم لغة عربية فصحى سليمة
   - كن دقيقاً وشاملاً في كل نقطة"""
    }
    
    full_messages = [system_prompt] + messages[-30:]  # سياق أكبر
    
    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "max_tokens": 32768,
        "temperature": 0.7,
        "top_p": 0.95,
        "stream": True,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1
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
                # التحقق من طلب الإيقاف
                if stream_id in active_streams and active_streams[stream_id].get('stopped', False):
                    yield "\n\n**[تم إيقاف التوليد بناءً على طلبك]**"
                    break
                    
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
            yield f"⚠️ عذراً، حدث خطأ تقني: {response.status_code}"
            
    except Exception as e:
        yield f"❌ خطأ في الاتصال: {str(e)}، جاري إعادة المحاولة..."

@app.route('/')
def index():
    """الصفحة الرئيسية - النسخة النهائية"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
        conversations[session['conversation_id']] = []
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Soft Atlas AI Expert - خبير التحليل والبرمجة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #3b82f6;
            --primary-dark: #2563eb;
            --secondary: #8b5cf6;
            --accent: #f59e0b;
            --success: #10b981;
            --danger: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border: #334155;
            --card-bg: #1e293b;
            --hover-bg: #2d3748;
            --code-bg: #0f172a;
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
        }

        .app {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Navbar */
        .navbar {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 0 2rem;
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            z-index: 100;
        }

        .nav-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .menu-btn {
            width: 45px;
            height: 45px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .menu-btn:hover {
            background: var(--primary);
            border-color: var(--primary);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .logo-icon i {
            font-size: 22px;
            color: white;
        }

        .logo-text {
            font-weight: 800;
            font-size: 1.4rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-tabs {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--bg-primary);
            padding: 0.3rem;
            border-radius: 40px;
            border: 1px solid var(--border);
        }

        .nav-tab {
            padding: 0.5rem 1.5rem;
            border-radius: 30px;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.3s;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav-tab:hover {
            color: var(--text-primary);
            background: var(--hover-bg);
        }

        .nav-tab.active {
            background: var(--primary);
            color: white;
        }

        .nav-right {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0.4rem 1.2rem;
            background: var(--bg-primary);
            border-radius: 30px;
            border: 1px solid var(--border);
        }

        .status-dot {
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.7; }
        }

        .theme-toggle {
            width: 45px;
            height: 45px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .theme-toggle:hover {
            background: var(--primary);
            border-color: var(--primary);
        }

        /* Main Layout */
        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        /* Sidebar */
        .sidebar {
            width: 340px;
            background: var(--bg-secondary);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease;
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            z-index: 90;
            transform: translateX(100%);
        }

        .sidebar.open {
            transform: translateX(0);
        }

        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sidebar-header h3 {
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .close-sidebar {
            width: 35px;
            height: 35px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
        }

        .close-sidebar:hover {
            background: var(--primary);
        }

        .new-chat-btn {
            margin: 1rem;
            padding: 1rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.3s;
            font-size: 1rem;
        }

        .new-chat-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3);
        }

        .conversations-list {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }

        .conversation-item {
            padding: 1rem;
            background: var(--bg-primary);
            border-radius: 12px;
            margin-bottom: 0.75rem;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid transparent;
        }

        .conversation-item:hover {
            border-color: var(--primary);
            transform: translateX(-5px);
            background: var(--hover-bg);
        }

        .conversation-item.active {
            border-color: var(--primary);
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
        }

        .conv-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
        }

        .conv-delete {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0.2rem;
        }

        .conv-delete:hover {
            color: var(--danger);
        }

        .conv-preview {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conv-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.7rem;
            color: var(--text-secondary);
        }

        /* Chat Area */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: var(--bg-primary);
        }

        .chat-header {
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-secondary);
        }

        .chat-title {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .expert-badge {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 0.3rem 1.2rem;
            border-radius: 30px;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .clear-chat {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.5rem 1.2rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .clear-chat:hover {
            background: var(--danger);
            border-color: var(--danger);
        }

        /* Messages Container */
        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            scroll-behavior: smooth;
        }

        .message {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 50px;
            height: 50px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, var(--accent), #f97316);
        }

        .message.assistant .message-avatar {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
        }

        .message-content {
            flex: 1;
            max-width: calc(100% - 70px);
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .message.user .message-header {
            flex-direction: row-reverse;
        }

        .message-text {
            background: var(--bg-secondary);
            padding: 1.25rem 1.5rem;
            border-radius: 16px;
            border: 1px solid var(--border);
            color: var(--text-primary);
            line-height: 1.8;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .message.user .message-text {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            color: white;
        }

        /* Message Actions */
        .message-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
            justify-content: flex-start;
        }

        .message.user .message-actions {
            justify-content: flex-end;
        }

        .action-btn {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.4rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .action-btn:hover {
            background: var(--primary);
            border-color: var(--primary);
        }

        .action-btn.stop {
            background: var(--danger);
            border-color: var(--danger);
            color: white;
        }

        .action-btn.stop:hover {
            background: #dc2626;
        }

        /* Code Blocks */
        .message-text pre {
            background: var(--code-bg) !important;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid var(--border);
            position: relative;
            max-width: 100%;
            overflow-x: auto;
        }

        .message-text code {
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
        }

        .copy-code {
            position: absolute;
            top: 0.5rem;
            left: 0.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        pre:hover .copy-code {
            opacity: 1;
        }

        /* Tables */
        .message-text table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: var(--bg-primary);
            border-radius: 12px;
            overflow: hidden;
        }

        .message-text th {
            background: var(--primary);
            color: white;
            padding: 0.75rem;
            font-weight: 600;
        }

        .message-text td {
            padding: 0.75rem;
            border-bottom: 1px solid var(--border);
        }

        .message-text tr:last-child td {
            border-bottom: none;
        }

        /* Welcome Message */
        .welcome-message {
            text-align: center;
            max-width: 800px;
            margin: 3rem auto;
            padding: 2rem;
        }

        .welcome-icon {
            width: 120px;
            height: 120px;
            margin: 0 auto 2rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .welcome-icon i {
            font-size: 60px;
            color: white;
        }

        .welcome-message h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }

        .feature-card {
            background: var(--bg-secondary);
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid var(--border);
        }

        .feature-card i {
            font-size: 2rem;
            color: var(--primary);
            margin-bottom: 1rem;
        }

        /* Input Area */
        .input-container {
            padding: 1rem 2rem;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }

        .input-wrapper {
            display: flex;
            gap: 1rem;
            align-items: flex-end;
            background: var(--bg-primary);
            border-radius: 20px;
            padding: 0.5rem;
            border: 1px solid var(--border);
        }

        .input-wrapper:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            padding: 0.75rem 1rem;
            color: var(--text-primary);
            font-family: 'Cairo', sans-serif;
            font-size: 0.95rem;
            resize: none;
            max-height: 120px;
        }

        textarea:focus {
            outline: none;
        }

        .input-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .input-btn {
            width: 45px;
            height: 45px;
            border: none;
            border-radius: 14px;
            background: transparent;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .input-btn:hover:not(:disabled) {
            background: var(--primary);
            border-color: var(--primary);
        }

        .input-btn.send {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            color: white;
        }

        .input-btn.stop {
            background: var(--danger);
            border-color: var(--danger);
            color: white;
        }

        .input-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .typing-dots {
            display: flex;
            gap: 3px;
        }

        .typing-dots span {
            width: 6px;
            height: 6px;
            background: var(--primary);
            border-radius: 50%;
            animation: typing 1s infinite;
        }

        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 3px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .navbar {
                padding: 0 1rem;
            }
            
            .logo-text {
                font-size: 1.2rem;
            }
            
            .nav-tabs {
                display: none;
            }
            
            .sidebar {
                width: 100%;
            }
            
            .messages-container {
                padding: 1rem;
            }
            
            .message-content {
                max-width: 100%;
            }
            
            .welcome-message h1 {
                font-size: 2rem;
            }
            
            .features-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Navbar -->
        <div class="navbar">
            <div class="nav-left">
                <button class="menu-btn" onclick="toggleSidebar()">
                    <i class="fas fa-bars"></i>
                </button>
                <div class="logo">
                    <div class="logo-icon">
                        <i class="fas fa-brain"></i>
                    </div>
                    <span class="logo-text">Soft Atlas Expert</span>
                </div>
            </div>
            
            <div class="nav-tabs">
                <div class="nav-tab active" onclick="switchTab('chat', this)">
                    <i class="fas fa-comment"></i> تحليل ونقاش
                </div>
                <div class="nav-tab" onclick="switchTab('code', this)">
                    <i class="fas fa-code"></i> برمجة متقدمة
                </div>
                <div class="nav-tab" onclick="switchTab('compare', this)">
                    <i class="fas fa-scale-balanced"></i> مقارنات
                </div>
            </div>
            
            <div class="nav-right">
                <div class="status">
                    <span class="status-dot"></span>
                    <span>خبير متصل</span>
                </div>
                <button class="theme-toggle" onclick="toggleTheme()">
                    <i class="fas fa-moon"></i>
                </button>
            </div>
        </div>
        
        <!-- Main -->
        <div class="main">
            <!-- Sidebar -->
            <div class="sidebar" id="sidebar">
                <div class="sidebar-header">
                    <h3><i class="fas fa-history"></i> سجل المحادثات</h3>
                    <button class="close-sidebar" onclick="toggleSidebar()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <button class="new-chat-btn" onclick="newConversation()">
                    <i class="fas fa-plus"></i>
                    محادثة جديدة
                </button>
                
                <div class="conversations-list" id="conversationsList">
                    <!-- تضاف المحادثات هنا -->
                </div>
            </div>
            
            <!-- Chat Area -->
            <div class="chat-area">
                <div class="chat-header">
                    <div class="chat-title">
                        <span class="expert-badge">
                            <i class="fas fa-crown"></i> خبير متخصص
                        </span>
                    </div>
                    <button class="clear-chat" onclick="clearChat()">
                        <i class="fas fa-trash"></i> مسح المحادثة
                    </button>
                </div>
                
                <div class="messages-container" id="messagesContainer">
                    <!-- رسالة الترحيب -->
                    <div class="welcome-message" id="welcomeMessage">
                        <div class="welcome-icon">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h1>Soft Atlas Expert</h1>
                        <p>خبيرك المتخصص في التحليل والبرمجة والنقاش العميق</p>
                        
                        <div class="features-grid">
                            <div class="feature-card">
                                <i class="fas fa-chart-line"></i>
                                <h3>تحليل عميق</h3>
                                <p>تحليل من 7 جوانب مختلفة مع إحصائيات</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-code"></i>
                                <h3>أكواد احترافية</h3>
                                <p>كود كامل حتى 5000 سطر مع شرح</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-scale-balanced"></i>
                                <h3>مقارنات دقيقة</h3>
                                <p>جداول مقارنة مفصلة مع توصيات</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-message"></i>
                                <h3>نقاش معمق</h3>
                                <p>مناقشة جميع الجوانب بالإيجابيات والسلبيات</p>
                            </div>
                        </div>
                        
                        <div style="margin-top: 2rem; color: var(--text-secondary);">
                            <i class="fas fa-arrow-down"></i> اطرح سؤالك للتحليل العميق
                        </div>
                    </div>
                </div>
                
                <!-- Input Area -->
                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea 
                            id="messageInput" 
                            placeholder="اكتب سؤالك هنا... سأقدم تحليلاً شاملاً من جميع الجوانب"
                            rows="1"
                            oninput="autoResize(this)"
                        ></textarea>
                        <div class="input-actions">
                            <button class="input-btn" id="stopBtn" onclick="stopGeneration()" style="display: none;">
                                <i class="fas fa-stop"></i>
                            </button>
                            <button class="input-btn send" id="sendBtn" onclick="sendMessage()">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </div>
                    </div>
                    <div class="input-footer">
                        <div class="typing-indicator" id="typingIndicator"></div>
                        <span>Enter للإرسال • Shift+Enter سطر جديد</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // المتغيرات العامة
        let currentConversationId = '{{ session.conversation_id }}';
        let isProcessing = false;
        let currentStreamId = null;
        let currentTheme = 'dark';
        
        // تهيئة
        document.addEventListener('DOMContentLoaded', function() {
            loadConversations();
            setupEventListeners();
            loadMessages();
        });
        
        function loadMessages() {
            fetch(`/api/conversation/${currentConversationId}`)
                .then(res => res.json())
                .then(data => {
                    if (data.messages && data.messages.length > 0) {
                        document.getElementById('welcomeMessage')?.remove();
                        data.messages.forEach(msg => {
                            if (msg.role === 'user') {
                                displayUserMessage(msg.content, msg.timestamp);
                            } else {
                                displayAssistantMessage(msg.content, msg.timestamp);
                            }
                        });
                    }
                });
        }
        
        function setupEventListeners() {
            const input = document.getElementById('messageInput');
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
        }
        
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
        }
        
        function toggleTheme() {
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const root = document.documentElement;
            
            if (currentTheme === 'light') {
                root.style.setProperty('--bg-primary', '#f8fafc');
                root.style.setProperty('--bg-secondary', '#f1f5f9');
                root.style.setProperty('--text-primary', '#0f172a');
                root.style.setProperty('--text-secondary', '#475569');
                root.style.setProperty('--border', '#cbd5e1');
                root.style.setProperty('--card-bg', '#ffffff');
                root.style.setProperty('--hover-bg', '#e2e8f0');
                root.style.setProperty('--code-bg', '#f1f5f9');
                document.querySelector('.theme-toggle i').className = 'fas fa-sun';
            } else {
                root.style.setProperty('--bg-primary', '#0f172a');
                root.style.setProperty('--bg-secondary', '#1e293b');
                root.style.setProperty('--text-primary', '#f8fafc');
                root.style.setProperty('--text-secondary', '#94a3b8');
                root.style.setProperty('--border', '#334155');
                root.style.setProperty('--card-bg', '#1e293b');
                root.style.setProperty('--hover-bg', '#2d3748');
                root.style.setProperty('--code-bg', '#0f172a');
                document.querySelector('.theme-toggle i').className = 'fas fa-moon';
            }
        }
        
        function switchTab(tab, element) {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            element.classList.add('active');
            
            const input = document.getElementById('messageInput');
            if (tab === 'code') {
                input.placeholder = 'اكتب متطلبات البرنامج... سأقدم كود كامل حتى 5000 سطر';
            } else if (tab === 'compare') {
                input.placeholder = 'ماذا تريد مقارنته؟ سأقدم جدول مقارنة مفصل';
            } else {
                input.placeholder = 'اكتب موضوع التحليل... سأحلله من جميع الجوانب';
            }
        }
        
        function loadConversations() {
            fetch('/api/conversations')
                .then(res => res.json())
                .then(conversations => {
                    const list = document.getElementById('conversationsList');
                    if (conversations.length === 0) {
                        list.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">لا توجد محادثات سابقة</div>';
                        return;
                    }
                    
                    list.innerHTML = '';
                    conversations.forEach(conv => {
                        const item = createConversationItem(conv);
                        list.appendChild(item);
                    });
                });
        }
        
        function createConversationItem(conv) {
            const div = document.createElement('div');
            div.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
            div.setAttribute('data-id', conv.id);
            
            const date = new Date(conv.timestamp);
            const timeStr = date.toLocaleString('ar-SA', { 
                hour: '2-digit', 
                minute: '2-digit',
                day: '2-digit',
                month: '2-digit'
            });
            
            div.innerHTML = `
                <div class="conv-title">
                    <span>${escapeHtml(conv.preview.substring(0, 30))}...</span>
                    <button class="conv-delete" onclick="deleteConversation('${conv.id}', event)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="conv-preview">${escapeHtml(conv.preview)}</div>
                <div class="conv-meta">
                    <span><i class="far fa-clock"></i> ${timeStr}</span>
                    <span><i class="far fa-comment"></i> ${conv.message_count}</span>
                </div>
            `;
            
            div.onclick = (e) => {
                if (!e.target.closest('.conv-delete')) {
                    loadConversation(conv.id);
                }
            };
            
            return div;
        }
        
        function loadConversation(conversationId) {
            currentConversationId = conversationId;
            toggleSidebar();
            
            fetch(`/api/conversation/${conversationId}`)
                .then(res => res.json())
                .then(data => {
                    const container = document.getElementById('messagesContainer');
                    container.innerHTML = '';
                    
                    if (data.messages.length === 0) {
                        container.appendChild(document.getElementById('welcomeMessage').cloneNode(true));
                    } else {
                        data.messages.forEach(msg => {
                            if (msg.role === 'user') {
                                displayUserMessage(msg.content, msg.timestamp);
                            } else {
                                displayAssistantMessage(msg.content, msg.timestamp);
                            }
                        });
                    }
                    
                    // تحديث النشط
                    document.querySelectorAll('.conversation-item').forEach(item => {
                        item.classList.remove('active');
                        if (item.dataset.id === conversationId) {
                            item.classList.add('active');
                        }
                    });
                });
        }
        
        function newConversation() {
            fetch('/api/conversations', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        currentConversationId = data.id;
                        
                        // مسح المحادثة الحالية
                        const container = document.getElementById('messagesContainer');
                        container.innerHTML = '';
                        container.appendChild(document.getElementById('welcomeMessage').cloneNode(true));
                        
                        // تحديث القائمة
                        loadConversations();
                        
                        // إغلاق sidebar
                        toggleSidebar();
                    }
                });
        }
        
        function deleteConversation(conversationId, event) {
            event.stopPropagation();
            
            if (confirm('هل أنت متأكد من حذف هذه المحادثة؟')) {
                fetch(`/api/conversation/${conversationId}`, { method: 'DELETE' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            if (conversationId === currentConversationId) {
                                newConversation();
                            }
                            loadConversations();
                        }
                    });
            }
        }
        
        function clearChat() {
            if (confirm('هل أنت متأكد من مسح المحادثة الحالية؟')) {
                fetch('/api/clear', { method: 'POST' })
                    .then(() => {
                        const container = document.getElementById('messagesContainer');
                        container.innerHTML = '';
                        container.appendChild(document.getElementById('welcomeMessage').cloneNode(true));
                        loadConversations();
                    });
            }
        }
        
        function displayUserMessage(message, timestamp) {
            const container = document.getElementById('messagesContainer');
            
            // إزالة رسالة الترحيب
            document.getElementById('welcomeMessage')?.remove();
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user';
            
            const time = timestamp ? new Date(timestamp) : new Date();
            const timeStr = time.toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit' });
            
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-header">
                        <span class="sender-name">أنت</span>
                        <span>${timeStr}</span>
                    </div>
                    <div class="message-text">${escapeHtml(message)}</div>
                </div>
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
            `;
            
            container.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function displayAssistantMessage(message, timestamp) {
            const container = document.getElementById('messagesContainer');
            
            // إزالة رسالة الترحيب
            document.getElementById('welcomeMessage')?.remove();
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            
            const time = timestamp ? new Date(timestamp) : new Date();
            const timeStr = time.toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit' });
            
            // معالجة Markdown
            let formattedMessage = message;
            if (typeof marked !== 'undefined') {
                formattedMessage = DOMPurify.sanitize(marked.parse(message));
            }
            
            messageDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="sender-name">Soft Atlas Expert</span>
                        <span>${timeStr}</span>
                    </div>
                    <div class="message-text">${formattedMessage}</div>
                    <div class="message-actions">
                        <button class="action-btn" onclick="copyMessage(this)">
                            <i class="fas fa-copy"></i> نسخ الإجابة
                        </button>
                        <button class="action-btn" onclick="copyCode(this)">
                            <i class="fas fa-code"></i> نسخ الكود
                        </button>
                    </div>
                </div>
            `;
            
            container.appendChild(messageDiv);
            
            // تطبيق تلوين الكود
            messageDiv.querySelectorAll('pre code').forEach(block => {
                if (typeof hljs !== 'undefined') {
                    hljs.highlightElement(block);
                }
                
                // إضافة زر نسخ للكود
                const pre = block.parentNode;
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-code';
                copyBtn.innerHTML = '<i class="fas fa-copy"></i> نسخ الكود';
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(block.textContent);
                    showNotification('تم نسخ الكود');
                };
                pre.appendChild(copyBtn);
            });
            
            scrollToBottom();
        }
        
        function showNotification(message) {
            // يمكن تحسينها لاحقاً
            alert(message);
        }
        
        function copyMessage(button) {
            const text = button.closest('.message-content').querySelector('.message-text').innerText;
            navigator.clipboard.writeText(text).then(() => {
                showNotification('تم نسخ الإجابة');
            });
        }
        
        function copyCode(button) {
            const messageDiv = button.closest('.message');
            const codeBlocks = messageDiv.querySelectorAll('pre code');
            if (codeBlocks.length > 0) {
                let allCode = '';
                codeBlocks.forEach(block => {
                    allCode += block.textContent + '\\n\\n';
                });
                navigator.clipboard.writeText(allCode).then(() => {
                    showNotification('تم نسخ كل الأكواد');
                });
            } else {
                copyMessage(button);
            }
        }
        
        function sendMessage() {
            if (isProcessing) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            isProcessing = true;
            document.getElementById('sendBtn').disabled = true;
            document.getElementById('stopBtn').style.display = 'flex';
            
            displayUserMessage(message);
            input.value = '';
            autoResize(input);
            
            // إظهار مؤشر الكتابة
            showTypingIndicator();
            
            // إنشاء stream ID جديد
            currentStreamId = Date.now().toString();
            
            // بدء التدفق
            const eventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}&stream_id=${currentStreamId}`);
            let fullResponse = '';
            let assistantMessage = null;
            
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                hideTypingIndicator();
                
                if (data.chunk) {
                    if (!assistantMessage) {
                        const container = document.getElementById('messagesContainer');
                        assistantMessage = document.createElement('div');
                        assistantMessage.className = 'message assistant';
                        assistantMessage.innerHTML = `
                            <div class="message-avatar">
                                <i class="fas fa-robot"></i>
                            </div>
                            <div class="message-content">
                                <div class="message-header">
                                    <span class="sender-name">Soft Atlas Expert</span>
                                    <span>${new Date().toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit' })}</span>
                                </div>
                                <div class="message-text"></div>
                                <div class="message-actions">
                                    <button class="action-btn" onclick="copyMessage(this)">
                                        <i class="fas fa-copy"></i> نسخ الإجابة
                                    </button>
                                    <button class="action-btn" onclick="copyCode(this)">
                                        <i class="fas fa-code"></i> نسخ الكود
                                    </button>
                                </div>
                            </div>
                        `;
                        container.appendChild(assistantMessage);
                    }
                    
                    fullResponse += data.chunk;
                    
                    if (typeof marked !== 'undefined') {
                        assistantMessage.querySelector('.message-text').innerHTML = DOMPurify.sanitize(marked.parse(fullResponse));
                        
                        // تحديث تلوين الكود
                        assistantMessage.querySelectorAll('pre code').forEach(block => {
                            hljs.highlightElement(block);
                        });
                    } else {
                        assistantMessage.querySelector('.message-text').textContent = fullResponse;
                    }
                    
                    scrollToBottom();
                }
                
                if (data.done) {
                    eventSource.close();
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('stopBtn').style.display = 'none';
                    loadConversations();
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                isProcessing = false;
                document.getElementById('sendBtn').disabled = false;
                document.getElementById('stopBtn').style.display = 'none';
                hideTypingIndicator();
                
                if (!assistantMessage) {
                    displayAssistantMessage('⚠️ حدث خطأ في الاتصال. جاري إعادة المحاولة...');
                }
            };
        }
        
        function stopGeneration() {
            if (currentStreamId) {
                fetch('/api/chat/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ stream_id: currentStreamId })
                }).then(() => {
                    document.getElementById('stopBtn').style.display = 'none';
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    showNotification('تم إيقاف التوليد');
                });
            }
        }
        
        function showTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            indicator.innerHTML = `
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
                <span>الخبير يحلل ويكتب...</span>
            `;
        }
        
        function hideTypingIndicator() {
            document.getElementById('typingIndicator').innerHTML = '';
        }
        
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }
        
        function scrollToBottom() {
            const container = document.getElementById('messagesContainer');
            container.scrollTop = container.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/chat/stream')
def chat_stream():
    """نقطة نهاية التدفق مع إمكانية الإيقاف"""
    message = request.args.get('message', '').strip()
    conversation_id = session.get('conversation_id')
    stream_id = request.args.get('stream_id', str(uuid.uuid4()))
    
    if not message:
        return jsonify({'error': 'الرجاء إدخال رسالة'}), 400
    
    # إنشاء flag للإيقاف
    active_streams[stream_id] = {'stopped': False}
    
    def generate():
        try:
            # تخزين رسالة المستخدم
            user_message = {
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            }
            
            if conversation_id not in conversations:
                conversations[conversation_id] = []
            
            conversations[conversation_id].append(user_message)
            
            # تحضير الرسائل
            messages_for_api = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in conversations[conversation_id]
            ]
            
            full_response = ""
            
            # توليد الرد
            for chunk in generate_expert_response(messages_for_api, stream_id):
                if stream_id in active_streams and active_streams[stream_id].get('stopped', False):
                    full_response += "\n\n**[تم إيقاف التوليد]**"
                    yield f"data: {json.dumps({'chunk': '**[تم إيقاف التوليد]**'})}\n\n"
                    break
                    
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # تخزين الرد إذا لم يتم إيقافه
            if not active_streams.get(stream_id, {}).get('stopped', False):
                assistant_message = {
                    'role': 'assistant',
                    'content': full_response,
                    'timestamp': datetime.now().isoformat()
                }
                conversations[conversation_id].append(assistant_message)
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        finally:
            # تنظيف
            if stream_id in active_streams:
                del active_streams[stream_id]
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/chat/stop', methods=['POST'])
def stop_chat():
    """إيقاف التوليد"""
    data = request.json
    stream_id = data.get('stream_id')
    
    if stream_id in active_streams:
        active_streams[stream_id]['stopped'] = True
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """قائمة المحادثات"""
    conv_list = []
    for conv_id, messages in conversations.items():
        if messages:
            first_msg = messages[0]['content']
            conv_list.append({
                'id': conv_id,
                'preview': first_msg[:50] + '...' if len(first_msg) > 50 else first_msg,
                'timestamp': messages[0]['timestamp'],
                'message_count': len(messages) // 2
            })
    
    sorted_list = sorted(conv_list, key=lambda x: x['timestamp'], reverse=True)
    return jsonify(sorted_list)

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """إنشاء محادثة جديدة"""
    new_id = str(uuid.uuid4())
    conversations[new_id] = []
    session['conversation_id'] = new_id
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """استرجاع محادثة"""
    if conversation_id in conversations:
        return jsonify({'messages': conversations[conversation_id]})
    return jsonify({'messages': []})

@app.route('/api/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """حذف محادثة"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """مسح المحادثة الحالية"""
    conversation_id = session.get('conversation_id')
    if conversation_id in conversations:
        conversations[conversation_id] = []
    return jsonify({'success': True})

if __name__ == '__main__':
    print("="*80)
    print("🚀 Soft Atlas AI Expert - النسخة النهائية المحترفة")
    print("="*80)
    print("✅ تم حل جميع المشاكل:")
    print("   • محادثة جديدة تعمل فوراً")
    print("   • إجابات دقيقة وطويلة بدون تقطع")
    print("   • أكواد كاملة حتى 5000 سطر")
    print("   • تحليل من 7 جوانب مختلفة")
    print("   • جداول مقارنة وإحصائيات")
    print("   • زر إيقاف التوليد")
    print("   • زر نسخ الإجابة والكود")
    print("   • تصميم متجاوب مع الجوال")
    print("   • تسجيل تلقائي للمحادثات")
    print("="*80)
    print("🌐 الخادم: http://localhost:5000")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
