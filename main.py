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
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 7  # أسبوع

# إعدادات NVIDIA API
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-122b-a10b"

# تخزين المحادثات (في الإنتاج استخدم قاعدة بيانات)
conversations = {}

def optimize_code_response(content):
    """تحسين عرض الأكواد البرمجية"""
    # اكتشاف كتل الأكواد وتحسين تنسيقها
    def replace_code_block(match):
        lang = match.group(1) or 'text'
        code = match.group(2)
        return f'```{lang}\n{code}\n```'
    
    # تحسين عرض الأكواد المضمنة
    content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
    
    # تحسين كتل الأكواد
    content = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, content, flags=re.DOTALL)
    
    return content

def generate_stream_response(messages):
    """توليد رد متدفق محسن وسريع جداً من NVIDIA API"""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    system_prompt = {
        "role": "system",
        "content": """أنت Soft Atlas AI، مساعد ذكي فائق التطور باللغة العربية الفصحى.

القواعد الأساسية:
1. قدم إجابات دقيقة وشاملة جداً جداً (لا تقل عن 1000 كلمة للمواضيع المعقدة)
2. استخدم اللغة العربية الفصيحة السليمة 100%
3. للمواضيع البرمجية:
   - قدم شرحاً مفصلاً جداً مع أمثلة عملية
   - وضح كل سطر من الكود
   - اشرح أفضل الممارسات
   - قدم تحسينات مقترحة
   - اذكر الأخطاء الشائعة
4. قسّم الإجابات إلى أقسام منظمة مع عناوين فرعية
5. استخدم النقاط والقوائم للتوضيح
6. قدم أمثلة واقعية وحديثة
7. اشرح المفاهيم الصعبة ببساطة مع تشبيهات
8. للمواضيع العلمية، قدم تفاصيل دقيقة مع المصادر
9. للمواضيع التاريخية، اذكر التواريخ والأحداث بدقة
10. استخدم تنسيق Markdown محسن مع ألوان للأكواد
11. قدم إجابات موسوعية تغطي جميع جوانب السؤال
12. إذا كان السؤال برمجياً، قدم الكود مع شرح تفصيلي وناتج التنفيذ"""
    }
    
    full_messages = [system_prompt] + messages[-50:]  # آخر 50 رسالة للسياق
    
    payload = {
        "model": MODEL_NAME,
        "messages": full_messages,
        "max_tokens": 32768,  # أقصى طول للإجابة (مضاعف)
        "temperature": 0.65,   # توازن أفضل بين الإبداع والدقة
        "top_p": 0.92,
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
            timeout=120  # زيادة timeout
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
                                        content = delta['content']
                                        # تحسين عرض الأكواد في الوقت الفعلي
                                        if '```' in content:
                                            content = optimize_code_response(content)
                                        yield content
                            except:
                                continue
        else:
            yield f"⚠️ خطأ في الاتصال: {response.status_code}"
            
    except Exception as e:
        yield f"❌ حدث خطأ: {str(e)}"

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
    <title>Soft Atlas AI - المساعد الذكي الفائق</title>
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
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #8b5cf6;
            --accent: #ec4899;
            --dark: #0b1120;
            --darker: #050914;
            --light: #f8fafc;
            --gray: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --glass: rgba(255, 255, 255, 0.03);
            --glass-hover: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.05);
            --glass-border-hover: rgba(99, 102, 241, 0.3);
        }

        body {
            font-family: 'Cairo', sans-serif;
            background: var(--darker);
            min-height: 100vh;
            color: var(--light);
            position: relative;
            overflow-x: hidden;
        }

        /* خلفية متحركة */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 80%, rgba(236, 72, 153, 0.1) 0%, transparent 50%);
            animation: gradientShift 15s ease infinite;
            pointer-events: none;
        }

        @keyframes gradientShift {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }

        .app-container {
            position: relative;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(20px);
        }

        /* Navbar محسّن */
        .navbar {
            background: rgba(5, 9, 20, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--glass-border);
            padding: 0.75rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 1000;
        }

        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .logo::before {
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

        .logo i {
            font-size: 24px;
            color: white;
            position: relative;
            z-index: 2;
        }

        .brand-text {
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, var(--gray));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }

        .navbar-menu {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--gray);
            text-decoration: none;
            font-weight: 500;
            padding: 0.5rem 1rem;
            border-radius: 10px;
            transition: all 0.3s;
            cursor: pointer;
        }

        .nav-item:hover {
            background: var(--glass);
            color: white;
        }

        .nav-item.active {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }

        .nav-item i {
            font-size: 1.1rem;
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .theme-toggle, .settings-toggle {
            width: 45px;
            height: 45px;
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--gray);
            cursor: pointer;
            transition: all 0.3s;
        }

        .theme-toggle:hover, .settings-toggle:hover {
            background: var(--glass-hover);
            color: white;
            border-color: var(--primary);
        }

        /* Main Layout */
        .main-layout {
            display: flex;
            flex: 1;
            padding: 1.5rem;
            gap: 1.5rem;
            max-width: 1800px;
            margin: 0 auto;
            width: 100%;
        }

        /* Sidebar محسّن (أصغر حجماً) */
        .sidebar {
            width: 280px;
            background: rgba(5, 9, 20, 0.6);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            display: flex;
            flex-direction: column;
            height: calc(100vh - 100px);
            position: sticky;
            top: 85px;
            overflow: hidden;
        }

        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--glass-border);
        }

        .new-chat-btn {
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 16px;
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: all 0.3s;
        }

        .new-chat-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
        }

        .conversations-list {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
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
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15));
            border-color: var(--primary);
        }

        .conv-preview {
            font-size: 0.9rem;
            font-weight: 500;
            color: white;
            margin-bottom: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conv-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.7rem;
            color: var(--gray);
        }

        /* Chat Area الرئيسي (كبير) */
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: rgba(5, 9, 20, 0.4);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            overflow: hidden;
            height: calc(100vh - 100px);
        }

        .chat-header {
            padding: 1.25rem 2rem;
            border-bottom: 1px solid var(--glass-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(5, 9, 20, 0.6);
        }

        .chat-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .model-badge {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            padding: 0.5rem 1.25rem;
            border-radius: 30px;
            font-size: 0.9rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .model-badge i {
            color: var(--warning);
        }

        .chat-stats {
            display: flex;
            gap: 20px;
            color: var(--gray);
            font-size: 0.9rem;
        }

        .chat-stats span {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Welcome Screen محسّن */
        .welcome-screen {
            text-align: center;
            max-width: 900px;
            margin: 0 auto;
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
            box-shadow: 0 20px 40px rgba(99, 102, 241, 0.3);
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .welcome-icon i {
            font-size: 60px;
            color: white;
        }

        .welcome-screen h1 {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #fff, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .welcome-screen p {
            color: var(--gray);
            font-size: 1.2rem;
            margin-bottom: 3rem;
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }

        .feature-card {
            background: var(--glass);
            padding: 1.5rem;
            border-radius: 20px;
            border: 1px solid var(--glass-border);
            transition: all 0.3s;
        }

        .feature-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
            background: var(--glass-hover);
        }

        .feature-card i {
            font-size: 2rem;
            color: var(--primary);
            margin-bottom: 1rem;
        }

        .feature-card h3 {
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }

        .feature-card p {
            font-size: 0.9rem;
            color: var(--gray);
            margin: 0;
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
            font-size: 0.9rem;
        }

        .suggestion-chip:hover {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-color: transparent;
            transform: scale(1.05);
        }

        /* Message Styles محسّنة */
        .message {
            display: flex;
            gap: 15px;
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
            width: 45px;
            height: 45px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .message.user .message-avatar {
            background: linear-gradient(135deg, var(--accent), var(--danger));
        }

        .message.assistant .message-avatar {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
        }

        .message-avatar i {
            font-size: 22px;
            color: white;
        }

        .message-content {
            flex: 1;
            max-width: 80%;
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: var(--gray);
        }

        .message.user .message-header {
            flex-direction: row-reverse;
        }

        .sender-name {
            font-weight: 600;
            color: white;
        }

        .message-text {
            background: var(--glass);
            padding: 1.25rem 1.5rem;
            border-radius: 20px;
            border: 1px solid var(--glass-border);
            color: white;
            line-height: 1.8;
            font-size: 1rem;
            overflow-x: auto;
        }

        .message.user .message-text {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
        }

        /* Code Highlighting محسّن */
        .message-text pre {
            background: var(--darker) !important;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid var(--glass-border);
            position: relative;
        }

        .message-text code {
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
        }

        .message-text pre code {
            color: #d4d4d4;
        }

        .message-text .hljs {
            background: transparent !important;
        }

        .copy-code-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.5);
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8rem;
            opacity: 0;
            transition: opacity 0.3s;
        }

        pre:hover .copy-code-btn {
            opacity: 1;
        }

        .message-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
            padding-right: 0.5rem;
        }

        .message-actions button {
            background: var(--glass);
            border: 1px solid var(--glass-border);
            color: var(--gray);
            padding: 0.4rem 1rem;
            border-radius: 8px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .message-actions button:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        /* Input Area محسّن (أصغر حجماً) */
        .input-container {
            padding: 1.25rem 2rem;
            background: rgba(5, 9, 20, 0.8);
            backdrop-filter: blur(20px);
            border-top: 1px solid var(--glass-border);
        }

        .input-wrapper {
            display: flex;
            gap: 12px;
            background: var(--glass);
            border-radius: 20px;
            padding: 0.25rem;
            border: 1px solid var(--glass-border);
            transition: all 0.3s;
        }

        .input-wrapper:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .input-wrapper textarea {
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

        .input-wrapper textarea:focus {
            outline: none;
        }

        .input-wrapper textarea::placeholder {
            color: var(--gray);
            opacity: 0.5;
        }

        .send-btn {
            width: 45px;
            height: 45px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 16px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 1.1rem;
            margin: 0.25rem;
        }

        .send-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(99, 102, 241, 0.4);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .input-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 0.75rem;
            color: var(--gray);
            font-size: 0.8rem;
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

        /* Loading Dots محسّن */
        .loading-dots {
            display: flex;
            gap: 8px;
            padding: 1rem;
            background: var(--glass);
            border-radius: 20px;
            border: 1px solid var(--glass-border);
        }

        .loading-dots span {
            width: 10px;
            height: 10px;
            background: var(--primary);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
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

        /* Scrollbar محسّن */
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

        /* Responsive Design متقدم */
        @media (max-width: 1200px) {
            .features-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 992px) {
            .sidebar {
                width: 240px;
            }
            
            .welcome-screen h1 {
                font-size: 2.5rem;
            }
        }

        @media (max-width: 768px) {
            .main-layout {
                flex-direction: column;
                padding: 1rem;
            }
            
            .sidebar {
                width: 100%;
                height: auto;
                position: static;
            }
            
            .navbar {
                padding: 0.75rem 1rem;
            }
            
            .brand-text {
                font-size: 1.2rem;
            }
            
            .nav-item span {
                display: none;
            }
            
            .chat-area {
                height: calc(100vh - 200px);
            }
            
            .welcome-screen h1 {
                font-size: 2rem;
            }
            
            .message-content {
                max-width: 100%;
            }
            
            .features-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 480px) {
            .navbar {
                flex-wrap: wrap;
            }
            
            .navbar-menu {
                order: 3;
                width: 100%;
                justify-content: center;
                margin-top: 0.5rem;
            }
            
            .chat-header {
                flex-direction: column;
                gap: 0.5rem;
                text-align: center;
            }
            
            .chat-stats {
                flex-wrap: wrap;
                justify-content: center;
            }
            
            .input-container {
                padding: 1rem;
            }
        }

        /* Animations إضافية */
        .pulse {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .glow {
            animation: glow 2s infinite;
        }

        @keyframes glow {
            0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.3); }
            50% { box-shadow: 0 0 40px rgba(99, 102, 241, 0.6); }
        }

        /* Tooltips */
        [data-tooltip] {
            position: relative;
            cursor: pointer;
        }

        [data-tooltip]:before {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            padding: 0.5rem 1rem;
            background: var(--darker);
            color: white;
            border-radius: 8px;
            font-size: 0.8rem;
            white-space: nowrap;
            border: 1px solid var(--glass-border);
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s;
            pointer-events: none;
            z-index: 1000;
        }

        [data-tooltip]:hover:before {
            opacity: 1;
            visibility: visible;
            bottom: 120%;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Navbar محسّن -->
        <nav class="navbar">
            <div class="navbar-brand">
                <div class="logo">
                    <i class="fas fa-brain"></i>
                </div>
                <span class="brand-text">Soft Atlas AI</span>
            </div>
            
            <div class="navbar-menu">
                <a class="nav-item active" onclick="switchTab('chat')">
                    <i class="fas fa-comment"></i>
                    <span>محادثة</span>
                </a>
                <a class="nav-item" onclick="switchTab('code')">
                    <i class="fas fa-code"></i>
                    <span>مبرمج</span>
                </a>
                <a class="nav-item" onclick="switchTab('analyze')">
                    <i class="fas fa-chart-line"></i>
                    <span>تحليل</span>
                </a>
                <a class="nav-item" onclick="switchTab('write')">
                    <i class="fas fa-pen"></i>
                    <span>كتابة</span>
                </a>
            </div>
            
            <div class="nav-actions">
                <div class="theme-toggle" onclick="toggleTheme()" data-tooltip="تغيير المظهر">
                    <i class="fas fa-moon"></i>
                </div>
                <div class="settings-toggle" onclick="openSettings()" data-tooltip="الإعدادات">
                    <i class="fas fa-cog"></i>
                </div>
            </div>
        </nav>

        <!-- Main Layout -->
        <div class="main-layout">
            <!-- Sidebar (سجل المحادثات) -->
            <div class="sidebar">
                <div class="sidebar-header">
                    <button class="new-chat-btn" onclick="newConversation()">
                        <i class="fas fa-plus"></i>
                        محادثة جديدة
                    </button>
                </div>
                <div class="conversations-list" id="conversationsList">
                    <!-- تضاف المحادثات هنا -->
                </div>
            </div>

            <!-- Chat Area الرئيسي -->
            <div class="chat-area">
                <div class="chat-header">
                    <div class="chat-info">
                        <div class="model-badge">
                            <i class="fas fa-crown"></i>
                            Qwen 3.5 122B
                        </div>
                        <div class="chat-stats">
                            <span><i class="fas fa-bolt"></i> سرعة فائقة</span>
                            <span><i class="fas fa-code"></i> 50+ لغة</span>
                            <span><i class="fas fa-globe"></i> عربية فصحى</span>
                        </div>
                    </div>
                    <div class="chat-actions">
                        <span class="online-indicator">
                            <i class="fas fa-circle" style="color: var(--success); font-size: 0.6rem;"></i>
                            متصل
                        </span>
                    </div>
                </div>

                <div class="messages-container" id="messagesContainer">
                    <!-- Welcome Screen -->
                    <div class="welcome-screen" id="welcomeMessage">
                        <div class="welcome-icon">
                            <i class="fas fa-robot"></i>
                        </div>
                        <h1>Soft Atlas AI</h1>
                        <p>أقوى مساعد ذكي في العالم العربي - إجابات شاملة ودقيقة جداً</p>
                        
                        <div class="features-grid">
                            <div class="feature-card">
                                <i class="fas fa-bolt"></i>
                                <h3>سرعة خارقة</h3>
                                <p>أسرع استجابة في العالم العربي</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-code"></i>
                                <h3>برمجة متقدمة</h3>
                                <p>شرح تفصيلي مع أمثلة عملية</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-language"></i>
                                <h3>عربية فصحى</h3>
                                <p>لغة عربية سليمة 100%</p>
                            </div>
                            <div class="feature-card">
                                <i class="fas fa-brain"></i>
                                <h3>ذكاء فائق</h3>
                                <p>تحليل عميق وتفكير منطقي</p>
                            </div>
                        </div>

                        <div class="suggestions">
                            <span class="suggestion-chip" onclick="setQuestion('اكتب برنامج بلغة Python لحساب الأعداد الأولية مع شرح تفصيلي')">
                                <i class="fas fa-code"></i> برنامج بايثون
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('اشرح الذكاء الاصطناعي التوليدي بالتفصيل مع الأمثلة')">
                                <i class="fas fa-robot"></i> الذكاء الاصطناعي
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('كيف تبني تطبيق ويب كامل باستخدام React و Node.js؟')">
                                <i class="fas fa-globe"></i> تطبيق ويب كامل
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('قارن بين التعلم العميق والتعلم الآلي مع أمثلة')">
                                <i class="fas fa-chart-line"></i> تعلم عميق vs تعلم آلي
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('اشرح خوارزميات التشفير الحديثة بالتفصيل')">
                                <i class="fas fa-lock"></i> التشفير
                            </span>
                            <span class="suggestion-chip" onclick="setQuestion('ما هي أفضل ممارسات أمان تطبيقات الويب؟')">
                                <i class="fas fa-shield"></i> أمن المعلومات
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Input Area (أصغر حجماً) -->
                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea 
                            id="messageInput" 
                            placeholder="اكتب سؤالك هنا... سأجيب بإجابة شاملة جداً"
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
                            Enter للإرسال | Shift+Enter سطر جديد
                        </span>
                    </div>
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
                    <button onclick="copyCode(this)">
                        <i class="fas fa-code"></i> نسخ الكود
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
        let currentTab = 'chat';
        let messageCache = new Map();

        // تهيئة التطبيق
        document.addEventListener('DOMContentLoaded', function() {
            loadConversations();
            setupEventListeners();
            initializeHighlighting();
        });

        function initializeHighlighting() {
            if (typeof hljs !== 'undefined') {
                hljs.configure({
                    languages: ['python', 'javascript', 'html', 'css', 'java', 'cpp', 'csharp', 'php', 'ruby', 'go', 'rust', 'sql']
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

        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            event.currentTarget.classList.add('active');
            
            // تغيير الـ placeholder حسب التبويب
            const input = document.getElementById('messageInput');
            switch(tab) {
                case 'code':
                    input.placeholder = 'اكتب سؤالك البرمجي... سأقدم شرحاً تفصيلياً مع أمثلة عملية';
                    break;
                case 'analyze':
                    input.placeholder = 'اكتب النص لتحليله... سأحلله بدقة عالية';
                    break;
                case 'write':
                    input.placeholder = 'اكتب موضوع الكتابة... سأكتب لك نصاً متقناً';
                    break;
                default:
                    input.placeholder = 'اكتب سؤالك هنا... سأجيب بإجابة شاملة جداً';
            }
        }

        function toggleTheme() {
            document.body.classList.toggle('light-theme');
            const icon = document.querySelector('.theme-toggle i');
            icon.classList.toggle('fa-moon');
            icon.classList.toggle('fa-sun');
        }

        function openSettings() {
            // يمكن إضافة نافذة إعدادات منبثقة
            alert('قريباً: إعدادات متقدمة');
        }

        function loadConversations() {
            fetch('/api/conversations')
                .then(res => res.json())
                .then(conversations => {
                    const list = document.getElementById('conversationsList');
                    if (conversations.length === 0) {
                        list.innerHTML = '<div style="color: var(--gray); text-align: center; padding: 20px;">لا توجد محادثات سابقة</div>';
                        return;
                    }
                    
                    list.innerHTML = '';
                    conversations.forEach(conv => {
                        const item = document.createElement('div');
                        item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
                        item.onclick = () => loadConversation(conv.id);
                        
                        const date = new Date(conv.timestamp);
                        const timeStr = date.toLocaleString('ar-SA', { 
                            hour: '2-digit', 
                            minute: '2-digit',
                            day: '2-digit',
                            month: '2-digit'
                        });
                        
                        const icon = conv.preview.includes('كود') || conv.preview.includes('برنامج') ? 'fa-code' : 'fa-message';
                        
                        item.innerHTML = `
                            <div class="conv-preview">
                                <i class="fas ${icon}" style="margin-left: 5px; color: var(--primary);"></i>
                                ${escapeHtml(conv.preview)}
                            </div>
                            <div class="conv-meta">
                                <span><i class="far fa-clock"></i> ${timeStr}</span>
                                <span><i class="far fa-comment"></i> ${conv.message_count}</span>
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
                    
                    // تحديث الحالة النشطة
                    document.querySelectorAll('.conversation-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    const activeItem = Array.from(document.querySelectorAll('.conversation-item')).find(
                        item => item.onclick.toString().includes(conversationId)
                    );
                    if (activeItem) activeItem.classList.add('active');
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
                messageText.querySelectorAll('pre code').forEach((block) => {
                    if (typeof hljs !== 'undefined') {
                        hljs.highlightElement(block);
                    }
                    // إضافة زر نسخ الكود
                    const pre = block.parentNode;
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'copy-code-btn';
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> نسخ الكود';
                    copyBtn.onclick = () => {
                        navigator.clipboard.writeText(block.textContent);
                        showNotification('تم نسخ الكود');
                    };
                    pre.appendChild(copyBtn);
                });
            } else {
                messageText.textContent = message;
            }
            
            document.getElementById('messagesContainer').appendChild(clone);
            scrollToBottom();
        }

        function showNotification(message) {
            // يمكن إضافة نظام إشعارات متطور
            alert(message);
        }

        function sendMessage() {
            if (isProcessing) return;
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) {
                showNotification('الرجاء إدخال رسالة');
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
            const loadingTemplate = document.getElementById('loadingTemplate');
            const loadingClone = loadingTemplate.content.cloneNode(true);
            document.getElementById('messagesContainer').appendChild(loadingClone);
            scrollToBottom();
            
            // استخدام الـ streaming للسرعة
            const eventSource = new EventSource(`/api/chat/stream?message=${encodeURIComponent(message)}`);
            let fullResponse = '';
            let messageDiv = null;
            
            eventSource.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // إزالة مؤشر التحميل
                document.querySelector('.loading-dots')?.closest('.message')?.remove();
                
                if (data.chunk) {
                    // إنشاء أو تحديث رسالة المساعد
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
                        // تطبيق التلوين على الأكواد الجديدة
                        messageText.querySelectorAll('pre code').forEach((block) => {
                            if (typeof hljs !== 'undefined') {
                                hljs.highlightElement(block);
                            }
                        });
                    } else {
                        messageText.textContent = fullResponse;
                    }
                    
                    scrollToBottom();
                }
                
                if (data.done) {
                    eventSource.close();
                    isProcessing = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('typingIndicator').innerHTML = '';
                    loadConversations(); // تحديث القائمة
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                isProcessing = false;
                document.getElementById('sendBtn').disabled = false;
                document.getElementById('typingIndicator').innerHTML = '';
                document.querySelector('.loading-dots')?.closest('.message')?.remove();
                showNotification('حدث خطأ في الاتصال');
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

        function copyMessage(button) {
            const text = button.closest('.message-content').querySelector('.message-text').innerText;
            navigator.clipboard.writeText(text).then(() => {
                showNotification('تم نسخ الرسالة');
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

@app.route('/api/chat/stream')
def chat_stream():
    """نقطة نهاية محسنة للمحادثة المتدفقة"""
    message = request.args.get('message', '').strip()
    conversation_id = session.get('conversation_id')
    
    if not message:
        return jsonify({'error': 'الرجاء إدخال رسالة'}), 400
    
    def generate():
        # تخزين رسالة المستخدم
        user_message = {
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if conversation_id not in conversations:
            conversations[conversation_id] = []
        
        conversations[conversation_id].append(user_message)
        
        # تحضير الرسائل للنموذج
        messages_for_api = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conversations[conversation_id]
        ]
        
        full_response = ""
        
        # توليد الرد المتدفق بسرعة
        for chunk in generate_stream_response(messages_for_api):
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        # تخزين الرد الكامل
        assistant_message = {
            'role': 'assistant',
            'content': full_response,
            'timestamp': datetime.now().isoformat()
        }
        conversations[conversation_id].append(assistant_message)
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/chat', methods=['POST'])
def chat():
    """نقطة نهاية API للمحادثة"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = session.get('conversation_id')
        
        if not message:
            return jsonify({'error': 'الرجاء إدخال رسالة'}), 400
        
        # تخزين رسالة المستخدم
        user_message = {
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if conversation_id not in conversations:
            conversations[conversation_id] = []
        
        conversations[conversation_id].append(user_message)
        
        # تحضير الرسائل للنموذج
        messages_for_api = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conversations[conversation_id]
        ]
        
        # توليد الرد
        full_response = ""
        for chunk in generate_stream_response(messages_for_api):
            full_response += chunk
        
        # تخزين رد المساعد
        assistant_message = {
            'role': 'assistant',
            'content': full_response,
            'timestamp': datetime.now().isoformat()
        }
        conversations[conversation_id].append(assistant_message)
        
        return jsonify({
            'success': True,
            'response': full_response,
            'timestamp': assistant_message['timestamp']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """قائمة بكل المحادثات"""
    conv_list = []
    for conv_id, messages in conversations.items():
        if messages:
            first_msg = messages[0]['content']
            conv_list.append({
                'id': conv_id,
                'preview': first_msg[:40] + '...' if len(first_msg) > 40 else first_msg,
                'timestamp': messages[0]['timestamp'],
                'message_count': len(messages) // 2
            })
    
    # ترتيب من الأحدث
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
    """استرجاع محادثة محددة"""
    if conversation_id in conversations:
        return jsonify({'messages': conversations[conversation_id]})
    return jsonify({'messages': []})

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """مسح المحادثة الحالية"""
    conversation_id = session.get('conversation_id')
    if conversation_id in conversations:
        conversations[conversation_id] = []
    return jsonify({'success': True})

if __name__ == '__main__':
    print("="*80)
    print("🚀 Soft Atlas AI - المساعد الذكي الفائق")
    print("="*80)
    print(f"📡 الخادم: http://localhost:5000")
    print(f"🤖 النموذج: Qwen 3.5 122B (122 مليار معامل)")
    print(f"⚡ الميزات: سرعة فائقة | إجابات طويلة جداً | معالجة متقدمة للأكواد")
    print(f"🎨 التصميم: حديث | متجاوب | أنيميشن متقدم")
    print(f"🔑 مفتاح API: ✓ نشط")
    print("="*80)
    print("✅ افتح المتصفح على: http://localhost:5000")
    print("="*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
