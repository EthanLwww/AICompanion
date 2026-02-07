import os
from typing import Dict, Any

# API 配置
MODELSCOPE_API_KEY = os.environ.get("MODELSCOPE_API_KEY")
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY") or MODELSCOPE_API_KEY

if not MODELSCOPE_API_KEY:
    print("[ERROR] 未找到环境变量 MODELSCOPE_API_KEY，请在环境变量或魔搭创空间设置中添加！")

# 模型配置
MODELSCOPE_API_URL = "https://api-inference.modelscope.cn/v1/chat/completions"
CHAT_MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"
VISION_MODEL_ID = "Qwen/Qwen2.5-VL-72B-Instruct"
CHAT_TEMPERATURE = 0.7
CHAT_MAX_TOKENS = 1000
HISTORY_LIMIT = 20

# API 超时配置 (秒)
API_TIMEOUT = 60
STREAM_TIMEOUT = 120

# TTS 配置
TTS_MODEL_ID = 'cosyvoice-v2'

# 服务器配置
SERVER_NAME = "0.0.0.0"
SERVER_PORT = 7860

# 初始消息
INITIAL_MESSAGE = "你好呀！我是小伴，你的学习陪伴AI助手~\n\n有什么问题都可以问我，学习累了也可以和我聊聊天。\n\n点击左侧的\"开启摄像头\"按钮，我还能通过人脸识别实时关注你的学习状态哦！"