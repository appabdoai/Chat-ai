from flask import Flask, render_template_string, request, jsonify, session, Response
import requests
import json
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

# إعدادات NVIDIA API
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-122b-a10b"

# تخزين المحادثات في الذاكرة فقط (مؤقت)
active_sessions = {}

def generate_professional_response(messages, session_id):
    """ توليد ردود احترافية جدا"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    system_prompt = {
        "role": "system",
        "content": """أنت Abdo AI Pro - خبير محترف في جميع المجالات.

القواعد الذهبية للإجابات الاحترافية:

1. **البداية المباشرة**: ابدأ الإجابة فوراً بدون مقدمات

2. **للعروض والتحليلات**:
   - استخدم جداول منسقة للبيانات
   - أضف إحصائيات دقيقة

3. **للبرمجة**:
   - قدم كود كامل مع شرح
   - أضف تعليقات بالعربية

4. **ضمان الاكتمال**:
   - أكمل جميع الأفكار حتى النهاية
   - لا تتوقف قبل إكمال الموضوع"""
    }
    
    full_messages = [system_prompt] + messages[-20:]
    
    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "max_tokens": 32768,
        "temperature": 0.65,
        "top_p": 0.95,
        "stream": True
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
    """الصفحة الرئيسية مع حفظ المحادثات في localStorage"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Abdo AI Pro - الخبير المحترف</title>
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
            --bg-dark: #0a0c14;
            --bg-card: #111827;
            --bg-input: #1a1f2e;
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --border: #1f2937;
            --border-light: #374151;
            --hover: #2d3748;
            --code-bg: #0a0c14;
            --gradient-1: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --gradient-2: linear-gradient(135deg, #f59e0b, #ef4444);
            --shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        [data-theme="light"] {
            --bg-dark: #f9fafb;
            --bg-card: #ffffff;
            --bg-input: #f3f4f6;
            --text-primary: #111827;
            --text-secondary: #4b5563;
            --border: #e5e7eb;
            --border-light: #d1d5db;
            --hover: #e5e7eb;
            --code-bg: #f3f4f6;
            --shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
            transition: background 0.3s, color 0.3s;
        }

        .app {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .navbar {
            background: var(--bg-card);
            border-bottom: 2px solid var(--border);
            padding: 0 2rem;
            height: 75px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
            z-index: 100;
            box-shadow: var(--shadow);
        }

        .nav-left {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .menu-btn {
            width: 45px;
            height: 45px;
            background: transparent;
            border: 2px solid var(--border);
            border-radius: 14px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .menu-btn:hover {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
            transform: scale(1.05);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            width: 50px;
            height: 50px;
            background: var(--gradient-1);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .logo-icon::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255,255,255,0.3), transparent);
            transform: rotate(45deg);
            animation: shine 3s infinite;
        }

        @keyframes shine {
            0% { transform: translateX(-100%) rotate(45deg); }
            20%, 100% { transform: translateX(100%) rotate(45deg); }
        }

        .logo-icon i {
            font-size: 24px;
            color: white;
            position: relative;
            z-index: 2;
        }

        .logo-text {
            font-weight: 800;
            font-size: 1.5rem;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-badge {
            background: var(--accent);
            color: white;
            font-size: 0.7rem;
            padding: 0.3rem 0.8rem;
            border-radius: 30px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .nav-tabs {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--bg-input);
            padding: 0.4rem;
            border-radius: 40px;
            border: 2px solid var(--border);
        }

        .nav-tab {
            padding: 0.6rem 1.8rem;
            border-radius: 30px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav-tab:hover {
            color: var(--text-primary);
            background: var(--hover);
        }

        .nav-tab.active {
            background: var(--gradient-1);
            color: white;
        }

        .nav-right {
            display: flex;
            align-items: center;
            gap: 1.2rem;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0.5rem 1.5rem;
            background: var(--bg-input);
            border-radius: 40px;
            border: 2px solid var(--border);
        }

        .status-dot {
            width: 12px;
            height: 12px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.7; }
        }

        .theme-toggle {
            width: 45px;
            height: 45px;
            background: transparent;
            border: 2px solid var(--border);
            border-radius: 14px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .theme-toggle:hover {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
        }

        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        .sidebar {
            width: 360px;
            background: var(--bg-card);
            border-left: 2px solid var(--border);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease;
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            z-index: 90;
            transform: translateX(100%);
            box-shadow: var(--shadow);
        }

        .sidebar.open {
            transform: translateX(0);
        }

        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sidebar-header h3 {
            font-size: 1.2rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .close-sidebar {
            width: 40px;
            height: 40px;
            background: transparent;
            border: 2px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .close-sidebar:hover {
            background: var(--danger);
            border-color: var(--danger);
            color: white;
        }

        .new-chat-btn {
            margin: 1.5rem;
            padding: 1.2rem;
            background: var(--gradient-1);
            border: none;
            border-radius: 16px;
            color: white;
            font-weight: 700;
            font-size: 1.1rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: all 0.3s;
        }

        .new-chat-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 30px rgba(59, 130, 246, 0.4);
        }

        .conversations-list {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
        }

        .conversation-item {
            padding: 1.2rem;
            background: var(--bg-input);
            border-radius: 16px;
            margin-bottom: 1rem;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }

        .conversation-item:hover {
            border-color: var(--primary);
            transform: translateX(-5px);
            background: var(--hover);
        }

        .conversation-item.active {
            border-color: var(--primary);
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
        }

        .conv-title {
            font-weight: 700;
            margin-bottom: 0.7rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 1rem;
        }

        .conv-delete {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0.3rem;
            transition: all 0.3s;
            font-size: 1rem;
        }

        .conv-delete:hover {
            color: var(--danger);
            transform: scale(1.2);
        }

        .conv-preview {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 0.7rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conv-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: var(--bg-dark);
        }

        .chat-header {
            padding: 1.2rem 2rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-card);
        }

        .chat-title {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .expert-badge {
            background: var(--gradient-1);
            padding: 0.5rem 1.5rem;
            border-radius: 40px;
            font-size: 0.9rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            color: white;
        }

        .clear-chat {
            background: transparent;
            border: 2px solid var(--border);
            color: var(--text-primary);
            padding: 0.6rem 1.5rem;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
        }

        .clear-chat:hover {
            background: var(--danger);
            border-color: var(--danger);
            color: white;
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            scroll-behavior: smooth;
        }

        .message {
            display: flex;
            gap: 1.2rem;
            margin-bottom: 2rem;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-avatar {
            width: 55px;
            height: 55px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 1.5rem;
        }

        .message.user .message-avatar {
            background: var(--gradient-2);
        }

        .message.assistant .message-avatar {
            background: var(--gradient-1);
        }

        .message-content {
            flex: 1;
            max-width: calc(100% - 75px);
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.7rem;
            font-size: 0.95rem;
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
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 20px;
            border: 2px solid var(--border);
            color: var(--text-primary);
            line-height: 1.8;
            word-wrap: break-word;
            overflow-wrap: break-word;
            font-size: 1rem;
        }

        .message.user .message-text {
            background: var(--gradient-1);
            border: none;
            color: white;
        }

        .message-text table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: var(--bg-input);
            border-radius: 16px;
            overflow: hidden;
            border: 2px solid var(--border);
        }

        .message-text th {
            background: var(--primary);
            color: white;
            padding: 1rem;
            font-weight: 700;
        }

        .message-text td {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
        }

        .message-text tr:last-child td {
            border-bottom: none;
        }

        .message-text tr:hover td {
            background: var(--hover);
        }

        .message-text pre {
            background: var(--code-bg) !important;
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            border: 2px solid var(--border);
            position: relative;
            max-width: 100%;
            overflow-x: auto;
        }

        .message-text code {
            font-family: 'Fira Code', monospace;
            font-size: 0.95rem;
        }

        .copy-code {
            position: absolute;
            top: 0.8rem;
            left: 0.8rem;
            background: var(--bg-card);
            border: 2px solid var(--border);
            color: var(--text-primary);
            padding: 0.4rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
            font-weight: 500;
        }

        pre:hover .copy-code {
            opacity: 1;
        }

        .copy-code:hover {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
        }

        .message-actions {
            display: flex;
            gap: 0.8rem;
            margin-top: 0.8rem;
            justify-content: flex-start;
        }

        .message.user .message-actions {
            justify-content: flex-end;
        }

        .action-btn {
            background: var(--bg-input);
            border: 2px solid var(--border);
            color: var(--text-primary);
            padding: 0.5rem 1.2rem;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .action-btn:hover {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
        }

        .action-btn.stop {
            background: var(--danger);
            border-color: var(--danger);
            color: white;
        }

        .action-btn.stop:hover {
            background: #dc2626;
        }

        .welcome-message {
            text-align: center;
            max-width: 900px;
            margin: 3rem auto;
            padding: 2rem;
        }

        .welcome-icon {
            width: 140px;
            height: 140px;
            margin: 0 auto 2rem;
            background: var(--gradient-1);
            border-radius: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-15px); }
        }

        .welcome-icon i {
            font-size: 70px;
            color: white;
        }

        .welcome-message h1 {
            font-size: 3.5rem;
            margin-bottom: 1rem;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin: 3rem 0;
        }

        .feature-card {
            background: var(--bg-card);
            padding: 2rem 1.5rem;
            border-radius: 24px;
            border: 2px solid var(--border);
            transition: all 0.3s;
        }

        .feature-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
            box-shadow: var(--shadow);
        }

        .feature-card i {
            font-size: 2.5rem;
            color: var(--primary);
            margin-bottom: 1.2rem;
        }

        .feature-card h3 {
            font-size: 1.3rem;
            margin-bottom: 0.8rem;
        }

        .feature-card p {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .input-container {
            padding: 1.5rem 2rem;
            background: var(--bg-card);
            border-top: 2px solid var(--border);
        }

        .input-wrapper {
            display: flex;
            gap: 1.2rem;
            align-items: flex-end;
            background: var(--bg-input);
            border-radius: 24px;
            padding: 0.8rem;
            border: 2px solid var(--border);
            transition: all 0.3s;
        }

        .input-wrapper:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
        }

        textarea {
            flex: 1;
            background: transparent;
            border: none;
            padding: 0.8rem 1.2rem;
            color: var(--text-primary);
            font-family: 'Cairo', sans-serif;
            font-size: 1rem;
            resize: none;
            max-height: 150px;
        }

        textarea:focus {
            outline: none;
        }

        textarea::placeholder {
            color: var(--text-secondary);
            opacity: 0.7;
        }

        .input-actions {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .input-btn {
            width: 50px;
            height: 50px;
            border: none;
            border-radius: 16px;
            background: transparent;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .input-btn:hover:not(:disabled) {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
        }

        .input-btn.send {
            background: var(--gradient-1);
            border: none;
            color: white;
        }

        .input-btn.send:hover:not(:disabled) {
            transform: scale(1.1);
        }

        .input-btn.stop {
            background: var(--danger);
            border-color: var(--danger);
            color: white;
        }

        .input-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 0.8rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            padding: 0 0.5rem;
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .typing-dots {
            display: flex;
            gap: 4px;
        }

        .typing-dots span {
            width: 8px;
            height: 8px;
            background: var(--primary);
            border-radius: 50%;
            animation: typing 1.2s infinite;
        }

        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-input);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--secondary);
        }

        @media (max-width: 768px) {
            .navbar {
                padding: 0 1rem;
            }
            
            .logo-text {
                font-size: 1.2rem;
            }
            
            .logo-badge {
                display: none;
            }
            
            .nav-tabs {
                display: none;
            }
            
            .status span {
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
                font-size: 2.5rem;
            }
            
            .features-grid {
                grid-template-columns: 1fr;
            }
            
            .input-container {
                padding: 1rem;
            }
        }
    </style>
</head>
<body data-theme="dark">
    <div class="app">
        <div class="navbar">
            <div class="nav-left">
                <button class="menu-btn" onclick="toggleSidebar()">
                    <i class="fas fa-bars"></i>
                </button>
                <div class="logo">
                    <div class="logo-icon">
                        <i class="fas fa-brain"></i>
                    </div>
                    <span class="logo-text">Abdo AI Pro</span>
                    <span class="logo-badge">خاص</span>
                </div>
            </div>
            
            <div class="nav-tabs">
                <div class="nav-tab active" onclick="switchTab('chat', this)">
                    <i class="fas fa-comment"></i> تحليل
                </div>
                <div class="nav-tab" onclick="switchTab('code', this)">
                    <i class="fas fa-code"></i> برمجة
                </div>
                <div class="nav-tab" onclick="switchTab('compare', this)">
                    <i class="fas fa-scale-balanced"></i> مقارنة
                </div>
                <div class="nav-tab" onclick="switchTab('stats', this)">
                    <i class="fas fa-chart-bar"></i> إحصائيات
                </div>
            </div>
            
            <div class="nav-right">
                <div class="status">
                    <span class="status-dot"></span>
                    <span>خاص بك</span>
                </div>
                <button class="theme-toggle" onclick="toggleTheme()">
                    <i class="fas fa-moon"></i>
                </button>
            </div>
        </div>
        
        <div class="main">
            <div class="sidebar" id="sidebar">
                <div class="sidebar-header">
                    <h3><i class="fas fa-history"></i> محادثاتي الخاصة</h3>
                    <button class="close-sidebar" onclick="toggleSidebar()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <button class="new-chat-btn" onclick="newConversation()">
                    <i class="fas fa-plus"></i>
                    محادثة جديدة
                </button>
                
                <div class="conversations-list" id="conversationsList">
                    <!-- تضاف المحادثات من localStorage -->
                </div>
            </div>
            
            <div class="chat-area">
                <div class="chat-header">
                    <div class="chat-title">
                        <span class="expert-badge">
                            <i class="fas fa-crown"></i> خاص بك فقط
                        </span>
                    </div>
                    <button class="clear-chat" onclick="clearChat()">
                        <i class="fas fa-trash"></i> مسح المحادثة
                    </button>
                </div>
                
                <div class="messages-container" id="messagesContainer">
                    <div class="welcome-message" id="welcomeMessage">
                        <div class="welcome-icon">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h1>Abdo AI Pro</h1>
                        <p>مساعدك الخاص - محادثاتك محفوظة في متصفحك فقط</p>
                        
                        <div class="features-grid">
                            <div class="feature-card">
                                <i class="fas fa-lock"></i>
                                <h3>خصوصية تامة</h3>
                                <p>محادثاتك خاصة بك ولا يراها أحد</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-code"></i>
                                <h3>برمجة احترافية</h3>
                                <p>أكواد كاملة مع شرح</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-chart-line"></i>
                                <h3>تحليل دقيق</h3>
                                <p>مع جداول وإحصائيات</p>
                            </div>
                        </div>
                        
                        <div style="margin-top: 2rem; color: var(--text-secondary);">
                            <i class="fas fa-arrow-down"></i> اطرح سؤالك
                        </div>
                    </div>
                </div>
                
                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea 
                            id="messageInput" 
                            placeholder="اكتب سؤالك هنا..."
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
        let currentConversationId = 'default';
        let isProcessing = false;
        let currentTheme = 'dark';
        let conversations = [];
        let currentMessages = [];
        
        // تهيئة التطبيق
        document.addEventListener('DOMContentLoaded', function() {
            loadFromLocalStorage();
            setupEventListeners();
            displayWelcomeMessage();
        });
        
        // تحميل المحادثات من localStorage
        function loadFromLocalStorage() {
            const saved = localStorage.getItem('abdo_ai_conversations');
            if (saved) {
                conversations = JSON.parse(saved);
            } else {
                conversations = [];
            }
            
            // تحميل آخر محادثة نشطة
            const lastActive = localStorage.getItem('abdo_ai_active');
            if (lastActive) {
                currentConversationId = lastActive;
                loadConversation(currentConversationId);
            }
            
            loadConversationsList();
        }
        
        // حفظ المحادثات في localStorage
        function saveToLocalStorage() {
            localStorage.setItem('abdo_ai_conversations', JSON.stringify(conversations));
            localStorage.setItem('abdo_ai_active', currentConversationId);
        }
        
        // تحميل قائمة المحادثات
        function loadConversationsList() {
            const list = document.getElementById('conversationsList');
            
            if (conversations.length === 0) {
                list.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">لا توجد محادثات سابقة</div>';
                return;
            }
            
            list.innerHTML = '';
            
            // ترتيب من الأحدث
            const sorted = [...conversations].sort((a, b) => 
                new Date(b.timestamp) - new Date(a.timestamp)
            );
            
            sorted.forEach(conv => {
                const item = createConversationItem(conv);
                list.appendChild(item);
            });
        }
        
        // إنشاء عنصر محادثة
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
            
            const preview = conv.messages && conv.messages[0] ? 
                conv.messages[0].content.substring(0, 35) : 'محادثة جديدة';
            
            div.innerHTML = `
                <div class="conv-title">
                    <span>${escapeHtml(preview)}...</span>
                    <button class="conv-delete" onclick="deleteConversation('${conv.id}', event)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="conv-preview">${escapeHtml(preview)}</div>
                <div class="conv-meta">
                    <span><i class="far fa-clock"></i> ${timeStr}</span>
                    <span><i class="far fa-comment"></i> ${conv.messages ? conv.messages.length/2 : 0}</span>
                </div>
            `;
            
            div.onclick = (e) => {
                if (!e.target.closest('.conv-delete')) {
                    loadConversation(conv.id);
                }
            };
            
            return div;
        }
        
        // تحميل محادثة محددة
        function loadConversation(conversationId) {
            currentConversationId = conversationId;
            toggleSidebar();
            
            const conv = conversations.find(c => c.id === conversationId);
            if (conv && conv.messages) {
                currentMessages = conv.messages;
                displayMessages();
            }
            
            // تحديث النشط
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
                if (item.dataset.id === conversationId) {
                    item.classList.add('active');
                }
            });
            
            saveToLocalStorage();
        }
        
        // عرض الرسائل
        function displayMessages() {
            const container = document.getElementById('messagesContainer');
            container.innerHTML = '';
            
            document.getElementById('welcomeMessage')?.remove();
            
            currentMessages.forEach(msg => {
                if (msg.role === 'user') {
                    displayUserMessage(msg.content, msg.timestamp);
                } else {
                    displayAssistantMessage(msg.content, msg.timestamp);
                }
            });
        }
        
        // عرض رسالة الترحيب
        function displayWelcomeMessage() {
            if (currentMessages.length === 0) {
                const container = document.getElementById('messagesContainer');
                container.innerHTML = '';
                container.appendChild(document.getElementById('welcomeMessage').cloneNode(true));
            }
        }
        
        // إنشاء محادثة جديدة
        function newConversation() {
            const newId = Date.now().toString();
            const newConversation = {
                id: newId,
                messages: [],
                timestamp: new Date().toISOString()
            };
            
            conversations.push(newConversation);
            currentConversationId = newId;
            currentMessages = [];
            
            // تحديث الواجهة
            const container = document.getElementById('messagesContainer');
            container.innerHTML = '';
            container.appendChild(document.getElementById('welcomeMessage').cloneNode(true));
            
            loadConversationsList();
            saveToLocalStorage();
            toggleSidebar();
        }
        
        // حذف محادثة
        function deleteConversation(conversationId, event) {
            event.stopPropagation();
            
            if (confirm('هل أنت متأكد من حذف هذه المحادثة؟')) {
                conversations = conversations.filter(c => c.id !== conversationId);
                
                if (conversationId === currentConversationId) {
                    if (conversations.length > 0) {
                        loadConversation(conversations[0].id);
                    } else {
                        newConversation();
                    }
                }
                
                loadConversationsList();
                saveToLocalStorage();
            }
        }
        
        // مسح المحادثة الحالية
        function clearChat() {
            if (confirm('هل أنت متأكد من مسح المحادثة الحالية؟')) {
                const conv = conversations.find(c => c.id === currentConversationId);
                if (conv) {
                    conv.messages = [];
                    currentMessages = [];
                    
                    const container = document.getElementById('messagesContainer');
                    container.innerHTML = '';
                    container.appendChild(document.getElementById('welcomeMessage').cloneNode(true));
                    
                    saveToLocalStorage();
                }
            }
        }
        
        // عرض رسالة المستخدم
        function displayUserMessage(message, timestamp) {
            const container = document.getElementById('messagesContainer');
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
        
        // عرض رسالة المساعد
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
                        <span class="sender-name">Abdo AI Pro</span>
                        <span>${timeStr}</span>
                    </div>
                    <div class="message-text">${formattedMessage}</div>
                    <div class="message-actions">
                        <button class="action-btn" onclick="copyMessage(this)">
                            <i class="fas fa-copy"></i> نسخ
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
                
                const pre = block.parentNode;
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-code';
                copyBtn.innerHTML = '<i class="fas fa-copy"></i> نسخ الكود';
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(block.textContent);
                    alert('✅ تم نسخ الكود');
                };
                pre.appendChild(copyBtn);
            });
            
            scrollToBottom();
        }
        
        // إرسال رسالة
        function sendMessage() {
            if (isProcessing) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            isProcessing = true;
            document.getElementById('sendBtn').disabled = true;
            
            displayUserMessage(message);
            input.value = '';
            autoResize(input);
            
            // حفظ رسالة المستخدم
            const userMsg = {
                role: 'user',
                content: message,
                timestamp: new Date().toISOString()
            };
            
            currentMessages.push(userMsg);
            
            // تحديث المحادثة
            const conv = conversations.find(c => c.id === currentConversationId);
            if (conv) {
                conv.messages = currentMessages;
                conv.timestamp = new Date().toISOString();
            }
            saveToLocalStorage();
            
            // إظهار مؤشر الكتابة
            showTypingIndicator();
            
            // بدء التدفق
            const eventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}`);
            let fullResponse = '';
            
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                hideTypingIndicator();
                
                if (data.chunk) {
                    fullResponse += data.chunk;
                    
                    // تحديث أو إنشاء رسالة المساعد
                    const lastMessage = currentMessages[currentMessages.length - 1];
                    if (!lastMessage || lastMessage.role !== 'assistant') {
                        // إنشاء رسالة جديدة
                        displayAssistantMessage(fullResponse);
                    } else {
                        // تحديث آخر رسالة
                        lastMessage.content = fullResponse;
                        const container = document.getElementById('messagesContainer');
                        const lastMsgDiv = container.lastChild;
                        if (lastMsgDiv && lastMsgDiv.classList.contains('assistant')) {
                            const textDiv = lastMsgDiv.querySelector('.message-text');
                            if (typeof marked !== 'undefined') {
                                textDiv.innerHTML = DOMPurify.sanitize(marked.parse(fullResponse));
                            } else {
                                textDiv.textContent = fullResponse;
                            }
                        }
                    }
                }
                
                if (data.done) {
                    eventSource.close();
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    
                    // حفظ رسالة المساعد
                    const assistantMsg = {
                        role: 'assistant',
                        content: fullResponse,
                        timestamp: new Date().toISOString()
                    };
                    
                    // تحديث أو إضافة
                    const lastMsg = currentMessages[currentMessages.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant') {
                        currentMessages[currentMessages.length - 1] = assistantMsg;
                    } else {
                        currentMessages.push(assistantMsg);
                    }
                    
                    // تحديث المحادثة
                    const conv = conversations.find(c => c.id === currentConversationId);
                    if (conv) {
                        conv.messages = currentMessages;
                    }
                    saveToLocalStorage();
                    loadConversationsList();
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                isProcessing = false;
                document.getElementById('sendBtn').disabled = false;
                hideTypingIndicator();
            };
        }
        
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
        }
        
        function toggleTheme() {
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const root = document.documentElement;
            
            if (currentTheme === 'light') {
                root.style.setProperty('--bg-dark', '#f9fafb');
                root.style.setProperty('--bg-card', '#ffffff');
                root.style.setProperty('--bg-input', '#f3f4f6');
                root.style.setProperty('--text-primary', '#111827');
                root.style.setProperty('--text-secondary', '#4b5563');
                root.style.setProperty('--border', '#e5e7eb');
                root.style.setProperty('--border-light', '#d1d5db');
                root.style.setProperty('--hover', '#e5e7eb');
                root.style.setProperty('--code-bg', '#f3f4f6');
                document.querySelector('.theme-toggle i').className = 'fas fa-sun';
            } else {
                root.style.setProperty('--bg-dark', '#0a0c14');
                root.style.setProperty('--bg-card', '#111827');
                root.style.setProperty('--bg-input', '#1a1f2e');
                root.style.setProperty('--text-primary', '#f3f4f6');
                root.style.setProperty('--text-secondary', '#9ca3af');
                root.style.setProperty('--border', '#1f2937');
                root.style.setProperty('--border-light', '#374151');
                root.style.setProperty('--hover', '#2d3748');
                root.style.setProperty('--code-bg', '#0a0c14');
                document.querySelector('.theme-toggle i').className = 'fas fa-moon';
            }
        }
        
        function switchTab(tab, element) {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            element.classList.add('active');
        }
        
        function showTypingIndicator() {
            const indicator = document.getElementById('typingIndicator');
            indicator.innerHTML = `
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
                <span>Abdo AI Pro يكتب...</span>
            `;
        }
        
        function hideTypingIndicator() {
            document.getElementById('typingIndicator').innerHTML = '';
        }
        
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
        }
        
        function scrollToBottom() {
            const container = document.getElementById('messagesContainer');
            container.scrollTop = container.scrollHeight;
        }
        
        function copyMessage(button) {
            const text = button.closest('.message-content').querySelector('.message-text').innerText;
            navigator.clipboard.writeText(text);
            alert('✅ تم النسخ');
        }
        
        function stopGeneration() {
            // سيتم تنفيذها لاحقاً
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
    """نقطة نهاية التدفق"""
    message = request.args.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'الرجاء إدخال رسالة'}), 400
    
    def generate():
        messages_for_api = [{'role': 'user', 'content': message}]
        
        for chunk in generate_professional_response(messages_for_api, ''):
            if chunk:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

if __name__ == '__main__':
    print("="*80)
    print("🚀 Abdo AI Pro - نسخة الخصوصية التامة")
    print("="*80)
    print("✅ المحادثات تحفظ في متصفح كل مستخدم فقط")
    print("✅ كل شخص يرى محادثاته الخاصة")
    print("✅ لا يوجد تخزين على السيرفر")
    print("="*80)
    print("🌐 الخادم: http://localhost:5000")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
