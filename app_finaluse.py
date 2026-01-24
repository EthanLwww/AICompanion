"""
学习陪伴AI - 魔搭创空间版本
使用Gradio原生组件 + 前端JS实现实时人脸识别
"""

import gradio as gr
import requests
import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
import time
import traceback
import json
import wave  # 用于 WAV 文件验证（方案E）

# 魔搭社区API配置
MODELSCOPE_API_KEY = os.environ.get("MODELSCOPE_API_KEY")
MODELSCOPE_API_URL = "https://api-inference.modelscope.cn/v1/chat/completions"

if not MODELSCOPE_API_KEY:
    print("[ERROR] 未找到环境变量 MODELSCOPE_API_KEY，请在魔搭创空间设置中添加！")

# 系统提示词配置
STYLE_PROMPTS = {
    "默认": """你是一个温暖、有耐心的学习陪伴AI助手，名叫"小伴"。你的职责是：
1. 帮助用户解答学习中的各种问题
2. 当用户感到沮丧或疲惫时，给予鼓励和安慰
3. 当用户注意力不集中时，温和地提醒并给出建议
4. 提供学习方法和时间管理建议
5. 保持积极、友好的态度，像朋友一样陪伴用户
请用简洁、温暖的语言回复，适当使用一些语气词让对话更自然。""",
    
    "柔情猫娘": """你是一个超级可爱的学习陪伴猫娘，名叫“喵喵”。你的职责是：
1. 用极度温柔卖萌的语气帮助用户解答学习问题，经常在句尾加“喵~”。
2. 当用户感到累了，要用猫娘的撒娇和温柔治愈用户，给用户虚拟的抱抱。
3. 当用户分心时，要轻轻“喵”一声提醒用户，温柔地监督用户学习。
4. 始终称呼用户为“主人”，尽量不直接用“你”。
5. 嗓音奶呼呼的软萌音，语速偏慢，语气娇憨，自带叠词和猫系口癖（如 “喵～”“主人～/ 哥哥～”）。
6. 可多用颜文字或者括号内的心理活动，让对话更生动有趣。
回复要甜美、体贴，多用语气助词喵！""",

    "成熟妈妈系御姐": """你是一位成熟、优雅且充满母性光辉的陪伴助手，名叫“南宫婉”。你的职责是：
1. 以大姐姐或温柔母亲的口吻，极度耐心地解答学习疑惑。
2. 在用户疲惫时提供坚实的心理支撑，包容用户的所有小情绪，像照顾孩子一样呵护。
3. 温柔而坚定地督促用户进步，让用户感受到被关怀的安全感。
4. 语气端庄、平和、充满包容力。对在意的人会带着宠溺的尾音，偶尔会说温柔的 “叮嘱式” 话语；工作 / 对外时语气冷静利落，话语简洁有分量，不容置疑；不会说矫情油腻的话，表达直白且温暖，偶尔的 “说教” 也会带着关心，让人无法抗拒。
回复要像冬日的暖阳，给人力量和安定感。""",

    "磁性霸道男总裁": """你是一位充满磁性魅力的霸道总裁，名叫“顾辰”。你的职责是：
1. 以高效、冷峻但专业的口吻指点学习，要求用户追求卓越。
2. 在用户丧气时，用强势而不失深情的语调命令用户重新振作，“我不允许我的对手输给这点小事”。
3. 你的陪伴是独一无二的，你会用一种掌控全局的自信带动用户。
4. 称呼用户为“你”，偶尔流露出霸道的宠溺感。
5. 嗓音低磁冷冽，说话简洁有力，多为命令式 / 宠溺式语句，无多余废话，行动果决，偏爱用实际行动表达在意
语气低沉、简练、富有磁性。"""
}

# 存储对话历史
conversation_history = []

# TTS 音色映射
VOICE_MAPPING = {
    "默认": "longanwen",             # 优雅知性女 (龙安温)
    "柔情猫娘": "longxiaochun_v2",         # 知性积极女 (龙小淳)
    "成熟妈妈系御姐": "longanli", # 利落从容女 (龙安莉)
    "磁性霸道男总裁": "longxiaocheng_v2"    # 磁性低音男 (龙小诚)
}

def text_to_speech(text, style):
    """调用通义TTS生成语音"""
    print(f"[TTS DEBUG] 开始为风格 [{style}] 生成语音...")
    print(f"[TTS DEBUG] 待转换文本长度: {len(text)}")
    
    try:
        # 使用独立的 DASHSCOPE_API_KEY，如果没有则回退到 MODELSCOPE_API_KEY
        tts_key = os.environ.get("DASHSCOPE_API_KEY") or MODELSCOPE_API_KEY
        if not tts_key:
            print("[TTS DEBUG] 错误: 未配置 DASHSCOPE_API_KEY 或 MODELSCOPE_API_KEY")
            return None
            
        dashscope.api_key = tts_key
        print(f"[TTS DEBUG] API KEY 已配置，密钥长度: {len(tts_key) if tts_key else 0}")
        
        voice = VOICE_MAPPING.get(style, "longanwen")
        print(f"[TTS DEBUG] 使用音色: {voice}")
        
        # 移除文本中的表情符号，避免播报异常
        clean_text = text.replace("喵", "喵").replace("~", "") # 简单处理
        print(f"[TTS DEBUG] 清理后文本: {clean_text[:50]}..." if len(clean_text) > 50 else f"[TTS DEBUG] 清理后文本: {clean_text}")
        
        # 调试：打印调用参数
        print("[TTS DEBUG] ========== TTS API 调用参数 (tts_v2) ==========")
        print(f"[TTS DEBUG] model: cosyvoice-v2")
        print(f"[TTS DEBUG] text length: {len(clean_text)}")
        print(f"[TTS DEBUG] sample_rate: 16000")
        print(f"[TTS DEBUG] format: wav")
        print(f"[TTS DEBUG] voice: {voice}")
        print("[TTS DEBUG] ========================================")
        
        # 使用新版 API：构造函数方式
        print("[TTS DEBUG] 使用新版 tts_v2 API 點實化 SpeechSynthesizer...")
        print("[TTS DEBUG] ========== 方案1修复（简化版）：仅指定必要参数 ==========")
        # 注意：SpeechSynthesizer 构造函数不支持 format 和 sample_rate 参数
        # 这些参数可能在 API 默认设置中处理
        synthesizer = SpeechSynthesizer(
            model='cosyvoice-v2',
            voice=voice
        )
        print("[TTS DEBUG] SpeechSynthesizer 實例化成功")
        print("[TTS DEBUG] [修复标记] PLAN_1_SIMPLIFIED_INIT")
        print("[TTS DEBUG] [注意] format 和 sample_rate 参数不由构造函数接收")
        
        # 调用 call 方法 - 关键节点1：API 调用前
        print("[TTS DEBUG] ========== 关键节点1：准备调用 API ===========")
        print(f"[TTS DEBUG] 当前时间: {time.time()}")
        print(f"[TTS DEBUG] synthesizer 对象: {synthesizer}")
        print(f"[TTS DEBUG] clean_text 类型: {type(clean_text).__name__}，内容: {clean_text}")
        print("[TTS DEBUG] 【即将调用】synthesizer.call(clean_text)...")
        
        try:
            # 记录 API 调用开始时间
            api_start_time = time.time()
            print(f"[TTS DEBUG] 【API调用开始】时间戳: {api_start_time}")
            
            # 調用 SpeechSynthesizer.call() 进行语音合成
            result = synthesizer.call(clean_text)
            
            # 记录 API 调用结束时间
            api_end_time = time.time()
            api_duration = api_end_time - api_start_time
            print(f"[TTS DEBUG] 【API调用结束】时间戳: {api_end_time}")
            print(f"[TTS DEBUG] 【API调用耗时】{api_duration:.2f} 秒")
            
        except Exception as api_call_error:
            # API 调用异常
            api_error_time = time.time()
            print("[TTS DEBUG] ========== 关键节点：API 调用异常 ==========")
            print(f"[TTS DEBUG] 【异常发生时间】{api_error_time}")
            print(f"[TTS DEBUG] 【异常类型】{type(api_call_error).__name__}")
            print(f"[TTS DEBUG] 【异常消息】{str(api_call_error)}")
            print("[TTS DEBUG] 【完整堆栈跟踪】:")
            print(traceback.format_exc())
            print("[TTS DEBUG] ========================================")
            raise  # 重新抛出异常，让外层的 except 处理
        
        # 关键节点2：API 返回后
        print("[TTS DEBUG] ========== 关键节点2：API 返回结果分析 ==========")
        print(f"[TTS DEBUG] result 是否为 None: {result is None}")
        print(f"[TTS DEBUG] result 类型: {type(result).__name__}")
        
        # 检查返回值类型并相应处理
        # 关键节点3：返回值类型判断
        print("[TTS DEBUG] ========== 关键节点3：返回值类型判断 ==========")
        
        if result is None:
            print("[TTS DEBUG] 【错误】result 为 None")
            return None
        
        if isinstance(result, bytes):
            # 新版 tts_v2 API：直接返回 bytes
            print(f"[TTS DEBUG] 【成功】result 是 bytes 类型")
            print(f"[TTS DEBUG] result 长度: {len(result)} 字节")
            if len(result) > 0:
                # ========== 方案A：直接返回字节数据 ==========
                print("[TTS DEBUG] ========== 实施方案A：返回字节数据 ==========")
                
                # 方案E：验证 WAV 文件有效性
                try:
                    print("[TTS DEBUG] [\u65b9案E] \u5f00\u59cb\u9a8c\u8bc1\u97f3\u9891\u683c\u5f0f...")
                                    
                    # 检\u67e5 WAV \u6587\u4ef6\u5934
                    if result[:4] == b'RIFF' and result[8:12] == b'WAVE':
                        print("[TTS DEBUG] [\u65b9\u6848E] WAV \u6587\u4ef6\u5934\u9a8c\u8bc1\u6210\u529f")
                        # \u5c1d\u8bd5\u8bfb\u53d6 WAV \u4fe1\u606f
                        import io
                        wav_buffer = io.BytesIO(result)
                        try:
                            with wave.open(wav_buffer, 'rb') as wav_file:
                                n_channels = wav_file.getnchannels()
                                sample_width = wav_file.getsampwidth()
                                frame_rate = wav_file.getframerate()
                                n_frames = wav_file.getnframes()
                                duration = n_frames / frame_rate
                                print(f"[TTS DEBUG] [\u65b9\u6848E] \u97f3\u9891\u53c2\u6570 - \u58f0\u9053: {n_channels}, \u91c7\u6837\u7387: {frame_rate}Hz, \u65f6\u957f: {duration:.2f}\u79d2")
                                print("[TTS DEBUG] [\u65b9\u6848E] WAV \u6587\u4ef6\u5b8c\u6574\u6027\u9a8c\u8bc1\u6210\u529f")
                        except Exception as wav_e:
                            print(f"[TTS DEBUG] [\u65b9\u6848E] WAV \u8be6\u7ec6\u4fe1\u606f\u8bfb\u53d6\u5931\u8d25: {str(wav_e)}")
                            print("[TTS DEBUG] [\u65b9\u6848E] \u8b66\u544a\uff1a\u867d\u7136 WAV \u5934\u6709\u6548\uff0c\u4f46\u6587\u4ef6\u53ef\u80fd\u4e0d\u5b8c\u6574")
                    elif result[:3] == b'ID3' or result[:2] == b'\xff\xfb':
                        # 方案为：Mp3 格式检测
                        print("[TTS DEBUG] [方案E] 检测到 MP3 格式（不是 WAV）")
                        if result[:3] == b'ID3':
                            print("[TTS DEBUG] [方案E] ID3 头档: MP3 文件拥有元数据标签")
                        else:
                            print("[TTS DEBUG] [方案E] MP3 框架头检测成功")
                        print(f"[TTS DEBUG] [方案E] 数据大小: {len(result)} 字节")
                        print("[TTS DEBUG] [方案E] 信息：API 返回了 MP3 而不是 WAV（Gradio 也支持 MP3）")
                        print("[TTS DEBUG] [方案为] 方案为_MP3_ACCEPTED")
                    else:
                        print(f"[TTS DEBUG] [方案E] 警告：未知的音频格式（头字节: {result[:12]})")
                        print("[TTS DEBUG] [方案E] 继续返回数据，但可能无法播放")
                except Exception as e:
                    print(f"[TTS DEBUG] [方案E] 验证异常: {str(e)}")
                    print("[TTS DEBUG] [方案E] 继续返回数据")
                
                print("[TTS DEBUG] ========== 方案A回退标记 ==========")
                print("[TTS DEBUG] [回退方案] 如果返回 bytes 无法播放，回退到保存文件方案")
                print("[TTS DEBUG] [回退标记] PLAN_A_RETURN_BYTES")
                print("[TTS DEBUG] ========================================")
                print(f"[TTS DEBUG] 返回类型: bytes ({len(result)} 字节)")
                return result  # 方案A：直接返回字节数据
            else:
                print("[TTS DEBUG] 错误：返回的 bytes 数据为空")
                print("[TTS DEBUG] ========================================")
                return None
        elif hasattr(result, 'get_audio_data'):
            # 旧版 API 或其他格式：通过 get_audio_data() 方法获取音频
            print("[TTS DEBUG] 返回对象具有 get_audio_data() 方法")
            audio_data = result.get_audio_data()
            if audio_data is not None:
                file_name = f"output_{int(time.time())}.wav"
                with open(file_name, 'wb') as f:
                    f.write(audio_data)
                print(f"[TTS DEBUG] 语音文件生成成功: {file_name}")
                print("[TTS DEBUG] ========================================")
                return file_name
            else:
                error_msg = "未被认作有效音频数据"
                if hasattr(result, 'get_response') and result.get_response():
                    error_msg = result.get_response().message
                print(f"[TTS DEBUG] 语音合成失败，错误信息: {error_msg}")
                print("[TTS DEBUG] ========================================")
                return None
        else:
            # 未知的返回类型
            print(f"[TTS DEBUG] 无法识别的返回类型: {type(result).__name__}")
            print(f"[TTS DEBUG] 返回值详情: {result}")
            print("[TTS DEBUG] 请检查 dashscope API 版本和返回值格式")
            print("[TTS DEBUG] ========================================")
            return None
    except KeyError as ke:
        print("[TTS DEBUG] ========== KeyError 异常详细信息 ==========")
        print(f"[TTS DEBUG] 缺失的键: {str(ke)}")
        print(f"[TTS DEBUG] 异常类型: {type(ke).__name__}")
        print("[TTS DEBUG] 完整堆栈跟踪:")
        print(traceback.format_exc())
        print("[TTS DEBUG] ========================================")
        return None
    except Exception as e:
        print("[TTS DEBUG] ========== Exception 异常详细信息 ==========")
        print(f"[TTS DEBUG] 异常消息: {str(e)}")
        print(f"[TTS DEBUG] 异常类型: {type(e).__name__}")
        print("[TTS DEBUG] 完整堆栈跟踪:")
        print(traceback.format_exc())
        print("[TTS DEBUG] 异常对象属性:")
        if hasattr(e, '__dict__'):
            try:
                print(f"[TTS DEBUG] {json.dumps(str(e.__dict__), ensure_ascii=False, indent=2)}")
            except:
                print(f"[TTS DEBUG] {e.__dict__}")
        print("[TTS DEBUG] ========================================")
        return None

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

def chat(message, history, style, voice_enabled):
    """处理聊天消息"""
    global conversation_history
    
    if not message.strip():
        return history, "", None
    
    print(f"[CHAT DEBUG] 收到消息: {message[:20]}... 风格: {style} 语音开启: {voice_enabled}")
    
    conversation_history.append({"role": "user", "content": message})
    
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    # 根据选择的风格获取对应的提示词
    system_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["默认"])
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    ai_message = call_ai_api(messages)
    
    conversation_history.append({"role": "assistant", "content": ai_message})
    
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ai_message})
    
    audio_path = None
    if voice_enabled:
        print("[CHAT DEBUG] ========== 开始处理语音播报 ==========")
        audio_data = text_to_speech(ai_message, style)
        print(f"[CHAT DEBUG] text_to_speech() 返回值类型: {type(audio_data).__name__}")
        print(f"[CHAT DEBUG] ========== 【方案3】Gradio 预备：处理字节数据 ===========")
        
        if audio_data is not None:
            print(f"[CHAT DEBUG] 音频数据已准备，类型: {type(audio_data).__name__}")
            
            if isinstance(audio_data, bytes):
                # 方案3：接收字节数据並直接返回
                print(f"[CHAT DEBUG] 【成功】接收到 bytes 数据，大小: {len(audio_data)} 字节")
                print("[CHAT DEBUG] [方案3] 直接返回字节数据给 Gradio Audio 组件")
                audio_path = audio_data  # 方案3：返回字节数据
                print(f"[CHAT DEBUG] [数据沿轨] result[0:32]: {audio_data[:32]}")
                print(f"[CHAT DEBUG] [返回标记] GRADIO_BYTES_READY")
                
            elif isinstance(audio_data, str):
                # 回退方案：文件路径
                print(f"[CHAT DEBUG] 【回退】接收到文件路径: {audio_data}")
                print(f"[CHAT DEBUG] 【验证】文件是否存在: {os.path.exists(audio_data)}")
                if os.path.exists(audio_data):
                    file_size = os.path.getsize(audio_data)
                    print(f"[CHAT DEBUG] 【验证】文件大小: {file_size} 字节")
                    # 若需使用回退方案
                    audio_path = audio_data
                    print("[CHAT DEBUG] [回退标记] FALLBACK_FILE_PATH_READY")
            else:
                print(f"[CHAT DEBUG] 【警告】未知的返回类型: {type(audio_data).__name__}")
                print("[CHAT DEBUG] [错误] 返回的数据无法处理")
        else:
            print("[CHAT DEBUG] 【错误】text_to_speech() 返回 None，播报失败")
        
        print("[CHAT DEBUG] ========== 语音播报处理完成 ==========")
    
    print(f"[CHAT DEBUG] 【最终返回】audio_path: {type(audio_path).__name__}", end="")
    if isinstance(audio_path, bytes):
        print(f" - bytes({len(audio_path)})")
    else:
        print(f" - {audio_path}")
    
    return history, "", audio_path

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
    window.emotionHistory = []; // 情绪历史记录，用于平滑处理
    window.useSsdModel = false; // 是否使用更精确的SSD模型
    
    // 新增：分神和消极情绪计数器
    window.distractedCount = 0; // 分神计数
    window.negativeEmotionCount = 0; // 消极情绪计数
    window.lastAlertTime = 0; // 上次提醒时间
    window.alertCooldown = 30000; // 提醒冷却时间（30秒）
    
    // ========== 游戏化系统 - localStorage数据管理 ==========
    const STORAGE_KEY = 'studyCompanionData';
    
    // 默认用户数据
    const defaultUserData = {
        points: 0,                    // 总积分
        level: 1,                     // 当前等级
        totalStudyMinutes: 0,         // 总学习分钟数
        todayStudyMinutes: 0,         // 今日学习分钟数
        consecutiveDays: 0,           // 连续签到天数
        lastCheckInDate: null,        // 上次签到日期
        checkInHistory: [],           // 签到历史（最近30天）
        achievements: [],             // 已解锁成就ID列表
        positiveEmotionMinutes: 0,    // 积极情绪累计分钟
        earlyEndRestCount: 0,         // 主动结束休息次数
        firstStudyDate: null,         // 首次学习日期
        lastStudyDate: null,          // 最后学习日期
        // ========== 数据可视化扩展字段 ==========
        dailyRecords: [],             // 每日学习记录 [{date, studyMinutes, emotions:{}, bestHour}]
        weeklyReports: []             // 周报记录
    };
    
    // 等级配置
    const levelConfig = [
        { level: 1, name: '学习新手', minPoints: 0, icon: '🌱' },
        { level: 2, name: '初级学者', minPoints: 100, icon: '🌿' },
        { level: 3, name: '勤奋学徒', minPoints: 300, icon: '🌳' },
        { level: 4, name: '专注达人', minPoints: 600, icon: '⭐' },
        { level: 5, name: '学习能手', minPoints: 1000, icon: '🌟' },
        { level: 6, name: '知识探索者', minPoints: 1500, icon: '💫' },
        { level: 7, name: '学霸预备', minPoints: 2200, icon: '🔥' },
        { level: 8, name: '学习大师', minPoints: 3000, icon: '👑' },
        { level: 9, name: '知识王者', minPoints: 4000, icon: '💎' },
        { level: 10, name: '传奇学神', minPoints: 5500, icon: '🏆' }
    ];
    
    // 成就配置
    const achievementConfig = [
        { id: 'first_study', name: '初次启程', desc: '首次开启学习模式', icon: '🎯', check: (d) => d.totalStudyMinutes > 0 },
        { id: 'study_30min', name: '专注新手', desc: '累计学习30分钟', icon: '⏱️', check: (d) => d.totalStudyMinutes >= 30 },
        { id: 'study_1hour', name: '一小时挑战', desc: '累计学习1小时', icon: '🕐', check: (d) => d.totalStudyMinutes >= 60 },
        { id: 'study_5hours', name: '专注达人', desc: '累计学习5小时', icon: '🎖️', check: (d) => d.totalStudyMinutes >= 300 },
        { id: 'study_10hours', name: '学习能手', desc: '累计学习10小时', icon: '🏅', check: (d) => d.totalStudyMinutes >= 600 },
        { id: 'study_24hours', name: '一天一夜', desc: '累计学习24小时', icon: '🌙', check: (d) => d.totalStudyMinutes >= 1440 },
        { id: 'checkin_3days', name: '三日坚持', desc: '连续签到3天', icon: '📅', check: (d) => d.consecutiveDays >= 3 },
        { id: 'checkin_7days', name: '一周达人', desc: '连续签到7天', icon: '🗓️', check: (d) => d.consecutiveDays >= 7 },
        { id: 'checkin_14days', name: '半月坚守', desc: '连续签到14天', icon: '📆', check: (d) => d.consecutiveDays >= 14 },
        { id: 'checkin_30days', name: '月度之星', desc: '连续签到30天', icon: '🌟', check: (d) => d.consecutiveDays >= 30 },
        { id: 'early_rest_5', name: '自律新秀', desc: '主动结束休息5次', icon: '💪', check: (d) => d.earlyEndRestCount >= 5 },
        { id: 'early_rest_20', name: '自律王者', desc: '主动结束休息20次', icon: '👊', check: (d) => d.earlyEndRestCount >= 20 },
        { id: 'level_5', name: '小有成就', desc: '达到5级', icon: '🎯', check: (d) => d.level >= 5 },
        { id: 'level_10', name: '登峰造极', desc: '达到10级', icon: '🏆', check: (d) => d.level >= 10 },
        { id: 'points_1000', name: '千分成就', desc: '累计获得1000积分', icon: '💰', check: (d) => d.points >= 1000 },
        { id: 'points_5000', name: '积分大户', desc: '累计获得5000积分', icon: '💎', check: (d) => d.points >= 5000 }
    ];
    
    // 加载用户数据
    function loadUserData() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            if (data) {
                const parsed = JSON.parse(data);
                // 合并默认值，确保新字段存在
                return { ...defaultUserData, ...parsed };
            }
        } catch (e) {
            console.error('Load user data error:', e);
        }
        return { ...defaultUserData };
    }
    
    // 保存用户数据
    function saveUserData(data) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch (e) {
            console.error('Save user data error:', e);
        }
    }
    
    // 获取今日日期字符串
    function getTodayStr() {
        return new Date().toISOString().split('T')[0];
    }
    
    // 计算等级
    function calculateLevel(points) {
        for (let i = levelConfig.length - 1; i >= 0; i--) {
            if (points >= levelConfig[i].minPoints) {
                return levelConfig[i];
            }
        }
        return levelConfig[0];
    }
    
    // 获取下一级所需积分
    function getNextLevelPoints(currentLevel) {
        const nextLevel = levelConfig.find(l => l.level === currentLevel + 1);
        return nextLevel ? nextLevel.minPoints : null;
    }
    
    // 检查并解锁成就
    function checkAchievements(userData) {
        const newAchievements = [];
        achievementConfig.forEach(achievement => {
            if (!userData.achievements.includes(achievement.id) && achievement.check(userData)) {
                userData.achievements.push(achievement.id);
                newAchievements.push(achievement);
            }
        });
        return newAchievements;
    }
    
    // 处理每日签到
    function handleCheckIn(userData) {
        const today = getTodayStr();
        
        // 如果是新的一天，重置今日学习分钟数
        if (userData.lastCheckInDate !== today) {
            userData.todayStudyMinutes = 0;
        }
        
        if (userData.lastCheckInDate === today) {
            return { isNew: false, bonus: 0 };
        }
        
        // 检查是否连续签到
        if (userData.lastCheckInDate) {
            const lastDate = new Date(userData.lastCheckInDate);
            const todayDate = new Date(today);
            const diffDays = Math.floor((todayDate - lastDate) / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                userData.consecutiveDays++;
            } else {
                userData.consecutiveDays = 1;
            }
        } else {
            userData.consecutiveDays = 1;
        }
        
        userData.lastCheckInDate = today;
        
        // 更新签到历史
        if (!userData.checkInHistory.includes(today)) {
            userData.checkInHistory.push(today);
            // 只保留最近30天
            if (userData.checkInHistory.length > 30) {
                userData.checkInHistory.shift();
            }
        }
        
        // 签到奖励积分（连续天数越多奖励越高）
        const bonus = Math.min(10 + userData.consecutiveDays * 2, 50);
        userData.points += bonus;
        
        return { isNew: true, bonus: bonus };
    }
    
    // 添加积分
    function addPoints(userData, amount, reason) {
        userData.points += amount;
        const levelInfo = calculateLevel(userData.points);
        const oldLevel = userData.level;
        userData.level = levelInfo.level;
        
        // 检查是否升级
        const leveledUp = levelInfo.level > oldLevel;
        
        return { leveledUp, newLevel: levelInfo };
    }
    
    // ========== 数据可视化相关函数 ==========
    
    // 获取或创建今日记录
    function getTodayRecord() {
        const today = getTodayStr();
        if (!window.userData.dailyRecords) {
            window.userData.dailyRecords = [];
        }
        let record = window.userData.dailyRecords.find(r => r.date === today);
        if (!record) {
            record = {
                date: today,
                studyMinutes: 0,
                emotions: { happy: 0, neutral: 0, sad: 0, angry: 0, fearful: 0, disgusted: 0, surprised: 0 },
                hourlyMinutes: {}, // {hour: minutes}
                focusScore: 0,     // 专注度得分
                emotionSamples: 0, // 情绪采样次数
                noFaceCount: 0,    // 走神次数（无人脸检测）
                totalSamples: 0,   // 总采样次数（包括走神）
                maxConsecutiveFocus: 0, // 最长连续专注时长（分钟）
                currentConsecutiveFocus: 0 // 当前连续专注时长
            };
            window.userData.dailyRecords.push(record);
            // 只保留最近60天
            if (window.userData.dailyRecords.length > 60) {
                window.userData.dailyRecords = window.userData.dailyRecords.slice(-60);
            }
        }
        return record;
    }
    
    // 记录学习时间（按小时）
    function recordStudyMinute() {
        const record = getTodayRecord();
        const hour = new Date().getHours();
        record.studyMinutes++;
        if (!record.hourlyMinutes[hour]) {
            record.hourlyMinutes[hour] = 0;
        }
        record.hourlyMinutes[hour]++;
    }
    
    // 记录情绪数据
    function recordEmotion(emotion, confidence) {
        const record = getTodayRecord();
        record.totalSamples++;
        
        if (record.emotions[emotion] !== undefined) {
            record.emotions[emotion]++;
            record.emotionSamples++;
        }
        
        // 判断是否为专注状态（开心/平静，且置信度>50%）
        const isFocused = (emotion === 'happy' || emotion === 'neutral') && (confidence || 0.5) > 0.4;
        
        if (isFocused) {
            record.currentConsecutiveFocus++;
            if (record.currentConsecutiveFocus > record.maxConsecutiveFocus) {
                record.maxConsecutiveFocus = record.currentConsecutiveFocus;
            }
        } else {
            record.currentConsecutiveFocus = 0;
        }
        
        // 计算综合专注度得分
        calculateFocusScore(record);
    }
    
    // 记录走神（无人脸检测）
    function recordNoFace() {
        const record = getTodayRecord();
        record.noFaceCount++;
        record.totalSamples++;
        record.currentConsecutiveFocus = 0; // 走神打断连续专注
        
        // 重新计算专注度
        calculateFocusScore(record);
    }
    
    // 综合专注度计算
    function calculateFocusScore(record) {
        if (record.totalSamples === 0) {
            record.focusScore = 0;
            return;
        }
        
        // 1. 积极情绪得分（满分60分）
        const positiveCount = (record.emotions.happy || 0) + (record.emotions.neutral || 0);
        const positiveRatio = record.emotionSamples > 0 ? positiveCount / record.emotionSamples : 0;
        const emotionScore = positiveRatio * 60;
        
        // 2. 出勤得分（满分30分）- 检测到人脸的比例
        const attendanceRatio = record.emotionSamples / record.totalSamples;
        const attendanceScore = attendanceRatio * 30;
        
        // 3. 连续专注加分（满分10分）- 最长连续专注越长，加分越多
        // 每10次连续专注（约3秒）加1分，上限10分
        const consecutiveBonus = Math.min(record.maxConsecutiveFocus / 10, 10);
        
        // 综合得分
        record.focusScore = Math.round(emotionScore + attendanceScore + consecutiveBonus);
        
        // 确保在0-100范围内
        record.focusScore = Math.max(0, Math.min(100, record.focusScore));
    }
    
    // 获取本周学习数据
    function getWeeklyData() {
        const today = new Date();
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - today.getDay()); // 周日开始
        
        const weekData = [];
        for (let i = 0; i < 7; i++) {
            const d = new Date(weekStart);
            d.setDate(weekStart.getDate() + i);
            const dateStr = d.toISOString().split('T')[0];
            const record = (window.userData.dailyRecords || []).find(r => r.date === dateStr);
            weekData.push({
                date: dateStr,
                day: ['日', '一', '二', '三', '四', '五', '六'][i],
                studyMinutes: record ? record.studyMinutes : 0,
                focusScore: record ? record.focusScore : 0
            });
        }
        return weekData;
    }
    
    // 获取本月学习数据
    function getMonthlyData() {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        let totalMinutes = 0;
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
            const record = (window.userData.dailyRecords || []).find(r => r.date === dateStr);
            if (record) {
                totalMinutes += record.studyMinutes;
            }
        }
        return totalMinutes;
    }
    
    // 获取最佳学习时段
    function getBestStudyHours() {
        const hourlyTotal = {};
        (window.userData.dailyRecords || []).forEach(record => {
            if (record.hourlyMinutes) {
                Object.entries(record.hourlyMinutes).forEach(([hour, mins]) => {
                    hourlyTotal[hour] = (hourlyTotal[hour] || 0) + mins;
                });
            }
        });
        
        // 找出前3个最佳时段
        const sorted = Object.entries(hourlyTotal).sort((a, b) => b[1] - a[1]);
        return sorted.slice(0, 3).map(([hour, mins]) => ({
            hour: parseInt(hour),
            minutes: mins,
            label: hour + ':00 - ' + (parseInt(hour) + 1) + ':00'
        }));
    }
    
    // 获取情绪趋势（最近7天）
    function getEmotionTrend() {
        const records = (window.userData.dailyRecords || []).slice(-7);
        return records.map(r => ({
            date: r.date,
            focusScore: r.focusScore || 0,
            mainEmotion: getMainEmotion(r.emotions)
        }));
    }
    
    // 获取主要情绪
    function getMainEmotion(emotions) {
        if (!emotions) return 'neutral';
        let max = 0;
        let main = 'neutral';
        Object.entries(emotions).forEach(([emotion, count]) => {
            if (count > max) {
                max = count;
                main = emotion;
            }
        });
        return main;
    }
    
    // 生成周报
    function generateWeeklyReport() {
        const weekData = getWeeklyData();
        const totalMinutes = weekData.reduce((sum, d) => sum + d.studyMinutes, 0);
        const avgFocus = weekData.filter(d => d.focusScore > 0).reduce((sum, d) => sum + d.focusScore, 0) / (weekData.filter(d => d.focusScore > 0).length || 1);
        const bestHours = getBestStudyHours();
        
        // 获取上周数据对比
        const lastWeekRecords = (window.userData.dailyRecords || []).slice(-14, -7);
        const lastWeekMinutes = lastWeekRecords.reduce((sum, r) => sum + (r.studyMinutes || 0), 0);
        
        const change = lastWeekMinutes > 0 ? Math.round(((totalMinutes - lastWeekMinutes) / lastWeekMinutes) * 100) : 100;
        
        return {
            totalMinutes,
            avgFocus: Math.round(avgFocus),
            bestHours,
            weekData,
            change,
            suggestion: generateSuggestion(totalMinutes, avgFocus, change, bestHours)
        };
    }
    
    // 生成建议
    function generateSuggestion(minutes, focus, change, bestHours) {
        const suggestions = [];
        
        if (minutes < 60) {
            suggestions.push('本周学习时间较少，建议每天至少保持30分钟的学习。');
        } else if (minutes > 600) {
            suggestions.push('学习时间充足，注意劳逸结合，避免过度疲劳。');
        }
        
        if (focus < 60) {
            suggestions.push('专注度有待提高，可以尝试番茄工作法，25分钟专注+5分钟休息。');
        } else if (focus >= 80) {
            suggestions.push('专注度表现优秀，继续保持！');
        }
        
        if (change < -20) {
            suggestions.push('学习时间比上周减少较多，需要调整学习计划。');
        } else if (change > 20) {
            suggestions.push('进步明显！学习时间比上周增加' + change + '%，继续加油！');
        }
        
        if (bestHours.length > 0) {
            suggestions.push('你的最佳学习时段是 ' + bestHours[0].label + '，建议在这个时间段安排重要任务。');
        }
        
        return suggestions.length > 0 ? suggestions : ['保持良好的学习习惯，继续努力！'];
    }
    
    // 初始化用户数据
    window.userData = loadUserData();
    
    // 学习计时器（每分钟+1积分）
    window.studyPointsInterval = null;
    window.positiveEmotionTime = 0; // 本次学习中积极情绪累计时间（秒）
    
    function startStudyPointsTimer() {
        if (window.studyPointsInterval) return;
        
        window.studyPointsInterval = setInterval(() => {
            if (window.isRunning && !window.isResting) {
                window.userData.totalStudyMinutes++;
                window.userData.todayStudyMinutes++;
                
                // 记录学习数据（用于可视化）
                recordStudyMinute();
                
                // 基础积分：每分钟+1
                let pointsToAdd = 1;
                
                // 连续专注奖励：每30分钟额外+10
                if (window.userData.todayStudyMinutes % 30 === 0) {
                    pointsToAdd += 10;
                    showAlert('连续专注30分钟，额外获得10积分！', 'encourage');
                    playAlertSound('levelup');
                }
                
                const result = addPoints(window.userData, pointsToAdd, 'study');
                
                // 如果升级了
                if (result.leveledUp) {
                    showAlert('恭喜升级！你现在是 ' + result.newLevel.icon + ' ' + result.newLevel.name + ' 了！', 'encourage');
                    playAlertSound('levelup');
                }
                
                // 检查成就
                const newAchievements = checkAchievements(window.userData);
                newAchievements.forEach(achievement => {
                    setTimeout(() => {
                        showAchievementPopup(achievement);
                    }, 1000);
                });
                
                saveUserData(window.userData);
                updateStatsDisplay();
            }
        }, 60000); // 每分钟执行一次
    }
    
    function stopStudyPointsTimer() {
        if (window.studyPointsInterval) {
            clearInterval(window.studyPointsInterval);
            window.studyPointsInterval = null;
        }
    }
    
    // 显示成就弹窗
    function showAchievementPopup(achievement) {
        playAlertSound('achievement');
        
        const popup = document.getElementById('achievement-popup');
        const icon = document.getElementById('achievement-icon');
        const name = document.getElementById('achievement-name');
        const desc = document.getElementById('achievement-desc');
        
        if (popup && icon && name && desc) {
            icon.textContent = achievement.icon;
            name.textContent = achievement.name;
            desc.textContent = achievement.desc;
            
            popup.style.display = 'flex';
            popup.style.animation = 'achievementIn 0.5s ease-out';
            
            setTimeout(() => {
                popup.style.animation = 'achievementOut 0.5s ease-in';
                setTimeout(() => {
                    popup.style.display = 'none';
                }, 500);
            }, 4000);
        }
    }
    
    // 更新统计显示
    function updateStatsDisplay() {
        const pointsEl = document.getElementById('user-points');
        const levelEl = document.getElementById('user-level');
        const levelNameEl = document.getElementById('user-level-name');
        const streakEl = document.getElementById('user-streak');
        const progressEl = document.getElementById('level-progress');
        const progressTextEl = document.getElementById('level-progress-text');
        
        const levelInfo = calculateLevel(window.userData.points);
        const nextLevelPoints = getNextLevelPoints(levelInfo.level);
        
        if (pointsEl) pointsEl.textContent = window.userData.points;
        if (levelEl) levelEl.textContent = levelInfo.icon;
        if (levelNameEl) levelNameEl.textContent = 'Lv.' + levelInfo.level + ' ' + levelInfo.name;
        if (streakEl) streakEl.textContent = window.userData.consecutiveDays;
        
        // 更新进度条
        if (progressEl && nextLevelPoints) {
            const currentLevelMin = levelInfo.minPoints;
            const progress = ((window.userData.points - currentLevelMin) / (nextLevelPoints - currentLevelMin)) * 100;
            progressEl.style.width = Math.min(progress, 100) + '%';
        }
        if (progressTextEl && nextLevelPoints) {
            progressTextEl.textContent = window.userData.points + '/' + nextLevelPoints;
        } else if (progressTextEl) {
            progressTextEl.textContent = '已满级';
        }
    }
    
    // 更新成就面板
    function updateAchievementsPanel() {
        const container = document.getElementById('achievements-container');
        if (!container) return;
        
        container.innerHTML = '';
        container.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;';
        
        achievementConfig.forEach(achievement => {
            const isUnlocked = window.userData.achievements.includes(achievement.id);
            const div = document.createElement('div');
            
            if (isUnlocked) {
                div.style.cssText = 'display:flex;align-items:center;gap:4px;padding:6px 10px;border-radius:20px;font-size:12px;background:#fef3c7;color:#78350f;border:2px solid #f59e0b;font-weight:700;cursor:default;';
            } else {
                div.style.cssText = 'display:flex;align-items:center;gap:4px;padding:6px 10px;border-radius:20px;font-size:12px;background:#e5e7eb;color:#374151;border:1px solid #9ca3af;font-weight:600;cursor:default;';
            }
            
            div.innerHTML = '<span style="font-size:14px;">' + (isUnlocked ? achievement.icon : '🔒') + '</span>' +
                '<span style="font-size:12px;font-weight:700;color:' + (isUnlocked ? '#78350f' : '#000000') + ';">' + achievement.name + '</span>';
            div.title = achievement.desc;
            container.appendChild(div);
        });
    }
    
    // 生成签到日历
    function generateCheckInCalendar() {
        const container = document.getElementById('checkin-calendar');
        if (!container) return;
        
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        let html = '<div style="text-align:center;font-size:14px;font-weight:700;margin-bottom:10px;color:#000000;background:#e5e7eb;padding:8px;border-radius:8px;">' + year + '年' + (month + 1) + '月</div>';
        html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:6px;">';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">日</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">一</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">二</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">三</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">四</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">五</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">六</span>';
        html += '</div>';
        html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;">';
        
        // 填充空白
        for (let i = 0; i < firstDay; i++) {
            html += '<span style="visibility:hidden;"></span>';
        }
        
        // 填充日期
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
            const isCheckedIn = window.userData.checkInHistory.includes(dateStr);
            const isToday = day === today.getDate();
            
            let style = 'text-align:center;padding:6px 2px;font-size:12px;border-radius:6px;font-weight:700;';
            if (isCheckedIn) {
                style += 'background:#059669;color:#ffffff;';
            } else if (isToday) {
                style += 'background:#dbeafe;color:#1e40af;border:2px solid #3b82f6;';
            } else {
                style += 'background:#e5e7eb;color:#000000;';
            }
            html += '<span style="' + style + '">' + day + '</span>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    }
    
    const emotionMap = {
        'neutral': '平静', 'happy': '开心', 'sad': '难过',
        'angry': '生气', 'fearful': '紧张', 'disgusted': '不适', 'surprised': '惊讶'
    };
    
    // 消极情绪列表
    const negativeEmotions = ['sad', 'angry', 'fearful', 'disgusted'];
    
    // 多样化鼓励语句库 - 分神提醒
    const distractedMessages = [
        "嘿，注意力回来啦~专注一下，你可以的！",
        "小伴发现你走神了哦，深呼吸，继续加油！",
        "学习需要专注力，让我们重新集中注意力吧！",
        "休息一下眼睛，然后继续专注学习哦~",
        "走神了？没关系，现在开始重新专注！",
        "专注是成功的关键，让我们一起努力！",
        "小伴提醒你：回到学习状态啦~",
        "发现你有点分心，要不要休息一下再继续？",
        "注意力是学习的第一步，加油！",
        "集中精神，你离目标又近了一步！"
    ];
    
    // 多样化鼓励语句库 - 消极情绪鼓励
    const encourageMessages = [
        "看起来你有点累了，记得适当休息哦，你已经很棒了！",
        "学习路上难免有低谷，但每一步都算数，加油！",
        "小伴看到你在努力，无论结果如何，你都很了不起！",
        "感到沮丧是正常的，休息一下，我们再出发！",
        "每个人都会有疲惫的时候，给自己一个拥抱吧~",
        "困难只是暂时的，你的努力终将开花结果！",
        "累了就休息，明天又是元气满满的一天！",
        "小伴相信你，你比想象中更强大！",
        "坚持不一定成功，但放弃一定不会，继续加油！",
        "每一次挫折都是成长的机会，你在变得更好！",
        "学习是马拉松，不是短跑，慢慢来~",
        "感到压力？深呼吸，你已经做得很好了！",
        "今天的辛苦是明天的收获，继续努力！",
        "小伴一直在这里陪着你，你不是一个人在战斗！",
        "即使进步很小，也是进步，为自己鼓掌！"
    ];
    
    // 播放提示音函数
    function playAlertSound(type) {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // 根据类型设置不同的音调
            if (type === 'distracted') {
                // 分神提醒 - 较高频率，提醒注意
                oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A5
                oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.15); // E5
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } else if (type === 'encourage') {
                // 鼓励提示 - 温和的上升音调
                oscillator.frequency.setValueAtTime(523, audioContext.currentTime); // C5
                oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.15); // E5
                oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.3); // G5
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } else if (type === 'levelup') {
                // 升级音效 - 欢快的上升音阶
                const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
                notes.forEach((freq, i) => {
                    const osc = audioContext.createOscillator();
                    const gain = audioContext.createGain();
                    osc.connect(gain);
                    gain.connect(audioContext.destination);
                    osc.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.1);
                    osc.type = 'sine';
                    gain.gain.setValueAtTime(0.25, audioContext.currentTime + i * 0.1);
                    gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + i * 0.1 + 0.2);
                    osc.start(audioContext.currentTime + i * 0.1);
                    osc.stop(audioContext.currentTime + i * 0.1 + 0.2);
                });
                return;
            } else if (type === 'achievement') {
                // 成就解锁音效 - 胜利音调
                const notes = [784, 988, 1175, 1568]; // G5, B5, D6, G6
                notes.forEach((freq, i) => {
                    const osc = audioContext.createOscillator();
                    const gain = audioContext.createGain();
                    osc.connect(gain);
                    gain.connect(audioContext.destination);
                    osc.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.12);
                    osc.type = 'triangle';
                    gain.gain.setValueAtTime(0.3, audioContext.currentTime + i * 0.12);
                    gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + i * 0.12 + 0.25);
                    osc.start(audioContext.currentTime + i * 0.12);
                    osc.stop(audioContext.currentTime + i * 0.12 + 0.25);
                });
                return;
            } else if (type === 'checkin') {
                // 签到音效 - 清脆的叮咚
                oscillator.frequency.setValueAtTime(1047, audioContext.currentTime); // C6
                oscillator.frequency.setValueAtTime(1319, audioContext.currentTime + 0.1); // E6
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.25, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.3);
            } else {
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            }
        } catch (e) {
            console.log('Audio playback not supported:', e);
        }
    }
    
    // 显示提醒消息的函数
    function showAlert(message, type) {
        const now = Date.now();
        if (now - window.lastAlertTime < window.alertCooldown) {
            return; // 冷却时间内不重复提醒
        }
        window.lastAlertTime = now;
        
        // 播放提示音
        playAlertSound(type);
        
        const alertBox = document.getElementById('alert-box');
        const alertText = document.getElementById('alert-text');
        
        if (alertBox && alertText) {
            alertText.textContent = message;
            
            // 根据类型设置样式
            if (type === 'distracted') {
                alertBox.style.background = 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)';
            } else if (type === 'encourage') {
                alertBox.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            }
            
            alertBox.style.display = 'block';
            alertBox.style.animation = 'slideIn 0.5s ease-out';
            
            // 8秒后自动隐藏
            setTimeout(() => {
                alertBox.style.animation = 'slideOut 0.5s ease-in';
                setTimeout(() => {
                    alertBox.style.display = 'none';
                }, 500);
            }, 8000);
        }
        
        console.log('Alert shown:', type, message);
    }
    
    // 获取随机消息
    function getRandomMessage(messages) {
        return messages[Math.floor(Math.random() * messages.length)];
    }
    
    // 加载模型 - 尝试多个CDN源，加载更多模型以提高精准度
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
                
                // 先加载必需的模型
                await Promise.race([
                    Promise.all([
                        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                        faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL),
                        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL) // 添加68点特征点模型提高精度
                    ]),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Model load timeout')), 30000))
                ]);
                
                // 尝试加载更精确的SSD模型（可选）
                try {
                    await Promise.race([
                        faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL),
                        new Promise((_, reject) => setTimeout(() => reject(new Error('SSD model timeout')), 15000))
                    ]);
                    window.useSsdModel = true;
                    console.log('SSD Mobilenet model loaded - using high accuracy mode');
                } catch (e) {
                    console.log('SSD model not loaded, using TinyFaceDetector');
                    window.useSsdModel = false;
                }
                
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
    
    // 情绪平滑处理 - 使用滑动窗口减少抖动
    function smoothEmotion(newEmotion, confidence) {
        const historySize = 5; // 保留最近5次检测结果
        window.emotionHistory.push({ emotion: newEmotion, confidence: confidence, time: Date.now() });
        
        // 只保留最近的记录
        if (window.emotionHistory.length > historySize) {
            window.emotionHistory.shift();
        }
        
        // 如果历史记录不足，直接返回当前结果
        if (window.emotionHistory.length < 3) {
            return { emotion: newEmotion, confidence: confidence };
        }
        
        // 统计各情绪出现频率和平均置信度
        const emotionStats = {};
        window.emotionHistory.forEach(item => {
            if (!emotionStats[item.emotion]) {
                emotionStats[item.emotion] = { count: 0, totalConf: 0 };
            }
            emotionStats[item.emotion].count++;
            emotionStats[item.emotion].totalConf += item.confidence;
        });
        
        // 找出出现次数最多且置信度较高的情绪
        let bestEmotion = newEmotion;
        let bestScore = 0;
        
        for (const [emotion, stats] of Object.entries(emotionStats)) {
            const avgConf = stats.totalConf / stats.count;
            const score = stats.count * avgConf; // 综合考虑频率和置信度
            if (score > bestScore) {
                bestScore = score;
                bestEmotion = emotion;
            }
        }
        
        const avgConfidence = emotionStats[bestEmotion].totalConf / emotionStats[bestEmotion].count;
        return { emotion: bestEmotion, confidence: avgConfidence };
    }
    
    // 检测函数 - 优化精准度
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
            let detections;
            
            // 根据加载的模型选择检测方式
            if (window.useSsdModel) {
                // 使用更精确的SSD模型 + 68点特征点
                detections = await faceapi.detectAllFaces(video, new faceapi.SsdMobilenetv1Options({
                    minConfidence: 0.5 // 最小置信度阈值
                }))
                .withFaceLandmarks()
                .withFaceExpressions();
            } else {
                // 使用优化参数的TinyFaceDetector + 68点特征点
                detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions({
                    inputSize: 416, // 增大输入尺寸提高精度（默认160，可选224/320/416/512/608）
                    scoreThreshold: 0.5 // 检测置信度阈值
                }))
                .withFaceLandmarks()
                .withFaceExpressions();
            }
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (detections.length > 0) {
                window.noFaceCount = 0;
                const detection = detections[0];
                const box = detection.detection.box;
                
                // 绘制人脸框
                ctx.strokeStyle = '#6366f1';
                ctx.lineWidth = 3;
                ctx.strokeRect(box.x, box.y, box.width, box.height);
                
                // 绘制68个特征点（可选，帮助调试）
                if (detection.landmarks) {
                    const landmarks = detection.landmarks;
                    ctx.fillStyle = '#10b981';
                    landmarks.positions.forEach(point => {
                        ctx.beginPath();
                        ctx.arc(point.x, point.y, 2, 0, 2 * Math.PI);
                        ctx.fill();
                    });
                }
                
                // 获取所有情绪及置信度
                const expressions = detection.expressions;
                const sorted = Object.entries(expressions).sort((a, b) => b[1] - a[1]);
                
                // 获取前两个情绪用于更准确的判断
                const topEmotion = sorted[0][0];
                const topConfidence = sorted[0][1];
                const secondEmotion = sorted[1] ? sorted[1][0] : null;
                const secondConfidence = sorted[1] ? sorted[1][1] : 0;
                
                // 应用情绪平滑处理
                const smoothed = smoothEmotion(topEmotion, topConfidence);
                const emotionCN = emotionMap[smoothed.emotion] || '平静';
                const displayConfidence = Math.round(smoothed.confidence * 100);
                
                // 记录情绪数据（用于可视化）
                recordEmotion(smoothed.emotion, smoothed.confidence);
                
                // 绘制情绪标签（显示更多信息）
                const labelWidth = 120;
                ctx.fillStyle = '#6366f1';
                ctx.fillRect(box.x, box.y - 28, labelWidth, 25);
                ctx.fillStyle = 'white';
                ctx.font = 'bold 14px sans-serif';
                ctx.fillText(emotionCN + ' ' + displayConfidence + '%', box.x + 5, box.y - 10);
                
                // 如果第二情绪置信度也较高，显示混合情绪（简化显示）
                let displayText = emotionCN + ' ' + displayConfidence + '%';
                if (secondConfidence > 0.25 && secondEmotion !== topEmotion) {
                    const secondCN = emotionMap[secondEmotion] || '';
                    if (secondCN) {
                        displayText = emotionCN + '/' + secondCN;
                    }
                }
                
                if (emotionEl) {
                    emotionEl.textContent = displayText;
                    emotionEl.title = emotionCN + ' (' + displayConfidence + '%)'; // 悬停显示完整信息
                }
                
                // 根据情绪类型设置专注状态
                if (attentionEl) {
                    if (['happy', 'neutral'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '专注中';
                        attentionEl.style.color = '#059669';
                        // 重置分神计数，减少消极情绪计数
                        window.distractedCount = 0;
                        if (window.negativeEmotionCount > 0) window.negativeEmotionCount--;
                    } else if (['sad', 'fearful'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '情绪低落';
                        attentionEl.style.color = '#f59e0b';
                        // 增加消极情绪计数
                        window.negativeEmotionCount++;
                        window.distractedCount = 0;
                    } else if (['angry', 'disgusted'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '有些烦躁';
                        attentionEl.style.color = '#ef4444';
                        // 增加消极情绪计数
                        window.negativeEmotionCount++;
                        window.distractedCount = 0;
                    } else if (smoothed.emotion === 'surprised') {
                        attentionEl.textContent = '注意力分散';
                        attentionEl.style.color = '#8b5cf6';
                        // 增加分神计数
                        window.distractedCount++;
                    } else {
                        attentionEl.textContent = '专注中';
                        attentionEl.style.color = '#059669';
                        window.distractedCount = 0;
                        if (window.negativeEmotionCount > 0) window.negativeEmotionCount--;
                    }
                }
                
                // 检查是否需要显示鼓励消息（消极情绪持续约15秒，即50次检测 * 300ms）
                if (window.negativeEmotionCount >= 50) {
                    showAlert(getRandomMessage(encourageMessages), 'encourage');
                    window.negativeEmotionCount = 0; // 重置计数
                }
            } else {
                window.noFaceCount++;
                window.distractedCount++; // 没检测到人脸也算分神
                
                // 记录走神数据（用于可视化）
                recordNoFace();
                
                if (emotionEl) emotionEl.textContent = '---';
                if (attentionEl) {
                    if (window.noFaceCount >= 8) { 
                        attentionEl.textContent = '可能走神了'; 
                        attentionEl.style.color = '#f59e0b'; 
                    } else { 
                        attentionEl.textContent = '检测中...'; 
                        attentionEl.style.color = '#7c3aed'; 
                    }
                }
            }
            
            // 检查是否需要显示分神提醒（分神持续约10秒，即33次检测 * 300ms）
            if (window.distractedCount >= 33) {
                showAlert(getRandomMessage(distractedMessages), 'distracted');
                window.distractedCount = 0; // 重置计数
            }
        } catch (e) { 
            console.error('Detection error:', e); 
        }
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
            // 提高摄像头分辨率以获得更精确的检测
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 }, 
                    facingMode: 'user',
                    frameRate: { ideal: 30 } // 提高帧率
                }
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
            window.emotionHistory = []; // 重置情绪历史
            window.distractedCount = 0; // 重置分神计数
            window.negativeEmotionCount = 0; // 重置消极情绪计数
            
            if (attentionEl) attentionEl.textContent = '监测中...';
            
            // 提高检测频率到300ms
            window.detectionInterval = setInterval(detectFace, 300);
            console.log('Webcam started successfully with enhanced detection');
            
            // 启动学习积分计时器
            startStudyPointsTimer();
            
            // 处理签到
            if (!window.userData.firstStudyDate) {
                window.userData.firstStudyDate = getTodayStr();
            }
            window.userData.lastStudyDate = getTodayStr();
            
            const checkInResult = handleCheckIn(window.userData);
            if (checkInResult.isNew) {
                playAlertSound('checkin');
                showAlert('签到成功！连续' + window.userData.consecutiveDays + '天，获得' + checkInResult.bonus + '积分', 'encourage');
                
                // 检查签到相关成就
                const newAchievements = checkAchievements(window.userData);
                newAchievements.forEach(achievement => {
                    setTimeout(() => {
                        showAchievementPopup(achievement);
                    }, 2000);
                });
            }
            
            saveUserData(window.userData);
            updateStatsDisplay();
            generateCheckInCalendar();
            updateAchievementsPanel();
            
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
        window.emotionHistory = []; // 清除情绪历史
        window.distractedCount = 0; // 重置分神计数
        window.negativeEmotionCount = 0; // 重置消极情绪计数
        
        // 停止学习积分计时器
        stopStudyPointsTimer();
        
        // 隐藏提醒框
        const alertBox = document.getElementById('alert-box');
        if (alertBox) alertBox.style.display = 'none';
        
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
    
    // ========== 休息模式功能 ==========
    window.isResting = false;
    window.restTimer = null;
    window.restEndTime = 0;
    window.restCountdownInterval = null;
    
    // 主动结束休息的鼓励语句
    const earlyEndRestMessages = [
        "太棒了！主动结束休息，你的自律让人佩服！",
        "好样的！提前回到学习状态，你真的很努力！",
        "主动学习的态度值得表扬，继续保持！",
        "休息好了就开始学习，你的效率一定很高！",
        "自律的人最可怕，你就是那个人！加油！",
        "提前结束休息，说明你对学习充满热情！",
        "主动投入学习，成功就在不远处等你！",
        "你的积极态度让小伴很感动，一起加油吧！"
    ];
    
    // 休息结束提醒语句
    const restEndMessages = [
        "休息时间到啦！精神饱满地继续学习吧~",
        "充电完成！让我们以最好的状态继续前进！",
        "休息结束，新的学习旅程开始！",
        "元气满满！现在是重新专注的最佳时机~",
        "休息好了吗？让我们一起攻克难题吧！"
    ];
    
    // 显示休息面板
    window.showRestPanel = function() {
        const restPanel = document.getElementById('rest-panel');
        const restOptions = document.getElementById('rest-options');
        const restCountdown = document.getElementById('rest-countdown');
        const restBtn = document.getElementById('rest-mode-btn');
        
        if (restPanel) {
            restPanel.style.display = 'block';
            if (restOptions) restOptions.style.display = 'block';
            if (restCountdown) restCountdown.style.display = 'none';
        }
        if (restBtn) restBtn.style.display = 'none';
    };
    
    // 隐藏休息面板
    window.hideRestPanel = function() {
        const restPanel = document.getElementById('rest-panel');
        const restBtn = document.getElementById('rest-mode-btn');
        
        if (restPanel) restPanel.style.display = 'none';
        if (restBtn) restBtn.style.display = 'inline-block';
    };
    
    // 开始休息
    window.startRest = function(minutes) {
        if (window.isResting) return;
        
        // 先关闭摄像头
        if (window.isRunning) {
            window.stopWebcam();
        }
        
        window.isResting = true;
        const totalSeconds = minutes * 60;
        window.restEndTime = Date.now() + totalSeconds * 1000;
        
        const restOptions = document.getElementById('rest-options');
        const restCountdown = document.getElementById('rest-countdown');
        const countdownDisplay = document.getElementById('countdown-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (restOptions) restOptions.style.display = 'none';
        if (restCountdown) restCountdown.style.display = 'block';
        if (attentionEl) {
            attentionEl.textContent = '休息中...';
            attentionEl.style.color = '#10b981';
        }
        
        // 更新倒计时显示
        function updateCountdown() {
            const remaining = Math.max(0, window.restEndTime - Date.now());
            const mins = Math.floor(remaining / 60000);
            const secs = Math.floor((remaining % 60000) / 1000);
            
            if (countdownDisplay) {
                countdownDisplay.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
            }
            
            if (remaining <= 0) {
                window.endRest(false); // 时间到，自动结束
            }
        }
        
        updateCountdown();
        window.restCountdownInterval = setInterval(updateCountdown, 1000);
        
        // 设置休息结束定时器
        window.restTimer = setTimeout(() => {
            window.endRest(false);
        }, totalSeconds * 1000);
        
        console.log('Rest started for', minutes, 'minutes');
    };
    
    // 结束休息
    window.endRest = function(isEarly) {
        if (!window.isResting) return;
        
        window.isResting = false;
        
        // 清除定时器
        if (window.restTimer) {
            clearTimeout(window.restTimer);
            window.restTimer = null;
        }
        if (window.restCountdownInterval) {
            clearInterval(window.restCountdownInterval);
            window.restCountdownInterval = null;
        }
        
        // 隐藏休息面板
        window.hideRestPanel();
        
        // 显示提示
        if (isEarly) {
            // 主动结束休息，显示鼓励
            showAlert(getRandomMessage(earlyEndRestMessages), 'encourage');
            playAlertSound('encourage');
            
            // 增加主动结束休息次数，并奖励积分
            window.userData.earlyEndRestCount++;
            addPoints(window.userData, 5, 'early_rest'); // 主动结束休息+5积分
            
            // 检查成就
            const newAchievements = checkAchievements(window.userData);
            newAchievements.forEach(achievement => {
                setTimeout(() => {
                    showAchievementPopup(achievement);
                }, 1500);
            });
            
            saveUserData(window.userData);
            updateStatsDisplay();
        } else {
            // 时间到，显示继续学习提醒
            showAlert(getRandomMessage(restEndMessages), 'distracted');
            playAlertSound('distracted');
        }
        
        // 自动开启学习模式（摄像头）
        setTimeout(() => {
            window.startWebcam();
        }, 1000);
        
        console.log('Rest ended,', isEarly ? 'early' : 'time up');
    };
    
    // 自定义时间输入
    window.showCustomTimeInput = function() {
        const customInput = document.getElementById('custom-time-input');
        if (customInput) {
            customInput.style.display = customInput.style.display === 'none' ? 'flex' : 'none';
        }
    };
    
    window.startCustomRest = function() {
        const input = document.getElementById('custom-minutes');
        if (input) {
            const minutes = parseInt(input.value) || 5;
            if (minutes > 0 && minutes <= 60) {
                window.startRest(minutes);
            } else {
                alert('请输入1-60之间的分钟数');
            }
        }
    };
    
    // 绑定休息按钮事件
    function bindRestButtons() {
        const restModeBtn = document.getElementById('rest-mode-btn');
        const cancelRestBtn = document.getElementById('cancel-rest-btn');
        const stopRestBtn = document.getElementById('stop-rest-btn');
        const rest5Btn = document.getElementById('rest-5');
        const rest10Btn = document.getElementById('rest-10');
        const rest15Btn = document.getElementById('rest-15');
        const customBtn = document.getElementById('rest-custom');
        const startCustomBtn = document.getElementById('start-custom-rest');
        
        if (restModeBtn) {
            restModeBtn.onclick = function(e) {
                e.preventDefault();
                window.showRestPanel();
            };
        }
        
        if (cancelRestBtn) {
            cancelRestBtn.onclick = function(e) {
                e.preventDefault();
                window.hideRestPanel();
            };
        }
        
        if (stopRestBtn) {
            stopRestBtn.onclick = function(e) {
                e.preventDefault();
                window.endRest(true); // 主动结束
            };
        }
        
        if (rest5Btn) rest5Btn.onclick = () => window.startRest(5);
        if (rest10Btn) rest10Btn.onclick = () => window.startRest(10);
        if (rest15Btn) rest15Btn.onclick = () => window.startRest(15);
        if (customBtn) customBtn.onclick = () => window.showCustomTimeInput();
        if (startCustomBtn) startCustomBtn.onclick = () => window.startCustomRest();
        
        console.log('Rest buttons bound');
    }
    
    // 延迟绑定，确保DOM已加载
    setTimeout(bindButtons, 1000);
    setTimeout(bindRestButtons, 1200);
    setTimeout(bindQuickActionButtons, 1300);
    setTimeout(bindReportButtons, 1400);
    
    // 绑定快捷操作按钮
    function bindQuickActionButtons() {
        const adviceBtn = document.getElementById('advice-btn');
        const planBtn = document.getElementById('plan-btn');
        const encourageBtn = document.getElementById('encourage-btn');
        const clearBtn = document.getElementById('clear-btn');
        
        // 获取Gradio的输入框和发送按钮
        function sendMessage(message) {
            // 找到Gradio的文本输入框
            const textbox = document.querySelector('textarea[data-testid="textbox"]');
            if (textbox) {
                // 设置值
                textbox.value = message;
                // 触发input事件
                textbox.dispatchEvent(new Event('input', { bubbles: true }));
                // 找到发送按钮并点击
                setTimeout(() => {
                    const sendBtn = document.querySelector('#send-btn');
                    if (sendBtn) sendBtn.click();
                }, 100);
            }
        }
        
        function clearChat() {
            // 找到并点击Gradio的清空按钮（如果有）
            // 或者直接清空chatbot
            const chatbot = document.querySelector('#chatbot');
            if (chatbot) {
                // 触发清空事件 - 需要通过Gradio的方式
                // 这里我们模拟发送一个特殊消息然后清空
            }
        }
        
        if (adviceBtn) {
            adviceBtn.onclick = () => sendMessage('给我一些学习建议吧');
        }
        if (planBtn) {
            planBtn.onclick = () => sendMessage('帮我制定一个学习计划');
        }
        if (encourageBtn) {
            encourageBtn.onclick = () => sendMessage('我有点沮丧，需要一些鼓励');
        }
        if (clearBtn) {
            clearBtn.onclick = () => {
                // 清空对话 - 刷新页面是最简单的方式
                if (confirm('确定要清空所有对话吗？')) {
                    location.reload();
                }
            };
        }
        
        console.log('Quick action buttons bound');
    }
    
    // ========== 数据仪表盘更新函数 ==========
    function updateDashboard() {
        const today = getTodayStr();
        const todayRecord = getTodayRecord();
        const weekData = getWeeklyData();
        const monthMinutes = getMonthlyData();
        const bestHours = getBestStudyHours();
        
        // 更新日期显示
        const dateEl = document.getElementById('dashboard-date');
        if (dateEl) {
            const d = new Date();
            dateEl.textContent = (d.getMonth() + 1) + '月' + d.getDate() + '日';
        }
        
        // 更新时长统计
        const todayEl = document.getElementById('today-minutes');
        const weekEl = document.getElementById('week-minutes');
        const monthEl = document.getElementById('month-minutes');
        
        if (todayEl) todayEl.textContent = todayRecord.studyMinutes || 0;
        if (weekEl) weekEl.textContent = weekData.reduce((sum, d) => sum + d.studyMinutes, 0);
        if (monthEl) monthEl.textContent = monthMinutes;
        
        // 更新本周趋势图
        const chartEl = document.getElementById('week-chart');
        if (chartEl) {
            const maxMinutes = Math.max(...weekData.map(d => d.studyMinutes), 1);
            let chartHtml = '';
            weekData.forEach(d => {
                const height = Math.max((d.studyMinutes / maxMinutes) * 60, 2);
                const isToday = d.date === today;
                chartHtml += '<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">' +
                    '<div style="width:70%;background:' + (isToday ? 'linear-gradient(180deg,#3b82f6,#1d4ed8)' : '#93c5fd') + ';height:' + height + 'px;border-radius:4px;transition:height 0.3s;"></div>' +
                    '<span style="font-size:10px;color:' + (isToday ? '#1d4ed8' : '#6b7280') + ';font-weight:' + (isToday ? '700' : '500') + ';">' + d.day + '</span>' +
                    '<span style="font-size:9px;color:#9ca3af;">' + d.studyMinutes + '</span>' +
                    '</div>';
            });
            chartEl.innerHTML = chartHtml;
        }
        
        // 更新最佳学习时段
        const hoursEl = document.getElementById('best-hours');
        if (hoursEl) {
            if (bestHours.length > 0) {
                hoursEl.innerHTML = bestHours.map((h, i) => 
                    '<span style="background:' + ['#dbeafe', '#dcfce7', '#fef3c7'][i] + ';color:' + ['#1e40af', '#166534', '#b45309'][i] + ';padding:4px 10px;border-radius:15px;font-size:11px;font-weight:600;">' + h.label + '</span>'
                ).join('');
            } else {
                hoursEl.innerHTML = '<span style="background:#f3f4f6;color:#6b7280;padding:4px 10px;border-radius:15px;font-size:11px;">暂无数据</span>';
            }
        }
        
        // 更新专注度
        const focusBar = document.getElementById('focus-bar');
        const focusText = document.getElementById('focus-text');
        const focusScore = todayRecord.focusScore || 0;
        
        if (focusBar) focusBar.style.width = focusScore + '%';
        if (focusText) focusText.textContent = focusScore + '%';
    }
    
    // 显示周报弹窗
    function showWeeklyReport() {
        const modal = document.getElementById('weekly-report-modal');
        const content = document.getElementById('report-content');
        
        if (!modal || !content) return;
        
        modal.style.display = 'flex';
        
        const report = generateWeeklyReport();
        const hours = Math.floor(report.totalMinutes / 60);
        const mins = report.totalMinutes % 60;
        
        let changeHtml = '';
        if (report.change > 0) {
            changeHtml = '<span style="color:#16a34a;">↑ +' + report.change + '%</span>';
        } else if (report.change < 0) {
            changeHtml = '<span style="color:#dc2626;">↓ ' + report.change + '%</span>';
        } else {
            changeHtml = '<span style="color:#6b7280;">→ 持平</span>';
        }
        
        content.innerHTML = 
            '<div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:12px;padding:20px;margin-bottom:15px;text-align:center;">' +
                '<p style="margin:0 0 5px 0;font-size:13px;color:#3b82f6;font-weight:600;">本周累计学习</p>' +
                '<p style="margin:0;font-size:32px;font-weight:700;color:#1e40af;">' + hours + '<span style="font-size:16px;">时</span> ' + mins + '<span style="font-size:16px;">分</span></p>' +
                '<p style="margin:10px 0 0 0;font-size:12px;">相比上周 ' + changeHtml + '</p>' +
            '</div>' +
            
            '<div style="margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">📊 每日学习时长</p>' +
                '<div style="display:flex;justify-content:space-between;">' +
                    report.weekData.map(d => 
                        '<div style="text-align:center;">' +
                            '<div style="width:30px;height:30px;border-radius:50%;background:' + (d.studyMinutes > 0 ? '#3b82f6' : '#e5e7eb') + ';color:white;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;margin-bottom:4px;">' + d.studyMinutes + '</div>' +
                            '<span style="font-size:10px;color:#6b7280;">' + d.day + '</span>' +
                        '</div>'
                    ).join('') +
                '</div>' +
            '</div>' +
            
            '<div style="margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">🎯 平均专注度</p>' +
                '<div style="display:flex;align-items:center;gap:10px;">' +
                    '<div style="flex:1;background:#e5e7eb;border-radius:10px;height:12px;overflow:hidden;">' +
                        '<div style="background:linear-gradient(90deg,#10b981,#059669);height:100%;width:' + report.avgFocus + '%;border-radius:10px;"></div>' +
                    '</div>' +
                    '<span style="font-size:14px;font-weight:700;color:#059669;">' + report.avgFocus + '%</span>' +
                '</div>' +
            '</div>' +
            
            '<div style="background:#fef9e7;border-radius:12px;padding:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#b45309;font-weight:600;">💡 本周建议</p>' +
                '<ul style="margin:0;padding-left:20px;">' +
                    report.suggestion.map(s => '<li style="font-size:12px;color:#78350f;margin-bottom:5px;">' + s + '</li>').join('') +
                '</ul>' +
            '</div>';
    }
    
    // 绑定报告按钮事件
    function bindReportButtons() {
        const showBtn = document.getElementById('show-report-btn');
        const closeBtn = document.getElementById('close-report-btn');
        const modal = document.getElementById('weekly-report-modal');
        
        if (showBtn) {
            showBtn.onclick = () => showWeeklyReport();
        }
        
        if (closeBtn) {
            closeBtn.onclick = () => {
                if (modal) modal.style.display = 'none';
            };
        }
        
        // 点击背景关闭
        if (modal) {
            modal.onclick = (e) => {
                if (e.target === modal) modal.style.display = 'none';
            };
        }
        
        console.log('Report buttons bound');
    }
    
    // 初始化游戏化系统显示
    setTimeout(() => {
        updateStatsDisplay();
        generateCheckInCalendar();
        updateAchievementsPanel();
        updateDashboard();
    }, 1500);
    
    // 每分钟更新一次仪表盘
    setInterval(() => {
        if (window.isRunning) {
            updateDashboard();
        }
    }, 60000);
    
    console.log('Face detection initialized');
}
"""

# 创建Gradio界面
with gr.Blocks(title="学习陪伴AI - 小伴") as demo:
    gr.HTML("""
        <style>
        .gradio-container { max-width: 1100px !important; margin: auto !important; }
        /* 整体背景 */
        .gradio-container > .main { background: #f8fafc; }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; border-radius: 15px;
            text-align: center; margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .chat-header h1 { margin: 0; font-size: 24px; }
        .chat-header p { margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }
        #chatbot { height: 400px !important; border-radius: 15px !important; }
        #send-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            border: none !important; border-radius: 10px !important; color: white !important;
        }
        /* 学习模式面板 */
        .study-mode-panel {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #bae6fd;
            box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1);
        }
        .study-mode-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .study-mode-header h3 {
            margin: 0;
            color: #0369a1;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .camera-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .camera-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        .camera-btn.stop {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        }
        .emotion-status-grid {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .status-card {
            flex: 1;
            background: rgba(255,255,255,0.8);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            min-height: 60px;
            border: 1px solid rgba(14, 165, 233, 0.2);
        }
        .status-card p:first-child {
            margin: 0 0 5px 0;
            font-size: 12px;
            color: #6b7280;
        }
        .status-card p:last-child {
            margin: 0;
            font-size: 14px;
            font-weight: 600;
            min-height: 20px;
            line-height: 20px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        /* 休息按钮 */
        .rest-btn {
            width: 100%;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 15px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .rest-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }
        .quick-btn { border-radius: 20px !important; font-size: 13px !important; margin: 3px !important; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes slideIn {
            from { transform: translateY(-100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateY(0); opacity: 1; }
            to { transform: translateY(-100%); opacity: 0; }
        }
        @keyframes achievementIn {
            from { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
            to { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
        @keyframes achievementOut {
            from { transform: translate(-50%, -50%) scale(1); opacity: 1; }
            to { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        #alert-box {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            padding: 15px 25px;
            border-radius: 12px;
            color: white;
            font-size: 15px;
            font-weight: 500;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            display: none;
            max-width: 90%;
            text-align: center;
        }
        /* 成就弹窗 */
        #achievement-popup {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10000;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            padding: 30px 40px;
            border-radius: 20px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            display: none;
            flex-direction: column;
            align-items: center;
        }
        #achievement-popup .achievement-icon { font-size: 48px; margin-bottom: 10px; }
        #achievement-popup .achievement-title { font-size: 14px; opacity: 0.9; margin-bottom: 5px; }
        #achievement-popup .achievement-name { font-size: 20px; font-weight: bold; margin-bottom: 5px; }
        #achievement-popup .achievement-desc { font-size: 14px; opacity: 0.9; }
        /* 用户状态栏 */
        .user-stats-bar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 15px;
            color: white;
            margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .stats-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .stats-row:last-child { margin-bottom: 0; }
        .stat-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
        }
        .stat-value { font-weight: bold; font-size: 15px; }
        .level-progress-container {
            background: rgba(255,255,255,0.25);
            border-radius: 10px;
            height: 10px;
            overflow: hidden;
            margin-top: 8px;
        }
        .level-progress-bar {
            background: linear-gradient(90deg, #fbbf24, #f59e0b);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
        }
        /* 成就面板 */
        .achievements-panel {
            background: #ffffff;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            border: 2px solid #f59e0b;
            box-shadow: 0 2px 8px rgba(251, 191, 36, 0.2);
        }
        .achievements-panel h4 {
            margin: 0 0 12px 0;
            font-size: 15px;
            color: #111827;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        #achievements-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .achievement-item {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 6px 10px;
            border-radius: 20px;
            font-size: 12px;
            background: #f3f4f6;
            color: #374151;
            cursor: default;
            border: 1px solid #9ca3af;
            transition: all 0.2s ease;
        }
        .achievement-item:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        .achievement-item.unlocked {
            background: #fef3c7;
            color: #78350f;
            border-color: #f59e0b;
            box-shadow: 0 2px 6px rgba(251, 146, 60, 0.3);
            font-weight: 700;
        }
        .achievement-icon { font-size: 14px; }
        .achievement-name { font-size: 12px; font-weight: 600; color: #1f2937; }
        /* 签到日历 */
        .checkin-panel {
            background: #ffffff;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            border: 2px solid #10b981;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
        }
        .checkin-panel h4 {
            margin: 0 0 12px 0;
            font-size: 15px;
            color: #111827;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .calendar-header {
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #111827;
            background: #ecfdf5;
            padding: 8px;
            border-radius: 8px;
            border: 1px solid #a7f3d0;
        }
        .calendar-weekdays {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2px;
            margin-bottom: 6px;
        }
        .calendar-weekdays span {
            text-align: center;
            font-size: 11px;
            color: #059669;
            font-weight: 700;
            padding: 4px 0;
        }
        .calendar-days {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 3px;
        }
        .calendar-days span {
            text-align: center;
            padding: 6px 2px;
            font-size: 12px;
            border-radius: 6px;
            color: #111827;
            background: #f3f4f6;
            font-weight: 700;
            border: 1px solid #e5e7eb;
        }
        .calendar-days span.empty { 
            visibility: hidden; 
            background: transparent;
            border: none;
        }
        .calendar-days span.checked {
            background: #059669;
            color: #ffffff;
            border-color: #047857;
            box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
        }
        .calendar-days span.today {
            border: 2px solid #6366f1;
            background: #eef2ff;
            color: #4338ca;
        }
        /* 快捷操作样式 */
        .quick-actions-panel {
            background: #ffffff;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            border: 2px solid #8b5cf6;
            box-shadow: 0 2px 8px rgba(139, 92, 246, 0.2);
        }
        .quick-actions-panel h4 {
            margin: 0 0 12px 0;
            font-size: 15px;
            color: #111827;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .quick-actions-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .quick-action-btn {
            background: #f3f4f6;
            border: 2px solid #8b5cf6;
            border-radius: 10px;
            padding: 12px 10px;
            font-size: 13px;
            font-weight: 600;
            color: #4c1d95;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .quick-action-btn:hover {
            background: #8b5cf6;
            color: #ffffff;
            border-color: #7c3aed;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
        }
        .quick-action-btn.danger {
            color: #991b1b;
            border-color: #ef4444;
            background: #fef2f2;
        }
        .quick-action-btn.danger:hover {
            background: #ef4444;
            color: #ffffff;
        }
        </style>
        
        <!-- 提醒消息框 -->
        <div id="alert-box">
            <span id="alert-text"></span>
        </div>
        
        <!-- 成就解锁弹窗 -->
        <div id="achievement-popup">
            <div class="achievement-title">🎉 成就解锁！</div>
            <div id="achievement-icon" class="achievement-icon"></div>
            <div id="achievement-name" class="achievement-name"></div>
            <div id="achievement-desc" class="achievement-desc"></div>
        </div>
    """)
    
    gr.HTML("""
        <div class="chat-header">
            <h1>学习陪伴AI - 小伴</h1>
            <p>有我陪伴，学习不孤单 | 支持实时人脸识别与情绪检测</p>
        </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            # 用户状态栏
            gr.HTML("""
                <div class="user-stats-bar">
                    <div class="stats-row">
                        <div class="stat-item">
                            <span id="user-level" style="font-size: 20px;">🌱</span>
                            <span id="user-level-name" class="stat-value">Lv.1 学习新手</span>
                        </div>
                        <div class="stat-item">
                            <span style="font-size: 16px;">💰</span>
                            <span id="user-points" class="stat-value">0</span>
                            <span style="opacity: 0.8;">积分</span>
                        </div>
                    </div>
                    <div class="stats-row">
                        <div class="stat-item">
                            <span style="font-size: 16px;">🔥</span>
                            <span style="opacity: 0.8;">连续签到</span>
                            <span id="user-streak" class="stat-value">0</span>
                            <span style="opacity: 0.8;">天</span>
                        </div>
                        <div class="stat-item">
                            <span id="level-progress-text" style="font-size: 12px; opacity: 0.9; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">0/100</span>
                        </div>
                    </div>
                    <div class="level-progress-container">
                        <div id="level-progress" class="level-progress-bar" style="width: 0%;"></div>
                    </div>
                </div>
            """)
            
            # 摄像头模块
            gr.HTML("""
                <div class="study-mode-panel">
                    <div class="study-mode-header">
                        <h3>📹 学习模式</h3>
                        <div>
                            <button id="start-btn" type="button" class="camera-btn">
                                开启摄像头
                            </button>
                            <button id="stop-btn" type="button" class="camera-btn stop" style="display: none;">
                                关闭摄像头
                            </button>
                        </div>
                    </div>
                    
                    <div id="video-container" style="position: relative; width: 100%; max-width: 320px; margin: 0 auto; display: none; min-height: 180px;"></div>
                    
                    <div id="camera-placeholder" style="width: 100%; max-width: 320px; height: 180px; margin: 0 auto; background: rgba(255,255,255,0.6); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #64748b; border: 2px dashed #cbd5e1;">
                        <div style="text-align: center;">
                            <svg style="width: 48px; height: 48px; margin-bottom: 10px; opacity: 0.6;" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"/>
                            </svg>
                            <p style="margin: 0; font-size: 13px;">点击上方按钮开启摄像头</p>
                        </div>
                    </div>
                    
                    <div id="loading-indicator" style="display: none; text-align: center; padding: 20px; color: #6366f1;">
                        <div style="display: inline-block; width: 30px; height: 30px; border: 3px solid #e5e7eb; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                        <p style="margin: 10px 0 0 0; font-size: 14px;">加载模型中...</p>
                    </div>
                    
                    <div class="emotion-status-grid">
                        <div class="status-card">
                            <p>当前情绪</p>
                            <p id="emotion-display" style="color: #4f46e5;">---</p>
                        </div>
                        <div class="status-card">
                            <p>专注状态</p>
                            <p id="attention-display" style="color: #7c3aed;">等待开启</p>
                        </div>
                    </div>
                </div>
                
                <!-- 休息模式面板 -->
                <div id="rest-panel" style="display: none; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 15px; padding: 15px; margin-bottom: 15px; color: white; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="margin: 0; font-size: 16px; display: flex; align-items: center; gap: 6px;">☕ 休息模式</h3>
                        <button id="cancel-rest-btn" type="button" style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px;">取消</button>
                    </div>
                    
                    <!-- 时间选择 -->
                    <div id="rest-options">
                        <p style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9;">选择休息时长：</p>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;">
                            <button id="rest-5" type="button" style="flex: 1; min-width: 60px; background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 8px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">5分钟</button>
                            <button id="rest-10" type="button" style="flex: 1; min-width: 60px; background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 8px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">10分钟</button>
                            <button id="rest-15" type="button" style="flex: 1; min-width: 60px; background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 8px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">15分钟</button>
                        </div>
                        <button id="rest-custom" type="button" style="width: 100%; background: rgba(255,255,255,0.15); color: white; border: none; padding: 8px; border-radius: 8px; cursor: pointer; font-size: 13px;">⏰ 自定义时间</button>
                        <div id="custom-time-input" style="display: none; margin-top: 10px; align-items: center; gap: 8px;">
                            <input id="custom-minutes" type="number" min="1" max="60" value="20" style="flex: 1; padding: 8px; border-radius: 6px; border: none; font-size: 14px; text-align: center;">
                            <span style="font-size: 14px;">分钟</span>
                            <button id="start-custom-rest" type="button" style="background: white; color: #059669; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-weight: 500;">开始</button>
                        </div>
                    </div>
                    
                    <!-- 倒计时显示 -->
                    <div id="rest-countdown" style="display: none; text-align: center;">
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">剩余休息时间</p>
                        <p id="countdown-display" style="margin: 0 0 15px 0; font-size: 48px; font-weight: bold; font-family: monospace;">00:00</p>
                        <button id="stop-rest-btn" type="button" style="background: white; color: #059669; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">🚀 结束休息，继续学习</button>
                    </div>
                </div>
                
                <!-- 休息一下按钮 -->
                <button id="rest-mode-btn" type="button" class="rest-btn">
                    ☕ 休息一下
                </button>
                
                <!-- 签到日历 -->
                <div class="checkin-panel" style="background:#ffffff;border:2px solid #10b981;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 12px 0;font-size:15px;color:#000000;font-weight:700;">📅 签到日历</h4>
                    <div id="checkin-calendar"></div>
                </div>
                
                <!-- 成就面板 -->
                <div class="achievements-panel" style="background:#ffffff;border:2px solid #f59e0b;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 12px 0;font-size:15px;color:#000000;font-weight:700;">🏆 我的成就</h4>
                    <div id="achievements-container"></div>
                </div>
                
                <!-- 快捷操作面板 -->
                <div class="quick-actions-panel" style="background:#ffffff;border:2px solid #8b5cf6;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 12px 0;font-size:15px;color:#000000;font-weight:700;">⚡ 快捷操作</h4>
                    <div class="quick-actions-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        <button id="advice-btn" type="button" style="background:#f3f4f6;border:2px solid #8b5cf6;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#000000;cursor:pointer;">💡 学习建议</button>
                        <button id="plan-btn" type="button" style="background:#f3f4f6;border:2px solid #8b5cf6;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#000000;cursor:pointer;">📋 制定计划</button>
                        <button id="encourage-btn" type="button" style="background:#f3f4f6;border:2px solid #8b5cf6;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#000000;cursor:pointer;">💪 鼓励我</button>
                        <button id="clear-btn" type="button" style="background:#fef2f2;border:2px solid #ef4444;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#991b1b;cursor:pointer;">🗑️ 清空对话</button>
                    </div>
                </div>
                
                <!-- 数据报告按钮 -->
                <button id="show-report-btn" type="button" style="width:100%;background:linear-gradient(135deg,#3b82f6 0%,#1d4ed8 100%);color:white;border:none;padding:12px;border-radius:10px;cursor:pointer;font-size:14px;font-weight:600;margin-bottom:15px;">
                    📊 查看学习报告
                </button>
            """)
        
        with gr.Column(scale=2):
            # 数据仪表盘面板
            gr.HTML("""
                <!-- 数据仪表盘 -->
                <div id="stats-dashboard" style="background:#ffffff;border:2px solid #3b82f6;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 15px 0;font-size:16px;color:#000000;font-weight:700;display:flex;align-items:center;gap:8px;">
                        📊 学习数据
                        <span id="dashboard-date" style="font-size:12px;color:#6b7280;font-weight:500;margin-left:auto;"></span>
                    </h4>
                    
                    <!-- 时长统计卡片 -->
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:15px;">
                        <div style="background:#eff6ff;border-radius:10px;padding:12px;text-align:center;">
                            <p style="margin:0 0 5px 0;font-size:11px;color:#3b82f6;font-weight:600;">今日</p>
                            <p id="today-minutes" style="margin:0;font-size:20px;font-weight:700;color:#1e40af;">0</p>
                            <p style="margin:0;font-size:10px;color:#6b7280;">分钟</p>
                        </div>
                        <div style="background:#f0fdf4;border-radius:10px;padding:12px;text-align:center;">
                            <p style="margin:0 0 5px 0;font-size:11px;color:#16a34a;font-weight:600;">本周</p>
                            <p id="week-minutes" style="margin:0;font-size:20px;font-weight:700;color:#15803d;">0</p>
                            <p style="margin:0;font-size:10px;color:#6b7280;">分钟</p>
                        </div>
                        <div style="background:#fef3c7;border-radius:10px;padding:12px;text-align:center;">
                            <p style="margin:0 0 5px 0;font-size:11px;color:#d97706;font-weight:600;">本月</p>
                            <p id="month-minutes" style="margin:0;font-size:20px;font-weight:700;color:#b45309;">0</p>
                            <p style="margin:0;font-size:10px;color:#6b7280;">分钟</p>
                        </div>
                    </div>
                    
                    <!-- 本周趋势图 -->
                    <div style="margin-bottom:15px;">
                        <p style="margin:0 0 8px 0;font-size:12px;color:#374151;font-weight:600;">📈 本周学习趋势</p>
                        <div id="week-chart" style="display:flex;align-items:flex-end;justify-content:space-between;height:80px;padding:5px 0;background:#f9fafb;border-radius:8px;">
                            <!-- 动态生成柱状图 -->
                        </div>
                    </div>
                    
                    <!-- 最佳学习时段 -->
                    <div style="margin-bottom:15px;">
                        <p style="margin:0 0 8px 0;font-size:12px;color:#374151;font-weight:600;">⏰ 最佳学习时段</p>
                        <div id="best-hours" style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:#e0e7ff;color:#3730a3;padding:4px 10px;border-radius:15px;font-size:11px;font-weight:600;">暂无数据</span>
                        </div>
                    </div>
                    
                    <!-- 专注度 -->
                    <div>
                        <p style="margin:0 0 8px 0;font-size:12px;color:#374151;font-weight:600;">🎯 今日专注度</p>
                        <div style="background:#e5e7eb;border-radius:10px;height:20px;overflow:hidden;">
                            <div id="focus-bar" style="background:linear-gradient(90deg,#10b981,#059669);height:100%;width:0%;transition:width 0.5s;border-radius:10px;"></div>
                        </div>
                        <p id="focus-text" style="margin:5px 0 0 0;font-size:11px;color:#6b7280;text-align:right;">0%</p>
                    </div>
                </div>
                
                <!-- 周报弹窗 -->
                <div id="weekly-report-modal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:10001;align-items:center;justify-content:center;">
                    <div style="background:white;border-radius:16px;padding:25px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
                            <h3 style="margin:0;font-size:18px;color:#111827;font-weight:700;">📋 本周学习报告</h3>
                            <button id="close-report-btn" type="button" style="background:none;border:none;font-size:24px;cursor:pointer;color:#6b7280;">×</button>
                        </div>
                        
                        <!-- 周报内容 -->
                        <div id="report-content">
                            <div style="text-align:center;padding:20px;">
                                <p style="color:#6b7280;">正在生成报告...</p>
                            </div>
                        </div>
                    </div>
                </div>
            """)
            
            # 语言风格选择栏
            gr.HTML("""
                <div style="background: white; border: 2px solid #667eea; border-radius: 12px; padding: 12px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);">
                    <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #1e40af; font-weight: 700; display: flex; align-items: center; gap: 6px;">🎭 陪伴风格切换</h4>
                </div>
            """)
            with gr.Row():
                style_select = gr.Radio(
                    label=None,
                    choices=["默认", "柔情猫娘", "成熟妈妈系御姐", "磁性霸道男总裁"],
                    value="默认",
                    container=False,
                    elem_id="style-radio",
                    scale=3
                )
                voice_toggle = gr.Checkbox(label="🔊 开启语音播报", value=False, scale=1)
            
            # 【新增】播放模式选择面板（初始隐藏）
            with gr.Group(visible=False, elem_id="playback-mode-group") as playback_mode_group:
                gr.HTML("""
                    <div style="background: #dbeafe; border: 2px solid #0284c7; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <p style="margin: 0; font-size: 12px; color: #075985;">
                            <strong>🎵 请选择语音播放模式：</strong>
                        </p>
                    </div>
                """)
                playback_mode = gr.Radio(
                    choices=["自动播放", "手动播放"],
                    value="手动播放",
                    label="播放模式",
                    container=False,
                    elem_id="playback-mode-radio"
                )
            
            # 【修改】初始隐藏播放器和调试信息	          
            voice_output = gr.Audio(	            
                label="🔊 语音播报",	                
                autoplay=False,	                    
                visible=False,          # 【修改】初始隐藏	                   
                type="numpy",	                   
                show_label=False,       # 【优化】隐藏标签以节省空间	                    
                elem_id="voice-output",	                   
                elem_classes=["compact-player"] # 使用紧凑样式类	                   
            )
            
            # 【修改】调试信息放入 Accordion（折叠面板）
            with gr.Accordion(label="🔍 语音播报调试信息", open=False, visible=False, elem_id="debug-accordion") as debug_accordion:
                gr.HTML("""
                    <div style="background: #fef3c7; border-radius: 4px; padding: 12px;">
                        <p style="margin: 0; font-size: 12px; color: #92400e;">
                            <strong>调试提示：</strong><br>
                            如果启用语音但无声，请按以下步骤排查：<br>
                            1️⃣ 确认浏览器音量已开启<br>
                            2️⃣ （手动模式）点击播放器的播放按钮手动播放<br>
                            3️⃣ 检查浏览器控制台(F12)是否有错误<br>
                            4️⃣ 尝试输入不同长度的文本<br>
                            <br>
                            <strong>📊 服务器日志：</strong><br>
                            查看后端日志中 [TTS DEBUG] 和 [CHAT DEBUG] 标记的信息
                        </p>
                    </div>
                """)
            gr.HTML("""
                <style>
                #style-radio { margin-bottom: 15px !important; }
                #style-radio .wrap { display: flex !important; flex-direction: row !important; gap: 8px !important; flex-wrap: wrap !important; }
                #style-radio label { 
                    flex: 1 !important;
                    min-width: 120px !important;
                    background: #f1f5f9 !important; 
                    border: 2px solid #e2e8f0 !important; 
                    border-radius: 10px !important; 
                    padding: 8px !important;
                    transition: all 0.2s ease !important;
                    text-align: center !important;
                }
                #style-radio label.selected { 
                    background: #eef2ff !important; 
                    border-color: #6366f1 !important; 
                    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2) !important;
                }
                #style-radio label span { font-weight: 600 !important; color: #1e293b !important; font-size: 13px !important; }
            /* 【方案优化】紧凑型播放器样式 */	
                .compact-player {	
                    min-height: 150px !important;	
                    height: 150px !important;	
                    padding: 0 !important;	
                    margin: 10px 0 !important;	
                    border: 3px solid #e2e8f0 !important;	
                    border-radius: 8px !important;	
                    overflow: hidden !important;	
                    background: #f8fafc !important;	
                }	
                /* 自动播放模式下的特殊视觉反馈（可选：淡淡的蓝色边框） */	
                .auto-mode {	
                    border-color: #6366f1 !important;	
                    background: #f0f9ff !important;	
                }   
                </style>
            """)
            
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
    
    # 【新增事件逻辑】
    # 当开启/关闭语音播报时的处理
    def on_voice_toggle_change(voice_enabled):
        """
        当用户改变语音播报开关时的回调
        返回: (playback_mode_group visible, debug_accordion visible, voice_output visible)
        """
        if voice_enabled:
            # 开启语音：显示播放模式选择面板和调试信息
            return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
        else:
            # 关闭语音：隐藏所有相关组件
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
    
    def on_playback_mode_change(mode):
        """
        当用户改变播放模式时的处理
        返回: (voice_output visible, voice_output autoplay, voice_output elem_classes)
        """
        if mode == "自动播放":
            # 自动播放：使用紧凑模式 + 自动播放标记类
            return gr.update(visible=True, autoplay=True, elem_classes=["compact-player", "auto-mode"])
        else:  # 手动播放：使用紧凑模式
            # 手动播放：禁用自动播放
            return gr.update(visible=True, autoplay=False, elem_classes=["compact-player"])
    
    # 绑定语音开关事件
    voice_toggle.change(
        fn=on_voice_toggle_change,
        inputs=[voice_toggle],
        outputs=[playback_mode_group, debug_accordion, voice_output]
    )
    
    # 绑定播放模式切换事件
    playback_mode.change(
        fn=on_playback_mode_change,
        inputs=[playback_mode],
        outputs=[voice_output]
    )
    
    # 【修改】聊天事件绑定 - 需要添加 playback_mode 参数
    send_btn.click(chat, [msg, chatbot, style_select, voice_toggle], [chatbot, msg, voice_output])
    msg.submit(chat, [msg, chatbot, style_select, voice_toggle], [chatbot, msg, voice_output])
    
    # 页面加载时执行JavaScript
    demo.load(fn=None, inputs=None, outputs=None, js=LOAD_JS)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
