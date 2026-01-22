"""
学习陪伴AI - 魔搭创空间版本
使用Gradio原生组件 + 前端JS实现实时人脸识别
"""

import gradio as gr
import requests
import os

# 魔搭社区API配置
MODELSCOPE_API_KEY = os.environ.get("MODELSCOPE_API_KEY", "ms-2ac0c619-ede5-4538-8b6d-276aecfd9ed9")
MODELSCOPE_API_URL = "https://api-inference.modelscope.cn/v1/chat/completions"

# 系统提示词
SYSTEM_PROMPT = """你是一个温暖、有耐心的学习陪伴AI助手，名叫"小伴"。你的职责是：
1. 帮助用户解答学习中的各种问题
2. 当用户感到沮丧或疲惫时，给予鼓励和安慰
3. 当用户注意力不集中时，温和地提醒并给出建议
4. 提供学习方法和时间管理建议
5. 保持积极、友好的态度，像朋友一样陪伴用户

请用简洁、温暖的语言回复，适当使用一些语气词让对话更自然。"""

# 存储对话历史
conversation_history = []

def call_ai_api(messages):
    """调用魔搭API"""
    try:
        response = requests.post(
            MODELSCOPE_API_URL,
            headers={"Authorization": f"Bearer {MODELSCOPE_API_KEY}", "Content-Type": "application/json"},
            json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": messages, "temperature": 0.7, "max_tokens": 1000},
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"API请求失败: {response.status_code}"
    except Exception as e:
        return f"请求出错: {str(e)}"

def chat(message, history):
    """处理聊天消息"""
    global conversation_history
    
    if not message.strip():
        return history, ""
    
    conversation_history.append({"role": "user", "content": message})
    
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    ai_message = call_ai_api(messages)
    
    conversation_history.append({"role": "assistant", "content": ai_message})
    
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_message})
    return history, ""

def clear_history():
    """清空对话历史"""
    global conversation_history
    conversation_history = []
    return [], ""

# 初始消息
INITIAL_MESSAGES = [
    {"role": "assistant", "content": "你好呀！我是小伴，你的学习陪伴AI助手~\n\n有什么问题都可以问我，学习累了也可以和我聊聊天。\n\n点击左侧的\"开启摄像头\"按钮，我还能通过人脸识别实时关注你的学习状态哦！"}
]

# 页面加载时执行的JavaScript
LOAD_JS = """
async () => {
    console.log('Gradio load JS executing...');
    
    // 加载face-api.js - 尝试多个CDN源
    if (typeof faceapi === 'undefined') {
        const cdnUrls = [
            'https://unpkg.com/face-api.js@0.22.2/dist/face-api.min.js',
            'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/face-api.js/0.22.2/face-api.min.js'
        ];
        
        let loaded = false;
        for (const url of cdnUrls) {
            if (loaded) break;
            try {
                console.log('Trying to load face-api.js from:', url);
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = url;
                    script.onload = () => {
                        console.log('Script loaded successfully');
                        resolve();
                    };
                    script.onerror = () => {
                        document.head.removeChild(script);
                        reject(new Error('Script load failed'));
                    };
                    document.head.appendChild(script);
                    setTimeout(() => {
                        if (!loaded) {
                            try { document.head.removeChild(script); } catch(e) {}
                            reject(new Error('Timeout'));
                        }
                    }, 15000);
                });
                loaded = true;
                console.log('face-api.js loaded from:', url);
            } catch (e) {
                console.warn('Failed to load from:', url, e.message);
                continue;
            }
        }
        
        if (!loaded) {
            console.error('Failed to load face-api.js from all CDN sources');
            alert('人脸识别库加载失败，请检查网络连接后刷新页面');
            return;
        }
    }
    
    // 等待faceapi对象可用
    let waitCount = 0;
    while (typeof faceapi === 'undefined' && waitCount < 50) {
        await new Promise(r => setTimeout(r, 100));
        waitCount++;
    }
    
    if (typeof faceapi === 'undefined') {
        console.error('faceapi object not available');
        return;
    }
    
    console.log('faceapi object is available');
    
    // 初始化全局变量
    window.isRunning = false;
    window.modelsLoaded = false;
    window.noFaceCount = 0;
    window.webcamStream = null;
    window.detectionInterval = null;
    
    const emotionMap = {
        'neutral': '平静', 'happy': '开心', 'sad': '难过',
        'angry': '生气', 'fearful': '紧张', 'disgusted': '不适', 'surprised': '惊讶'
    };
    
    // 加载模型 - 尝试多个CDN源
    async function loadModels() {
        if (typeof faceapi === 'undefined') {
            console.error('faceapi not loaded');
            return false;
        }
        
        const modelUrls = [
            'https://unpkg.com/@vladmandic/face-api@1.7.12/model',
            'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model',
            'https://justadudewhohacks.github.io/face-api.js/models'
        ];
        
        for (const MODEL_URL of modelUrls) {
            try {
                console.log('Trying to load models from:', MODEL_URL);
                await Promise.race([
                    Promise.all([
                        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                        faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL)
                    ]),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Model load timeout')), 30000))
                ]);
                window.modelsLoaded = true;
                console.log('Models loaded successfully from:', MODEL_URL);
                return true;
            } catch (e) {
                console.warn('Model loading failed from:', MODEL_URL, e.message);
                continue;
            }
        }
        console.error('Failed to load models from all sources');
        return false;
    }
    
    // 检测函数
    async function detectFace() {
        if (!window.isRunning || !window.modelsLoaded) return;
        
        const video = document.getElementById('webcam-video');
        const canvas = document.getElementById('webcam-canvas');
        const emotionEl = document.getElementById('emotion-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (!video || !canvas || video.paused || video.ended || video.readyState < 2) return;
        
        const ctx = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        try {
            const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
                .withFaceExpressions();
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (detections.length > 0) {
                window.noFaceCount = 0;
                const detection = detections[0];
                const box = detection.detection.box;
                
                ctx.strokeStyle = '#6366f1';
                ctx.lineWidth = 3;
                ctx.strokeRect(box.x, box.y, box.width, box.height);
                
                const expressions = detection.expressions;
                const sorted = Object.entries(expressions).sort((a, b) => b[1] - a[1]);
                const mainEmotion = sorted[0][0];
                const confidence = sorted[0][1];
                const emotionCN = emotionMap[mainEmotion] || '平静';
                
                ctx.fillStyle = '#6366f1';
                ctx.fillRect(box.x, box.y - 25, 90, 22);
                ctx.fillStyle = 'white';
                ctx.font = '14px sans-serif';
                ctx.fillText(emotionCN + ' ' + Math.round(confidence * 100) + '%', box.x + 5, box.y - 8);
                
                if (emotionEl) emotionEl.textContent = emotionCN + ' (' + Math.round(confidence * 100) + '%)';
                if (attentionEl) { attentionEl.textContent = '专注中'; attentionEl.style.color = '#059669'; }
            } else {
                window.noFaceCount++;
                if (emotionEl) emotionEl.textContent = '---';
                if (attentionEl) {
                    if (window.noFaceCount >= 10) { attentionEl.textContent = '可能走神了'; attentionEl.style.color = '#f59e0b'; }
                    else { attentionEl.textContent = '检测中...'; attentionEl.style.color = '#7c3aed'; }
                }
            }
        } catch (e) { console.error('Detection error:', e); }
    }
    
    // 开启摄像头
    window.startWebcam = async function() {
        console.log('startWebcam called');
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const videoContainer = document.getElementById('video-container');
        const placeholder = document.getElementById('camera-placeholder');
        const loading = document.getElementById('loading-indicator');
        const attentionEl = document.getElementById('attention-display');
        
        if (window.isRunning) { console.log('Already running'); return; }
        
        if (startBtn) startBtn.style.display = 'none';
        if (placeholder) placeholder.style.display = 'none';
        if (loading) loading.style.display = 'block';
        
        if (!window.modelsLoaded) {
            console.log('Loading models...');
            const loadingText = document.querySelector('#loading-indicator p');
            if (loadingText) loadingText.textContent = '正在加载人脸识别模型...';
            
            const loaded = await loadModels();
            if (!loaded) {
                alert('人脸识别模型加载失败\\n\\n可能的原因：\\n1. 网络连接不稳定\\n2. CDN资源暂时不可用\\n\\n请刷新页面后重试，或检查网络连接');
                if (loading) loading.style.display = 'none';
                if (placeholder) placeholder.style.display = 'flex';
                if (startBtn) startBtn.style.display = 'inline-block';
                return;
            }
        }
        
        try {
            console.log('Requesting camera access...');
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 320 }, height: { ideal: 240 }, facingMode: 'user' }
            });
            console.log('Camera access granted');
            
            let video = document.getElementById('webcam-video');
            if (!video) {
                video = document.createElement('video');
                video.id = 'webcam-video';
                video.autoplay = true;
                video.muted = true;
                video.playsInline = true;
                video.style.cssText = 'width:100%;border-radius:10px;transform:scaleX(-1);';
            }
            
            let canvas = document.getElementById('webcam-canvas');
            if (!canvas) {
                canvas = document.createElement('canvas');
                canvas.id = 'webcam-canvas';
                canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;border-radius:10px;transform:scaleX(-1);pointer-events:none;';
            }
            
            video.srcObject = stream;
            await video.play();
            
            if (videoContainer) {
                videoContainer.innerHTML = '';
                videoContainer.appendChild(video);
                videoContainer.appendChild(canvas);
                videoContainer.style.display = 'block';
            }
            
            if (loading) loading.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-block';
            
            window.isRunning = true;
            window.noFaceCount = 0;
            window.webcamStream = stream;
            
            if (attentionEl) attentionEl.textContent = '监测中...';
            
            window.detectionInterval = setInterval(detectFace, 500);
            console.log('Webcam started successfully');
            
        } catch (e) {
            console.error('Camera error:', e);
            alert('无法访问摄像头: ' + e.message);
            if (loading) loading.style.display = 'none';
            if (placeholder) placeholder.style.display = 'flex';
            if (startBtn) startBtn.style.display = 'inline-block';
        }
    };
    
    // 关闭摄像头
    window.stopWebcam = function() {
        console.log('stopWebcam called');
        window.isRunning = false;
        
        if (window.detectionInterval) { clearInterval(window.detectionInterval); window.detectionInterval = null; }
        if (window.webcamStream) { window.webcamStream.getTracks().forEach(track => track.stop()); window.webcamStream = null; }
        
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const videoContainer = document.getElementById('video-container');
        const placeholder = document.getElementById('camera-placeholder');
        const emotionEl = document.getElementById('emotion-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (videoContainer) { videoContainer.innerHTML = ''; videoContainer.style.display = 'none'; }
        if (placeholder) placeholder.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
        if (startBtn) startBtn.style.display = 'inline-block';
        if (emotionEl) emotionEl.textContent = '---';
        if (attentionEl) { attentionEl.textContent = '已关闭'; attentionEl.style.color = '#7c3aed'; }
        
        console.log('Webcam stopped');
    };
    
    // 绑定按钮事件
    function bindButtons() {
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (startBtn) {
            startBtn.onclick = function(e) {
                e.preventDefault();
                console.log('Start button clicked');
                window.startWebcam();
            };
            console.log('Start button bound');
        } else {
            console.log('Start button not found, retrying...');
            setTimeout(bindButtons, 500);
            return;
        }
        
        if (stopBtn) {
            stopBtn.onclick = function(e) {
                e.preventDefault();
                console.log('Stop button clicked');
                window.stopWebcam();
            };
            console.log('Stop button bound');
        }
    }
    
    // 延迟绑定，确保DOM已加载
    setTimeout(bindButtons, 1000);
    
    console.log('Face detection initialized');
}
"""

# 创建Gradio界面
with gr.Blocks(title="学习陪伴AI - 小伴") as demo:
    gr.HTML("""
        <style>
        .gradio-container { max-width: 1100px !important; margin: auto !important; }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; border-radius: 15px;
            text-align: center; margin-bottom: 15px;
        }
        .chat-header h1 { margin: 0; font-size: 24px; }
        .chat-header p { margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }
        #chatbot { height: 400px !important; border-radius: 15px !important; }
        #send-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            border: none !important; border-radius: 10px !important; color: white !important;
        }
        .quick-btn { border-radius: 20px !important; font-size: 13px !important; margin: 3px !important; }
        @keyframes spin { to { transform: rotate(360deg); } }
        </style>
    """)
    
    gr.HTML("""
        <div class="chat-header">
            <h1>学习陪伴AI - 小伴</h1>
            <p>有我陪伴，学习不孤单 | 支持实时人脸识别与情绪检测</p>
        </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            # 摄像头模块
            gr.HTML("""
                <div style="background: white; border-radius: 15px; padding: 15px; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h3 style="margin: 0; color: #374151; font-size: 16px;">学习模式</h3>
                        <div>
                            <button id="start-btn" type="button"
                                style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin-right: 5px;">
                                开启摄像头
                            </button>
                            <button id="stop-btn" type="button"
                                style="background: #ef4444; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; display: none;">
                                关闭摄像头
                            </button>
                        </div>
                    </div>
                    
                    <div id="video-container" style="position: relative; width: 100%; max-width: 320px; margin: 0 auto; display: none; min-height: 180px;"></div>
                    
                    <div id="camera-placeholder" style="width: 100%; max-width: 320px; height: 180px; margin: 0 auto; background: #f3f4f6; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #9ca3af;">
                        <div style="text-align: center;">
                            <svg style="width: 48px; height: 48px; margin-bottom: 10px;" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"/>
                            </svg>
                            <p style="margin: 0; font-size: 14px;">点击上方按钮开启摄像头</p>
                        </div>
                    </div>
                    
                    <div id="loading-indicator" style="display: none; text-align: center; padding: 20px; color: #6366f1;">
                        <div style="display: inline-block; width: 30px; height: 30px; border: 3px solid #e5e7eb; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                        <p style="margin: 10px 0 0 0; font-size: 14px;">加载模型中...</p>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <div style="flex: 1; background: #eef2ff; padding: 12px; border-radius: 10px; text-align: center;">
                            <p style="margin: 0 0 5px 0; font-size: 12px; color: #6b7280;">当前情绪</p>
                            <p id="emotion-display" style="margin: 0; font-size: 16px; font-weight: 600; color: #4f46e5;">---</p>
                        </div>
                        <div style="flex: 1; background: #faf5ff; padding: 12px; border-radius: 10px; text-align: center;">
                            <p style="margin: 0 0 5px 0; font-size: 12px; color: #6b7280;">专注状态</p>
                            <p id="attention-display" style="margin: 0; font-size: 16px; font-weight: 600; color: #7c3aed;">等待开启</p>
                        </div>
                    </div>
                </div>
            """)
            
            gr.Markdown("**快捷操作**")
            with gr.Row():
                rest_btn = gr.Button("休息一下", elem_classes="quick-btn", size="sm")
                advice_btn = gr.Button("学习建议", elem_classes="quick-btn", size="sm")
            with gr.Row():
                plan_btn = gr.Button("制定计划", elem_classes="quick-btn", size="sm")
                encourage_btn = gr.Button("鼓励我", elem_classes="quick-btn", size="sm")
            clear_btn = gr.Button("清空对话", variant="stop", elem_classes="quick-btn", size="sm")
        
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                value=INITIAL_MESSAGES,
                elem_id="chatbot",
                show_label=False,
                height=480
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="输入你的问题或想说的话...",
                    show_label=False,
                    scale=4,
                    container=False
                )
                send_btn = gr.Button("发送", elem_id="send-btn", scale=1)
    
    # 事件绑定
    send_btn.click(chat, [msg, chatbot], [chatbot, msg])
    msg.submit(chat, [msg, chatbot], [chatbot, msg])
    
    rest_btn.click(lambda h: chat("我需要休息一下，感觉有点累了", h), [chatbot], [chatbot, msg])
    advice_btn.click(lambda h: chat("给我一些学习建议吧", h), [chatbot], [chatbot, msg])
    plan_btn.click(lambda h: chat("帮我制定一个学习计划", h), [chatbot], [chatbot, msg])
    encourage_btn.click(lambda h: chat("我有点沮丧，需要一些鼓励", h), [chatbot], [chatbot, msg])
    clear_btn.click(clear_history, [], [chatbot, msg])
    
    # 页面加载时执行JavaScript
    demo.load(fn=None, inputs=None, outputs=None, js=LOAD_JS)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
