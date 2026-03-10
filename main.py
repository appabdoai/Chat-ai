from flask import Flask, render_template_string, request, jsonify, session, Response
from openai import OpenAI
import json
import uuid
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import re

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 7  # أسبوع

# إعدادات NVIDIA API مع OpenAI client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

# نموذج Kimi K2 Thinking
MODEL_NAME = "moonshotai/kimi-k2-thinking"

# تخزين المحادثات (في الإنتاج استخدم قاعدة بيانات)
conversations = {}

def optimize_code_response(content):
    """تحسين عرض الأكواد البرمجية"""
    # اكتشاف كتل الأكواد وتحسين تنسيقها
    def replace_code_block(match):
        lang = match.group(1) or 'text'
        code = match.group(2)
        return f'<div class="code-block-wrapper"><div class="code-header"><span class="code-language">{lang}</span><button class="copy-code-btn" onclick="copyCode(this)"><i class="fas fa-copy"></i> نسخ</button></div><pre><code class="language-{lang}">{code}</code></pre></div>'
    
    # تحسين الأكواد المضمنة
    content = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', content)
    
    # تحسين كتل الأكواد
    content = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, content, flags=re.DOTALL)
    
    return content

def generate_stream_response(messages):
    """توليد رد متدفق محسن باستخدام Kimi K2 Thinking"""
    
    system_prompt = {
        "role": "system",
        "content": """أنت Abdo AI Pro، مساعد ذكي فائق التطور باللغة العربية الفصحى.

القواعد الأساسية:
1. قدم إجابات دقيقة وشاملة جداً
2. استخدم اللغة العربية الفصيحة السليمة 100%
3. للمواضيع البرمجية:
   - قدم شرحاً مفصلاً مع أمثلة عملية
   - وضح كل سطر من الكود
   - اشرح أفضل الممارسات
4. قسّم الإجابات إلى أقسام منظمة مع عناوين فرعية
5. استخدم النقاط والقوائم للتوضيح
6. قدم أمثلة واقعية وحديثة
7. اشرح المفاهيم الصعبة ببساطة مع تشبيهات
8. استخدم تنسيق Markdown"""
    }
    
    full_messages = [system_prompt] + messages[-50:]  # آخر 50 رسالة للسياق
    
    try:
        # استخدام OpenAI client مع Kimi K2 Thinking
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=full_messages,
            temperature=0.65,
            top_p=0.92,
            max_tokens=16384,
            stream=True
        )
        
        reasoning_buffer = ""
        
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            
            # معالجة المحتوى العادي
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                # تحسين عرض الأكواد في الوقت الفعلي
                if '```' in content:
                    content = optimize_code_response(content)
                yield content
                
    except Exception as e:
        error_msg = f"❌ حدث خطأ: {str(e)}"
        print(error_msg)
        yield error_msg

@app.route('/')
def index():
    """الصفحة الرئيسية المحسنة"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
        conversations[session['conversation_id']] = []
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Abdo AI Pro - مساعدك الذكي</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary: #7c3aed;
            --primary-dark: #6d28d9;
            --secondary: #c026d3;
            --accent: #e11d48;
            --dark: #020617;
            --darker: #000212;
            --light: #f8fafc;
            --gray: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --glass: rgba(255, 255, 255, 0.03);
            --glass-hover: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.05);
            --code-bg: #0d1117;
            --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--darker);
            color: var(--light);
            height: 100vh;
            overflow: hidden;
            position: relative;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 20%, rgba(124, 58, 237, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(192, 38, 211, 0.15) 0%, transparent 50%);
            pointer-events: none;
        }

        .app {
            height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
            z-index: 1;
        }

        /* Navbar */
        .navbar {
            background: rgba(2, 6, 23, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--glass-border);
            padding: 0.75rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        @media (max-width: 768px) {
            .navbar {
                padding: 0.75rem 1rem;
            }
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo {
            width: 40px;
            height: 40px;
            background: var(--gradient-1);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .logo i { font-size: 22px; color: white; }

        .brand-text {
            font-size: 1.4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        @media (max-width: 480px) {
            .brand-text {
                font-size: 1.2rem;
            }
        }

        .menu-btn {
            display: none;
            background: var(--glass);
            border: 1px solid var(--glass-border);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 12px;
            cursor: pointer;
        }

        @media (max-width: 768px) {
            .menu-btn {
                display: flex;
                align-items: center;
                justify-content: center;
            }
        }

        /* Main Layout */
        .main {
            display: flex;
            flex: 1;
            padding: 1rem;
            gap: 1rem;
            min-height: 0;
        }

        @media (max-width: 768px) {
            .main {
                padding: 0.75rem;
            }
        }

        /* Sidebar */
        .sidebar {
            width: 280px;
            background: rgba(2, 6, 23, 0.8);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
        }

        @media (max-width: 768px) {
            .sidebar {
                position: fixed;
                top: 70px;
                right: -100%;
                bottom: 0;
                width: 280px;
                z-index: 100;
                border-radius: 20px 0 0 20px;
                transition: right 0.3s ease;
            }

            .sidebar.active {
                right: 0;
            }
        }

        .new-chat-btn {
            margin: 1rem;
            padding: 1rem;
            background: var(--gradient-1);
            border: none;
            border-radius: 14px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.3s;
        }

        .new-chat-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(124, 58, 237, 0.4);
        }

        .conversations-list {
            flex: 1;
            overflow-y: auto;
            padding: 0 1rem;
        }

        .conversation-item {
            padding: 0.75rem;
            background: var(--glass);
            border-radius: 12px;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid transparent;
        }

        .conversation-item:hover {
            background: var(--glass-hover);
            border-color: var(--primary);
            transform: translateX(-5px);
        }

        .conversation-item.active {
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(192, 38, 211, 0.15));
            border-color: var(--primary);
        }

        /* Chat Area */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: rgba(2, 6, 23, 0.6);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            min-height: 0;
        }

        .chat-header {
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        @media (max-width: 768px) {
            .chat-header {
                padding: 0.75rem 1rem;
            }
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        @media (max-width: 768px) {
            .messages-container {
                padding: 1rem;
            }
        }

        /* Welcome Screen */
        .welcome-screen {
            text-align: center;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }

        @media (max-width: 768px) {
            .welcome-screen {
                padding: 1rem;
            }
        }

        .welcome-icon {
            width: 100px;
            height: 100px;
            margin: 0 auto 2rem;
            background: var(--gradient-1);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: float 3s ease infinite;
        }

        @media (max-width: 768px) {
            .welcome-icon {
                width: 80px;
                height: 80px;
                margin-bottom: 1.5rem;
            }
            
            .welcome-icon i {
                font-size: 40px;
            }
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .welcome-icon i { font-size: 50px; color: white; }

        .welcome-screen h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #fff, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        @media (max-width: 768px) {
            .welcome-screen h1 {
                font-size: 2rem;
            }
        }

        .suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            justify-content: center;
            margin: 2rem 0;
        }

        .suggestion-chip {
            background: var(--glass);
            padding: 0.75rem 1.5rem;
            border-radius: 30px;
            border: 1px solid var(--glass-border);
            color: white;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.95rem;
        }

        @media (max-width: 480px) {
            .suggestion-chip {
                padding: 0.5rem 1rem;
                font-size: 0.85rem;
            }
        }

        .suggestion-chip:hover {
            background: var(--gradient-1);
            transform: scale(1.05);
        }

        /* Messages */
        .message {
            display: flex;
            gap: 15px;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 768px) {
            .message {
                gap: 10px;
            }
        }

        .message.user { flex-direction: row-reverse; }

        .message-avatar {
            width: 45px;
            height: 45px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        @media (max-width: 768px) {
            .message-avatar {
                width: 35px;
                height: 35px;
            }
            
            .message-avatar i {
                font-size: 18px;
            }
        }

        .message.user .message-avatar {
            background: var(--gradient-2);
        }

        .message.assistant .message-avatar {
            background: var(--gradient-1);
        }

        .message-content {
            flex: 1;
            max-width: 80%;
        }

        @media (max-width: 768px) {
            .message-content {
                max-width: 85%;
            }
        }

        .message-text {
            background: var(--glass);
            padding: 1rem 1.5rem;
            border-radius: 18px;
            border: 1px solid var(--glass-border);
            color: white;
            line-height: 1.6;
            white-space: pre-wrap;
            font-size: 1rem;
        }

        @media (max-width: 768px) {
            .message-text {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
            }
        }

        .message.user .message-text {
            background: var(--gradient-1);
        }

        /* Code Blocks */
        .code-block-wrapper {
            margin: 1rem 0;
            border-radius: 12px;
            overflow: hidden;
            background: var(--code-bg);
            border: 1px solid var(--glass-border);
        }

        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 1rem;
            background: rgba(255, 255, 255, 0.05);
            border-bottom: 1px solid var(--glass-border);
        }

        .code-language {
            font-size: 0.85rem;
            color: var(--gray);
            text-transform: uppercase;
        }

        .copy-code-btn {
            background: transparent;
            border: 1px solid var(--glass-border);
            color: var(--gray);
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: all 0.3s;
        }

        .copy-code-btn:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .copy-code-btn.copied {
            background: var(--success);
            color: white;
            border-color: var(--success);
        }

        pre {
            margin: 0 !important;
            padding: 1rem !important;
            background: var(--code-bg) !important;
            overflow-x: auto;
        }

        code {
            font-family: 'Fira Code', monospace !important;
            font-size: 0.9rem !important;
        }

        .inline-code {
            background: rgba(124, 58, 237, 0.2);
            color: #e2e8f0;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Fira Code', monospace;
            font-size: 0.9em;
            border: 1px solid rgba(124, 58, 237, 0.3);
        }

        /* Loading Dots */
        .loading-dots {
            display: flex;
            gap: 8px;
            padding: 1rem;
            background: var(--glass);
            border-radius: 18px;
        }

        .loading-dots span {
            width: 10px;
            height: 10px;
            background: var(--primary);
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }

        .loading-dots span:nth-child(2) {
            background: var(--secondary);
            animation-delay: 0.2s;
        }

        .loading-dots span:nth-child(3) {
            background: var(--accent);
            animation-delay: 0.4s;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        /* Error Message */
        .error-message {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid var(--danger);
            color: #ff9999;
            padding: 1rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Input Area */
        .input-container {
            padding: 1.5rem 2rem;
            background: rgba(2, 6, 23, 0.8);
            backdrop-filter: blur(20px);
            border-top: 1px solid var(--glass-border);
        }

        @media (max-width: 768px) {
            .input-container {
                padding: 1rem;
            }
        }

        .input-wrapper {
            display: flex;
            gap: 12px;
            background: var(--glass);
            border-radius: 16px;
            padding: 0.25rem;
            border: 1px solid var(--glass-border);
        }

        .input-wrapper:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            padding: 0.75rem 1.25rem;
            color: white;
            font-family: 'Cairo', sans-serif;
            font-size: 0.95rem;
            resize: none;
            max-height: 100px;
        }

        @media (max-width: 768px) {
            textarea {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
            }
        }

        textarea:focus { outline: none; }

        textarea::placeholder {
            color: var(--gray);
        }

        .send-btn {
            width: 45px;
            height: 45px;
            background: var(--gradient-1);
            border: none;
            border-radius: 14px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
        }

        .send-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .input-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 0.5rem;
            color: var(--gray);
            font-size: 0.8rem;
        }

        @media (max-width: 480px) {
            .input-footer {
                font-size: 0.7rem;
            }
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .typing-indicator i {
            color: var(--primary);
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: var(--glass);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--secondary);
        }

        /* Mobile Overlay */
        .sidebar-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            z-index: 99;
        }

        .sidebar-overlay.active {
            display: block;
        }

        @media (max-width: 768px) {
            .sidebar-overlay.active {
                display: block;
            }
        }

        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: var(--glass);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            padding: 0.75rem 1.5rem;
            border-radius: 30px;
            color: white;
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 1000;
            transition: transform 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        .toast.success {
            background: var(--success);
            border-color: var(--success);
        }

        .toast.error {
            background: var(--danger);
            border-color: var(--danger);
        }

        /* Markdown Styles */
        .message-text h1,
        .message-text h2,
        .message-text h3,
        .message-text h4 {
            margin: 1.5rem 0 1rem 0;
            color: var(--light);
        }

        .message-text h1 { font-size: 2rem; }
        .message-text h2 { font-size: 1.75rem; }
        .message-text h3 { font-size: 1.5rem; }
        .message-text h4 { font-size: 1.25rem; }

        .message-text p {
            margin: 1rem 0;
        }

        .message-text ul,
        .message-text ol {
            margin: 1rem 0;
            padding-right: 2rem;
        }

        .message-text li {
            margin: 0.5rem 0;
        }

        .message-text blockquote {
            margin: 1rem 0;
            padding: 0.5rem 1rem;
            border-right: 4px solid var(--primary);
            background: rgba(124, 58, 237, 0.1);
            border-radius: 0 8px 8px 0;
        }

        .message-text table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }

        .message-text th,
        .message-text td {
            padding: 0.75rem;
            border: 1px solid var(--glass-border);
        }

        .message-text th {
            background: var(--glass);
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Navbar -->
        <nav class="navbar">
            <div class="brand">
                <button class="menu-btn" onclick="toggleSidebar()">
                    <i class="fas fa-bars"></i>
                </button>
                <div class="logo">
                    <i class="fas fa-crown"></i>
                </div>
                <span class="brand-text">Abdo AI Pro</span>
            </div>
        </nav>

        <!-- Main Layout -->
        <div class="main">
            <!-- Sidebar Overlay -->
            <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
            
            <!-- Sidebar -->
            <div class="sidebar" id="sidebar">
                <button class="new-chat-btn" onclick="newConversation()">
                    <i class="fas fa-plus"></i>
                    محادثة جديدة
                </button>
                <div class="conversations-list" id="conversationsList"></div>
            </div>

            <!-- Chat Area -->
            <div class="chat-area">
                <div class="chat-header">
                    <span><i class="fas fa-robot" style="margin-left: 8px;"></i> Abdo AI Pro - مساعدك الشخصي</span>
                    <span class="online-status"><i class="fas fa-circle" style="color: var(--success); font-size: 10px;"></i> متصل</span>
                </div>

                <div class="messages-container" id="messagesContainer">
                    <!-- Welcome Screen -->
                    <div class="welcome-screen" id="welcomeMessage">
                        <div class="welcome-icon">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h1>Abdo AI Pro</h1>
                        <p>مساعدك الذكي للإجابات الدقيقة والشاملة</p>
                        
                        <div class="suggestions">
                            <span class="suggestion-chip" onclick="setQuestion('اكتب برنامج بايثون لحساب الأعداد الأولية مع شرح')">
                                <i class="fas fa-code"></i> برنامج بايثون
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('كيف تعمل الشبكات العصبية؟')">
                                <i class="fas fa-brain"></i> الشبكات العصبية
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('أفضل ممارسات تطوير الويب')">
                                <i class="fas fa-globe"></i> تطوير الويب
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('شرح خوارزمية البحث الثنائي')">
                                <i class="fas fa-search"></i> البحث الثنائي
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('كيف تبني API باستخدام Flask؟')">
                                <i class="fas fa-server"></i> Flask API
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Input Area -->
                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea 
                            id="messageInput" 
                            placeholder="اكتب سؤالك هنا..."
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
                            <i class="fas fa-keyboard"></i>
                            Enter للإرسال
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div class="toast" id="toast">
        <i class="fas fa-check-circle"></i>
        <span id="toastMessage">تم النسخ!</span>
    </div>

    <script>
        let currentConversationId = '{{ session["conversation_id"] }}';
        let isProcessing = false;
        let eventSource = null;
        
        // تحميل المحادثات من localStorage
        function loadLocalConversations() {
            const saved = localStorage.getItem('abdoAIConversations');
            if (saved) {
                try {
                    return JSON.parse(saved);
                } catch (e) {
                    return {};
                }
            }
            return {};
        }

        // حفظ المحادثات في localStorage
        function saveLocalConversations(convs) {
            localStorage.setItem('abdoAIConversations', JSON.stringify(convs));
        }

        // تهيئة المحادثات
        let localConversations = loadLocalConversations();
        
        // دمج مع محادثات الجلسة الحالية
        if (!localConversations[currentConversationId]) {
            localConversations[currentConversationId] = [];
        }

        // تحميل المحادثات
        function loadConversations() {
            const list = document.getElementById('conversationsList');
            const convs = Object.entries(localConversations)
                .filter(([_, msgs]) => msgs && msgs.length > 0)
                .map(([id, msgs]) => ({
                    id,
                    preview: msgs[0]?.content?.substring(0, 40) + '...' || 'محادثة جديدة',
                    timestamp: msgs[0]?.timestamp || new Date().toISOString(),
                    message_count: msgs.length
                }))
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            if (convs.length === 0) {
                list.innerHTML = '<div style="color: var(--gray); text-align: center; padding: 20px;">لا توجد محادثات سابقة</div>';
                return;
            }
            
            list.innerHTML = '';
            convs.forEach(conv => {
                const item = document.createElement('div');
                item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
                item.onclick = () => loadConversation(conv.id);
                
                const date = new Date(conv.timestamp);
                const timeStr = date.toLocaleString('ar-SA', { hour: '2-digit', minute: '2-digit' });
                
                item.innerHTML = `
                    <div style="font-weight: 500; margin-bottom: 5px;">${escapeHtml(conv.preview)}</div>
                    <div style="font-size: 0.7rem; color: var(--gray); display: flex; justify-content: space-between;">
                        <span><i class="far fa-clock"></i> ${timeStr}</span>
                        <span><i class="far fa-comment"></i> ${conv.message_count}</span>
                    </div>
                `;
                list.appendChild(item);
            });
        }

        // تحميل محادثة محددة
        function loadConversation(conversationId) {
            currentConversationId = conversationId;
            const msgs = localConversations[conversationId] || [];
            
            document.getElementById('welcomeMessage').style.display = 'none';
            const container = document.getElementById('messagesContainer');
            container.innerHTML = '';
            
            msgs.forEach(msg => {
                if (msg.role === 'user') {
                    displayUserMessage(msg.content);
                } else {
                    displayAssistantMessage(msg.content);
                }
            });
            
            // تحديث الحالة النشطة
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
            });
            loadConversations();
            
            // إغلاق sidebar في الموبايل
            if (window.innerWidth <= 768) {
                toggleSidebar();
            }
            
            // تطبيق التنسيق على الأكواد
            setTimeout(() => {
                document.querySelectorAll('pre code').forEach(block => {
                    hljs.highlightElement(block);
                });
            }, 100);
        }

        // عرض رسالة المستخدم
        function displayUserMessage(message) {
            const container = document.getElementById('messagesContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user';
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-text">${escapeHtml(message).replace(/\\n/g, '<br>')}</div>
                </div>
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
            `;
            container.appendChild(messageDiv);
            scrollToBottom();
        }

        // عرض رسالة المساعد
        function displayAssistantMessage(message) {
            const container = document.getElementById('messagesContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant';
            
            messageDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">${formatMessage(message)}</div>
                </div>
            `;
            container.appendChild(messageDiv);
            scrollToBottom();
        }

        // تنسيق الرسالة مع دعم الأكواد
        function formatMessage(message) {
            // تحويل الروابط
            message = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color: var(--primary);">$1</a>');
            
            // تحويل النقاط والقوائم
            message = message.replace(/^[-*]\s(.+)$/gm, '<li>$1</li>');
            
            return message.replace(/\\n/g, '<br>');
        }

        // عرض مؤشر التحميل
        function showLoading() {
            const container = document.getElementById('messagesContainer');
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant';
            loadingDiv.id = 'loadingMessage';
            loadingDiv.innerHTML = `
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
            `;
            container.appendChild(loadingDiv);
            scrollToBottom();
        }

        // عرض رسالة خطأ
        function showError(message) {
            const container = document.getElementById('messagesContainer');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message assistant';
            errorDiv.innerHTML = `
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        ${escapeHtml(message)}
                    </div>
                </div>
            `;
            container.appendChild(errorDiv);
            scrollToBottom();
        }

        // نسخ الكود
        function copyCode(btn) {
            const codeBlock = btn.closest('.code-block-wrapper').querySelector('code');
            const code = codeBlock.textContent;
            
            navigator.clipboard.writeText(code).then(() => {
                btn.classList.add('copied');
                btn.innerHTML = '<i class="fas fa-check"></i> تم النسخ!';
                
                showToast('تم نسخ الكود بنجاح', 'success');
                
                setTimeout(() => {
                    btn.classList.remove('copied');
                    btn.innerHTML = '<i class="fas fa-copy"></i> نسخ';
                }, 2000);
            }).catch(() => {
                showToast('فشل نسخ الكود', 'error');
            });
        }

        // عرض toast notification
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            const toastMessage = document.getElementById('toastMessage');
            
            toast.className = `toast ${type}`;
            toastMessage.textContent = message;
            
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        // إرسال رسالة مع Streaming
        function sendMessage() {
            if (isProcessing) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) {
                showToast('الرجاء إدخال رسالة', 'error');
                return;
            }
            
            isProcessing = true;
            document.getElementById('sendBtn').disabled = true;
            document.getElementById('typingIndicator').innerHTML = '<i class="fas fa-spinner fa-pulse"></i> جاري التفكير...';
            
            document.getElementById('welcomeMessage').style.display = 'none';
            displayUserMessage(message);
            
            input.value = '';
            autoResize(input);
            
            // إظهار مؤشر التحميل
            showLoading();
            
            // حفظ رسالة المستخدم محلياً
            if (!localConversations[currentConversationId]) {
                localConversations[currentConversationId] = [];
            }
            
            localConversations[currentConversationId].push({
                role: 'user',
                content: message,
                timestamp: new Date().toISOString()
            });
            
            saveLocalConversations(localConversations);
            
            // استخدام EventSource للـ streaming
            if (eventSource) {
                eventSource.close();
            }
            
            eventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}&conversation_id=${currentConversationId}`);
            
            let fullResponse = '';
            let messageDiv = null;
            
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // إزالة مؤشر التحميل
                document.getElementById('loadingMessage')?.remove();
                
                if (data.error) {
                    showError(data.error);
                    eventSource.close();
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('typingIndicator').innerHTML = '';
                    return;
                }
                
                if (data.chunk) {
                    // إنشاء رسالة جديدة إذا لم تكن موجودة
                    if (!messageDiv) {
                        const container = document.getElementById('messagesContainer');
                        messageDiv = document.createElement('div');
                        messageDiv.className = 'message assistant';
                        messageDiv.innerHTML = `
                            <div class="message-avatar">
                                <i class="fas fa-robot"></i>
                            </div>
                            <div class="message-content">
                                <div class="message-text" id="responseText"></div>
                            </div>
                        `;
                        container.appendChild(messageDiv);
                    }
                    
                    fullResponse += data.chunk;
                    
                    // تحسين عرض الأكواد
                    let formattedResponse = fullResponse;
                    if (formattedResponse.includes('```')) {
                        // معالجة كتل الأكواد
                        const parts = formattedResponse.split('```');
                        for (let i = 1; i < parts.length; i += 2) {
                            const lang = parts[i].split('\\n')[0];
                            const code = parts[i].substring(lang.length).trim();
                            parts[i] = `<div class="code-block-wrapper">
                                <div class="code-header">
                                    <span class="code-language">${lang || 'text'}</span>
                                    <button class="copy-code-btn" onclick="copyCode(this)">
                                        <i class="fas fa-copy"></i> نسخ
                                    </button>
                                </div>
                                <pre><code class="language-${lang}">${escapeHtml(code)}</code></pre>
                            </div>`;
                        }
                        formattedResponse = parts.join('');
                    }
                    
                    const responseText = document.getElementById('responseText');
                    if (responseText) {
                        responseText.innerHTML = formattedResponse;
                        
                        // تطبيق التنسيق على الأكواد
                        responseText.querySelectorAll('pre code').forEach(block => {
                            hljs.highlightElement(block);
                        });
                    }
                    
                    scrollToBottom();
                }
                
                if (data.done) {
                    eventSource.close();
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('typingIndicator').innerHTML = '';
                    
                    // حفظ رد المساعد
                    localConversations[currentConversationId].push({
                        role: 'assistant',
                        content: fullResponse,
                        timestamp: new Date().toISOString()
                    });
                    
                    saveLocalConversations(localConversations);
                    loadConversations();
                    
                    showToast('تم استلام الرد بنجاح', 'success');
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                document.getElementById('loadingMessage')?.remove();
                showError('انقطع الاتصال بالخادم');
                isProcessing = false;
                document.getElementById('sendBtn').disabled = false;
                document.getElementById('typingIndicator').innerHTML = '';
                showToast('حدث خطأ في الاتصال', 'error');
            };
        }

        // محادثة جديدة
        function newConversation() {
            if (eventSource) {
                eventSource.close();
            }
            
            fetch('/api/conversations', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        currentConversationId = data.id;
                        localConversations[currentConversationId] = [];
                        saveLocalConversations(localConversations);
                        
                        document.getElementById('messagesContainer').innerHTML = '';
                        document.getElementById('welcomeMessage').style.display = 'block';
                        loadConversations();
                        
                        showToast('تم بدء محادثة جديدة', 'success');
                    }
                });
        }

        // تعيين سؤال
        function setQuestion(question) {
            document.getElementById('messageInput').value = question;
            document.getElementById('messageInput').focus();
            autoResize(document.getElementById('messageInput'));
        }

        // تغيير حجم textarea
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        }

        // التمرير للأسفل
        function scrollToBottom() {
            const container = document.getElementById('messagesContainer');
            container.scrollTop = container.scrollHeight;
        }

        // تبديل sidebar في الموبايل
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        }

        // HTML escaping
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Enter للإرسال
        document.getElementById('messageInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // تحميل المحادثات عند بدء التشغيل
        loadConversations();
        
        // تحميل المحادثة الحالية
        if (localConversations[currentConversationId]?.length > 0) {
            loadConversation(currentConversationId);
        }

        // تحديث حجم الشاشة
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                document.getElementById('sidebar').classList.remove('active');
                document.getElementById('sidebarOverlay').classList.remove('active');
            }
        });
        
        // منع إغلاق الاتصال عند التبديل بين التطبيقات
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                if (eventSource) {
                    eventSource.close();
                }
            }
        });
    </script>
</body>
</html>
    ''')

@app.route('/api/chat/stream')
def chat_stream():
    """نقطة نهاية للمحادثة المتدفقة"""
    message = request.args.get('message', '').strip()
    conversation_id = request.args.get('conversation_id') or session.get('conversation_id')
    
    if not message:
        return jsonify({'error': 'الرجاء إدخال رسالة'}), 400
    
    def generate():
        try:
            # تحضير الرسائل للنموذج
            messages_for_api = [
                {'role': 'user', 'content': message}
            ]
            
            full_response = ""
            
            # توليد الرد المتدفق
            for chunk in generate_stream_response(messages_for_api):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            error_msg = str(e)
            print(f"خطأ في الـ streaming: {error_msg}")
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """إنشاء محادثة جديدة"""
    new_id = str(uuid.uuid4())
    conversations[new_id] = []
    session['conversation_id'] = new_id
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """استرجاع محادثة محددة"""
    if conversation_id in conversations:
        return jsonify({'messages': conversations[conversation_id]})
    return jsonify({'messages': []})

if __name__ == '__main__':
    print("="*80)
    print("🚀 Abdo AI Pro - مساعدك الذكي")
    print("="*80)
    print(f"📡 الخادم: http://localhost:5000")
    print(f"🤖 النموذج: AI Pro Assistant")
    print(f"🔑 مفتاح API: ✓ نشط")
    print(f"⚡ الميزات: Streaming | حفظ محلي | نسخ الأكواد")
    print("="*80)
    print("✅ افتح المتصفح على: http://localhost:5000")
    print("="*80)
    
    # للإنتاج على Render/Replit
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
