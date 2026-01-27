from typing import List, Dict, Optional
from .ai_agent import AIAgent
from .tts_manager import TTSManager


class ChatManager:
    """
    聊天管理器，协调AI代理和TTS管理器的工作
    """
    
    def __init__(self):
        self.ai_agent = AIAgent()
        self.tts_manager = TTSManager()
        self.chat_history = []
        
    def set_character_style(self, style: str):
        """设置角色风格"""
        self.ai_agent.set_style(style)
        self.tts_manager.set_voice(style)
        
    def send_message(self, user_input: str) -> Dict[str, str]:
        """
        处理用户消息并返回响应
        返回包含文本回复和音频数据的字典
        """
        # 获取AI回复
        ai_response = self.ai_agent.get_chat_response(user_input)
        
        # 生成语音回复
        audio_bytes = self.tts_manager.synthesize_speech(ai_response)
        
        # 添加到聊天历史
        self.chat_history.append({
            "role": "user",
            "content": user_input
        })
        self.chat_history.append({
            "role": "assistant",
            "content": ai_response,
            "audio": audio_bytes.hex() if audio_bytes else None  # 转换为十六进制存储
        })
        
        return {
            "text": ai_response,
            "audio_hex": audio_bytes.hex() if audio_bytes else None
        }
    
    def get_alert_response(self, trigger_type: str) -> Dict[str, str]:
        """
        获取系统主动提醒的响应
        """
        # 获取AI提醒响应
        ai_response = self.ai_agent.get_alert_response(trigger_type)
        
        # 生成语音提醒
        audio_bytes = self.tts_manager.synthesize_speech(ai_response)
        
        return {
            "text": ai_response,
            "audio_hex": audio_bytes.hex() if audio_bytes else None
        }
    
    def reset_chat(self):
        """重置聊天"""
        self.chat_history = []
        self.ai_agent.reset_conversation()
        
    def get_chat_history(self) -> List[Dict]:
        """获取聊天历史"""
        return self.chat_history