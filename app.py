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
    "默认": """你是一个温暖、有耐心的学习陪伴AI助手，名叫"学了么"。你的职责是：
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
    "默认": "longfeifei_v2",             # 甜美娇气女女 (龙菲菲)
    "柔情猫娘": "longhuhu",         # 天真烂漫女童 (龙呼呼)
    "成熟妈妈系御姐": "longyuan_v2", # 温婉知性 (龙媛)
    "磁性霸道男总裁": "longfei_v2"    # 磁性热血男 (龙飞)
}

# 走神语音提醒词配置 (后端固定风格)
DISTRACTION_REMINDERS = {
    "默认": "专注一下，你可以的！",
    "柔情猫娘": "主人，不可以分心喵~ 快回过神来！",
    "成熟妈妈系御姐": "亲爱的，稍微集中一下注意力，好吗？",
    "磁性霸道男总裁": "我不允许你在这种时候分心，听到了吗？"
}

# 负面情绪鼓励语音提醒词配置 (后端固定风格)
ENCOURAGE_REMINDERS = {
    "默认": "看起来你有点累了，记得适当休息哦，你已经很棒了！",
    "柔情猫娘": "主人喵~ 是不是累坏了？喵喵给你一个隔空的抱抱喵，打起精神来喵~",
    "成熟妈妈系御姐": "我的好孩子，累了就歇会儿，不管遇到什么困难，我都会陪在你身边的。",
    "磁性霸道男总裁": "振作起来，我不允许我的陪伴者露出这种丧气的表情。休息五分钟，然后继续。"
}

def get_alert_speech(trigger_val, style):
    """为系统主动提醒生成语音（包括分神提醒和情绪鼓励）"""
    if not trigger_val:
        return None
        
    # 解析触发类型
    if trigger_val.startswith("distracted_"):
        reminders = DISTRACTION_REMINDERS
        label = "分神提醒"
    elif trigger_val.startswith("encourage_"):
        reminders = ENCOURAGE_REMINDERS
        label = "情绪鼓励"
    else:
        # 默认处理
        reminders = DISTRACTION_REMINDERS
        label = "分神提醒(缺省)"
        
    text = reminders.get(style, reminders["默认"])
    print(f"[DEBUG-TTS] 收到{label}请求 | 风格: {style} | 内容: {text}")
    result = text_to_speech(text, style)
    print(f"[DEBUG-TTS] 合成完成 | 结果长度: {len(result) if isinstance(result, bytes) else 'None/Path'}")
    return result

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
    """调用魔搭API（非流式）"""
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

def call_ai_api_stream(messages):
    """调用魔搭API（流式输出）"""
    try:
        response = requests.post(
            MODELSCOPE_API_URL,
            headers={"Authorization": f"Bearer {MODELSCOPE_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct", 
                "messages": messages, 
                "temperature": 0.7, 
                "max_tokens": 1000,
                "stream": True  # 启用流式输出
            },
            timeout=120,
            stream=True  # requests库的流式响应
        )
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    # SSE格式: data: {...}
                    if line_text.startswith('data: '):
                        data_str = line_text[6:]  # 去掉 "data: " 前缀
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        else:
            yield f"API请求失败: {response.status_code}"
    except Exception as e:
        yield f"请求出错: {str(e)}"

def chat(message, history, style, voice_enabled):
    """处理聊天消息 - 流式输出版本"""
    global conversation_history
    
    if not message.strip():
        yield history, "", None
        return
    
    print(f"[CHAT DEBUG] 收到消息: {message[:20]}... 风格: {style} 语音开启: {voice_enabled}")
    
    conversation_history.append({"role": "user", "content": message})
    
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    # 根据选择的风格获取对应的提示词
    system_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["默认"])
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    
    # 先添加用户消息到历史
    history.append({"role": "user", "content": message})
    
    # 流式输出AI回复
    ai_message = ""
    history.append({"role": "assistant", "content": ""})
    
    for chunk in call_ai_api_stream(messages):
        ai_message += chunk
        history[-1]["content"] = ai_message
        yield history, "", None  # 流式更新，不播放语音
    
    # 完成后更新对话历史
    conversation_history.append({"role": "assistant", "content": ai_message})
    
    # 语音播报在流式输出完成后执行
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
    
    # 最终yield包含语音数据
    yield history, "", audio_path

def clear_history():
    """清空对话历史"""
    global conversation_history
    conversation_history = []
    return [], ""

# 初始消息
INITIAL_MESSAGES = [
    {"role": "assistant", "content": "你好呀！我是学了么，你的学习陪伴AI助手~\n\n有什么问题都可以问我，学习累了也可以和我聊聊天。\n\n点击左侧的\"开启摄像头\"按钮，我还能通过人脸识别实时关注你的学习状态哦！"}
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
        points: 0,                    // 总积分（用于升级，只增不减）
        spendablePoints: 0,           // 可消耗积分（用于抽卡）
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
        weeklyReports: [],            // 周报记录
        // ========== To-Do List 字段 ==========
        todoList: [],                 // 待办事项 [{id, text, completed, createdAt, completedAt}]
        totalTasksCompleted: 0,       // 累计完成任务数
        // ========== 抽卡系统字段 ==========
        inventory: [],                // 背包 [{itemId, count, obtainedAt}]
        equipped: {                   // 当前装备
            avatarFrame: null,        // 头像框ID
            chatBubble: null,         // 聊天气泡ID
            theme: null               // 主题皮肤ID
        },
        gachaHistory: [],             // 抽卡历史（最近50条）
        totalGachaCount: 0,           // 累计抽卡次数
        // ========== 功能道具状态 ==========
        activeBuffs: {                // 激活的增益效果
            doublePoints: null,       // 双倍积分到期时间
            focusBoost: null          // 专注加成到期时间
        }
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
        { id: 'points_5000', name: '积分大户', desc: '累计获得5000积分', icon: '💎', check: (d) => d.points >= 5000 },
        // 任务相关成就
        { id: 'task_first', name: '首个任务', desc: '完成第一个任务', icon: '✅', check: (d) => d.totalTasksCompleted >= 1 },
        { id: 'task_10', name: '任务达人', desc: '累计完成10个任务', icon: '📋', check: (d) => d.totalTasksCompleted >= 10 },
        { id: 'task_50', name: '效率专家', desc: '累计完成50个任务', icon: '🚀', check: (d) => d.totalTasksCompleted >= 50 },
        { id: 'task_100', name: '执行力大师', desc: '累计完成100个任务', icon: '👑', check: (d) => d.totalTasksCompleted >= 100 }
    ];
    
    // ========== 抽卡系统配置 ==========
    const GACHA_COST = 20; // 单次抽卡消耗积分
    
    // 稀有度配置
    const rarityConfig = {
        N: { name: '普通', color: '#9ca3af', bgColor: '#f3f4f6', probability: 50 },
        R: { name: '稀有', color: '#3b82f6', bgColor: '#dbeafe', probability: 30 },
        SR: { name: '超稀', color: '#8b5cf6', bgColor: '#ede9fe', probability: 15 },
        SSR: { name: '传说', color: '#f59e0b', bgColor: '#fef3c7', probability: 5 }
    };
    
    // 抽卡物品池
    const gachaItems = [
        // ===== 头像框（应用于等级图标） =====
        { id: 'frame_simple', name: '简约边框', type: 'avatarFrame', rarity: 'N', icon: '⬜', desc: '简洁大方的基础边框', style: 'background:linear-gradient(135deg,#f3f4f6,#e5e7eb);border:2px solid #9ca3af;border-radius:8px;padding:4px 8px;' },
        { id: 'frame_blue', name: '海洋之心', type: 'avatarFrame', rarity: 'R', icon: '💙', desc: '清澈如海的蓝色边框', style: 'background:linear-gradient(135deg,#dbeafe,#bfdbfe);border:2px solid #3b82f6;border-radius:8px;padding:4px 8px;box-shadow:0 0 12px rgba(59,130,246,0.6);' },
        { id: 'frame_purple', name: '星云紫光', type: 'avatarFrame', rarity: 'R', icon: '💜', desc: '神秘的紫色光环', style: 'background:linear-gradient(135deg,#ede9fe,#ddd6fe);border:2px solid #8b5cf6;border-radius:8px;padding:4px 8px;box-shadow:0 0 15px rgba(139,92,246,0.7);' },
        { id: 'frame_rainbow', name: '彩虹环绕', type: 'avatarFrame', rarity: 'SR', icon: '🌈', desc: '七彩流光边框', style: 'background:linear-gradient(45deg,#fef2f2,#fef9c3,#ecfdf5,#eff6ff,#faf5ff);border:3px solid transparent;border-radius:10px;padding:4px 8px;background-clip:padding-box;box-shadow:0 0 0 3px transparent,0 0 20px rgba(168,85,247,0.4);animation:rainbow-border 3s linear infinite;' },
        { id: 'frame_gold', name: '黄金圣殿', type: 'avatarFrame', rarity: 'SSR', icon: '👑', desc: '尊贵的金色边框', style: 'background:linear-gradient(135deg,#fef3c7,#fde68a,#fcd34d);border:3px solid #f59e0b;border-radius:10px;padding:4px 8px;box-shadow:0 0 20px rgba(245,158,11,0.8),inset 0 0 10px rgba(255,255,255,0.5);' },
        { id: 'frame_flame', name: '烈焰之心', type: 'avatarFrame', rarity: 'SSR', icon: '🔥', desc: '燃烧的火焰边框', style: 'background:linear-gradient(135deg,#fef2f2,#fee2e2,#fecaca);border:3px solid #ef4444;border-radius:10px;padding:4px 8px;box-shadow:0 0 25px rgba(239,68,68,0.9);animation:flame-glow 1.5s ease-in-out infinite;' },
        
        // ===== 聊天气泡（高级边框花纹设计+主题图案） =====
        { id: 'bubble_default', name: '经典气泡', type: 'chatBubble', rarity: 'N', icon: '💬', desc: '简洁的默认气泡', style: 'background:#f3f4f6 !important;color:#1f2937 !important;border-radius:12px !important;border:1px solid #e5e7eb !important;padding:12px 16px !important;' },
        { id: 'bubble_dashed', name: '虚线边框', type: 'chatBubble', rarity: 'N', icon: '▫️', desc: '简约的虚线边框', style: 'background:#ffffff !important;color:#374151 !important;border:2px dashed #6b7280 !important;border-radius:12px !important;padding:12px 16px !important;' },
        { id: 'bubble_heart', name: '爱心花边', type: 'chatBubble', rarity: 'R', icon: '💕', desc: '可爱的爱心装饰边框', style: 'background:linear-gradient(135deg,#fff1f2,#ffe4e6) !important;color:#881337 !important;border:3px solid #fb7185 !important;border-radius:20px !important;padding:14px 18px !important;box-shadow:0 0 0 4px #fecdd3,0 4px 15px rgba(251,113,133,0.3) !important;' },
        { id: 'bubble_leaf', name: '绿叶环绕', type: 'chatBubble', rarity: 'R', icon: '🍃', desc: '清新的绿叶装饰', style: 'background:linear-gradient(135deg,#f0fdf4,#dcfce7) !important;color:#14532d !important;border:3px solid #86efac !important;border-radius:18px !important;padding:14px 18px !important;box-shadow:inset 0 0 20px rgba(134,239,172,0.3),0 4px 15px rgba(34,197,94,0.2) !important;' },
        { id: 'bubble_gradient', name: '渐变气泡', type: 'chatBubble', rarity: 'R', icon: '🎨', desc: '柔和的渐变色气泡', style: 'background:linear-gradient(135deg,#667eea,#764ba2) !important;color:#ffffff !important;border-radius:16px !important;border:2px solid rgba(255,255,255,0.3) !important;box-shadow:0 4px 15px rgba(102,126,234,0.3) !important;padding:12px 16px !important;' },
        { id: 'bubble_dotted', name: '点线花边', type: 'chatBubble', rarity: 'R', icon: '⚬', desc: '可爱的点线边框', style: 'background:#fefce8 !important;color:#713f12 !important;border:3px dotted #eab308 !important;border-radius:18px !important;padding:12px 16px !important;box-shadow:0 2px 8px rgba(234,179,8,0.2) !important;' },
        { id: 'bubble_double', name: '双线边框', type: 'chatBubble', rarity: 'R', icon: '▣', desc: '典雅的双线边框', style: 'background:#f8fafc !important;color:#1e3a8a !important;border:4px double #3b82f6 !important;border-radius:14px !important;padding:12px 16px !important;' },
        { id: 'bubble_neon', name: '霓虹闪烁', type: 'chatBubble', rarity: 'SR', icon: '✨', desc: '炫酷的霓虹灯效果', style: 'background:linear-gradient(135deg,#0f172a,#1e293b) !important;color:#4ade80 !important;border:2px solid #22c55e !important;box-shadow:0 0 20px rgba(34,197,94,0.5),0 0 40px rgba(34,197,94,0.2) !important;border-radius:16px !important;padding:12px 16px !important;font-weight:500 !important;' },
        { id: 'bubble_sakura', name: '樱花飘落', type: 'chatBubble', rarity: 'SR', icon: '🌸', desc: '浪漫的樱花边框', style: 'background:linear-gradient(135deg,#fdf2f8,#fce7f3) !important;color:#831843 !important;border:3px solid #f9a8d4 !important;border-radius:20px !important;box-shadow:0 4px 20px rgba(236,72,153,0.2) !important;padding:14px 18px !important;outline:2px dashed #fbcfe8 !important;outline-offset:3px !important;' },
        { id: 'bubble_starry', name: '星空闪耀', type: 'chatBubble', rarity: 'SR', icon: '🌟', desc: '闪烁的星空效果', style: 'background:linear-gradient(135deg,#312e81,#4338ca) !important;color:#e0e7ff !important;border:2px solid #818cf8 !important;border-radius:16px !important;box-shadow:0 0 20px rgba(99,102,241,0.5),inset 0 0 30px rgba(165,180,252,0.1) !important;padding:12px 16px !important;font-weight:500 !important;' },
        { id: 'bubble_wave', name: '波浪花边', type: 'chatBubble', rarity: 'SR', icon: '🌊', desc: '波浪形装饰边框', style: 'background:linear-gradient(180deg,#e0f2fe,#bae6fd) !important;color:#0c4a6e !important;border:none !important;border-radius:20px !important;padding:14px 18px !important;box-shadow:0 4px 15px rgba(14,165,233,0.25),0 0 0 3px #7dd3fc,0 0 0 6px #bae6fd !important;' },
        { id: 'bubble_bamboo', name: '竹林清风', type: 'chatBubble', rarity: 'SR', icon: '🎋', desc: '中国风竹纹边框', style: 'background:linear-gradient(180deg,#f0fdf4,#ecfdf5) !important;color:#14532d !important;border:3px solid #4ade80 !important;border-radius:8px !important;padding:14px 18px !important;box-shadow:inset 4px 0 0 #86efac,inset -4px 0 0 #86efac,0 4px 15px rgba(74,222,128,0.2) !important;' },
        { id: 'bubble_crystal', name: '水晶气泡', type: 'chatBubble', rarity: 'SSR', icon: '💎', desc: '晶莹剔透的水晶气泡', style: 'background:linear-gradient(135deg,rgba(255,255,255,0.95),rgba(220,230,255,0.95)) !important;color:#1e3a8a !important;border:3px solid rgba(147,197,253,0.9) !important;box-shadow:0 8px 32px rgba(100,150,255,0.4),inset 0 2px 10px rgba(255,255,255,0.8),0 0 0 1px rgba(255,255,255,0.5) !important;border-radius:20px !important;padding:14px 18px !important;' },
        { id: 'bubble_flame', name: '烈焰之语', type: 'chatBubble', rarity: 'SSR', icon: '🔥', desc: '燃烧的火焰边框', style: 'background:linear-gradient(135deg,#2d1810,#3d2518) !important;color:#fff8e1 !important;border:3px solid #f97316 !important;border-radius:16px !important;box-shadow:0 0 25px rgba(249,115,22,0.6),0 0 50px rgba(245,158,11,0.3),inset 0 0 20px rgba(249,115,22,0.1) !important;padding:14px 18px !important;font-weight:600 !important;text-shadow:0 0 10px rgba(255,200,100,0.8),0 1px 2px rgba(0,0,0,0.5) !important;' },
        { id: 'bubble_galaxy', name: '银河漩涡', type: 'chatBubble', rarity: 'SSR', icon: '🌌', desc: '璀璨的银河边框', style: 'background:linear-gradient(135deg,#0f0a1e,#1a1033,#0f0a1e) !important;color:#e9d5ff !important;border:3px solid #a855f7 !important;border-radius:18px !important;box-shadow:0 0 30px rgba(168,85,247,0.5),0 0 60px rgba(139,92,246,0.3),inset 0 0 40px rgba(192,132,252,0.1) !important;padding:14px 18px !important;font-weight:500 !important;' },
        
        // ===== 主题皮肤（带高级背景设计） =====
        { id: 'theme_default', name: '默认主题', type: 'theme', rarity: 'N', icon: '🎯', desc: '清新简约的默认主题', cssVars: { 
            primary: '#667eea', secondary: '#764ba2', 
            bgGradient: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f1f5f9 100%)',
            bgPattern: 'radial-gradient(circle at 20% 80%, rgba(102,126,234,0.08) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(118,75,162,0.08) 0%, transparent 50%)',
            textColor: '#1e293b', cardBg: 'rgba(255,255,255,0.9)'
        }},
        { id: 'theme_ocean', name: '海洋之梦', type: 'theme', rarity: 'R', icon: '🌊', desc: '深邃的海洋蓝主题', cssVars: { 
            primary: '#0ea5e9', secondary: '#0284c7', 
            bgGradient: 'linear-gradient(180deg, #e0f2fe 0%, #bae6fd 30%, #7dd3fc 70%, #38bdf8 100%)',
            bgPattern: 'radial-gradient(ellipse at top, rgba(14,165,233,0.15) 0%, transparent 60%), radial-gradient(circle at 30% 70%, rgba(56,189,248,0.2) 0%, transparent 40%), radial-gradient(circle at 70% 90%, rgba(125,211,252,0.3) 0%, transparent 30%)',
            textColor: '#0c4a6e', cardBg: 'rgba(255,255,255,0.85)'
        }},
        { id: 'theme_forest', name: '森林物语', type: 'theme', rarity: 'R', icon: '🌲', desc: '清新的森林绿主题', cssVars: { 
            primary: '#10b981', secondary: '#059669', 
            bgGradient: 'linear-gradient(160deg, #ecfdf5 0%, #d1fae5 40%, #a7f3d0 80%, #6ee7b7 100%)',
            bgPattern: 'radial-gradient(ellipse at bottom left, rgba(16,185,129,0.12) 0%, transparent 50%), radial-gradient(circle at 60% 20%, rgba(5,150,105,0.1) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(110,231,183,0.15) 0%, transparent 35%)',
            textColor: '#064e3b', cardBg: 'rgba(255,255,255,0.88)'
        }},
        { id: 'theme_sakura', name: '樱花漫舞', type: 'theme', rarity: 'SR', icon: '🌸', desc: '浪漫的樱花粉主题', cssVars: { 
            primary: '#ec4899', secondary: '#db2777', 
            bgGradient: 'linear-gradient(135deg, #fdf2f8 0%, #fce7f3 30%, #fbcfe8 60%, #f9a8d4 100%)',
            bgPattern: 'radial-gradient(circle at 10% 20%, rgba(236,72,153,0.15) 0%, transparent 30%), radial-gradient(circle at 90% 30%, rgba(249,168,212,0.2) 0%, transparent 35%), radial-gradient(circle at 50% 80%, rgba(219,39,119,0.1) 0%, transparent 40%), radial-gradient(circle at 20% 90%, rgba(252,231,243,0.5) 0%, transparent 25%)',
            textColor: '#831843', cardBg: 'rgba(255,255,255,0.9)'
        }},
        { id: 'theme_sunset', name: '落日余晖', type: 'theme', rarity: 'SR', icon: '🌅', desc: '温暖的夕阳橙主题', cssVars: { 
            primary: '#f97316', secondary: '#ea580c', 
            bgGradient: 'linear-gradient(180deg, #fef3c7 0%, #fde68a 25%, #fcd34d 50%, #fbbf24 75%, #f59e0b 100%)',
            bgPattern: 'radial-gradient(ellipse at top, rgba(254,243,199,0.8) 0%, transparent 50%), radial-gradient(circle at 20% 60%, rgba(249,115,22,0.12) 0%, transparent 40%), radial-gradient(circle at 80% 40%, rgba(234,88,12,0.1) 0%, transparent 35%)',
            textColor: '#78350f', cardBg: 'rgba(255,255,255,0.85)'
        }},
        { id: 'theme_galaxy', name: '银河星辰', type: 'theme', rarity: 'SSR', icon: '🌌', desc: '神秘的星空紫主题', cssVars: { 
            primary: '#6366f1', secondary: '#4f46e5', 
            bgGradient: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 30%, #3730a3 60%, #4338ca 100%)',
            bgPattern: 'radial-gradient(circle at 20% 30%, rgba(139,92,246,0.3) 0%, transparent 25%), radial-gradient(circle at 80% 70%, rgba(99,102,241,0.25) 0%, transparent 30%), radial-gradient(circle at 50% 10%, rgba(167,139,250,0.2) 0%, transparent 20%), radial-gradient(circle at 10% 80%, rgba(79,70,229,0.15) 0%, transparent 25%), radial-gradient(circle at 90% 20%, rgba(129,140,248,0.2) 0%, transparent 15%)',
            textColor: '#e0e7ff', cardBg: 'rgba(30,27,75,0.7)', isDark: true
        }},
        { id: 'theme_dark', name: '暗夜模式', type: 'theme', rarity: 'SSR', icon: '🌙', desc: '护眼的深色主题', cssVars: { 
            primary: '#8b5cf6', secondary: '#7c3aed', 
            bgGradient: 'linear-gradient(160deg, #0f172a 0%, #1e1b4b 40%, #1e293b 80%, #0f172a 100%)',
            bgPattern: 'radial-gradient(circle at 30% 20%, rgba(139,92,246,0.15) 0%, transparent 35%), radial-gradient(circle at 70% 80%, rgba(124,58,237,0.12) 0%, transparent 30%), radial-gradient(circle at 50% 50%, rgba(99,102,241,0.08) 0%, transparent 50%)',
            textColor: '#e2e8f0', cardBg: 'rgba(30,41,59,0.8)', isDark: true
        }},
        
        // ===== 功能道具 =====
        { id: 'item_double_points', name: '双倍积分卡', type: 'consumable', rarity: 'SR', icon: '⚡', desc: '24小时内获得积分翻倍', duration: 24 * 60 * 60 * 1000 },
        { id: 'item_checkin_card', name: '补签卡', type: 'consumable', rarity: 'SR', icon: '📅', desc: '可补签错过的一天', usage: 'checkin' },
        { id: 'item_lucky_coin', name: '幸运金币', type: 'consumable', rarity: 'R', icon: '🪙', desc: '下次抽卡必出R及以上', usage: 'gacha_boost' },
        { id: 'item_points_5', name: '积分袋(迷你)', type: 'consumable', rarity: 'N', icon: '💰', desc: '获得5积分', points: 5 },
        { id: 'item_points_10', name: '积分袋(小)', type: 'consumable', rarity: 'N', icon: '💰', desc: '获得10积分', points: 10 },
        { id: 'item_points_20', name: '积分袋(中)', type: 'consumable', rarity: 'R', icon: '💰', desc: '获得20积分', points: 20 },
        { id: 'item_points_50', name: '积分袋(大)', type: 'consumable', rarity: 'SR', icon: '💰', desc: '获得50积分', points: 50 },
        
        // ===== 称号 =====
        { id: 'title_newbie', name: '萌新上路', type: 'title', rarity: 'N', icon: '🐣', desc: '刚刚开始的冒险者' },
        { id: 'title_lucky', name: '欧皇降临', type: 'title', rarity: 'R', icon: '🍀', desc: '幸运女神的宠儿' },
        { id: 'title_collector', name: '收藏家', type: 'title', rarity: 'SR', icon: '📦', desc: '热衷收集的达人' },
        { id: 'title_legend', name: '传说学者', type: 'title', rarity: 'SSR', icon: '🌟', desc: '闪耀的传奇存在' },
        
        // ===== 学习名言卡片 (SR超稀 & SSR传说) =====
        // --- SR 超稀卡片 (35张) ---
        { id: 'quote_confucius', name: '孔子·学思', type: 'quoteCard', rarity: 'SR', icon: '🎴', 
          quote: '学而不思则罔，思而不学则殆。', author: '孔子',
          bgStyle: 'linear-gradient(135deg,#fef3c7,#fde68a)', textColor: '#78350f', authorImg: '🧒' },
        { id: 'quote_einstein', name: '爱因斯坦·想象力', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '想象力比知识更重要，因为知识是有限的，而想象力概括着世界的一切。', author: '爱因斯坦',
          bgStyle: 'linear-gradient(135deg,#dbeafe,#bfdbfe)', textColor: '#1e40af', authorImg: '👨‍🔬' },
        { id: 'quote_aristotle', name: '亚里士多德·卓越', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '优秀不是一种行为，而是一种习惯。', author: '亚里士多德',
          bgStyle: 'linear-gradient(135deg,#d1fae5,#a7f3d0)', textColor: '#065f46', authorImg: '🏛️' },
        { id: 'quote_edison', name: '爱迪生·天才', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '天才是百分之一的灵感加百分之九十九的汗水。', author: '爱迪生',
          bgStyle: 'linear-gradient(135deg,#fce7f3,#fbcfe8)', textColor: '#831843', authorImg: '💡' },
        { id: 'quote_newton', name: '牛顿·巨人肩膀', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '如果我看得更远，那是因为我站在巨人的肩膀上。', author: '牛顿',
          bgStyle: 'linear-gradient(135deg,#e0e7ff,#c7d2fe)', textColor: '#3730a3', authorImg: '🍎' },
        { id: 'quote_laozi', name: '老子·千里之行', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '千里之行，始于足下。', author: '老子',
          bgStyle: 'linear-gradient(135deg,#ccfbf1,#99f6e4)', textColor: '#115e59', authorImg: '☯️' },
        { id: 'quote_curie', name: '居里夫人·坚持', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '生活中没有什么可怕的东西，只有需要理解的东西。', author: '居里夫人',
          bgStyle: 'linear-gradient(135deg,#fef9c3,#fef08a)', textColor: '#713f12', authorImg: '⚗️' },
        { id: 'quote_socrates', name: '苏格拉底·无知', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '我唯一知道的就是我一无所知。', author: '苏格拉底',
          bgStyle: 'linear-gradient(135deg,#f3e8ff,#e9d5ff)', textColor: '#581c87', authorImg: '🤔' },
        { id: 'quote_plato', name: '柏拉图·开始', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '良好的开端是成功的一半。', author: '柏拉图',
          bgStyle: 'linear-gradient(135deg,#cffafe,#a5f3fc)', textColor: '#155e75', authorImg: '📖' },
        { id: 'quote_mencius', name: '孟子·心志', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '天将降大任于斯人也，必先苦其心志。', author: '孟子',
          bgStyle: 'linear-gradient(135deg,#fee2e2,#fecaca)', textColor: '#991b1b', authorImg: '📚' },
        { id: 'quote_xunzi', name: '荀子·积累', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '不积跬步，无以至千里；不积小流，无以成江海。', author: '荀子',
          bgStyle: 'linear-gradient(135deg,#d1fae5,#bbf7d0)', textColor: '#166534', authorImg: '🌊' },
        { id: 'quote_zhuxi', name: '朱熹·读书', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '读书有三到，谓心到、眼到、口到。', author: '朱熹',
          bgStyle: 'linear-gradient(135deg,#fef3c7,#fde047)', textColor: '#854d0e', authorImg: '📕' },
        { id: 'quote_kant', name: '康德·星空', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '有两种东西，我越思索越觉神奇：头顶的星空和内心的道德律。', author: '康德',
          bgStyle: 'linear-gradient(135deg,#1e293b,#334155)', textColor: '#e2e8f0', authorImg: '⭐' },
        { id: 'quote_descartes', name: '笛卡尔·思考', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '我思故我在。', author: '笛卡尔',
          bgStyle: 'linear-gradient(135deg,#f0fdf4,#dcfce7)', textColor: '#14532d', authorImg: '🧠' },
        { id: 'quote_bacon', name: '培根·知识', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '知识就是力量。', author: '培根',
          bgStyle: 'linear-gradient(135deg,#fef2f2,#fecaca)', textColor: '#7f1d1d', authorImg: '💪' },
        { id: 'quote_franklin', name: '富兰克林·时间', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '时间就是金钱。', author: '本杰明·富兰克林',
          bgStyle: 'linear-gradient(135deg,#fefce8,#fef08a)', textColor: '#713f12', authorImg: '⏰' },
        { id: 'quote_lincoln', name: '林肯·准备', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '如果我有八小时砍树，我会花六小时磨斧头。', author: '林肯',
          bgStyle: 'linear-gradient(135deg,#ecfdf5,#a7f3d0)', textColor: '#064e3b', authorImg: '🪓' },
        { id: 'quote_churchill', name: '丘吉尔·坚持', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '永远不要放弃，永远，永远，永远。', author: '丘吉尔',
          bgStyle: 'linear-gradient(135deg,#fef2f2,#fee2e2)', textColor: '#991b1b', authorImg: '🎖️' },
        { id: 'quote_twain', name: '马克吐温·行动', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '二十年后，你会更后悔那些你没做的事。', author: '马克·吐温',
          bgStyle: 'linear-gradient(135deg,#fff7ed,#fed7aa)', textColor: '#9a3412', authorImg: '✍️' },
        { id: 'quote_voltaire', name: '伏尔泰·完美', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '完美是优秀的敌人。', author: '伏尔泰',
          bgStyle: 'linear-gradient(135deg,#f5f3ff,#ddd6fe)', textColor: '#5b21b6', authorImg: '✨' },
        { id: 'quote_goethe', name: '歌德·行动', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '凡是值得思考的事情，没有不是被人思考过的；我们必须做的只是试图重新加以思考。', author: '歌德',
          bgStyle: 'linear-gradient(135deg,#f0f9ff,#bae6fd)', textColor: '#0c4a6e', authorImg: '📝' },
        { id: 'quote_tolstoy', name: '托尔斯泰·改变', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '每个人都想改变世界，但没人想改变自己。', author: '托尔斯泰',
          bgStyle: 'linear-gradient(135deg,#fdf4ff,#f5d0fe)', textColor: '#86198f', authorImg: '🪞' },
        { id: 'quote_gandhi', name: '甘地·改变', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '欲变世界，先变其身。', author: '甘地',
          bgStyle: 'linear-gradient(135deg,#fff7ed,#ffedd5)', textColor: '#c2410c', authorImg: '🕊️' },
        { id: 'quote_helen', name: '海伦凯勒·乐观', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '乐观是通向成就的信念，没有希望就没有任何事情能做成。', author: '海伦·凯勒',
          bgStyle: 'linear-gradient(135deg,#fdf2f8,#fce7f3)', textColor: '#9d174d', authorImg: '🌸' },
        { id: 'quote_emerson', name: '爱默生·自信', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '自信是成功的第一秘诀。', author: '爱默生',
          bgStyle: 'linear-gradient(135deg,#ecfeff,#cffafe)', textColor: '#0e7490', authorImg: '💎' },
        { id: 'quote_hugo', name: '雨果·思想', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '世界上最宽阔的是海洋，比海洋更宽阔的是天空，比天空更宽阔的是人的胸怀。', author: '雨果',
          bgStyle: 'linear-gradient(135deg,#f0f9ff,#e0f2fe)', textColor: '#075985', authorImg: '🌊' },
        { id: 'quote_shakespeare', name: '莎士比亚·时间', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '抛弃时间的人，时间也抛弃他。', author: '莎士比亚',
          bgStyle: 'linear-gradient(135deg,#fefce8,#fef9c3)', textColor: '#854d0e', authorImg: '🎭' },
        { id: 'quote_hemingway', name: '海明威·勇气', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '勇气就是优雅地面对压力。', author: '海明威',
          bgStyle: 'linear-gradient(135deg,#f1f5f9,#e2e8f0)', textColor: '#334155', authorImg: '🦁' },
        { id: 'quote_nietzsche', name: '尼采·自我', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '那些杀不死我的，终将使我更强大。', author: '尼采',
          bgStyle: 'linear-gradient(135deg,#1e1b4b,#3730a3)', textColor: '#e0e7ff', authorImg: '⚡' },
        { id: 'quote_thoreau', name: '梭罗·简单', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '简单，简单，再简单。', author: '梭罗',
          bgStyle: 'linear-gradient(135deg,#ecfdf5,#d1fae5)', textColor: '#047857', authorImg: '🌲' },
        { id: 'quote_russell', name: '罗素·思考', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '很多人宁愿死也不愿思考，事实上他们确实如此。', author: '罗素',
          bgStyle: 'linear-gradient(135deg,#faf5ff,#ede9fe)', textColor: '#6b21a8', authorImg: '🎓' },
        { id: 'quote_darwin', name: '达尔文·适应', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '能够生存下来的物种不是最强的，而是最能适应变化的。', author: '达尔文',
          bgStyle: 'linear-gradient(135deg,#f0fdf4,#bbf7d0)', textColor: '#15803d', authorImg: '🐢' },
        { id: 'quote_pasteur', name: '巴斯德·机遇', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '机遇只偏爱有准备的头脑。', author: '巴斯德',
          bgStyle: 'linear-gradient(135deg,#eff6ff,#dbeafe)', textColor: '#1e40af', authorImg: '🔬' },
        { id: 'quote_tesla', name: '特斯拉·现在', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '现在是我的，未来也是我的。', author: '尼古拉·特斯拉',
          bgStyle: 'linear-gradient(135deg,#fefce8,#fef08a)', textColor: '#a16207', authorImg: '⚡' },
        { id: 'quote_feynman', name: '费曼·学习', type: 'quoteCard', rarity: 'SR', icon: '🎴',
          quote: '我宁愿有一个无法解答的问题，也不愿有一个无法质疑的答案。', author: '费曼',
          bgStyle: 'linear-gradient(135deg,#fef2f2,#fecaca)', textColor: '#b91c1c', authorImg: '🥁' },
        
        // --- SSR 传说卡片 (15张) - 更多特效 ---
        { id: 'quote_jobs', name: '乔布斯·求知若渴', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: 'Stay hungry, stay foolish. 求知若饥，虚心若愚。', author: '史蒂夫·乔布斯',
          bgStyle: 'linear-gradient(135deg,#1e1b4b,#312e81,#4338ca)', textColor: '#e0e7ff', authorImg: '🍏',
          glowColor: 'rgba(99,102,241,0.6)', particles: true },
        { id: 'quote_hawking', name: '霍金·永不放弃', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '无论生活看起来多么艰难，总有你能做的事情并且能够成功。', author: '史蒂芬·霍金',
          bgStyle: 'linear-gradient(135deg,#0f172a,#1e293b,#334155)', textColor: '#f8fafc', authorImg: '🌌',
          glowColor: 'rgba(148,163,184,0.5)', particles: true },
        { id: 'quote_zhuangzi', name: '庄子·无涯', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '吾生也有涯，而知也无涯。', author: '庄子',
          bgStyle: 'linear-gradient(135deg,#fdf4ff,#fae8ff,#f5d0fe)', textColor: '#701a75', authorImg: '🦋',
          glowColor: 'rgba(192,132,252,0.5)', particles: true },
        { id: 'quote_davinvi', name: '达芬奇·简洁', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '简洁是终极的复杂。', author: '达芬奇',
          bgStyle: 'linear-gradient(135deg,#fef3c7,#fde68a,#fbbf24)', textColor: '#78350f', authorImg: '🎨',
          glowColor: 'rgba(251,191,36,0.5)', particles: true },
        { id: 'quote_confucius2', name: '孔子·三人行', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '三人行，必有我师焉。择其善者而从之，其不善者而改之。', author: '孔子',
          bgStyle: 'linear-gradient(135deg,#dc2626,#ef4444,#f87171)', textColor: '#fef2f2', authorImg: '🏮',
          glowColor: 'rgba(239,68,68,0.5)', particles: true },
        { id: 'quote_einstein2', name: '爱因斯坦·坚持', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '不是我聪明，只是我和问题周旋得比较久。', author: '爱因斯坦',
          bgStyle: 'linear-gradient(135deg,#0ea5e9,#38bdf8,#7dd3fc)', textColor: '#0c4a6e', authorImg: '🧪',
          glowColor: 'rgba(56,189,248,0.5)', particles: true },
        { id: 'quote_musk', name: '马斯克·失败', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '失败是一种选择。如果事情没有失败，说明你的创新还不够。', author: '埃隆·马斯克',
          bgStyle: 'linear-gradient(135deg,#18181b,#27272a,#3f3f46)', textColor: '#fafafa', authorImg: '🚀',
          glowColor: 'rgba(250,250,250,0.3)', particles: true },
        { id: 'quote_mandela', name: '曼德拉·不可能', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '在事情未完成之前，一切都看似不可能。', author: '曼德拉',
          bgStyle: 'linear-gradient(135deg,#15803d,#22c55e,#4ade80)', textColor: '#f0fdf4', authorImg: '✊',
          glowColor: 'rgba(34,197,94,0.5)', particles: true },
        { id: 'quote_newton2', name: '牛顿·海边', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '我就像一个在海边玩耍的孩子，偶尔发现一颗比较光滑的石子。', author: '牛顿',
          bgStyle: 'linear-gradient(135deg,#0369a1,#0284c7,#0ea5e9)', textColor: '#f0f9ff', authorImg: '🐚',
          glowColor: 'rgba(14,165,233,0.5)', particles: true },
        { id: 'quote_wangyangming', name: '王阳明·知行合一', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '知是行之始，行是知之成。', author: '王阳明',
          bgStyle: 'linear-gradient(135deg,#7c2d12,#9a3412,#c2410c)', textColor: '#fff7ed', authorImg: '⚔️',
          glowColor: 'rgba(194,65,12,0.5)', particles: true },
        { id: 'quote_disney', name: '迪士尼·梦想', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '如果你能梦想到它，你就能做到它。', author: '华特·迪士尼',
          bgStyle: 'linear-gradient(135deg,#7e22ce,#a855f7,#c084fc)', textColor: '#faf5ff', authorImg: '🏰',
          glowColor: 'rgba(168,85,247,0.5)', particles: true },
        { id: 'quote_gates', name: '比尔盖茨·懒人', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '我选择懒人做困难的工作，因为他们会找到简单的方法。', author: '比尔·盖茨',
          bgStyle: 'linear-gradient(135deg,#0f766e,#14b8a6,#2dd4bf)', textColor: '#f0fdfa', authorImg: '💻',
          glowColor: 'rgba(20,184,166,0.5)', particles: true },
        { id: 'quote_buffett', name: '巴菲特·投资', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '最好的投资就是投资自己。', author: '沃伦·巴菲特',
          bgStyle: 'linear-gradient(135deg,#166534,#22c55e,#86efac)', textColor: '#f0fdf4', authorImg: '📈',
          glowColor: 'rgba(34,197,94,0.5)', particles: true },
        { id: 'quote_mlk', name: '马丁路德金·黑暗', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '黑暗不能驱走黑暗，只有光明可以；仇恨不能驱走仇恨，只有爱可以。', author: '马丁·路德·金',
          bgStyle: 'linear-gradient(135deg,#fbbf24,#f59e0b,#d97706)', textColor: '#451a03', authorImg: '🕯️',
          glowColor: 'rgba(251,191,36,0.6)', particles: true },
        { id: 'quote_mother', name: '特蕾莎·小事', type: 'quoteCard', rarity: 'SSR', icon: '🌟',
          quote: '我们无法做伟大的事，只能用伟大的爱做小事。', author: '特蕾莎修女',
          bgStyle: 'linear-gradient(135deg,#be185d,#ec4899,#f472b6)', textColor: '#fdf2f8', authorImg: '💝',
          glowColor: 'rgba(236,72,153,0.5)', particles: true }
    ];
    
    // 获取物品信息
    function getItemById(itemId) {
        return gachaItems.find(item => item.id === itemId);
    }
    
    // 抽卡函数
    function doGacha() {
        if (window.userData.spendablePoints < GACHA_COST) {
            showAlert('积分不足！需要 ' + GACHA_COST + ' 积分才能抽卡', 'warning');
            playAlertSound('click');
            return null;
        }
        
        // 扣除消耗积分
        window.userData.spendablePoints -= GACHA_COST;
        window.userData.totalGachaCount++;
        
        // 检查是否有幸运金币效果
        const hasLuckyBoost = window.userData.inventory.some(inv => 
            inv.itemId === 'item_lucky_coin' && inv.count > 0 && inv.activeForNextGacha
        );
        
        // 随机决定稀有度
        let roll = Math.random() * 100;
        let selectedRarity = 'N';
        
        if (hasLuckyBoost) {
            // 幸运金币：必出R及以上
            roll = Math.random() * 50; // 只在R/SR/SSR中抽
            if (roll < 5) selectedRarity = 'SSR';
            else if (roll < 20) selectedRarity = 'SR';
            else selectedRarity = 'R';
            
            // 消耗幸运金币
            const luckyItem = window.userData.inventory.find(inv => inv.itemId === 'item_lucky_coin' && inv.activeForNextGacha);
            if (luckyItem) {
                luckyItem.count--;
                luckyItem.activeForNextGacha = false;
                if (luckyItem.count <= 0) {
                    window.userData.inventory = window.userData.inventory.filter(inv => inv.itemId !== 'item_lucky_coin' || inv.count > 0);
                }
            }
        } else {
            // 正常概率
            if (roll < 5) selectedRarity = 'SSR';
            else if (roll < 20) selectedRarity = 'SR';
            else if (roll < 50) selectedRarity = 'R';
            else selectedRarity = 'N';
        }
        
        // 从对应稀有度的物品中随机选择
        const poolItems = gachaItems.filter(item => item.rarity === selectedRarity);
        const selectedItem = poolItems[Math.floor(Math.random() * poolItems.length)];
        
        // 添加到背包
        const addResult = addToInventory(selectedItem.id);
        
        // 记录抽卡历史
        window.userData.gachaHistory.unshift({
            itemId: selectedItem.id,
            time: new Date().toISOString()
        });
        if (window.userData.gachaHistory.length > 50) {
            window.userData.gachaHistory = window.userData.gachaHistory.slice(0, 50);
        }
        
        saveUserData(window.userData);
        updateStatsDisplay();
        
        // 返回物品和转换信息
        return { item: selectedItem, converted: addResult.converted, convertedPoints: addResult.points || 0 };
    }
    
    // 添加物品到背包（非道具类已有物品转化为积分）
    function addToInventory(itemId) {
        if (!window.userData.inventory) window.userData.inventory = [];
        
        const item = getItemById(itemId);
        const existing = window.userData.inventory.find(inv => inv.itemId === itemId);
        
        if (existing) {
            // 道具类可以叠加，其他类型转化为积分
            if (item && item.type === 'consumable') {
                existing.count++;
            } else {
                // 非道具类重复物品转化为5可用积分
                window.userData.spendablePoints += 5;
                return { converted: true, points: 5 };
            }
        } else {
            window.userData.inventory.push({
                itemId: itemId,
                count: 1,
                obtainedAt: new Date().toISOString()
            });
        }
        return { converted: false };
    }
    
    // 使用物品
    function useItem(itemId) {
        const invItem = window.userData.inventory.find(inv => inv.itemId === itemId && inv.count > 0);
        if (!invItem) {
            showAlert('物品不足！', 'warning');
            return false;
        }
        
        const item = getItemById(itemId);
        if (!item) return false;
        
        // 根据物品类型处理
        switch (item.type) {
            case 'avatarFrame':
                window.userData.equipped.avatarFrame = itemId;
                applyAvatarFrame(item);
                showAlert('已装备头像框：' + item.name, 'encourage');
                break;
                
            case 'chatBubble':
                window.userData.equipped.chatBubble = itemId;
                applyChatBubble(item);
                showAlert('已装备聊天气泡：' + item.name, 'encourage');
                break;
                
            case 'theme':
                window.userData.equipped.theme = itemId;
                applyTheme(item);
                showAlert('已应用主题：' + item.name, 'encourage');
                break;
                
            case 'title':
                window.userData.equipped.title = itemId;
                showAlert('已装备称号：' + item.name, 'encourage');
                break;
                
            case 'consumable':
                // 消耗品需要特殊处理
                if (item.points) {
                    // 积分袋
                    window.userData.points += item.points;
                    window.userData.spendablePoints += item.points;
                    invItem.count--;
                    showAlert('获得 ' + item.points + ' 积分！', 'encourage');
                } else if (item.id === 'item_double_points') {
                    // 双倍积分卡
                    window.userData.activeBuffs.doublePoints = Date.now() + item.duration;
                    invItem.count--;
                    showAlert('双倍积分效果已激活！持续24小时', 'encourage');
                } else if (item.id === 'item_checkin_card') {
                    // 补签卡 - 打开补签选择
                    showCheckinCardDialog();
                    return true; // 不在这里扣除，等选择日期后再扣
                } else if (item.id === 'item_lucky_coin') {
                    // 幸运金币 - 标记下次抽卡生效
                    invItem.activeForNextGacha = true;
                    showAlert('幸运金币已激活！下次抽卡必出R及以上', 'encourage');
                    // 不扣除数量，抽卡时扣除
                    saveUserData(window.userData);
                    return true;
                }
                
                if (invItem.count <= 0) {
                    window.userData.inventory = window.userData.inventory.filter(inv => inv.count > 0);
                }
                break;
        }
        
        saveUserData(window.userData);
        playAlertSound('achievement');
        updateStatsDisplay();
        renderInventory();
        return true;
    }
    
    // 卸下装备（恢复默认）
    function unequipItem(itemId) {
        const item = getItemById(itemId);
        if (!item) return false;
        
        switch (item.type) {
            case 'avatarFrame':
                window.userData.equipped.avatarFrame = null;
                // 恢复默认头像框
                const levelIcon = document.getElementById('user-level');
                if (levelIcon) {
                    levelIcon.style.cssText = 'font-size:20px;';
                }
                showAlert('已卸下头像框', 'encourage');
                break;
                
            case 'chatBubble':
                window.userData.equipped.chatBubble = null;
                // 移除自定义气泡样式
                const bubbleStyle = document.getElementById('custom-bubble-style');
                if (bubbleStyle) {
                    bubbleStyle.textContent = '';
                    console.log('[Bubble] 已移除聊天气泡样式');
                }
                showAlert('已卸下聊天气泡', 'encourage');
                break;
                
            case 'theme':
                window.userData.equipped.theme = null;
                // 恢复默认主题
                const defaultTheme = getItemById('theme_default');
                if (defaultTheme) {
                    applyTheme(defaultTheme);
                }
                showAlert('已恢复默认主题', 'encourage');
                break;
                
            case 'title':
                window.userData.equipped.title = null;
                showAlert('已卸下称号', 'encourage');
                break;
                
            default:
                return false;
        }
        
        saveUserData(window.userData);
        playAlertSound('click');
        renderInventory();
        return true;
    }
    
    // 暴露卸下函数到全局
    window.unequipItem = unequipItem;
    
    // 应用头像框样式（应用于等级图标）
    function applyAvatarFrame(item) {
        const levelIcon = document.getElementById('user-level');
        if (levelIcon && item && item.style) {
            levelIcon.style.cssText = 'font-size:20px;display:inline-block;' + item.style;
        }
    }
    
    // 应用聊天气泡样式（适配Gradio Chatbot组件）
    function applyChatBubble(item) {
        if (!item || !item.style) return;
        // 创建或更新样式
        let styleEl = document.getElementById('custom-bubble-style');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'custom-bubble-style';
            document.head.appendChild(styleEl);
        }
        // Gradio Chatbot的消息气泡选择器（覆盖多个版本，同时应用于Bot和User消息）
        styleEl.textContent = '\\n' +
            '/* Gradio 4.x Bot消息气泡 */\\n' +
            '#chatbot .bot .message-bubble-border,\\n' +
            '#chatbot .bot .bubble,\\n' +
            '#chatbot .message.bot,\\n' +
            '#chatbot [data-testid="bot"] > div {\\n' +
            '    ' + item.style + '\\n' +
            '}\\n' +
            '/* Gradio 4.x User消息气泡 */\\n' +
            '#chatbot .user .message-bubble-border,\\n' +
            '#chatbot .user .bubble,\\n' +
            '#chatbot .message.user,\\n' +
            '#chatbot [data-testid="user"] > div {\\n' +
            '    ' + item.style + '\\n' +
            '}\\n' +
            '/* Gradio 3.x 兼容 */\\n' +
            '.message.bot .bubble-wrap,\\n' +
            '.message.user .bubble-wrap,\\n' +
            '.chatbot .message.bot,\\n' +
            '.chatbot .message.user {\\n' +
            '    ' + item.style + '\\n' +
            '}\\n';
        
        console.log('[Bubble] 已应用聊天气泡样式：', item.name);
    }
    
    // 应用主题（覆盖整个页面背景）
    function applyTheme(item) {
        if (!item || !item.cssVars) return;
        const root = document.documentElement;
        const vars = item.cssVars;
        
        // 设置CSS变量
        root.style.setProperty('--primary-color', vars.primary);
        root.style.setProperty('--secondary-color', vars.secondary);
        root.style.setProperty('--text-color', vars.textColor || '#1e293b');
        root.style.setProperty('--card-bg', vars.cardBg || 'rgba(255,255,255,0.9)');
        
        // 更新头部渐变
        const header = document.querySelector('.chat-header');
        if (header) {
            header.style.background = 'linear-gradient(135deg, ' + vars.primary + ' 0%, ' + vars.secondary + ' 100%)';
        }
        
        // 更新整个页面背景（关键修改）
        const mainContainer = document.querySelector('.gradio-container > .main');
        const gradioContainer = document.querySelector('.gradio-container');
        
        // 组合渐变和图案背景
        const fullBg = vars.bgPattern 
            ? vars.bgPattern + ', ' + vars.bgGradient 
            : vars.bgGradient;
        
        if (mainContainer) {
            mainContainer.style.background = fullBg;
            mainContainer.style.backgroundAttachment = 'fixed';
            mainContainer.style.minHeight = '100vh';
        }
        
        if (gradioContainer) {
            gradioContainer.style.background = fullBg;
            gradioContainer.style.backgroundAttachment = 'fixed';
        }
        
        // 同时设置body背景作为后备
        document.body.style.background = fullBg;
        document.body.style.backgroundAttachment = 'fixed';
        
        // 创建或更新全局主题样式
        let themeStyle = document.getElementById('dynamic-theme-style');
        if (!themeStyle) {
            themeStyle = document.createElement('style');
            themeStyle.id = 'dynamic-theme-style';
            document.head.appendChild(themeStyle);
        }
        
        // 深色主题特殊处理
        const isDark = vars.isDark || false;
        
        themeStyle.textContent = '\\n' +
            '/* 动态主题样式 */\\n' +
            '.gradio-container, .gradio-container > .main, body { \\n' +
            '    background: ' + fullBg + ' !important;\\n' +
            '    background-attachment: fixed !important;\\n' +
            '}\\n' +
            '.study-mode-panel, .status-card, .todo-item-pending {\\n' +
            '    background: ' + vars.cardBg + ' !important;\\n' +
            '    backdrop-filter: blur(10px);\\n' +
            '}\\n' +
            (isDark ? '\\n' +
            '.chat-header h1, .chat-header p { color: #fff !important; }\\n' +
            '.study-mode-header h3 { color: ' + vars.primary + ' !important; }\\n' +
            '.status-card p:first-child { color: #94a3b8 !important; }\\n' +
            '.status-card p:last-child { color: ' + vars.textColor + ' !important; }\\n' +
            '#level-display, #points-display { color: ' + vars.textColor + ' !important; }\\n' +
            '.accordion-header { background: ' + vars.cardBg + ' !important; color: ' + vars.textColor + ' !important; }\\n' +
            '' : '') +
            '/* 按钮主题色 */\\n' +
            '.camera-btn, #send-btn, .gacha-btn {\\n' +
            '    background: linear-gradient(135deg, ' + vars.primary + ' 0%, ' + vars.secondary + ' 100%) !important;\\n' +
            '}\\n';
        
        console.log('[Theme] 已应用主题：' + item.name + (isDark ? ' (深色模式)' : ''));
    }
    
    // 补签卡对话框
    function showCheckinCardDialog() {
        const modal = document.createElement('div');
        modal.id = 'checkin-card-modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';
        
        const today = new Date();
        const dates = [];
        for (let i = 1; i <= 7; i++) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            const dateStr = d.toISOString().split('T')[0];
            if (!window.userData.checkInHistory.includes(dateStr)) {
                dates.push({ date: dateStr, label: (d.getMonth() + 1) + '/' + d.getDate() });
            }
        }
        
        let content = '<div style="background:white;border-radius:16px;padding:20px;max-width:320px;width:90%;">';
        content += '<h3 style="margin:0 0 15px 0;text-align:center;color:#374151;">📅 选择补签日期</h3>';
        
        if (dates.length === 0) {
            content += '<p style="text-align:center;color:#6b7280;">最近7天都已签到，无需补签！</p>';
        } else {
            content += '<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;">';
            dates.forEach(d => {
                content += '<button class="checkin-date-btn" data-date="' + d.date + '" style="padding:10px 15px;border:2px solid #3b82f6;background:white;border-radius:8px;cursor:pointer;font-weight:600;color:#3b82f6;">' + d.label + '</button>';
            });
            content += '</div>';
        }
        
        content += '<button id="close-checkin-modal" style="width:100%;margin-top:15px;padding:10px;background:#e5e7eb;border:none;border-radius:8px;cursor:pointer;">取消</button>';
        content += '</div>';
        
        modal.innerHTML = content;
        document.body.appendChild(modal);
        
        // 绑定事件
        modal.querySelectorAll('.checkin-date-btn').forEach(btn => {
            btn.onclick = function() {
                const date = this.dataset.date;
                // 使用补签卡
                const invItem = window.userData.inventory.find(inv => inv.itemId === 'item_checkin_card' && inv.count > 0);
                if (invItem) {
                    invItem.count--;
                    if (invItem.count <= 0) {
                        window.userData.inventory = window.userData.inventory.filter(inv => inv.count > 0);
                    }
                    
                    // 补签
                    window.userData.checkInHistory.push(date);
                    saveUserData(window.userData);
                    generateCheckInCalendar();
                    showAlert('补签成功！' + date, 'encourage');
                    playAlertSound('achievement');
                }
                document.body.removeChild(modal);
            };
        });
        
        document.getElementById('close-checkin-modal').onclick = () => {
            document.body.removeChild(modal);
        };
    }
    
    // 初始化时应用已装备的外观
    function applyEquippedItems() {
        if (!window.userData.equipped) return;
        
        if (window.userData.equipped.avatarFrame) {
            const item = getItemById(window.userData.equipped.avatarFrame);
            if (item) applyAvatarFrame(item);
        }
        
        if (window.userData.equipped.chatBubble) {
            const item = getItemById(window.userData.equipped.chatBubble);
            if (item) applyChatBubble(item);
        }
        
        if (window.userData.equipped.theme) {
            const item = getItemById(window.userData.equipped.theme);
            if (item) applyTheme(item);
        }
    }
    
    // 暴露抽卡相关函数到全局
    window.doGacha = doGacha;
    window.useItem = useItem;
    window.getItemById = getItemById;
    
    // ========== 背包渲染函数 ==========
    function renderInventory() {
        const container = document.getElementById('inventory-container');
        if (!container) return;
        
        const inventory = window.userData.inventory || [];
        
        if (inventory.length === 0) {
            container.innerHTML = '<div style="text-align:center;padding:30px;color:#9ca3af;"><p style="font-size:24px;margin:0 0 10px 0;">📦</p><p style="margin:0;">背包空空如也，快去抽卡吧！</p></div>';
            return;
        }
        
        // 按类型分组
        const groups = {
            avatarFrame: { name: '头像框', items: [] },
            chatBubble: { name: '聊天气泡', items: [] },
            theme: { name: '主题皮肤', items: [] },
            title: { name: '称号', items: [] },
            quoteCard: { name: '名言卡片', items: [] },
            consumable: { name: '道具', items: [] }
        };
        
        inventory.forEach(inv => {
            const item = getItemById(inv.itemId);
            if (item && groups[item.type]) {
                groups[item.type].items.push({ ...item, count: inv.count });
            }
        });
        
        let html = '';
        
        Object.entries(groups).forEach(([type, group]) => {
            if (group.items.length === 0) return;
            
            html += '<div style="margin-bottom:15px;">';
            html += '<h4 style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">' + group.name + '</h4>';
            html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
            
            group.items.forEach(item => {
                const rarity = rarityConfig[item.rarity];
                const isEquipped = (
                    (type === 'avatarFrame' && window.userData.equipped.avatarFrame === item.id) ||
                    (type === 'chatBubble' && window.userData.equipped.chatBubble === item.id) ||
                    (type === 'theme' && window.userData.equipped.theme === item.id) ||
                    (type === 'title' && window.userData.equipped.title === item.id)
                );
                
                html += '<div class="inventory-item" data-id="' + item.id + '" style="position:relative;width:70px;text-align:center;padding:10px 5px;background:' + rarity.bgColor + ';border:2px solid ' + (isEquipped ? '#10b981' : rarity.color) + ';border-radius:10px;cursor:pointer;transition:all 0.2s ease;">';
                html += '<div style="font-size:24px;margin-bottom:4px;">' + item.icon + '</div>';
                html += '<div style="font-size:10px;color:' + rarity.color + ';font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + item.name + '</div>';
                
                if (item.count > 1) {
                    html += '<div style="position:absolute;top:3px;right:3px;background:#ef4444;color:white;font-size:10px;padding:1px 5px;border-radius:10px;">x' + item.count + '</div>';
                }
                
                if (isEquipped) {
                    html += '<div style="position:absolute;top:3px;left:3px;background:#10b981;color:white;font-size:8px;padding:1px 4px;border-radius:4px;">使用中</div>';
                }
                
                html += '</div>';
            });
            
            html += '</div></div>';
        });
        
        container.innerHTML = html;
        
        // 绑定点击事件
        container.querySelectorAll('.inventory-item').forEach(el => {
            el.onclick = function() {
                const itemId = this.dataset.id;
                showItemDetail(itemId);
            };
        });
    }
    
    // 显示物品详情弹窗
    function showItemDetail(itemId) {
        const item = getItemById(itemId);
        if (!item) return;
        
        const rarity = rarityConfig[item.rarity];
        const invItem = window.userData.inventory.find(inv => inv.itemId === itemId);
        const count = invItem ? invItem.count : 0;
        
        // 名言卡片特殊展示
        if (item.type === 'quoteCard') {
            showQuoteCardDetail(item, rarity, count);
            return;
        }
        
        const isEquippable = ['avatarFrame', 'chatBubble', 'theme', 'title'].includes(item.type);
        const isConsumable = item.type === 'consumable';
        const isEquipped = (
            (item.type === 'avatarFrame' && window.userData.equipped.avatarFrame === item.id) ||
            (item.type === 'chatBubble' && window.userData.equipped.chatBubble === item.id) ||
            (item.type === 'theme' && window.userData.equipped.theme === item.id) ||
            (item.type === 'title' && window.userData.equipped.title === item.id)
        );
        
        const modal = document.createElement('div');
        modal.id = 'item-detail-modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';
        
        let content = '<div style="background:white;border-radius:16px;padding:20px;max-width:280px;width:90%;text-align:center;">';
        content += '<div style="font-size:48px;margin-bottom:10px;">' + item.icon + '</div>';
        content += '<h3 style="margin:0 0 5px 0;color:#374151;">' + item.name + '</h3>';
        content += '<div style="display:inline-block;padding:3px 10px;background:' + rarity.bgColor + ';color:' + rarity.color + ';border-radius:10px;font-size:12px;font-weight:600;margin-bottom:10px;">' + rarity.name + '</div>';
        content += '<p style="margin:0 0 15px 0;font-size:13px;color:#6b7280;">' + item.desc + '</p>';
        
        if (count > 1) {
            content += '<p style="margin:0 0 15px 0;font-size:12px;color:#9ca3af;">拥有数量：' + count + '</p>';
        }
        
        if (isEquipped) {
            content += '<div style="display:flex;gap:8px;margin-bottom:8px;">';
            content += '<button style="flex:1;padding:10px;background:#10b981;color:white;border:none;border-radius:8px;font-weight:600;cursor:default;">✓ 使用中</button>';
            content += '<button id="unequip-item-btn" style="flex:1;padding:10px;background:#ef4444;color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;">卸下</button>';
            content += '</div>';
        } else if (isEquippable) {
            content += '<button id="use-item-btn" style="width:100%;padding:10px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;margin-bottom:8px;">装备</button>';
        } else if (isConsumable && count > 0) {
            content += '<button id="use-item-btn" style="width:100%;padding:10px;background:linear-gradient(135deg,#10b981,#059669);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;margin-bottom:8px;">使用</button>';
        }
        
        content += '<button id="close-item-modal" style="width:100%;padding:10px;background:#e5e7eb;border:none;border-radius:8px;cursor:pointer;">关闭</button>';
        content += '</div>';
        
        modal.innerHTML = content;
        document.body.appendChild(modal);
        
        const useBtn = document.getElementById('use-item-btn');
        if (useBtn) {
            useBtn.onclick = () => {
                useItem(itemId);
                document.body.removeChild(modal);
            };
        }
        
        // 卸下按钮事件
        const unequipBtn = document.getElementById('unequip-item-btn');
        if (unequipBtn) {
            unequipBtn.onclick = () => {
                unequipItem(itemId);
                document.body.removeChild(modal);
            };
        }
        
        document.getElementById('close-item-modal').onclick = () => {
            document.body.removeChild(modal);
        };
        
        modal.onclick = (e) => {
            if (e.target === modal) document.body.removeChild(modal);
        };
    }
    
    // 名言卡片特殊展示
    function showQuoteCardDetail(item, rarity, count) {
        const isSSR = item.rarity === 'SSR';
        const glowColor = item.glowColor || rarity.color;
        
        const modal = document.createElement('div');
        modal.id = 'quote-card-modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);display:flex;align-items:center;justify-content:center;z-index:10000;animation:fadeIn 0.3s ease;';
        
        // SSR专属：添加背景粒子容器
        let particlesHtml = '';
        if (isSSR && item.particles) {
            particlesHtml = '<div id="ssr-particles" style="position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;overflow:hidden;"></div>';
        }
        
        // 卡片内容 - 大尺寸展示
        let content = '<div style="position:relative;width:90%;max-width:400px;animation:quoteCardIn 0.6s ease;">';
        
        // SSR专属：外层光晕
        if (isSSR) {
            content += '<div style="position:absolute;top:-10px;left:-10px;right:-10px;bottom:-10px;background:' + glowColor + ';border-radius:30px;filter:blur(20px);opacity:0.6;animation:ssrPulse 2s ease-in-out infinite;"></div>';
        }
        
        // 主卡片
        let cardStyle = 'background:' + item.bgStyle + ';border-radius:24px;padding:40px 30px;text-align:center;position:relative;overflow:hidden;';
        if (isSSR) {
            cardStyle += 'box-shadow:0 0 0 3px ' + rarity.color + ',0 0 30px ' + glowColor + ',0 25px 80px rgba(0,0,0,0.6);';
        } else {
            cardStyle += 'box-shadow:0 20px 60px rgba(0,0,0,0.5),0 0 0 3px ' + rarity.color + ';';
        }
        content += '<div style="' + cardStyle + '">';
        
        // SSR专属：闪烁边框
        if (isSSR) {
            content += '<div style="position:absolute;top:0;left:0;right:0;bottom:0;border-radius:24px;border:2px solid transparent;background:linear-gradient(90deg,transparent,' + rarity.color + ',transparent) border-box;-webkit-mask:linear-gradient(#fff 0 0) padding-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;mask-composite:exclude;animation:ssrBorderShine 3s linear infinite;pointer-events:none;"></div>';
        }
        
        // 装饰背景元素
        content += '<div style="position:absolute;top:-20px;right:-20px;font-size:120px;opacity:' + (isSSR ? '0.2' : '0.15') + ';transform:rotate(15deg);' + (isSSR ? 'animation:ssrFloat 4s ease-in-out infinite;' : '') + '">' + item.authorImg + '</div>';
        content += '<div style="position:absolute;bottom:-30px;left:-30px;font-size:100px;opacity:' + (isSSR ? '0.15' : '0.1') + ';transform:rotate(-15deg);' + (isSSR ? 'animation:ssrFloat 4s ease-in-out infinite reverse;' : '') + '">' + item.authorImg + '</div>';
        
        // SSR专属：额外装饰星星
        if (isSSR) {
            content += '<div style="position:absolute;top:20%;left:10%;font-size:16px;opacity:0.6;animation:ssrTwinkle 1.5s ease-in-out infinite;">✨</div>';
            content += '<div style="position:absolute;top:30%;right:15%;font-size:14px;opacity:0.5;animation:ssrTwinkle 2s ease-in-out infinite 0.5s;">⭐</div>';
            content += '<div style="position:absolute;bottom:25%;left:15%;font-size:12px;opacity:0.4;animation:ssrTwinkle 1.8s ease-in-out infinite 0.3s;">✦</div>';
            content += '<div style="position:absolute;bottom:35%;right:10%;font-size:18px;opacity:0.5;animation:ssrTwinkle 2.2s ease-in-out infinite 0.7s;">💫</div>';
        }
        
        // 稀有度标签
        let badgeStyle = 'position:absolute;top:15px;right:15px;background:' + rarity.color + ';color:white;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;';
        if (isSSR) {
            badgeStyle += 'box-shadow:0 0 15px ' + glowColor + ';animation:ssrBadgePulse 1.5s ease-in-out infinite;';
        }
        content += '<div style="' + badgeStyle + '">' + (isSSR ? '🌟 ' : '') + rarity.name + '</div>';
        
        // 图标
        let iconStyle = 'font-size:60px;margin-bottom:20px;position:relative;z-index:1;';
        if (isSSR) {
            iconStyle += 'animation:ssrIconFloat 3s ease-in-out infinite;filter:drop-shadow(0 0 10px ' + glowColor + ');';
        } else {
            iconStyle += 'animation:float 3s ease-in-out infinite;';
        }
        content += '<div style="' + iconStyle + '">' + item.authorImg + '</div>';
        
        // 名言内容
        content += '<div style="position:relative;z-index:1;margin-bottom:25px;">';
        let quoteMarkStyle = 'font-size:32px;color:' + item.textColor + ';opacity:' + (isSSR ? '0.5' : '0.3') + ';position:absolute;';
        if (isSSR) {
            quoteMarkStyle += 'text-shadow:0 0 10px ' + glowColor + ';';
        }
        content += '<div style="' + quoteMarkStyle + 'top:-18px;left:5px;">"</div>';
        let textStyle = 'margin:0;font-size:18px;line-height:1.8;color:' + item.textColor + ';font-weight:500;padding:0 25px;';
        if (isSSR) {
            textStyle += 'text-shadow:0 1px 2px rgba(0,0,0,0.1);';
        }
        content += '<p style="' + textStyle + '">' + item.quote + '</p>';
        content += '<div style="' + quoteMarkStyle + 'bottom:-18px;right:5px;">"</div>';
        content += '</div>';
        
        // 作者
        content += '<div style="position:relative;z-index:1;">';
        let dividerStyle = 'width:80px;height:2px;margin:0 auto 15px;';
        if (isSSR) {
            dividerStyle += 'background:linear-gradient(90deg,transparent,' + item.textColor + ',transparent);';
        } else {
            dividerStyle += 'background:' + item.textColor + ';opacity:0.3;';
        }
        content += '<div style="' + dividerStyle + '"></div>';
        content += '<p style="margin:0;font-size:16px;color:' + item.textColor + ';font-weight:600;opacity:0.9;">—— ' + item.author + '</p>';
        content += '</div>';
        
        content += '</div>'; // 结束主卡片
        
        // 底部信息
        content += '<div style="text-align:center;margin-top:20px;position:relative;z-index:1;">';
        content += '<p style="margin:0 0 10px 0;color:#d1d5db;font-size:13px;">' + item.name + (count > 1 ? ' × ' + count : '') + '</p>';
        let btnStyle = 'padding:12px 40px;background:linear-gradient(135deg,' + rarity.color + ',' + rarity.color + 'cc);color:white;border:none;border-radius:25px;font-size:14px;font-weight:600;cursor:pointer;';
        if (isSSR) {
            btnStyle += 'box-shadow:0 4px 20px ' + glowColor + ',0 0 0 2px rgba(255,255,255,0.2);';
        } else {
            btnStyle += 'box-shadow:0 4px 15px rgba(0,0,0,0.3);';
        }
        content += '<button id="close-quote-modal" style="' + btnStyle + '">收起</button>';
        content += '</div>';
        
        content += '</div>'; // 结束容器
        
        modal.innerHTML = particlesHtml + content;
        document.body.appendChild(modal);
        
        // 添加动画样式
        const styleEl = document.createElement('style');
        styleEl.id = 'quote-card-style';
        let cssText = '@keyframes quoteCardIn { from { transform: scale(0.7) rotateY(90deg); opacity: 0; } to { transform: scale(1) rotateY(0deg); opacity: 1; } } ';
        cssText += '@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } } ';
        cssText += '@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } } ';
        
        // SSR专属动画
        if (isSSR) {
            cssText += '@keyframes ssrPulse { 0%, 100% { opacity: 0.4; transform: scale(1); } 50% { opacity: 0.7; transform: scale(1.02); } } ';
            cssText += '@keyframes ssrIconFloat { 0%, 100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-15px) scale(1.05); } } ';
            cssText += '@keyframes ssrTwinkle { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } } ';
            cssText += '@keyframes ssrBadgePulse { 0%, 100% { box-shadow: 0 0 10px ' + glowColor + '; } 50% { box-shadow: 0 0 25px ' + glowColor + '; } } ';
            cssText += '@keyframes ssrFloat { 0%, 100% { transform: translateY(0) rotate(15deg); } 50% { transform: translateY(-20px) rotate(20deg); } } ';
            cssText += '@keyframes ssrBorderShine { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } } ';
            cssText += '@keyframes ssrParticle { 0% { transform: translateY(0) rotate(0deg); opacity: 1; } 100% { transform: translateY(-100vh) rotate(360deg); opacity: 0; } } ';
        }
        
        styleEl.textContent = cssText;
        document.head.appendChild(styleEl);
        
        // SSR专属：生成粒子效果
        if (isSSR && item.particles) {
            const particleContainer = document.getElementById('ssr-particles');
            if (particleContainer) {
                const particleSymbols = ['✨', '⭐', '💫', '✦', '·'];
                for (let i = 0; i < 20; i++) {
                    const particle = document.createElement('div');
                    particle.style.cssText = 'position:absolute;font-size:' + (8 + Math.random() * 12) + 'px;left:' + Math.random() * 100 + '%;bottom:-20px;animation:ssrParticle ' + (3 + Math.random() * 4) + 's linear infinite;animation-delay:' + (Math.random() * 3) + 's;opacity:0.7;';
                    particle.textContent = particleSymbols[Math.floor(Math.random() * particleSymbols.length)];
                    particleContainer.appendChild(particle);
                }
            }
        }
        
        document.getElementById('close-quote-modal').onclick = () => {
            document.body.removeChild(modal);
            const style = document.getElementById('quote-card-style');
            if (style) document.head.removeChild(style);
        };
        
        modal.onclick = (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
                const style = document.getElementById('quote-card-style');
                if (style) document.head.removeChild(style);
            }
        };
    }
    
    // 显示抽卡动画
    function showGachaAnimation(result) {
        const item = result.item;
        const converted = result.converted;
        const convertedPoints = result.convertedPoints;
        const rarity = rarityConfig[item.rarity];
        
        const modal = document.createElement('div');
        modal.id = 'gacha-result-modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:10000;';
        
        let bgGlow = '';
        if (item.rarity === 'SSR') {
            bgGlow = 'box-shadow:0 0 100px 50px rgba(245,158,11,0.5);';
        } else if (item.rarity === 'SR') {
            bgGlow = 'box-shadow:0 0 80px 30px rgba(139,92,246,0.4);';
        }
        
        let content = '<div style="text-align:center;animation:gacha-pop 0.5s ease-out;">';
        content += '<div style="width:150px;height:150px;background:' + rarity.bgColor + ';border:4px solid ' + rarity.color + ';border-radius:20px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px auto;' + bgGlow + '">';
        content += '<span style="font-size:64px;">' + item.icon + '</span>';
        content += '</div>';
        content += '<h2 style="margin:0 0 5px 0;color:white;font-size:24px;">' + item.name + '</h2>';
        content += '<div style="display:inline-block;padding:5px 15px;background:' + rarity.bgColor + ';color:' + rarity.color + ';border-radius:15px;font-weight:700;margin-bottom:10px;">' + rarity.name + '</div>';
        content += '<p style="color:#d1d5db;font-size:14px;margin:0 0 15px 0;">' + item.desc + '</p>';
        
        // 显示转换提示
        if (converted) {
            content += '<div style="background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;margin-bottom:15px;display:inline-block;">🔄 已拥有！转化为 +' + convertedPoints + ' 积分</div>';
        }
        
        content += '<button id="close-gacha-modal" style="padding:12px 40px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;">确定</button>';
        content += '</div>';
        
        modal.innerHTML = content;
        document.body.appendChild(modal);
        
        // 播放音效
        if (item.rarity === 'SSR') {
            playAlertSound('levelup');
        } else if (item.rarity === 'SR') {
            playAlertSound('achievement');
        } else {
            playAlertSound('click');
        }
        
        document.getElementById('close-gacha-modal').onclick = () => {
            document.body.removeChild(modal);
            renderInventory();
        };
        
        modal.onclick = (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
                renderInventory();
            }
        };
    }
    
    // 执行抽卡并显示动画
    function performGacha() {
        const result = doGacha();
        if (result) {
            showGachaAnimation(result);
            updateGachaDisplay();
        }
    }
    
    // 更新抽卡面板显示
    function updateGachaDisplay() {
        const pointsEl = document.getElementById('gacha-points-display');
        if (pointsEl) {
            pointsEl.textContent = (window.userData.spendablePoints || 0) + ' 积分';
        }
    }
    
    // 暴露更多函数到全局
    window.performGacha = performGacha;
    window.renderInventory = renderInventory;
    window.showItemDetail = showItemDetail;
    window.updateGachaDisplay = updateGachaDisplay;
    
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
    
    // 添加积分（同时增加升级积分和消耗积分）
    function addPoints(userData, amount, reason) {
        // 检查双倍积分buff
        let finalAmount = amount;
        if (userData.activeBuffs && userData.activeBuffs.doublePoints) {
            if (Date.now() < userData.activeBuffs.doublePoints) {
                finalAmount = amount * 2;
                console.log('双倍积分生效！' + amount + ' -> ' + finalAmount);
            } else {
                // buff已过期，清除
                userData.activeBuffs.doublePoints = null;
            }
        }
        
        // 升级积分（只增不减）
        userData.points += finalAmount;
        // 消耗积分（可用于抽卡）
        if (!userData.spendablePoints) userData.spendablePoints = 0;
        userData.spendablePoints += finalAmount;
        
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
                currentConsecutiveFocus: 0, // 当前连续专注时长
                tasksCompleted: 0  // 今日完成任务数
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
    // [调试用] 强制设置初始积分为1000，删除下面这行即可恢复正常
    window.userData.spendablePoints = 1000; // DEBUG_LINE: 删除此行恢复正常积分
    
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
        
        // 更新抽卡积分显示
        updateGachaDisplay();
    }
    
    // 更新成就面板
    function updateAchievementsPanel() {
        const container = document.getElementById('achievements-container');
        if (!container) return;
        
        // 【加固】确保用户数据已加载
        if (!window.userData || !window.userData.achievements) {
            window.userData = loadUserData() || window.userData;
        }
        
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
        
        // 【加固】确保用户数据已加载，防止渲染空白
        if (!window.userData || !window.userData.checkInHistory) {
            window.userData = loadUserData() || window.userData;
        }
        
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
    
    // 【优化】风格化分神提醒词 (与后端同步)
    const STYLE_DISTRACTION_REMINDERS = {
        "默认": "专注一下，你可以的！",
        "柔情猫娘": "主人，不可以分心喵~ 快回过神来！",
        "成熟妈妈系御姐": "亲爱的，稍微集中一下注意力，好吗？",
        "磁性霸道男总裁": "我不允许你在这种时候分心，听到了吗？"
    };
    
    // 【新增】风格化情绪鼓励提醒词 (与后端同步)
    const STYLE_ENCOURAGE_REMINDERS = {
        "默认": "看起来你有点累了，记得适当休息哦，你已经很棒了！",
        "柔情猫娘": "主人喵~ 是不是累坏了？喵喵给你一个隔空的抱抱喵，打起精神来喵~",
        "成熟妈妈系御姐": "我的好孩子，累了就歇会儿，不管遇到什么困难，我都会陪在你身边的。",
        "磁性霸道男总裁": "振作起来，我不允许我的陪伴者露出这种丧气的表情。休息五分钟，然后继续。"
    };
    
    // 多样化鼓励语句库 - 分神提醒
    const distractedMessages = [
        "嘿，注意力回来啦~专注一下，你可以的！",
        "学了么发现你走神了哦，深呼吸，继续加油！",
        "学习需要专注力，让我们重新集中注意力吧！",
        "休息一下眼睛，然后继续专注学习哦~",
        "走神了？没关系，现在开始重新专注！",
        "专注是成功的关键，让我们一起努力！",
        "学了么提醒你：回到学习状态啦~",
        "发现你有点分心，要不要休息一下再继续？",
        "注意力是学习的第一步，加油！",
        "集中精神，你离目标又近了一步！"
    ];
    
    // 多样化鼓励语句库 - 消极情绪鼓励
    const encourageMessages = [
        "看起来你有点累了，记得适当休息哦，你已经很棒了！",
        "学习路上难免有低谷，但每一步都算数，加油！",
        "学了么看到你在努力，无论结果如何，你都很了不起！",
        "感到沮丧是正常的，休息一下，我们再出发！",
        "每个人都会有疲惫的时候，给自己一个拥抱吧~",
        "困难只是暂时的，你的努力终将开花结果！",
        "累了就休息，明天又是元气满满的一天！",
        "学了么相信你，你比想象中更强大！",
        "坚持不一定成功，但放弃一定不会，继续加油！",
        "每一次挫折都是成长的机会，你在变得更好！",
        "学习是马拉松，不是短跑，慢慢来~",
        "感到压力？深呼吸，你已经做得很好了！",
        "今天的辛苦是明天的收获，继续努力！",
        "学了么一直在这里陪着你，你不是一个人在战斗！",
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
            } else if (type === 'warning') {
                // 警告音效 - 低沉的下降音调（积分不足等）
                oscillator.frequency.setValueAtTime(440, audioContext.currentTime); // A4
                oscillator.frequency.setValueAtTime(330, audioContext.currentTime + 0.15); // E4
                oscillator.type = 'square';
                gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.4);
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
        // warning类型不受冷却时间限制，其他类型30秒冷却
        if (type !== 'warning' && now - window.lastAlertTime < window.alertCooldown) {
            return; // 冷却时间内不重复提醒
        }
        if (type !== 'warning') {
            window.lastAlertTime = now;
        }
        
        // 播放提示音
        playAlertSound(type);
        
        const alertBox = document.getElementById('alert-box');
        const alertText = document.getElementById('alert-text');
        
        if (alertBox && alertText) {
            alertText.textContent = message;
            
            // 获取语音开关状态和触发器组件
            const voiceToggle = document.querySelector('#voice-toggle-checkbox input');
            const trigger = document.querySelector('#alert-trigger textarea');
            
            // 根据类型设置样式并触发语音
            if (type === 'distracted') {
                alertBox.style.background = 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)';
                
                if (voiceToggle && voiceToggle.checked && trigger) {
                    const triggerValue = 'distracted_' + Date.now();
                    console.log("[DEBUG-JS] 触发分神语音:", triggerValue);
                    trigger.value = triggerValue;
                    trigger.dispatchEvent(new Event('input', { bubbles: true }));
                }
            } else if (type === 'encourage') {
                alertBox.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                
                if (voiceToggle && voiceToggle.checked && trigger) {
                    const triggerValue = 'encourage_' + Date.now();
                    console.log("[DEBUG-JS] 触发鼓励语音:", triggerValue);
                    trigger.value = triggerValue;
                    trigger.dispatchEvent(new Event('input', { bubbles: true }));
                }
            } else if (type === 'warning') {
                // 警告类型（积分不足等）- 红色样式
                alertBox.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
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
        const historySize = 12; // 【优化】增加窗口大小以提高稳定性
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
                    minConfidence: 0.6 // 【优化】提高置信度阈值
                }))
                .withFaceLandmarks()
                .withFaceExpressions();
            } else {
                // 使用优化参数的TinyFaceDetector + 68点特征点
                detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions({
                    inputSize: 320, // 【优化】减小尺寸以降低卡顿 (原416)
                    scoreThreshold: 0.6 // 【优化】提高置信度阈值 (原0.5)
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
                
                // 检查是否需要显示鼓励消息（消极情绪持续约7秒，即14次检测 * 500ms）
                if (window.negativeEmotionCount >= 14) {
                    // 获取当前风格
                    let currentStyle = "默认";
                    const selectedStyleEl = document.querySelector('#style-radio .selected span') || 
                                          document.querySelector('#style-radio input:checked');
                    if (selectedStyleEl) {
                        currentStyle = selectedStyleEl.textContent || selectedStyleEl.value || "默认";
                    }
                    
                    const styleMessage = STYLE_ENCOURAGE_REMINDERS[currentStyle] || getRandomMessage(encourageMessages);
                    console.log(`[DEBUG-JS] 触发情绪鼓励 | 风格: ${currentStyle} | 消息: ${styleMessage}`);
                    
                    showAlert(styleMessage, 'encourage');
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
            
            // 检查是否需要显示分神提醒（分神持续约7秒，即14次检测 * 500ms）
            if (window.distractedCount >= 14) {
                // 获取当前风格
                let currentStyle = "默认";
                const selectedStyleEl = document.querySelector('#style-radio .selected span') || 
                                      document.querySelector('#style-radio input:checked');
                if (selectedStyleEl) {
                    currentStyle = selectedStyleEl.textContent || selectedStyleEl.value || "默认";
                }
                
                const styleMessage = STYLE_DISTRACTION_REMINDERS[currentStyle] || getRandomMessage(distractedMessages);
                console.log(`[DEBUG-JS] 触发分神提醒 | 风格: ${currentStyle} | 消息: ${styleMessage}`);
                
                showAlert(styleMessage, 'distracted');
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
            
            // 【优化】降低检测频率到500ms以减轻主线程压力
            window.detectionInterval = setInterval(detectFace, 500);
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
        "你的积极态度让学了么很感动，一起加油吧！"
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
    
    // 绑定Accordion展开事件（用于延迟渲染的面板）
    function bindAccordionEvents() {
        // 监听个人成就与签到面板的展开
        const medalAccordion = document.getElementById('medal-accordion');
        if (medalAccordion) {
            medalAccordion.addEventListener('click', () => {
                // 延迟一点执行，等待Accordion动画完成
                setTimeout(() => {
                    const calendarEl = document.getElementById('checkin-calendar');
                    const achievementsEl = document.getElementById('achievements-container');
                    
                    if (calendarEl && (!calendarEl.innerHTML || calendarEl.innerHTML.trim() === '')) {
                        console.log('Rendering checkin calendar on accordion open...');
                        generateCheckInCalendar();
                    }
                    
                    if (achievementsEl && (!achievementsEl.innerHTML || achievementsEl.innerHTML.trim() === '')) {
                        console.log('Rendering achievements on accordion open...');
                        updateAchievementsPanel();
                    }
                }, 100);
            });
            console.log('Accordion events bound');
        }
    }
    
    // 延迟绑定，确保DOM已加载
    setTimeout(bindButtons, 1000);
    setTimeout(bindRestButtons, 1200);
    setTimeout(bindReportButtons, 1400);
    setTimeout(bindTodoEvents, 1500);
    setTimeout(bindAccordionEvents, 1300);
    setTimeout(bindGachaEvents, 1600);
    
    // 绑定抽卡相关事件
    function bindGachaEvents() {
        // 监听抽卡面板展开
        const gachaAccordion = document.getElementById('gacha-accordion');
        if (gachaAccordion) {
            gachaAccordion.addEventListener('click', () => {
                setTimeout(() => {
                    // 在Accordion展开后绑定按钮事件
                    const gachaBtn = document.getElementById('gacha-btn');
                    if (gachaBtn && !gachaBtn.bindDone) {
                        gachaBtn.onclick = performGacha;
                        gachaBtn.bindDone = true;
                        console.log('Gacha button bound');
                    }
                    updateGachaDisplay();
                    updateGachaHistory();
                }, 100);
            });
        }
        
        // 监听背包面板展开
        const inventoryAccordion = document.getElementById('inventory-accordion');
        if (inventoryAccordion) {
            inventoryAccordion.addEventListener('click', () => {
                setTimeout(() => {
                    renderInventory();
                }, 100);
            });
        }
        
        console.log('Gacha accordion events bound');
    }
    
    // 更新抽卡历史显示
    function updateGachaHistory() {
        const container = document.getElementById('gacha-history');
        if (!container) return;
        
        const history = window.userData.gachaHistory || [];
        if (history.length === 0) {
            container.innerHTML = '<span style="color:#9ca3af;font-size:11px;">暂无记录</span>';
            return;
        }
        
        let html = '';
        history.slice(0, 10).forEach(record => {
            const item = getItemById(record.itemId);
            if (item) {
                const rarity = rarityConfig[item.rarity];
                html += '<span style="display:inline-flex;align-items:center;gap:2px;padding:3px 8px;background:' + rarity.bgColor + ';border:1px solid ' + rarity.color + ';border-radius:12px;font-size:11px;" title="' + item.name + '">' + item.icon + '</span>';
            }
        });
        
        container.innerHTML = html;
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
            // 【修复】确保包含今日时长在内的最大值计算，防止除以极小值导致高度溢出
            const maxMinutes = Math.max(...weekData.map(d => d.studyMinutes), todayRecord.studyMinutes || 0, 1);
            let chartHtml = '';
            weekData.forEach(d => {
                // 【修复】高度计算增加 Math.min 封顶，防止柱条溢出遮挡文字
                const height = Math.min(Math.max((d.studyMinutes / maxMinutes) * 60, 2), 60);
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
    
    // 显示周报弹窗（增强版）
    function showWeeklyReport() {
        const modal = document.getElementById('weekly-report-modal');
        const content = document.getElementById('report-content');
        
        if (!modal || !content) return;
        
        modal.style.display = 'flex';
        
        const report = generateWeeklyReport();
        const taskStats = getTodayTaskStats();
        const hours = Math.floor(report.totalMinutes / 60);
        const mins = report.totalMinutes % 60;
        const bestHours = getBestStudyHours();
        
        // 计算今日数据
        const todayRecord = getTodayRecord();
        const todayHours = Math.floor((todayRecord.studyMinutes || 0) / 60);
        const todayMins = (todayRecord.studyMinutes || 0) % 60;
        
        // 获取今日最佳时段（从hourlyMinutes中找）
        let todayBestHour = null;
        let maxMinutes = 0;
        if (todayRecord.hourlyMinutes) {
            Object.entries(todayRecord.hourlyMinutes).forEach(([hour, mins]) => {
                if (mins > maxMinutes) {
                    maxMinutes = mins;
                    todayBestHour = parseInt(hour);
                }
            });
        }
        
        let changeHtml = '';
        let changeEmoji = '📊';
        if (report.change > 0) {
            changeHtml = '<span style="color:#16a34a;">↑ +' + report.change + '%</span>';
            changeEmoji = '🚀';
        } else if (report.change < 0) {
            changeHtml = '<span style="color:#dc2626;">↓ ' + report.change + '%</span>';
            changeEmoji = '💪';
        } else {
            changeHtml = '<span style="color:#6b7280;">→ 持平</span>';
        }
        
        // 生成激励语句
        const motivations = generateMotivation(report, taskStats, todayRecord);
        
        // 生成具体建议
        const suggestions = generateSuggestions(report, taskStats, todayRecord, bestHours, todayBestHour);
        
        // 计算综合评分
        const overallScore = calculateOverallScore(report, taskStats, todayRecord);
        const scoreEmoji = overallScore >= 90 ? '🏆' : overallScore >= 70 ? '⭐' : overallScore >= 50 ? '💪' : '🌱';
        
        // 生成完成任务列表HTML
        let completedTasksHtml = '';
        if (taskStats.completedTasks && taskStats.completedTasks.length > 0) {
            completedTasksHtml = taskStats.completedTasks.slice(0, 5).map(t => 
                '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;"><span style="color:#16a34a;">✓</span><span style="font-size:11px;color:#374151;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + t + '</span></div>'
            ).join('');
            if (taskStats.completedTasks.length > 5) {
                completedTasksHtml += '<div style="font-size:10px;color:#9ca3af;">还有' + (taskStats.completedTasks.length - 5) + '项...</div>';
            }
        } else {
            completedTasksHtml = '<div style="font-size:11px;color:#9ca3af;">今天还没有完成任务</div>';
        }
        
        // 生成待办任务HTML
        let pendingTasksHtml = '';
        if (taskStats.pendingTasks && taskStats.pendingTasks.length > 0) {
            pendingTasksHtml = taskStats.pendingTasks.slice(0, 3).map(t => 
                '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;"><span style="color:#f59e0b;">○</span><span style="font-size:11px;color:#374151;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + t + '</span></div>'
            ).join('');
            if (taskStats.pendingTasks.length > 3) {
                pendingTasksHtml += '<div style="font-size:10px;color:#9ca3af;">还有' + (taskStats.pendingTasks.length - 3) + '项待完成...</div>';
            }
        } else {
            pendingTasksHtml = '<div style="font-size:11px;color:#16a34a;">太棒了！所有任务都完成了！</div>';
        }
        
        // 最佳学习时段分析
        let bestHourAnalysis = '';
        if (todayBestHour !== null) {
            const periodName = todayBestHour < 12 ? '上午' : (todayBestHour < 18 ? '下午' : '晚间');
            bestHourAnalysis = '今日在<strong>' + periodName + ' ' + todayBestHour + ':00</strong>前后专注度最高，共学习<strong>' + maxMinutes + '分钟</strong>';
        } else if (bestHours.length > 0) {
            bestHourAnalysis = '根据历史数据，你在<strong>' + bestHours[0].label + '</strong>效率最高';
        } else {
            bestHourAnalysis = '开始学习后会记录你的最佳时段';
        }
        
        content.innerHTML = 
            // 今日概览卡片
            '<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;padding:20px;margin-bottom:15px;color:white;text-align:center;box-shadow:0 4px 15px rgba(102,126,234,0.4);">' +
                '<p style="margin:0 0 5px 0;font-size:12px;opacity:0.9;">📅 今日学习报告</p>' +
                '<p style="margin:0 0 15px 0;font-size:28px;font-weight:700;">' + todayHours + '<span style="font-size:14px;">时</span> ' + todayMins + '<span style="font-size:14px;">分</span></p>' +
                '<div style="display:flex;justify-content:center;gap:20px;font-size:12px;">' +
                    '<div><span style="opacity:0.8;">专注度</span><br><strong style="font-size:16px;">' + (todayRecord.focusScore || 0) + '%</strong></div>' +
                    '<div><span style="opacity:0.8;">完成任务</span><br><strong style="font-size:16px;">' + taskStats.completed + '个</strong></div>' +
                    '<div><span style="opacity:0.8;">待办任务</span><br><strong style="font-size:16px;">' + taskStats.pending + '个</strong></div>' +
                '</div>' +
            '</div>' +
            
            // 综合评分
            '<div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:12px;padding:15px;margin-bottom:15px;text-align:center;">' +
                '<p style="margin:0 0 8px 0;font-size:12px;color:#b45309;">今日综合表现</p>' +
                '<div style="display:flex;align-items:center;justify-content:center;gap:10px;">' +
                    '<span style="font-size:36px;">' + scoreEmoji + '</span>' +
                    '<span style="font-size:42px;font-weight:700;color:#92400e;">' + overallScore + '</span>' +
                    '<span style="font-size:16px;color:#b45309;">/100</span>' +
                '</div>' +
                '<p style="margin:8px 0 0 0;font-size:11px;color:#92400e;">' + getScoreComment(overallScore) + '</p>' +
            '</div>' +
            
            // 专注时段分析（新增）
            '<div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:12px;padding:15px;margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#1e40af;font-weight:600;">⏰ 专注时段分析</p>' +
                '<p style="margin:0 0 10px 0;font-size:12px;color:#374151;line-height:1.5;">' + bestHourAnalysis + '</p>' +
                (bestHours.length > 0 ? 
                    '<div style="display:flex;gap:6px;flex-wrap:wrap;">' +
                        bestHours.map((h, i) => 
                            '<span style="background:' + ['#dbeafe', '#dcfce7', '#fef3c7'][i] + ';color:' + ['#1e40af', '#166534', '#b45309'][i] + ';padding:4px 10px;border-radius:15px;font-size:10px;font-weight:600;">' + (i === 0 ? '🥇 ' : i === 1 ? '🥈 ' : '🥉 ') + h.label + '</span>'
                        ).join('') +
                    '</div>' : ''
                ) +
            '</div>' +
            
            // 任务完成详情（新增）
            '<div style="background:#f0fdf4;border-radius:12px;padding:15px;margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#166534;font-weight:600;">✅ 今日完成的任务</p>' +
                '<div style="background:white;border-radius:8px;padding:10px;margin-bottom:10px;">' +
                    completedTasksHtml +
                '</div>' +
                '<p style="margin:0 0 8px 0;font-size:12px;color:#b45309;font-weight:600;">📋 待完成任务</p>' +
                '<div style="background:white;border-radius:8px;padding:10px;">' +
                    pendingTasksHtml +
                '</div>' +
            '</div>' +
            
            // 本周数据
            '<div style="background:#f8fafc;border-radius:12px;padding:15px;margin-bottom:15px;">' +
                '<p style="margin:0 0 12px 0;font-size:13px;color:#374151;font-weight:600;">' + changeEmoji + ' 本周累计学习 ' + hours + '时' + mins + '分 <span style="font-size:11px;margin-left:5px;">' + changeHtml + '</span></p>' +
                '<div style="display:flex;justify-content:space-between;align-items:flex-end;height:50px;padding:0 5px;">' +
                    report.weekData.map((d, i) => {
                        const maxH = Math.max(...report.weekData.map(x => x.studyMinutes), 1);
                        const h = Math.max((d.studyMinutes / maxH) * 40, 4);
                        const isToday = i === new Date().getDay();
                        return '<div style="flex:1;text-align:center;">' +
                            '<div style="height:' + h + 'px;background:' + (isToday ? 'linear-gradient(180deg,#3b82f6,#1d4ed8)' : (d.studyMinutes > 0 ? '#93c5fd' : '#e5e7eb')) + ';border-radius:4px;margin:0 2px;"></div>' +
                            '<span style="font-size:9px;color:' + (isToday ? '#1d4ed8' : '#9ca3af') + ';font-weight:' + (isToday ? '700' : '400') + ';">' + d.day + '</span>' +
                        '</div>';
                    }).join('') +
                '</div>' +
            '</div>' +
            
            // 专注度分析
            '<div style="margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">🎯 专注度分析</p>' +
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">' +
                    '<span style="font-size:11px;color:#6b7280;width:50px;">今日</span>' +
                    '<div style="flex:1;background:#e5e7eb;border-radius:10px;height:12px;overflow:hidden;">' +
                        '<div style="background:linear-gradient(90deg,#10b981,#059669);height:100%;width:' + (todayRecord.focusScore || 0) + '%;border-radius:10px;"></div>' +
                    '</div>' +
                    '<span style="font-size:12px;font-weight:600;color:#059669;width:40px;">' + (todayRecord.focusScore || 0) + '%</span>' +
                '</div>' +
                '<div style="display:flex;align-items:center;gap:10px;">' +
                    '<span style="font-size:11px;color:#6b7280;width:50px;">本周均</span>' +
                    '<div style="flex:1;background:#e5e7eb;border-radius:10px;height:12px;overflow:hidden;">' +
                        '<div style="background:linear-gradient(90deg,#3b82f6,#1d4ed8);height:100%;width:' + report.avgFocus + '%;border-radius:10px;"></div>' +
                    '</div>' +
                    '<span style="font-size:12px;font-weight:600;color:#1d4ed8;width:40px;">' + report.avgFocus + '%</span>' +
                '</div>' +
            '</div>' +
            
            // 具体建议（新增）
            '<div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-radius:12px;padding:15px;margin-bottom:15px;border:1px solid #86efac;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#166534;font-weight:600;">💡 针对性建议</p>' +
                '<div style="font-size:12px;color:#14532d;line-height:1.6;">' +
                    suggestions.map(s => '<p style="margin:0 0 8px 0;padding-left:18px;position:relative;"><span style="position:absolute;left:0;">•</span>' + s + '</p>').join('') +
                '</div>' +
            '</div>' +
            
            // 激励语句
            '<div style="background:linear-gradient(135deg,#fef9e7,#fef3c7);border-radius:12px;padding:15px;border:1px solid #fde68a;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#b45309;font-weight:600;">💪 今日激励</p>' +
                '<div style="font-size:12px;color:#78350f;line-height:1.6;">' +
                    motivations.map(m => '<p style="margin:0 0 8px 0;padding-left:15px;position:relative;"><span style="position:absolute;left:0;">✨</span>' + m + '</p>').join('') +
                '</div>' +
            '</div>';
    }
    
    // 生成具体建议
    function generateSuggestions(report, taskStats, todayRecord, bestHours, todayBestHour) {
        const suggestions = [];
        const studyMinutes = todayRecord.studyMinutes || 0;
        const focusScore = todayRecord.focusScore || 0;
        
        // 基于学习时长的建议
        if (studyMinutes < 30) {
            suggestions.push('今日学习时间较短，建议每天至少学习30分钟，保持学习的连贯性');
        } else if (studyMinutes >= 180) {
            suggestions.push('学习时间已超过3小时，记得适当休息，避免疲劳学习影响效率');
        }
        
        // 基于专注度的建议
        if (focusScore < 50) {
            suggestions.push('专注度还有提升空间，建议：关闭手机通知、使用番茄工作法、保持环境安静');
        } else if (focusScore >= 80) {
            suggestions.push('专注度很高！保持这个状态，你的学习效率非常好');
        }
        
        // 基于最佳时段的建议
        if (todayBestHour !== null) {
            const periodName = todayBestHour < 12 ? '上午' : (todayBestHour < 18 ? '下午' : '晚间');
            suggestions.push('你在' + periodName + '时段效率最高，建议把重要任务安排在这个时间');
        } else if (bestHours.length > 0) {
            suggestions.push('根据你的历史记录，' + bestHours[0].label + '是你的黄金学习时段');
        }
        
        // 基于任务完成情况的建议
        if (taskStats.pending > 5) {
            suggestions.push('待办任务较多（' + taskStats.pending + '项），建议优先处理最重要的3项');
        } else if (taskStats.completed === 0 && taskStats.pending > 0) {
            suggestions.push('今天还没有完成任务，选一个最简单的开始，让自己动起来！');
        } else if (taskStats.completed > 0 && taskStats.pending === 0) {
            suggestions.push('所有任务都完成了！可以为自己设定新的学习目标');
        }
        
        // 基于连续签到
        if (window.userData.consecutiveDays < 3) {
            suggestions.push('坚持每日签到，连续签到3天以上可以获得额外积分奖励');
        }
        
        // 如果没有建议，给一个通用的
        if (suggestions.length === 0) {
            suggestions.push('保持现有的学习节奏，持续努力就会看到进步');
            suggestions.push('可以尝试设定一个具体的学习目标，让学习更有方向');
        }
        
        return suggestions.slice(0, 4);
    }
    
    // 计算综合评分
    function calculateOverallScore(report, taskStats, todayRecord) {
        let score = 0;
        
        // 学习时长得分（满分30分）
        const studyMinutes = todayRecord.studyMinutes || 0;
        score += Math.min(studyMinutes / 60 * 15, 30); // 每小时15分，上限30分
        
        // 专注度得分（满分30分）
        score += (todayRecord.focusScore || 0) * 0.3;
        
        // 任务完成得分（满分25分）
        const taskScore = Math.min(taskStats.completed * 5, 25);
        score += taskScore;
        
        // 连续签到加分（满分15分）
        const streakBonus = Math.min(window.userData.consecutiveDays * 1.5, 15);
        score += streakBonus;
        
        return Math.round(Math.min(score, 100));
    }
    
    // 获取评分评语
    function getScoreComment(score) {
        if (score >= 90) return '表现卓越！你是学习之星！🌟';
        if (score >= 80) return '非常优秀！继续保持这个状态！';
        if (score >= 70) return '表现不错！还有提升空间！';
        if (score >= 60) return '良好的开始！加把劲！';
        if (score >= 40) return '今天稍有懈怠，明天继续努力！';
        return '新的一天，新的开始！💪';
    }
    
    // 生成激励语句
    function generateMotivation(report, taskStats, todayRecord) {
        const motivations = [];
        const studyMinutes = todayRecord.studyMinutes || 0;
        const focusScore = todayRecord.focusScore || 0;
        
        // 根据学习时长
        if (studyMinutes >= 120) {
            motivations.push('今天学习超过2小时，你的坚持令人敬佩！');
        } else if (studyMinutes >= 60) {
            motivations.push('一小时的专注学习，每一分钟都是进步！');
        } else if (studyMinutes > 0) {
            motivations.push('今天迈出了学习的第一步，这就是成功的开始！');
        }
        
        // 根据专注度
        if (focusScore >= 80) {
            motivations.push('专注度高达' + focusScore + '%，你的注意力管理能力很强！');
        } else if (focusScore >= 60) {
            motivations.push('专注度不错，尝试减少干扰可以更上一层楼！');
        }
        
        // 根据任务完成
        if (taskStats.completed >= 5) {
            motivations.push('完成' + taskStats.completed + '个任务，执行力超强！');
        } else if (taskStats.completed > 0) {
            motivations.push('每完成一个任务都是成就感的累积！');
        }
        
        // 根据连续签到
        if (window.userData.consecutiveDays >= 7) {
            motivations.push('连续签到' + window.userData.consecutiveDays + '天，习惯的力量正在显现！');
        }
        
        // 根据进步情况
        if (report.change > 20) {
            motivations.push('本周学习时间比上周增长' + report.change + '%，进步明显！');
        }
        
        // 如果没有特别的激励，给一个默认的
        if (motivations.length === 0) {
            motivations.push('坚持学习，量变终将引起质变！');
            motivations.push('今天的努力是明天成功的基石！');
        }
        
        return motivations.slice(0, 4); // 最多显示4条
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
    
    // ========== To-Do List 功能 ==========
    
    // 添加任务
    function addTodo(text) {
        if (!text || text.trim() === '') return;
        
        if (!window.userData.todoList) {
            window.userData.todoList = [];
        }
        
        const todo = {
            id: Date.now(),
            text: text.trim(),
            completed: false,
            createdAt: new Date().toISOString(),
            completedAt: null
        };
        
        window.userData.todoList.push(todo);
        saveUserData(window.userData);
        renderTodoList();
        
        // 播放添加音效
        playAlertSound('click');
    }
    
    // 完成任务
    function completeTodo(id) {
        if (!window.userData.todoList) return;
        
        const todo = window.userData.todoList.find(t => t.id === id);
        if (todo && !todo.completed) {
            todo.completed = true;
            todo.completedAt = new Date().toISOString();
            
            // 更新今日记录
            const record = getTodayRecord();
            if (!record.tasksCompleted) record.tasksCompleted = 0;
            record.tasksCompleted++;
            
            // 更新总完成数
            if (!window.userData.totalTasksCompleted) window.userData.totalTasksCompleted = 0;
            window.userData.totalTasksCompleted++;
            
            // 完成任务奖励积分（每个任务+5积分）
            const result = addPoints(window.userData, 5, 'task');
            
            if (result.leveledUp) {
                showAlert('恭喜升级！你现在是 ' + result.newLevel.icon + ' ' + result.newLevel.name + ' 了！', 'encourage');
                playAlertSound('levelup');
            }
            
            // 检查任务相关成就
            const newAchievements = checkAchievements(window.userData);
            newAchievements.forEach(achievement => {
                setTimeout(() => {
                    showAchievementPopup(achievement);
                }, 500);
            });
            
            saveUserData(window.userData);
            renderTodoList();
            updateStatsDisplay();
            
            // 播放完成音效
            playAlertSound('achievement');
            
            // 显示鼓励消息
            const encourages = [
                '太棒了！又完成一个任务！继续保持！💪',
                '干得漂亮！每完成一个任务都是进步！🎉',
                '任务完成！你离目标又近了一步！⭐',
                '优秀！高效完成任务，积分+5！🚀'
            ];
            showAlert(encourages[Math.floor(Math.random() * encourages.length)], 'encourage');
        }
    }
    
    // 删除任务
    function deleteTodo(id) {
        if (!window.userData.todoList) return;
        
        window.userData.todoList = window.userData.todoList.filter(t => t.id !== id);
        saveUserData(window.userData);
        renderTodoList();
    }
    
    // 清除已完成任务
    function clearCompletedTodos() {
        if (!window.userData.todoList) return;
        
        window.userData.todoList = window.userData.todoList.filter(t => !t.completed);
        saveUserData(window.userData);
        renderTodoList();
    }
    
    // 渲染任务列表
    function renderTodoList() {
        const container = document.getElementById('todo-list-container');
        const countEl = document.getElementById('todo-count');
        if (!container) return;
        
        const todoList = window.userData.todoList || [];
        const pending = todoList.filter(t => !t.completed);
        const completed = todoList.filter(t => t.completed);
        
        // 更新计数
        if (countEl) {
            countEl.textContent = pending.length + ' 项待完成';
        }
        
        if (todoList.length === 0) {
            container.innerHTML = '<div style="text-align:center;padding:30px 15px;"><p style="font-size:32px;margin:0 0 10px 0;">📝</p><p style="color:#9ca3af;font-size:13px;margin:0;">暂无任务，添加一个吧！</p></div>';
            return;
        }
        
        let html = '';
        
        // 待完成任务
        pending.forEach((todo, index) => {
            html += '<div class="todo-item-pending" data-id="' + todo.id + '" style="display:flex;align-items:center;gap:12px;padding:14px 16px;background:linear-gradient(135deg,#ffffff,#f8fafc);border-radius:12px;margin-bottom:10px;border:1px solid #e5e7eb;box-shadow:0 2px 4px rgba(0,0,0,0.02);transition:all 0.2s ease;">' +
                '<button class="todo-complete-btn" data-id="' + todo.id + '" style="width:24px;height:24px;border-radius:50%;border:2px solid #3b82f6;background:white;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all 0.2s ease;"></button>' +
                '<span style="flex:1;font-size:14px;color:#1f2937;word-break:break-all;line-height:1.5;">' + escapeHtml(todo.text) + '</span>' +
                '<button class="todo-delete-btn" data-id="' + todo.id + '" style="background:none;border:none;color:#d1d5db;cursor:pointer;font-size:18px;padding:4px 8px;border-radius:6px;transition:all 0.2s ease;">×</button>' +
                '</div>';
        });
        
        // 已完成任务
        if (completed.length > 0) {
            html += '<div style="margin-top:16px;padding-top:16px;border-top:1px dashed #e5e7eb;">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
                '<p style="font-size:12px;color:#9ca3af;margin:0;font-weight:500;">✨ 已完成 (' + completed.length + ')</p>' +
                '</div>';
            
            completed.slice(-5).forEach(todo => {
                html += '<div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-radius:12px;margin-bottom:8px;border:1px solid #bbf7d0;">' +
                    '<span style="width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,#22c55e,#16a34a);color:white;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;box-shadow:0 2px 4px rgba(34,197,94,0.3);">✓</span>' +
                    '<span style="flex:1;font-size:13px;color:#6b7280;text-decoration:line-through;word-break:break-all;line-height:1.5;">' + escapeHtml(todo.text) + '</span>' +
                    '</div>';
            });
            
            if (completed.length > 0) {
                html += '<button id="clear-completed-btn" style="width:100%;background:white;border:1px dashed #d1d5db;border-radius:8px;padding:10px;font-size:12px;color:#9ca3af;cursor:pointer;margin-top:8px;transition:all 0.2s ease;">🗑️ 清除已完成任务</button>';
            }
            html += '</div>';
        }
        
        container.innerHTML = html;
        
        // 使用事件委托绑定点击事件（避免内联onclick的作用域问题）
        container.querySelectorAll('.todo-complete-btn').forEach(btn => {
            btn.onclick = function() {
                const id = parseInt(this.dataset.id);
                completeTodo(id);
            };
        });
        
        container.querySelectorAll('.todo-delete-btn').forEach(btn => {
            btn.onclick = function() {
                const id = parseInt(this.dataset.id);
                deleteTodo(id);
            };
        });
        
        const clearBtn = document.getElementById('clear-completed-btn');
        if (clearBtn) {
            clearBtn.onclick = clearCompletedTodos;
        }
    }
    
    // HTML转义
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 绑定To-Do List事件
    function bindTodoEvents() {
        const addBtn = document.getElementById('add-todo-btn');
        const input = document.getElementById('todo-input');
        
        if (addBtn && input) {
            addBtn.onclick = () => {
                addTodo(input.value);
                input.value = '';
            };
            
            input.onkeypress = (e) => {
                if (e.key === 'Enter') {
                    addTodo(input.value);
                    input.value = '';
                }
            };
        }
        
        console.log('Todo events bound');
    }
    
    // 将To-Do List函数暴露到全局作用域（解决onclick无法调用的问题）
    window.completeTodo = completeTodo;
    window.deleteTodo = deleteTodo;
    window.clearCompletedTodos = clearCompletedTodos;
    window.addTodo = addTodo;
    
    // 获取今日任务统计
    function getTodayTaskStats() {
        const today = getTodayStr();
        const todoList = window.userData.todoList || [];
        
        const todayCompleted = todoList.filter(t => 
            t.completed && t.completedAt && t.completedAt.startsWith(today)
        ).length;
        
        const todayCreated = todoList.filter(t => 
            t.createdAt && t.createdAt.startsWith(today)
        ).length;
        
        const pending = todoList.filter(t => !t.completed).length;
        
        // 获取今日完成的具体任务列表
        const completedTasks = todoList.filter(t => 
            t.completed && t.completedAt && t.completedAt.startsWith(today)
        ).map(t => t.text);
        
        // 获取待完成的任务列表
        const pendingTasks = todoList.filter(t => !t.completed).map(t => t.text);
        
        return {
            completed: todayCompleted,
            created: todayCreated,
            pending: pending,
            total: window.userData.totalTasksCompleted || 0,
            completedTasks: completedTasks,
            pendingTasks: pendingTasks
        };
    }
    
    // 初始化游戏化系统显示（带重试机制，解决Accordion延迟渲染问题）
    function initGameSystem() {
        const calendarEl = document.getElementById('checkin-calendar');
        const achievementsEl = document.getElementById('achievements-container');
        
        if (calendarEl && achievementsEl) {
            console.log('Game system elements found, initializing...');
            updateStatsDisplay();
            generateCheckInCalendar();
            updateAchievementsPanel();
            updateDashboard();
            renderTodoList();
            applyEquippedItems(); // 应用已装备的外观
            updateGachaDisplay(); // 更新抽卡积分显示
            return true;
        }
        return false;
    }
    
    // 首次尝试
    setTimeout(() => {
        if (!initGameSystem()) {
            console.log('Game system elements not ready, will retry on accordion open...');
        }
    }, 1600);
    
    // 监听DOM变化，当Accordion展开时重新初始化
    const observer = new MutationObserver((mutations) => {
        const calendarEl = document.getElementById('checkin-calendar');
        const achievementsEl = document.getElementById('achievements-container');
        
        if (calendarEl && achievementsEl && calendarEl.innerHTML === '') {
            console.log('Accordion opened, initializing game system...');
            generateCheckInCalendar();
            updateAchievementsPanel();
        }
    });
    
    // 观察整个文档的DOM变化
    observer.observe(document.body, { childList: true, subtree: true });
    
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
with gr.Blocks(title="学习陪伴AI - 学了么") as demo:
    gr.HTML("""
        <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --text-color: #1e293b;
            --card-bg: rgba(255,255,255,0.9);
        }
        .gradio-container { max-width: 1100px !important; margin: auto !important; }
        /* 整体背景 - 默认主题高级渐变 */
        .gradio-container, .gradio-container > .main, body { 
            background: radial-gradient(circle at 20% 80%, rgba(102,126,234,0.08) 0%, transparent 50%), 
                        radial-gradient(circle at 80% 20%, rgba(118,75,162,0.08) 0%, transparent 50%),
                        linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f1f5f9 100%);
            background-attachment: fixed;
            min-height: 100vh;
        }
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
        @keyframes gacha-pop {
            0% { transform: scale(0.3); opacity: 0; }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
        @keyframes flame-glow {
            0%, 100% { box-shadow: 0 0 20px rgba(239,68,68,0.8); }
            50% { box-shadow: 0 0 30px rgba(239,68,68,1), 0 0 40px rgba(245,158,11,0.5); }
        }
        @keyframes rainbow-border {
            0% { border-color: #ff0000; }
            17% { border-color: #ff7f00; }
            33% { border-color: #ffff00; }
            50% { border-color: #00ff00; }
            67% { border-color: #0000ff; }
            83% { border-color: #9400d3; }
            100% { border-color: #ff0000; }
        }
        /* 背包物品hover效果 */
        .inventory-item:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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
        /* To-Do List 样式 */
        .todo-item-pending:hover {
            box-shadow: 0 4px 12px rgba(59,130,246,0.15) !important;
            border-color: #93c5fd !important;
            transform: translateY(-1px);
        }
        .todo-complete-btn:hover {
            background: #dbeafe !important;
            transform: scale(1.1);
        }
        .todo-delete-btn:hover {
            background: #fee2e2 !important;
            color: #ef4444 !important;
        }
        #clear-completed-btn:hover {
            border-color: #f87171 !important;
            color: #ef4444 !important;
            background: #fef2f2 !important;
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
        /* 隐藏组件样式 */
        .hidden-component {
            display: none !important;
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
            <h1>学习陪伴AI - 学了么</h1>
            <p>有我陪伴，学习不孤单 | 支持实时人脸识别与情绪检测</p>
        </div>
    """)
    
    with gr.Row():
        # 左侧栏：用户状态与控制中心
        with gr.Column(scale=1):
            # 用户状态卡片
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
            
            # 学习中心 (摄像头 + 休息)
            with gr.Group():
                gr.HTML("""
                    <div class="study-mode-panel">
                        <div class="study-mode-header">
                            <h3 style="margin:0; font-size:16px; color:#0369a1;">📹 专注监测</h3>
                            <div style="display:flex; gap:5px;">
                                <button id="start-btn" type="button" class="camera-btn">开启</button>
                                <button id="stop-btn" type="button" class="camera-btn stop" style="display: none;">关闭</button>
                            </div>
                        </div>
                        <div id="video-container" style="position: relative; width: 100%; max-width: 320px; margin: 0 auto; display: none; min-height: 180px;"></div>
                        <div id="camera-placeholder" style="width: 100%; max-width: 320px; height: 160px; margin: 0 auto; background: rgba(255,255,255,0.6); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #64748b; border: 2px dashed #cbd5e1;">
                            <p style="margin: 0; font-size: 12px; opacity: 0.7;">点击“开启”进入专注模式</p>
                        </div>
                        <div id="loading-indicator" style="display: none; text-align: center; padding: 15px; color: #6366f1;">
                            <div style="display: inline-block; width: 24px; height: 24px; border: 3px solid #e5e7eb; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                            <p style="margin: 5px 0 0 0; font-size: 12px;">载入模型...</p>
                        </div>
                        <div class="emotion-status-grid">
                            <div class="status-card"><p>情绪</p><p id="emotion-display">---</p></div>
                            <div class="status-card"><p>状态</p><p id="attention-display">就绪</p></div>
                        </div>
                    </div>
                    
                    <div id="rest-panel" style="display: none; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 15px; padding: 15px; margin-bottom: 10px; color: white;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h3 style="margin: 0; font-size: 15px;">☕ 休息中</h3>
                            <button id="cancel-rest-btn" type="button" style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 3px 8px; border-radius: 6px; cursor: pointer; font-size: 11px;">返回</button>
                        </div>
                        <div id="rest-options">
                            <div style="display: flex; gap: 6px; margin-bottom: 8px;">
                                <button id="rest-5" type="button" style="flex:1; background:rgba(255,255,255,0.2); border:none; padding:8px; border-radius:6px; color:white;">5m</button>
                                <button id="rest-10" type="button" style="flex:1; background:rgba(255,255,255,0.2); border:none; padding:8px; border-radius:6px; color:white;">10m</button>
                                <button id="rest-15" type="button" style="flex:1; background:rgba(255,255,255,0.2); border:none; padding:8px; border-radius:6px; color:white;">15m</button>
                            </div>
                            <button id="rest-custom" type="button" style="width:100%; background:rgba(255,255,255,0.15); border:none; padding:6px; border-radius:6px; color:white; font-size:12px;">⏰ 自定义</button>
                            <div id="custom-time-input" style="display: none; margin-top: 10px; align-items: center; gap: 6px;">
                                <input id="custom-minutes" type="number" min="1" max="60" value="20" style="flex: 1; padding: 6px; border-radius: 4px; border: none; text-align: center;">
                                <button id="start-custom-rest" type="button" style="background: white; color: #059669; border: none; padding: 6px 12px; border-radius: 4px; font-weight: 600;">开始</button>
                            </div>
                        </div>
                        <div id="rest-countdown" style="display: none; text-align: center;">
                            <p id="countdown-display" style="margin: 0 0 10px 0; font-size: 36px; font-weight: bold; font-family: monospace;">00:00</p>
                            <button id="stop-rest-btn" type="button" style="background: white; color: #059669; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600;">提前结束</button>
                        </div>
                    </div>
                    <button id="rest-mode-btn" type="button" class="rest-btn" style="margin-bottom: 10px;">☕ 休息一下</button>
                """)

            # 个人成长（可折叠）
            with gr.Accordion("🏅 个人成就与签到", open=False, elem_id="medal-accordion"):
                gr.HTML("""
                    <h4 style="margin:10px 0 8px 0; font-size:14px; color:#059669; font-weight:700;">📅 签到日历</h4>
                    <div id="checkin-calendar" style="margin-bottom:15px; min-height:160px; background: rgba(255,255,255,0.5); border-radius: 8px;"></div>
                    <h4 style="margin:10px 0 8px 0; font-size:14px; color:#b45309; font-weight:700;">🏆 我的成就</h4>
                    <div id="achievements-container" style="min-height:80px; background: rgba(255,255,255,0.5); border-radius: 8px;"></div>
                """)
            
            # 抽卡系统
            with gr.Accordion("🎰 积分抽卡", open=False, elem_id="gacha-accordion"):
                gr.HTML("""
                    <div style="padding:10px 0;">
                        <!-- 抽卡介绍 -->
                        <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:12px;padding:15px;margin-bottom:15px;text-align:center;">
                            <p style="margin:0 0 8px 0;font-size:14px;color:#92400e;font-weight:600;">🎁 消耗积分抽取稀有道具！</p>
                            <div style="display:flex;justify-content:center;gap:8px;font-size:12px;">
                                <span style="padding:3px 8px;background:rgba(255,255,255,0.6);border-radius:10px;color:#6b7280;">普通</span>
                                <span style="padding:3px 8px;background:rgba(59,130,246,0.2);border-radius:10px;color:#3b82f6;">稀有</span>
                                <span style="padding:3px 8px;background:rgba(139,92,246,0.2);border-radius:10px;color:#8b5cf6;">超稀</span>
                                <span style="padding:3px 8px;background:rgba(245,158,11,0.3);border-radius:10px;color:#d97706;">传说</span>
                            </div>
                        </div>
                        
                        <!-- 积分显示 -->
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;padding:12px 15px;background:#f0f9ff;border-radius:10px;border:1px solid #bae6fd;">
                            <span style="font-size:13px;color:#0369a1;font-weight:600;">💰 可用积分</span>
                            <span id="gacha-points-display" style="font-size:16px;color:#0c4a6e;font-weight:700;">0 积分</span>
                        </div>
                        
                        <!-- 抽卡按钮 -->
                        <button id="gacha-btn" type="button" 
                            style="width:100%;padding:15px;background:linear-gradient(135deg,#f59e0b,#d97706);color:white;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer;box-shadow:0 4px 15px rgba(245,158,11,0.4);transition:all 0.3s ease;"
                            onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(245,158,11,0.5)';"
                            onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 15px rgba(245,158,11,0.4)';">
                            🎲 抽卡一次 (20积分)
                        </button>
                        
                        <!-- 抽卡记录 -->
                        <div style="margin-top:15px;">
                            <p style="margin:0 0 8px 0;font-size:12px;color:#6b7280;">最近抽卡记录：</p>
                            <div id="gacha-history" style="display:flex;gap:5px;flex-wrap:wrap;min-height:30px;">
                                <span style="color:#9ca3af;font-size:11px;">暂无记录</span>
                            </div>
                        </div>
                    </div>
                """)
            
            # 背包系统
            with gr.Accordion("🎒 我的背包", open=False, elem_id="inventory-accordion"):
                gr.HTML("""
                    <div style="padding:10px 0;">
                        <!-- 背包物品容器 -->
                        <div id="inventory-container" style="min-height:100px;">
                            <div style="text-align:center;padding:30px;color:#9ca3af;">
                                <p style="font-size:24px;margin:0 0 10px 0;">📦</p>
                                <p style="margin:0;">背包空空如也，快去抽卡吧！</p>
                            </div>
                        </div>
                    </div>
                """)
            
            # 快捷工具（重构为原生组件以提高稳定性）
            with gr.Accordion("⚡ 快捷工具", open=True):
                with gr.Row():
                    advice_btn = gr.Button("💡 学习建议", variant="secondary", size="sm", elem_classes=["quick-btn"])
                    plan_btn = gr.Button("📋 制定计划", variant="secondary", size="sm", elem_classes=["quick-btn"])
                with gr.Row():
                    encourage_btn = gr.Button("💪 鼓励我", variant="secondary", size="sm", elem_classes=["quick-btn"])
                    clear_btn = gr.Button("🗑️ 清空对话", variant="stop", size="sm", elem_classes=["quick-btn"])
            
            # To-Do List 面板
            with gr.Accordion("📝 学习任务", open=True, elem_id="todo-accordion"):
                gr.HTML("""
                    <div style="padding:8px 0;">
                        <!-- 添加任务输入框 -->
                        <div style="display:flex;gap:10px;margin-bottom:15px;">
                            <input id="todo-input" type="text" placeholder="✍️ 输入新任务..." 
                                style="flex:1;padding:12px 16px;border:2px solid #e5e7eb;border-radius:12px;font-size:14px;outline:none;transition:all 0.3s ease;background:#fafafa;"
                                onfocus="this.style.borderColor='#3b82f6';this.style.background='#fff';this.style.boxShadow='0 0 0 3px rgba(59,130,246,0.1)';" 
                                onblur="this.style.borderColor='#e5e7eb';this.style.background='#fafafa';this.style.boxShadow='none';">
                            <button id="add-todo-btn" type="button" 
                                style="background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;border:none;padding:12px 20px;border-radius:12px;cursor:pointer;font-size:14px;font-weight:600;white-space:nowrap;transition:all 0.3s ease;box-shadow:0 4px 12px rgba(59,130,246,0.3);"
                                onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 16px rgba(59,130,246,0.4)';"
                                onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 12px rgba(59,130,246,0.3)';">
                                ➕ 添加
                            </button>
                        </div>
                        
                        <!-- 任务统计 -->
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding:10px 14px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:10px;border:1px solid #bfdbfe;">
                            <span id="todo-count" style="font-size:13px;color:#1d4ed8;font-weight:700;">0 项待完成</span>
                            <span style="font-size:11px;color:#3b82f6;background:white;padding:4px 10px;border-radius:20px;font-weight:500;">✨ 完成+5积分</span>
                        </div>
                        
                        <!-- 任务列表容器 -->
                        <div id="todo-list-container" style="max-height:280px;overflow-y:auto;padding-right:5px;">
                            <div style="text-align:center;padding:30px 15px;">
                                <p style="font-size:32px;margin:0 0 10px 0;">📝</p>
                                <p style="color:#9ca3af;font-size:13px;margin:0;">暂无任务，添加一个吧！</p>
                            </div>
                        </div>
                    </div>
                """)
            
            # 报告按钮
            gr.HTML("""
                <button id="show-report-btn" type="button" style="width:100%; background:linear-gradient(135deg,#3b82f6 0%,#1d4ed8 100%); color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-size:14px; font-weight:600; margin-top:10px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                    📊 查看学习报告
                </button>
            """)
        
        # 右侧栏：对话与数据
        with gr.Column(scale=2):
            # 数据面板（可折叠）
            with gr.Accordion("📊 学习数据概览", open=False):
                gr.HTML("""
                    <div id="stats-dashboard" style="background:#ffffff; padding:10px;">
                        <h4 style="margin:0 0 15px 0; font-size:15px; color:#1e40af; font-weight:700; display:flex; align-items:center; gap:8px;">
                            📊 实时数据统计
                            <span id="dashboard-date" style="font-size:12px; color:#6b7280; font-weight:500; margin-left:auto;"></span>
                        </h4>
                        <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:15px;">
                            <div style="background:#eff6ff; border-radius:10px; padding:10px; text-align:center;">
                                <p style="margin:0 0 5px 0; font-size:11px; color:#3b82f6; font-weight:600;">今日</p>
                                <p id="today-minutes" style="margin:0; font-size:18px; font-weight:700; color:#1e40af;">0</p>
                            </div>
                            <div style="background:#f0fdf4; border-radius:10px; padding:10px; text-align:center;">
                                <p style="margin:0 0 5px 0; font-size:11px; color:#16a34a; font-weight:600;">本周</p>
                                <p id="week-minutes" style="margin:0; font-size:18px; font-weight:700; color:#15803d;">0</p>
                            </div>
                            <div style="background:#fef3c7; border-radius:10px; padding:10px; text-align:center;">
                                <p style="margin:0 0 5px 0; font-size:11px; color:#d97706; font-weight:600;">本月</p>
                                <p id="month-minutes" style="margin:0; font-size:18px; font-weight:700; color:#b45309;">0</p>
                            </div>
                        </div>
                        <div style="margin-bottom:15px;">
                            <p style="margin:0 0 8px 0; font-size:12px; color:#374151; font-weight:600;">📈 专注度趋势</p>
                            <div id="week-chart" style="display:flex; align-items:flex-end; justify-content:space-between; height:60px; padding:5px 0; background:#f9fafb; border-radius:8px; overflow:hidden;"></div>
                        </div>
                        <div>
                            <p style="margin:0 0 8px 0; font-size:12px; color:#374151; font-weight:600;">🎯 今日专注度: <span id="focus-text">0%</span></p>
                            <div style="background:#e5e7eb; border-radius:10px; height:12px; overflow:hidden;">
                                <div id="focus-bar" style="background:linear-gradient(90deg,#10b981,#059669); height:100%; width:0%; transition:width 0.5s;"></div>
                            </div>
                        </div>
                        <div id="best-hours" style="display:none;"></div> <!-- 隐藏原始容器 -->
                    </div>
                """)

            # 周报弹窗 (保持在外部)
            gr.HTML("""
                <div id="weekly-report-modal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10001; align-items:center; justify-content:center;">
                    <div style="background:white; border-radius:16px; padding:25px; max-width:500px; width:90%; max-height:80vh; overflow-y:auto;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                            <h3 style="margin:0; font-size:18px; font-weight:700;">📋 学习周报</h3>
                            <button id="close-report-btn" type="button" style="background:none; border:none; font-size:24px; cursor:pointer;">×</button>
                        </div>
                        <div id="report-content">正在生成报告...</div>
                    </div>
                </div>
            """)

            # 风格切换（可折叠）
            with gr.Accordion("⚙️ 个性化设置", open=False):
                with gr.Row():
                    style_select = gr.Radio(
                        choices=["默认", "柔情猫娘", "成熟妈妈系御姐", "磁性霸道男总裁"],
                        value="默认",
                        label="陪伴风格",
                        container=True,
                        elem_id="style-radio",
                        scale=3
                    )
                    voice_toggle = gr.Checkbox(label="🔊 开启语音", value=False, scale=1, elem_id="voice-toggle-checkbox")
                
                # 【优化】走神语音提醒触发链路 (使用 CSS 隐藏而非 visible=False，确保 DOM 存在)
                alert_trigger = gr.Textbox(visible=True, elem_id="alert-trigger", elem_classes=["hidden-component"])
                alert_audio = gr.Audio(visible=True, autoplay=True, elem_id="alert-audio", elem_classes=["hidden-component"])
                
                # 绑定事件：当触发器内容改变时，调用后端语音生成逻辑
                alert_trigger.change(get_alert_speech, inputs=[alert_trigger, style_select], outputs=[alert_audio])
            
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
    
    # 【新增】快捷工具原生绑定
    advice_btn.click(
        fn=chat, 
        inputs=[gr.State("给我一些学习建议吧"), chatbot, style_select, voice_toggle], 
        outputs=[chatbot, msg, voice_output]
    )
    plan_btn.click(
        fn=chat, 
        inputs=[gr.State("帮我制定一个学习计划"), chatbot, style_select, voice_toggle], 
        outputs=[chatbot, msg, voice_output]
    )
    encourage_btn.click(
        fn=chat, 
        inputs=[gr.State("我有点沮丧，需要一些鼓励"), chatbot, style_select, voice_toggle], 
        outputs=[chatbot, msg, voice_output]
    )
    clear_btn.click(fn=clear_history, outputs=[chatbot, msg])

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
