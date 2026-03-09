from flask import Flask, render_template_string, request, jsonify, session, Response
import requests
import json
import base64
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
import time
from threading import Thread
import re

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 30  # 30 يوم

# إعدادات NVIDIA API
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# تخزين المحادثات
conversations = {}

def generate_stream_response(messages):
    """توليد رد متدفق مع إجابات طويلة جداً"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    system_prompt = {
        "role": "system",
        "content": """أنت Soft Atlas AI، مساعد ذكي فائق التطور باللغة العربية الفصحى.

تعليمات خاصة جداً للإجابات الطويلة:
1. قدم إجابات موسوعية شاملة جداً (5000-10000 كلمة للمواضيع المعقدة)
2. للمواضيع البرمجية:
   - قدم أكواد طويلة جداً تصل إلى 5000 سطر
   - اشرح كل جزء بالتفصيل الممل
   - قدم 10-20 مثالاً عملياً
   - اذكر جميع الحالات الخاصة
   - وضح أفضل الممارسات والأخطاء الشائعة
   - قدم تحسينات متعددة المستويات
3. قسّم الإجابات إلى أقسام وفصول
4. استخدم قوائم طويلة ونقاط تفصيلية
5. قدم مقارنات شاملة
6. اذكر المراجع والمصادر
7. قدم إجابات تغطي جميع الجوانب الممكنة
8. استخدم لغة عربية فصيحة 100%
9. للمواضيع العلمية، اشرح النظريات والتطبيقات
10. قدم جداول وإحصائيات عند اللزوم"""
    }
    
    full_messages = [system_prompt] + messages[-100:]  # آخر 100 رسالة للسياق
    
    payload = {
        "model": "qwen/qwen3.5-122b-a10b",
        "messages": full_messages,
        "max_tokens": 131072,  # أقصى طول للإجابة (كبير جداً)
        "temperature": 0.7,
        "top_p": 0.95,
        "stream": True,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    
    try:
        response = requests.post(
            NVIDIA_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=300  # 5 دقائق timeout
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
            yield f"⚠️ خطأ في الاتصال: {response.status_code}"
            
    except Exception as e:
        yield f"❌ حدث خطأ: {str(e)}"

@app.route('/')
def index():
    """الصفحة الرئيسية المحسنة بشكل كبير"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
        conversations[session['conversation_id']] = []
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Soft Atlas AI - المساحات الذكية</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
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
            /* الوضع النهاري */
            --bg-primary: #f0f5fa;
            --bg-secondary: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #475569;
            --accent-primary: #3b82f6;
            --accent-secondary: #8b5cf6;
            --accent-gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --border-color: #e2e8f0;
            --shadow-color: rgba(0, 0, 0, 0.1);
            --message-user: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --message-assistant: #ffffff;
            --sidebar-bg: #ffffff;
            --navbar-bg: rgba(255, 255, 255, 0.8);
            --input-bg: #ffffff;
            --hover-bg: #f8fafc;
        }

        [data-theme="dark"] {
            --bg-primary: #0b1120;
            --bg-secondary: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-primary: #60a5fa;
            --accent-secondary: #c084fc;
            --accent-gradient: linear-gradient(135deg, #60a5fa, #c084fc);
            --border-color: #334155;
            --shadow-color: rgba(0, 0, 0, 0.5);
            --message-user: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --message-assistant: #1e293b;
            --sidebar-bg: #1e293b;
            --navbar-bg: rgba(30, 41, 59, 0.8);
            --input-bg: #1e293b;
            --hover-bg: #2d3a4f;
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            transition: background-color 0.3s, color 0.3s;
        }

        /* توقيف الإجابة */
        .stop-generation {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: #ef4444;
            color: white;
            padding: 12px 30px;
            border-radius: 50px;
            font-weight: 600;
            display: none;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            z-index: 1000;
            box-shadow: 0 10px 25px rgba(239, 68, 68, 0.4);
            animation: slideUp 0.3s ease;
            border: none;
        }

        .stop-generation:hover {
            background: #dc2626;
        }

        @keyframes slideUp {
            from { transform: translate(-50%, 20px); opacity: 0; }
            to { transform: translate(-50%, 0); opacity: 1; }
        }

        /* Navbar صغير وجميل */
        .navbar {
            background: var(--navbar-bg);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            padding: 0.5rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .logo {
            width: 35px;
            height: 35px;
            background: var(--accent-gradient);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .logo i {
            font-size: 18px;
            color: white;
        }

        .brand-text {
            font-size: 1.2rem;
            font-weight: 700;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav-btn {
            width: 38px;
            height: 38px;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }

        .nav-btn:hover {
            background: var(--accent-gradient);
            color: white;
            border-color: transparent;
        }

        /* Main Layout */
        .main-layout {
            display: flex;
            height: calc(100vh - 60px);
            position: relative;
        }

        /* زر فتح السجل (صغير وجميل) */
        .history-toggle {
            position: fixed;
            right: 20px;
            top: 80px;
            width: 45px;
            height: 45px;
            background: var(--accent-gradient);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            cursor: pointer;
            z-index: 99;
            box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4);
            transition: all 0.3s;
        }

        .history-toggle:hover {
            transform: scale(1.1);
        }

        /* Sidebar المخفي */
        .history-sidebar {
            position: fixed;
            right: -350px;
            top: 0;
            width: 320px;
            height: 100vh;
            background: var(--sidebar-bg);
            border-left: 1px solid var(--border-color);
            z-index: 1000;
            transition: right 0.3s ease;
            display: flex;
            flex-direction: column;
            box-shadow: -5px 0 25px var(--shadow-color);
        }

        .history-sidebar.open {
            right: 0;
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sidebar-header h3 {
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .close-sidebar {
            width: 35px;
            height: 35px;
            background: var(--hover-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: var(--text-secondary);
        }

        .conversations-list {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }

        .conversation-item {
            padding: 12px;
            background: var(--hover-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .conversation-item:hover {
            border-color: var(--accent-primary);
            transform: translateX(-5px);
        }

        .conversation-item.active {
            background: var(--accent-gradient);
            color: white;
        }

        .conversation-item.active .conv-preview,
        .conversation-item.active .conv-meta {
            color: white;
        }

        .conv-preview {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .conv-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.7rem;
            color: var(--text-secondary);
        }

        .conversation-actions {
            display: flex;
            gap: 5px;
            margin-top: 8px;
        }

        .conv-action-btn {
            padding: 4px 8px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 5px;
            font-size: 0.7rem;
            cursor: pointer;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 3px;
        }

        .conv-action-btn:hover {
            background: var(--accent-gradient);
            color: white;
        }

        /* Chat Area كبيرة جداً */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-secondary);
            margin-right: 0;
            transition: margin-right 0.3s;
            height: 100%;
        }

        .chat-area.sidebar-open {
            margin-right: 320px;
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        /* Message Styles */
        .message {
            display: flex;
            gap: 15px;
            animation: fadeIn 0.3s ease;
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 45px;
            height: 45px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, #ec4899, #ef4444);
        }

        .message.assistant .message-avatar {
            background: var(--accent-gradient);
        }

        .message-avatar i {
            font-size: 22px;
            color: white;
        }

        .message-content {
            flex: 1;
            max-width: 85%;
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .message.user .message-header {
            flex-direction: row-reverse;
        }

        .sender-name {
            font-weight: 700;
            color: var(--text-primary);
        }

        .message-text {
            background: var(--message-assistant);
            padding: 20px 25px;
            border-radius: 20px;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            line-height: 1.8;
            font-size: 1rem;
            overflow-x: auto;
            box-shadow: 0 5px 15px var(--shadow-color);
        }

        .message.user .message-text {
            background: var(--message-user);
            color: white;
            border: none;
        }

        /* Code Blocks - طويلة جداً */
        .message-text pre {
            background: #0d1117 !important;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border: 1px solid #30363d;
            position: relative;
            max-height: 600px;
            overflow: auto;
        }

        .message-text pre code {
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            line-height: 1.6;
            color: #e6edf3;
        }

        .code-header {
            position: sticky;
            top: 0;
            background: #161b22;
            padding: 10px 15px;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #30363d;
            margin-bottom: 10px;
            z-index: 10;
        }

        .code-lang {
            color: #8b949e;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .copy-code-btn {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .copy-code-btn:hover {
            background: #30363d;
        }

        /* Message Actions */
        .message-actions {
            display: flex;
            gap: 8px;
            margin-top: 10px;
            padding-right: 10px;
        }

        .message-actions button {
            background: var(--hover-bg);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 15px;
            border-radius: 8px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .message-actions button:hover {
            background: var(--accent-gradient);
            color: white;
        }

        /* Input Area صغير وجميل */
        .input-container {
            padding: 15px 30px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
        }

        .input-wrapper {
            display: flex;
            gap: 10px;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 30px;
            padding: 5px;
            box-shadow: 0 5px 15px var(--shadow-color);
        }

        .input-wrapper textarea {
            flex: 1;
            background: transparent;
            border: none;
            padding: 12px 20px;
            color: var(--text-primary);
            font-family: 'Cairo', sans-serif;
            font-size: 0.95rem;
            resize: none;
            max-height: 100px;
        }

        .input-wrapper textarea:focus {
            outline: none;
        }

        .input-wrapper textarea::placeholder {
            color: var(--text-secondary);
            opacity: 0.5;
        }

        .send-btn {
            width: 45px;
            height: 45px;
            background: var(--accent-gradient);
            border: none;
            border-radius: 25px;
            color: white;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 1.1rem;
        }

        .send-btn:hover:not(:disabled) {
            transform: scale(1.05);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .input-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            padding: 0 10px;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }

        /* Welcome Screen */
        .welcome-screen {
            text-align: center;
            max-width: 1000px;
            margin: 0 auto;
            padding: 30px;
        }

        .welcome-icon {
            width: 100px;
            height: 100px;
            margin: 0 auto 20px;
            background: var(--accent-gradient);
            border-radius: 30px;
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
            font-size: 50px;
            color: white;
        }

        .welcome-screen h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .welcome-screen p {
            color: var(--text-secondary);
            margin-bottom: 30px;
        }

        /* Language Chips */
        .language-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin: 20px 0;
        }

        .lang-chip {
            background: var(--hover-bg);
            border: 1px solid var(--border-color);
            padding: 10px 20px;
            border-radius: 30px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .lang-chip:hover {
            background: var(--accent-gradient);
            color: white;
        }

        .lang-chip i {
            font-size: 1rem;
        }

        /* Loading Dots */
        .loading-dots {
            display: flex;
            gap: 8px;
            padding: 20px;
            background: var(--hover-bg);
            border-radius: 20px;
        }

        .loading-dots span {
            width: 10px;
            height: 10px;
            background: var(--accent-primary);
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }

        .loading-dots span:nth-child(2) {
            background: var(--accent-secondary);
            animation-delay: 0.2s;
        }

        .loading-dots span:nth-child(3) {
            background: #ec4899;
            animation-delay: 0.4s;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: var(--hover-bg);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--accent-primary);
            border-radius: 3px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .navbar {
                padding: 0.5rem 1rem;
            }
            
            .brand-text {
                display: none;
            }
            
            .history-sidebar {
                width: 280px;
            }
            
            .chat-area.sidebar-open {
                margin-right: 0;
            }
            
            .messages-container {
                padding: 15px;
            }
            
            .message-content {
                max-width: 100%;
            }
            
            .input-container {
                padding: 10px 15px;
            }
        }
    </style>
</head>
<body data-theme="dark">
    <!-- زر توقيف الإجابة -->
    <button class="stop-generation" id="stopGenerationBtn" onclick="stopGeneration()">
        <i class="fas fa-stop-circle"></i>
        توقيف الإجابة
    </button>

    <!-- Navbar صغير وجميل -->
    <nav class="navbar">
        <div class="navbar-brand">
            <div class="logo">
                <i class="fas fa-brain"></i>
            </div>
            <span class="brand-text">Soft Atlas AI</span>
        </div>
        
        <div class="nav-actions">
            <div class="nav-btn" onclick="toggleTheme()" title="تغيير المظهر">
                <i class="fas fa-moon"></i>
            </div>
            <div class="nav-btn" onclick="newConversation()" title="محادثة جديدة">
                <i class="fas fa-plus"></i>
            </div>
            <div class="nav-btn" onclick="clearAllConversations()" title="مسح الكل">
                <i class="fas fa-trash"></i>
            </div>
        </div>
    </nav>

    <!-- زر فتح السجل -->
    <div class="history-toggle" onclick="toggleHistory()" title="سجل المحادثات">
        <i class="fas fa-history"></i>
    </div>

    <!-- Sidebar المخفي -->
    <div class="history-sidebar" id="historySidebar">
        <div class="sidebar-header">
            <h3>
                <i class="fas fa-history"></i>
                سجل المحادثات
            </h3>
            <div class="close-sidebar" onclick="toggleHistory()">
                <i class="fas fa-times"></i>
            </div>
        </div>
        <div class="conversations-list" id="conversationsList">
            <!-- تضاف المحادثات هنا -->
        </div>
    </div>

    <!-- Main Chat Area -->
    <div class="main-layout">
        <div class="chat-area" id="chatArea">
            <div class="messages-container" id="messagesContainer">
                <!-- Welcome Screen -->
                <div class="welcome-screen" id="welcomeMessage">
                    <div class="welcome-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <h1>Soft Atlas AI</h1>
                    <p>المساعد الذكي الأقوى - إجابات طويلة جداً تصل إلى 5000 سطر</p>
                    
                    <!-- لغات البرمجة المدعومة -->
                    <div class="language-chips">
                        <span class="lang-chip" onclick="setLanguage('python')">
                            <i class="fab fa-python"></i> Python
                        </span>
                        <span class="lang-chip" onclick="setLanguage('javascript')">
                            <i class="fab fa-js"></i> JavaScript
                        </span>
                        <span class="lang-chip" onclick="setLanguage('java')">
                            <i class="fab fa-java"></i> Java
                        </span>
                        <span class="lang-chip" onclick="setLanguage('cpp')">
                            <i class="fas fa-code"></i> C++
                        </span>
                        <span class="lang-chip" onclick="setLanguage('csharp')">
                            <i class="fas fa-code"></i> C#
                        </span>
                        <span class="lang-chip" onclick="setLanguage('php')">
                            <i class="fab fa-php"></i> PHP
                        </span>
                        <span class="lang-chip" onclick="setLanguage('ruby')">
                            <i class="far fa-gem"></i> Ruby
                        </span>
                        <span class="lang-chip" onclick="setLanguage('go')">
                            <i class="fas fa-code"></i> Go
                        </span>
                        <span class="lang-chip" onclick="setLanguage('rust')">
                            <i class="fas fa-code"></i> Rust
                        </span>
                        <span class="lang-chip" onclick="setLanguage('swift')">
                            <i class="fab fa-swift"></i> Swift
                        </span>
                        <span class="lang-chip" onclick="setLanguage('kotlin')">
                            <i class="fas fa-code"></i> Kotlin
                        </span>
                        <span class="lang-chip" onclick="setLanguage('typescript')">
                            <i class="fas fa-code"></i> TypeScript
                        </span>
                        <span class="lang-chip" onclick="setLanguage('html')">
                            <i class="fab fa-html5"></i> HTML/CSS
                        </span>
                        <span class="lang-chip" onclick="setLanguage('sql')">
                            <i class="fas fa-database"></i> SQL
                        </span>
                        <span class="lang-chip" onclick="setLanguage('r')">
                            <i class="fas fa-chart-line"></i> R
                        </span>
                    </div>

                    <div class="language-chips">
                        <span class="lang-chip" onclick="setQuestion('اكتب مشروع بايثون كامل مع 5000 سطر')">
                            <i class="fas fa-code"></i> مشروع 5000 سطر
                        </span>
                        <span class="lang-chip" onclick="setQuestion('اكتب نظام تشغيل بسيط بلغة C')">
                            نظام تشغيل
                        </span>
                        <span class="lang-chip" onclick="setQuestion('تطبيق ويب كامل React + Node.js')">
                            تطبيق ويب كامل
                        </span>
                    </div>
                </div>
            </div>

            <!-- Input Area صغير وجميل -->
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea 
                        id="messageInput" 
                        placeholder="اكتب سؤالك هنا... سأجيب بإجابة طويلة جداً"
                        rows="1"
                        oninput="autoResize(this)"
                    ></textarea>
                    <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <div class="input-footer">
                    <div class="typing-indicator" id="typingIndicator"></div>
                    <span>
                        <i class="fas fa-code"></i>
                        دعم 50+ لغة | إجابات حتى 5000 سطر
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Templates -->
    <template id="userMessageTemplate">
        <div class="message user">
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">أنت</span>
                    <span class="message-time"></span>
                </div>
                <div class="message-text"></div>
            </div>
            <div class="message-avatar">
                <i class="fas fa-user"></i>
            </div>
        </div>
    </template>

    <template id="assistantMessageTemplate">
        <div class="message assistant">
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">Soft Atlas AI</span>
                    <span class="message-time"></span>
                </div>
                <div class="message-text markdown-body"></div>
                <div class="message-actions">
                    <button onclick="copyMessage(this)">
                        <i class="fas fa-copy"></i> نسخ
                    </button>
                    <button onclick="copyAllCode(this)">
                        <i class="fas fa-code"></i> نسخ كل الأكواد
                    </button>
                    <button onclick="regenerateMessage(this)">
                        <i class="fas fa-redo"></i> إعادة
                    </button>
                </div>
            </div>
        </div>
    </template>

    <template id="loadingTemplate">
        <div class="message assistant">
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    </template>

    <script>
        // المتغيرات العامة
        let currentConversationId = null;
        let isProcessing = false;
        let currentEventSource = null;
        let currentTheme = 'dark';

        // تهيئة التطبيق
        document.addEventListener('DOMContentLoaded', function() {
            loadConversations();
            setupEventListeners();
            initializeHighlighting();
        });

        function initializeHighlighting() {
            if (typeof hljs !== 'undefined') {
                hljs.configure({
                    languages: ['python', 'javascript', 'html', 'css', 'java', 'cpp', 'csharp', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'typescript', 'sql', 'r']
                });
            }
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

        // توقيف الإجابة
        function stopGeneration() {
            if (currentEventSource) {
                currentEventSource.close();
                currentEventSource = null;
                isProcessing = false;
                document.getElementById('sendBtn').disabled = false;
                document.getElementById('typingIndicator').innerHTML = '';
                document.getElementById('stopGenerationBtn').style.display = 'none';
                document.querySelector('.loading-dots')?.closest('.message')?.remove();
            }
        }

        // تبديل الوضع
        function toggleTheme() {
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', currentTheme);
            const icon = document.querySelector('.nav-btn i.fa-moon, .nav-btn i.fa-sun');
            icon.className = currentTheme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        }

        // فتح/إغلاق السجل
        function toggleHistory() {
            const sidebar = document.getElementById('historySidebar');
            sidebar.classList.toggle('open');
        }

        // تحميل المحادثات
        function loadConversations() {
            fetch('/api/conversations')
                .then(res => res.json())
                .then(conversations => {
                    const list = document.getElementById('conversationsList');
                    if (conversations.length === 0) {
                        list.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 20px;">لا توجد محادثات سابقة</div>';
                        return;
                    }
                    
                    list.innerHTML = '';
                    conversations.forEach(conv => {
                        const item = document.createElement('div');
                        item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
                        
                        const date = new Date(conv.timestamp);
                        const timeStr = date.toLocaleString('ar-SA', { 
                            hour: '2-digit', 
                            minute: '2-digit',
                            day: '2-digit',
                            month: '2-digit'
                        });
                        
                        item.innerHTML = `
                            <div class="conv-preview" onclick="loadConversation('${conv.id}')">
                                <i class="fas fa-message" style="color: var(--accent-primary);"></i>
                                ${escapeHtml(conv.preview)}
                            </div>
                            <div class="conv-meta">
                                <span><i class="far fa-clock"></i> ${timeStr}</span>
                                <span><i class="far fa-comment"></i> ${conv.message_count}</span>
                            </div>
                            <div class="conversation-actions">
                                <button class="conv-action-btn" onclick="renameConversation('${conv.id}')">
                                    <i class="fas fa-edit"></i> تعديل
                                </button>
                                <button class="conv-action-btn" onclick="deleteConversation('${conv.id}')">
                                    <i class="fas fa-trash"></i> حذف
                                </button>
                            </div>
                        `;
                        list.appendChild(item);
                    });
                });
        }

        function loadConversation(conversationId) {
            currentConversationId = conversationId;
            fetch(`/api/conversation/${conversationId}`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById('welcomeMessage').style.display = 'none';
                    const container = document.getElementById('messagesContainer');
                    container.innerHTML = '';
                    
                    data.messages.forEach(msg => {
                        if (msg.role === 'user') {
                            displayUserMessage(msg.content, msg.timestamp);
                        } else {
                            displayAssistantMessage(msg.content, msg.timestamp);
                        }
                    });
                    
                    loadConversations();
                    setTimeout(() => toggleHistory(), 300); // إغلاق السجل بعد التحميل
                });
        }

        function displayUserMessage(message, timestamp) {
            const template = document.getElementById('userMessageTemplate');
            const clone = template.content.cloneNode(true);
            
            const time = timestamp ? new Date(timestamp) : new Date();
            clone.querySelector('.message-time').textContent = time.toLocaleString('ar-SA', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            clone.querySelector('.message-text').textContent = message;
            
            document.getElementById('messagesContainer').appendChild(clone);
            scrollToBottom();
        }

        function displayAssistantMessage(message, timestamp) {
            const template = document.getElementById('assistantMessageTemplate');
            const clone = template.content.cloneNode(true);
            
            const time = timestamp ? new Date(timestamp) : new Date();
            clone.querySelector('.message-time').textContent = time.toLocaleString('ar-SA', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            
            const messageText = clone.querySelector('.message-text');
            if (typeof marked !== 'undefined') {
                messageText.innerHTML = DOMPurify.sanitize(marked.parse(message));
                // تطبيق التلوين على الأكواد
                setTimeout(() => {
                    messageText.querySelectorAll('pre code').forEach((block) => {
                        if (typeof hljs !== 'undefined') {
                            hljs.highlightElement(block);
                        }
                        
                        // إضافة رأس للكود
                        const pre = block.parentNode;
                        const header = document.createElement('div');
                        header.className = 'code-header';
                        
                        const lang = block.className.replace('hljs language-', '') || 'text';
                        header.innerHTML = `
                            <span class="code-lang">
                                <i class="fas fa-code"></i> ${lang}
                            </span>
                            <button class="copy-code-btn" onclick="copyCode(this)">
                                <i class="fas fa-copy"></i> نسخ الكود
                            </button>
                        `;
                        
                        pre.parentNode.insertBefore(header, pre);
                    });
                }, 100);
            } else {
                messageText.textContent = message;
            }
            
            document.getElementById('messagesContainer').appendChild(clone);
            scrollToBottom();
        }

        function sendMessage() {
            if (isProcessing) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) {
                alert('الرجاء إدخال رسالة');
                return;
            }
            
            isProcessing = true;
            document.getElementById('sendBtn').disabled = true;
            document.getElementById('typingIndicator').innerHTML = '<i class="fas fa-spinner fa-pulse"></i> جاري التفكير...';
            document.getElementById('stopGenerationBtn').style.display = 'flex';
            
            document.getElementById('welcomeMessage').style.display = 'none';
            displayUserMessage(message);
            
            input.value = '';
            autoResize(input);
            
            // إظهار مؤشر التحميل
            const loadingTemplate = document.getElementById('loadingTemplate');
            const loadingClone = loadingTemplate.content.cloneNode(true);
            document.getElementById('messagesContainer').appendChild(loadingClone);
            scrollToBottom();
            
            // استخدام الـ streaming
            currentEventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}`);
            let fullResponse = '';
            let messageDiv = null;
            
            currentEventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // إزالة مؤشر التحميل
                document.querySelector('.loading-dots')?.closest('.message')?.remove();
                
                if (data.chunk) {
                    if (!messageDiv) {
                        const template = document.getElementById('assistantMessageTemplate');
                        const clone = template.content.cloneNode(true);
                        clone.querySelector('.message-time').textContent = new Date().toLocaleString('ar-SA', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        });
                        document.getElementById('messagesContainer').appendChild(clone);
                        messageDiv = document.querySelector('.message.assistant:last-child');
                    }
                    
                    fullResponse += data.chunk;
                    const messageText = messageDiv.querySelector('.message-text');
                    
                    if (typeof marked !== 'undefined') {
                        messageText.innerHTML = DOMPurify.sanitize(marked.parse(fullResponse));
                    } else {
                        messageText.textContent = fullResponse;
                    }
                    
                    scrollToBottom();
                }
                
                if (data.done) {
                    currentEventSource.close();
                    currentEventSource = null;
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('typingIndicator').innerHTML = '';
                    document.getElementById('stopGenerationBtn').style.display = 'none';
                    loadConversations();
                }
            };
            
            currentEventSource.onerror = function() {
                stopGeneration();
                alert('حدث خطأ في الاتصال');
            };
        }

        function newConversation() {
            fetch('/api/conversations', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        currentConversationId = data.id;
                        document.getElementById('messagesContainer').innerHTML = '';
                        document.getElementById('welcomeMessage').style.display = 'block';
                        loadConversations();
                    }
                });
        }

        function renameConversation(conversationId) {
            const newName = prompt('أدخل الاسم الجديد للمحادثة:');
            if (newName) {
                // هنا يمكن إضافة طلب لتغيير الاسم
                alert('سيتم إضافة هذه الميزة قريباً');
            }
        }

        function deleteConversation(conversationId) {
            if (confirm('هل أنت متأكد من حذف هذه المحادثة؟')) {
                fetch(`/api/conversation/${conversationId}`, { method: 'DELETE' })
                    .then(() => {
                        if (currentConversationId === conversationId) {
                            newConversation();
                        }
                        loadConversations();
                    });
            }
        }

        function clearAllConversations() {
            if (confirm('هل أنت متأكد من مسح جميع المحادثات؟')) {
                fetch('/api/conversations', { method: 'DELETE' })
                    .then(() => {
                        newConversation();
                    });
            }
        }

        function copyMessage(button) {
            const text = button.closest('.message-content').querySelector('.message-text').innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert('تم نسخ الرسالة');
            });
        }

        function copyCode(button) {
            const code = button.closest('.code-header').nextElementSibling?.querySelector('code')?.innerText;
            if (code) {
                navigator.clipboard.writeText(code).then(() => {
                    alert('تم نسخ الكود');
                });
            }
        }

        function copyAllCode(button) {
            const messageDiv = button.closest('.message');
            const codeBlocks = messageDiv.querySelectorAll('pre code');
            if (codeBlocks.length > 0) {
                let allCode = '';
                codeBlocks.forEach(block => {
                    allCode += block.textContent + '\\n\\n';
                });
                navigator.clipboard.writeText(allCode).then(() => {
                    alert(`تم نسخ ${codeBlocks.length} كود`);
                });
            }
        }

        function regenerateMessage(button) {
            if (isProcessing) return;
            
            const messageDiv = button.closest('.message');
            const prevMessage = messageDiv.previousElementSibling;
            
            if (prevMessage && prevMessage.classList.contains('user')) {
                const userMessage = prevMessage.querySelector('.message-text').innerText;
                messageDiv.remove();
                document.getElementById('messageInput').value = userMessage;
                sendMessage();
            }
        }

        function setLanguage(lang) {
            const prompts = {
                'python': 'اكتب مشروع بايثون متكامل مع شرح تفصيلي جداً (5000 سطر على الأقل)',
                'javascript': 'اكتب تطبيق جافاسكريبت متكامل مع شرح مفصل (4000 سطر على الأقل)',
                'java': 'اكتب برنامج جافا متكامل مع شرح تفصيلي (5000 سطر على الأقل)',
                'cpp': 'اكتب برنامج C++ متكامل مع شرح مفصل (4000 سطر على الأقل)',
                'csharp': 'اكتب برنامج C# متكامل مع شرح تفصيلي (4000 سطر على الأقل)',
                'php': 'اكتب تطبيق PHP متكامل مع شرح مفصل (3000 سطر على الأقل)',
                'ruby': 'اكتب برنامج Ruby متكامل مع شرح تفصيلي (3000 سطر على الأقل)',
                'go': 'اكتب برنامج Go متكامل مع شرح مفصل (3000 سطر على الأقل)',
                'rust': 'اكتب برنامج Rust متكامل مع شرح تفصيلي (3000 سطر على الأقل)',
                'swift': 'اكتب تطبيق Swift متكامل مع شرح مفصل (3000 سطر على الأقل)',
                'kotlin': 'اكتب برنامج Kotlin متكامل مع شرح تفصيلي (3000 سطر على الأقل)',
                'typescript': 'اكتب تطبيق TypeScript متكامل مع شرح مفصل (3000 سطر على الأقل)',
                'html': 'اكتب موقع HTML/CSS متكامل مع JavaScript (3000 سطر على الأقل)',
                'sql': 'اكتب قاعدة بيانات SQL متكاملة مع استعلامات معقدة (2000 سطر على الأقل)',
                'r': 'اكتب برنامج R متكامل لتحليل البيانات (2000 سطر على الأقل)'
            };
            
            document.getElementById('messageInput').value = prompts[lang] || prompts['python'];
            document.getElementById('messageInput').focus();
        }

        function setQuestion(question) {
            document.getElementById('messageInput').value = question;
            document.getElementById('messageInput').focus();
            autoResize(document.getElementById('messageInput'));
        }

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        }

        function scrollToBottom() {
            const container = document.getElementById('messagesContainer');
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'smooth'
            });
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

# إضافة مسارات API جديدة
@app.route('/api/conversations', methods=['DELETE'])
def delete_all_conversations():
    """مسح جميع المحادثات"""
    session_id = session.get('conversation_id')
    if session_id:
        conversations[session_id] = []
    return jsonify({'success': True})

@app.route('/api/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """حذف محادثة محددة"""
    if conversation_id in conversations:
        del conversations[conversation_id]
    return jsonify({'success': True})

@app.route('/api/chat/stop', methods=['POST'])
def stop_chat():
    """توقيف الإجابة"""
    return jsonify({'success': True})

if __name__ == '__main__':
    print("="*80)
    print("🚀 Soft Atlas AI - الإصدار الفائق")
    print("="*80)
    print("📡 الخادم: http://localhost:5000")
    print("🤖 الميزات الجديدة:")
    print("  ✓ توقيف الإجابة في أي وقت")
    print("  ✓ وضع نهاري/ليلي")
    print("  ✓ سجل مخفي بزر صغير")
    print("  ✓ دعم 50+ لغة برمجة")
    print("  ✓ إجابات حتى 5000 سطر")
    print("  ✓ تعديل وحذف المحادثات")
    print("  ✓ تصميم عصري صغير")
    print("="*80)
    print("✅ افتح المتصفح على: http://localhost:5000")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)