from typing import List, Dict, Optional, Generator
from .ai_agent import AIAgent
from .tts_manager import TTSManager
from utils.logger import logger


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
            "audio": audio_bytes if audio_bytes else None
        })
        
        return {
            "text": ai_response,
            "audio": audio_bytes
        }
    
    def send_message_stream(self, user_input: str) -> Generator[Dict[str, any], None, None]:
        """
        处理用户消息并以流式方式返回响应
        使用生成器逐字返回 AI 回复文本
        最后一次 yield 包含完整的音频数据
        """
        logger.debug(f"[CHAT_MANAGER] 开始流式处理消息, 指前文本: {user_input[:50]}...")
        full_response = ""
            
        try:
            # 流式获取 AI 回复，逐字返回
            logger.debug("[CHAT_MANAGER] 调用 ai_agent.get_chat_response_stream()...")
            chunk_count = 0
            for chunk in self.ai_agent.get_chat_response_stream(user_input):
                full_response += chunk
                chunk_count += 1
                logger.debug(f"[CHAT_MANAGER] 接收文本块 #{chunk_count}: {len(chunk)} 字符")
                # 每获得一个文本块，就返回一次（为前端打字机效果）
                yield {
                    "text": chunk,
                    "audio": None,
                    "is_streaming": True
                }
                
            logger.info(f"[CHAT_MANAGER] ✅ 流式文本输出完成, 共 {len(full_response)} 字符")
                
            # 流式输出完成后，生成完整的语音回复
            logger.debug("[CHAT_MANAGER] 开始语音合成...")
            audio_bytes = self.tts_manager.synthesize_speech(full_response)
            logger.debug(f"[CHAT_MANAGER] 语音合成完成: {type(audio_bytes).__name__} {f'({len(audio_bytes)} bytes)' if isinstance(audio_bytes, bytes) else ''}")
                
            # 添加到聊天历史
            self.chat_history.append({
                "role": "user",
                "content": user_input
            })
            self.chat_history.append({
                "role": "assistant",
                "content": full_response,
                "audio": audio_bytes if audio_bytes else None
            })
                
            # 最后一次返回，包含语音数据
            logger.debug(f"[CHAT_MANAGER] 最后一次 yield 包含语音数据")
            yield {
                "text": "",
                "audio": audio_bytes if audio_bytes else None,
                "is_streaming": False
            }
                
        except Exception as e:
            logger.error(f"[CHAT_MANAGER] ❌ 流式处理错误: {str(e)}", exc_info=True)
            raise
    
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
            "audio": audio_bytes
        }
    
    def reset_chat(self):
        """重置聊天"""
        self.chat_history = []
        self.ai_agent.reset_conversation()
        
    def get_chat_history(self) -> List[Dict]:
        """获取聊天历史"""
        return self.chat_history