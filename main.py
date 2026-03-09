from flask import Flask, render_template_string, request, jsonify, session, Response
import requests
import json
import uuid
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import re
from threading import Thread, Lock
import queue

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 30  # شهر

# إعدادات NVIDIA API
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-122b-a10b"

# تخزين المحادثات مع قفل للتزامن
conversations = {}
conversations_lock = Lock()
active_streams = {}  # لتتبع التدفقات النشطة وإمكانية إيقافها

def generate_long_response(messages, stream_id, stop_flag):
    """توليد ردود طويلة جداً مع إمكانية الإيقاف"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    system_prompt = {
        "role": "system",
        "content": """أنت Soft Atlas AI، مساعد ذكي فائق التطور باللغة العربية الفصحى.

تعليمات مهمة جداً:
1. قدم إجابات موسوعية شاملة جداً (5000-10000 كلمة للمواضيع المعقدة)
2. للمواضيع البرمجية:
   - قدم كود كامل ومتشغل يصل لـ 5000 سطر إذا لزم الأمر
   - اشرح كل جزء بالتفصيل الممل
   - وضح جميع الدوال والكلاسات
   - أضف تعليقات توضيحية على كل سطر
   - قدم 10 أمثلة عملية على الأقل
3. قسّم الإجابات الطويلة إلى أقسام واضحة
4. استخدم تنسيق Markdown متقدم مع جداول ورسوم بيانية نصية
5. قدم أمثلة بلغات برمجة متعددة (Python, JavaScript, Java, C++, C#, PHP, Ruby, Go, Rust, Swift, Kotlin, TypeScript)
6. للمشاريع الكبيرة، قدم هيكل المشروع كاملاً
7. اشرح أفضل الممارسات والأخطاء الشائعة
8. قدم تحسينات أداء وأمان
9. أضف روابط لمصادر تعلم إضافية
10. استخدم اللغة العربية الفصحى 100%"""
    }
    
    full_messages = [system_prompt] + messages[-20:]  # سياق أكبر
    
    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "max_tokens": 32768,  # أقصى طول
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
                # التحقق من طلب الإيقاف
                if stop_flag and stop_flag.get('stopped', False):
                    yield "**[تم إيقاف التوليد]**"
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
            yield f"⚠️ خطأ في الاتصال: {response.status_code}"
            
    except Exception as e:
        yield f"❌ حدث خطأ: {str(e)}، جاري إعادة المحاولة..."

@app.route('/')
def index():
    """الصفحة الرئيسية الفائقة"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
        with conversations_lock:
            conversations[session['conversation_id']] = []
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soft Atlas AI Pro - المساعد الفائق</title>
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
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #8b5cf6;
            --accent: #ec4899;
            --dark-bg: #0f172a;
            --darker-bg: #020617;
            --light-bg: #f8fafc;
            --dark-text: #f1f5f9;
            --light-text: #0f172a;
            --glass: rgba(255, 255, 255, 0.03);
            --glass-hover: rgba(255, 255, 255, 0.05);
            --border: rgba(255, 255, 255, 0.1);
        }

        [data-theme="light"] {
            --dark-bg: #f8fafc;
            --darker-bg: #f1f5f9;
            --dark-text: #0f172a;
            --light-text: #f8fafc;
            --glass: rgba(0, 0, 0, 0.03);
            --glass-hover: rgba(0, 0, 0, 0.05);
            --border: rgba(0, 0, 0, 0.1);
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--darker-bg);
            color: var(--dark-text);
            transition: all 0.3s ease;
            height: 100vh;
            overflow: hidden;
        }

        .app {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Navbar صغير وجميل */
        .navbar {
            background: var(--glass);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            padding: 0.5rem 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 60px;
        }

        .nav-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .menu-toggle {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--dark-text);
            cursor: pointer;
            transition: all 0.3s;
        }

        .menu-toggle:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .logo-icon {
            width: 35px;
            height: 35px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .logo-icon i {
            color: white;
            font-size: 18px;
        }

        .logo-text {
            font-weight: 700;
            font-size: 1.2rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-center {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--glass);
            padding: 0.25rem;
            border-radius: 30px;
            border: 1px solid var(--border);
        }

        .nav-tab {
            padding: 0.4rem 1.2rem;
            border-radius: 30px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s;
            color: var(--dark-text);
            opacity: 0.7;
        }

        .nav-tab:hover {
            opacity: 1;
            background: var(--glass-hover);
        }

        .nav-tab.active {
            background: var(--primary);
            color: white;
            opacity: 1;
        }

        .nav-right {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .theme-toggle {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--dark-text);
            cursor: pointer;
            transition: all 0.3s;
        }

        .theme-toggle:hover {
            background: var(--primary);
            color: white;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.85rem;
            padding: 0.4rem 1rem;
            background: var(--glass);
            border-radius: 30px;
            border: 1px solid var(--border);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.7; }
        }

        /* Main layout */
        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        /* Sidebar مخفي افتراضياً */
        .sidebar {
            width: 280px;
            background: var(--glass);
            backdrop-filter: blur(10px);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease;
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            z-index: 100;
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
        }

        .close-sidebar {
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .close-sidebar:hover {
            background: var(--primary);
            color: white;
        }

        .conversations-list {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }

        .conversation-item {
            padding: 1rem;
            background: var(--glass);
            border-radius: 12px;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid transparent;
        }

        .conversation-item:hover {
            border-color: var(--primary);
            transform: translateX(-5px);
        }

        .conversation-item.active {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2));
            border-color: var(--primary);
        }

        .conv-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }

        .conv-title {
            font-weight: 600;
            font-size: 0.95rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 150px;
        }

        .conv-menu {
            position: relative;
        }

        .conv-menu-btn {
            background: none;
            border: none;
            color: var(--dark-text);
            cursor: pointer;
            padding: 0.25rem;
            opacity: 0.7;
        }

        .conv-menu-btn:hover {
            opacity: 1;
        }

        .conv-menu-dropdown {
            position: absolute;
            left: 0;
            top: 100%;
            background: var(--darker-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.25rem;
            min-width: 120px;
            display: none;
            z-index: 10;
        }

        .conv-menu:hover .conv-menu-dropdown {
            display: block;
        }

        .menu-item {
            padding: 0.5rem;
            font-size: 0.85rem;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .menu-item:hover {
            background: var(--primary);
            color: white;
        }

        .menu-item.delete:hover {
            background: #ef4444;
        }

        .conv-preview {
            font-size: 0.8rem;
            color: var(--dark-text);
            opacity: 0.7;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conv-date {
            font-size: 0.7rem;
            color: var(--dark-text);
            opacity: 0.5;
            margin-top: 0.25rem;
        }

        /* Chat area الرئيسي */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: var(--darker-bg);
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            scroll-behavior: smooth;
        }

        /* تنسيق الرسائل */
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
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, var(--accent), #f43f5e);
        }

        .message.assistant .message-avatar {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
        }

        .message-content {
            flex: 1;
            max-width: 80%;
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
            opacity: 0.7;
        }

        .message.user .message-header {
            flex-direction: row-reverse;
        }

        .message-text {
            background: var(--glass);
            padding: 1.25rem;
            border-radius: 16px;
            border: 1px solid var(--border);
            line-height: 1.8;
            overflow-x: auto;
        }

        .message.user .message-text {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border: none;
        }

        /* تنسيق الكود */
        .message-text pre {
            background: var(--darker-bg) !important;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid var(--border);
            position: relative;
            max-height: 500px;
            overflow: auto;
        }

        .message-text code {
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
        }

        .copy-btn {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: var(--glass);
            border: 1px solid var(--border);
            color: var(--dark-text);
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s;
        }

        pre:hover .copy-btn {
            opacity: 1;
        }

        .message-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        .action-btn {
            background: var(--glass);
            border: 1px solid var(--border);
            color: var(--dark-text);
            padding: 0.25rem 1rem;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .action-btn:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .action-btn.stop {
            background: #ef4444;
            color: white;
            border-color: #ef4444;
        }

        /* Input area صغير وجميل */
        .input-container {
            padding: 1rem 2rem;
            background: var(--glass);
            border-top: 1px solid var(--border);
        }

        .input-wrapper {
            display: flex;
            gap: 1rem;
            align-items: flex-end;
            background: var(--darker-bg);
            border-radius: 20px;
            padding: 0.5rem;
            border: 1px solid var(--border);
            transition: all 0.3s;
        }

        .input-wrapper:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            padding: 0.75rem 1rem;
            color: var(--dark-text);
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
            width: 40px;
            height: 40px;
            border: none;
            border-radius: 12px;
            background: var(--glass);
            color: var(--dark-text);
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid var(--border);
        }

        .input-btn:hover:not(:disabled) {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .input-btn.send {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border: none;
        }

        .input-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 0.5rem;
            font-size: 0.75rem;
            opacity: 0.5;
        }

        /* Loading indicator */
        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 0.5rem;
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
            animation: typingBounce 1s infinite;
        }

        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typingBounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        /* Responsive */
        @media (max-width: 768px) {
            .nav-center {
                display: none;
            }
            
            .sidebar {
                width: 100%;
            }
            
            .message-content {
                max-width: 100%;
            }
            
            .input-container {
                padding: 1rem;
            }
        }
    </style>
</head>
<body data-theme="dark">
    <div class="app">
        <!-- Navbar صغير وجميل -->
        <div class="navbar">
            <div class="nav-left">
                <div class="menu-toggle" onclick="toggleSidebar()">
                    <i class="fas fa-bars"></i>
                </div>
                <div class="logo">
                    <div class="logo-icon">
                        <i class="fas fa-brain"></i>
                    </div>
                    <span class="logo-text">Soft Atlas Pro</span>
                </div>
            </div>
            
            <div class="nav-center">
                <div class="nav-tab active" onclick="switchTab('chat')">
                    <i class="fas fa-comment"></i> محادثة
                </div>
                <div class="nav-tab" onclick="switchTab('code')">
                    <i class="fas fa-code"></i> برمجة
                </div>
                <div class="nav-tab" onclick="switchTab('analyze')">
                    <i class="fas fa-chart-line"></i> تحليل
                </div>
            </div>
            
            <div class="nav-right">
                <div class="status">
                    <span class="status-dot"></span>
                    <span>متصل</span>
                </div>
                <div class="theme-toggle" onclick="toggleTheme()">
                    <i class="fas fa-moon"></i>
                </div>
            </div>
        </div>
        
        <!-- Main content -->
        <div class="main">
            <!-- Sidebar للمحادثات المسجلة -->
            <div class="sidebar" id="sidebar">
                <div class="sidebar-header">
                    <h3><i class="fas fa-history"></i> المحادثات</h3>
                    <div class="close-sidebar" onclick="toggleSidebar()">
                        <i class="fas fa-times"></i>
                    </div>
                </div>
                <div class="sidebar-header" style="padding-top: 0;">
                    <button class="action-btn" onclick="newConversation()" style="width: 100%;">
                        <i class="fas fa-plus"></i> محادثة جديدة
                    </button>
                </div>
                <div class="conversations-list" id="conversationsList">
                    <!-- تضاف المحادثات هنا -->
                </div>
            </div>
            
            <!-- Chat area -->
            <div class="chat-area">
                <div class="messages-container" id="messagesContainer">
                    <!-- رسالة الترحيب -->
                    <div style="text-align: center; padding: 3rem; opacity: 0.7;">
                        <i class="fas fa-robot" style="font-size: 4rem; margin-bottom: 1rem;"></i>
                        <h2>مرحباً بك في Soft Atlas Pro</h2>
                        <p>المساعد الذكي الفائق - أجوبة طويلة جداً، أكود حتى 5000 سطر</p>
                    </div>
                </div>
                
                <!-- Input area صغير وجميل -->
                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea 
                            id="messageInput" 
                            placeholder="اكتب سؤالك هنا... سأجيب بإجابة شاملة جداً"
                            rows="1"
                            oninput="autoResize(this)"
                        ></textarea>
                        <div class="input-actions">
                            <button class="input-btn" onclick="attachFile()" title="إرفاق ملف">
                                <i class="fas fa-paperclip"></i>
                            </button>
                            <button class="input-btn stop" id="stopBtn" onclick="stopGeneration()" style="display: none;">
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
        let currentTab = 'chat';
        
        // تهيئة
        document.addEventListener('DOMContentLoaded', function() {
            loadConversations();
            setupEventListeners();
        });
        
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
            document.body.setAttribute('data-theme', currentTheme);
            const icon = document.querySelector('.theme-toggle i');
            icon.className = currentTheme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        }
        
        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            event.currentTarget.classList.add('active');
            
            const input = document.getElementById('messageInput');
            if (tab === 'code') {
                input.placeholder = 'اكتب سؤالك البرمجي... سأقدم كود كامل يصل لـ 5000 سطر';
            } else {
                input.placeholder = 'اكتب سؤالك هنا... سأجيب بإجابة شاملة جداً';
            }
        }
        
        function loadConversations() {
            fetch('/api/conversations')
                .then(res => res.json())
                .then(conversations => {
                    const list = document.getElementById('conversationsList');
                    if (conversations.length === 0) {
                        list.innerHTML = '<div style="text-align: center; padding: 1rem; opacity: 0.7;">لا توجد محادثات سابقة</div>';
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
            
            const date = new Date(conv.timestamp);
            const timeStr = date.toLocaleString('ar-SA', { 
                hour: '2-digit', 
                minute: '2-digit',
                day: '2-digit',
                month: '2-digit'
            });
            
            div.innerHTML = `
                <div class="conv-header">
                    <span class="conv-title">${escapeHtml(conv.preview)}</span>
                    <div class="conv-menu">
                        <button class="conv-menu-btn"><i class="fas fa-ellipsis-v"></i></button>
                        <div class="conv-menu-dropdown">
                            <div class="menu-item" onclick="renameConversation('${conv.id}')">
                                <i class="fas fa-edit"></i> تعديل الاسم
                            </div>
                            <div class="menu-item delete" onclick="deleteConversation('${conv.id}')">
                                <i class="fas fa-trash"></i> حذف
                            </div>
                        </div>
                    </div>
                </div>
                <div class="conv-preview">${escapeHtml(conv.preview)}</div>
                <div class="conv-date"><i class="far fa-clock"></i> ${timeStr}</div>
            `;
            
            div.onclick = (e) => {
                if (!e.target.closest('.conv-menu')) {
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
                    
                    data.messages.forEach(msg => {
                        if (msg.role === 'user') {
                            displayUserMessage(msg.content, msg.timestamp);
                        } else {
                            displayAssistantMessage(msg.content, msg.timestamp);
                        }
                    });
                    
                    // تحديث النشط
                    document.querySelectorAll('.conversation-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    const activeItem = Array.from(document.querySelectorAll('.conversation-item')).find(
                        item => item.innerHTML.includes(conversationId)
                    );
                    if (activeItem) activeItem.classList.add('active');
                });
        }
        
        function newConversation() {
            fetch('/api/conversations', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        currentConversationId = data.id;
                        document.getElementById('messagesContainer').innerHTML = `
                            <div style="text-align: center; padding: 3rem; opacity: 0.7;">
                                <i class="fas fa-robot" style="font-size: 4rem; margin-bottom: 1rem;"></i>
                                <h2>محادثة جديدة</h2>
                                <p>كيف يمكنني مساعدتك اليوم؟</p>
                            </div>
                        `;
                        loadConversations();
                    }
                });
        }
        
        function deleteConversation(conversationId) {
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
            event.stopPropagation();
        }
        
        function renameConversation(conversationId) {
            const newName = prompt('أدخل الاسم الجديد للمحادثة:');
            if (newName) {
                fetch(`/api/conversation/${conversationId}/rename`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: newName })
                }).then(() => loadConversations());
            }
            event.stopPropagation();
        }
        
        function displayUserMessage(message, timestamp) {
            const container = document.getElementById('messagesContainer');
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
                        <span class="sender-name">Soft Atlas Pro</span>
                        <span>${timeStr}</span>
                    </div>
                    <div class="message-text">${formattedMessage}</div>
                    <div class="message-actions">
                        <button class="action-btn" onclick="copyMessage(this)">
                            <i class="fas fa-copy"></i> نسخ
                        </button>
                        <button class="action-btn" onclick="regenerateMessage(this)">
                            <i class="fas fa-redo"></i> إعادة
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
                
                // إضافة زر نسخ الكود
                const pre = block.parentNode;
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-btn';
                copyBtn.innerHTML = '<i class="fas fa-copy"></i> نسخ الكود';
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(block.textContent);
                    alert('تم نسخ الكود!');
                };
                pre.appendChild(copyBtn);
            });
            
            scrollToBottom();
        }
        
        function sendMessage() {
            if (isProcessing) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // إزالة رسالة الترحيب
            document.querySelector('.messages-container > div[style*="text-align: center"]')?.remove();
            
            displayUserMessage(message);
            input.value = '';
            autoResize(input);
            
            // إظهار مؤشر الكتابة
            showTypingIndicator();
            
            // إنشاء stream ID جديد
            currentStreamId = Date.now().toString();
            
            // إظهار زر الإيقاف
            document.getElementById('stopBtn').style.display = 'block';
            
            // بدء التدفق
            const eventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}&stream_id=${currentStreamId}`);
            let fullResponse = '';
            let assistantMessage = null;
            
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // إخفاء مؤشر الكتابة
                hideTypingIndicator();
                
                if (data.chunk) {
                    if (!assistantMessage) {
                        assistantMessage = document.createElement('div');
                        assistantMessage.className = 'message assistant';
                        assistantMessage.innerHTML = `
                            <div class="message-avatar">
                                <i class="fas fa-robot"></i>
                            </div>
                            <div class="message-content">
                                <div class="message-header">
                                    <span class="sender-name">Soft Atlas Pro</span>
                                    <span>${new Date().toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit' })}</span>
                                </div>
                                <div class="message-text"></div>
                            </div>
                        `;
                        document.getElementById('messagesContainer').appendChild(assistantMessage);
                    }
                    
                    fullResponse += data.chunk;
                    assistantMessage.querySelector('.message-text').innerHTML = marked.parse(fullResponse);
                    
                    // تحديث تلوين الكود
                    assistantMessage.querySelectorAll('pre code').forEach(block => {
                        hljs.highlightElement(block);
                    });
                    
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
                
                // إظهار رسالة الخطأ
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
                });
            }
        }
        
        function showTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            indicator.innerHTML = `
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
                <span>Soft Atlas Pro يكتب...</span>
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
        
        function copyMessage(button) {
            const text = button.closest('.message-content').querySelector('.message-text').innerText;
            navigator.clipboard.writeText(text);
            alert('تم النسخ!');
        }
        
        function regenerateMessage(button) {
            const messageDiv = button.closest('.message');
            const prevMessage = messageDiv.previousElementSibling;
            
            if (prevMessage && prevMessage.classList.contains('user')) {
                const userMessage = prevMessage.querySelector('.message-text').innerText;
                messageDiv.remove();
                document.getElementById('messageInput').value = userMessage;
                sendMessage();
            }
        }
        
        function attachFile() {
            alert('قريباً: دعم رفع الملفات');
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
    """نقطة نهاية التدفق المحسنة للإجابات الطويلة"""
    message = request.args.get('message', '').strip()
    conversation_id = session.get('conversation_id')
    stream_id = request.args.get('stream_id', str(uuid.uuid4()))
    
    if not message:
        return jsonify({'error': 'الرجاء إدخال رسالة'}), 400
    
    # إنشاء flag للإيقاف
    stop_flag = {'stopped': False}
    active_streams[stream_id] = stop_flag
    
    def generate():
        try:
            # تخزين رسالة المستخدم
            user_message = {
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            }
            
            with conversations_lock:
                if conversation_id not in conversations:
                    conversations[conversation_id] = []
                conversations[conversation_id].append(user_message)
            
            # تحضير الرسائل
            messages_for_api = [
                {'role': msg['role'], 'content': msg['content']}
                for msg in conversations[conversation_id]
            ]
            
            full_response = ""
            
            # توليد الرد الطويل
            for chunk in generate_long_response(messages_for_api, stream_id, stop_flag):
                if stop_flag.get('stopped', False):
                    break
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # تخزين الرد الكامل
            if full_response and not stop_flag.get('stopped', False):
                assistant_message = {
                    'role': 'assistant',
                    'content': full_response,
                    'timestamp': datetime.now().isoformat()
                }
                with conversations_lock:
                    conversations[conversation_id].append(assistant_message)
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        finally:
            # تنظيف
            active_streams.pop(stream_id, None)
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/chat/stop', methods=['POST'])
def stop_chat():
    """إيقاف توليد الإجابة"""
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
    with conversations_lock:
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
    with conversations_lock:
        conversations[new_id] = []
    session['conversation_id'] = new_id
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """استرجاع محادثة محددة"""
    with conversations_lock:
        if conversation_id in conversations:
            return jsonify({'messages': conversations[conversation_id]})
    return jsonify({'messages': []})

@app.route('/api/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """حذف محادثة"""
    with conversations_lock:
        if conversation_id in conversations:
            del conversations[conversation_id]
            return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/conversation/<conversation_id>/rename', methods=['POST'])
def rename_conversation(conversation_id):
    """تغيير اسم المحادثة"""
    data = request.json
    new_name = data.get('name')
    
    with conversations_lock:
        if conversation_id in conversations and conversations[conversation_id]:
            # تعديل أول رسالة لتكون الاسم الجديد
            if conversations[conversation_id][0]['role'] == 'user':
                conversations[conversation_id][0]['content'] = new_name
    
    return jsonify({'success': True})

if __name__ == '__main__':
    print("="*80)
    print("🚀 Soft Atlas AI Pro - النسخة الفائقة")
    print("="*80)
    print("📡 الخادم: http://localhost:5000")
    print("🤖 الميزات الجديدة:")
    print("   • إجابات طويلة جداً (حتى 5000 سطر كود)")
    print("   • زر إيقاف التوليد")
    print("   • شريط جانبي مخفي للمحادثات")
    print("   • وضع داكن/نهاري")
    print("   • حذف وتعديل المحادثات")
    print("   • دعدة لغات برمجة")
    print("   • تصميم صغير وجميل")
    print("="*80)
    print("✅ تم حل مشكلة التوقف!")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
