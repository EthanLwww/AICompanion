import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
import os
import time
import wave
from typing import Optional
from config.settings import DASHSCOPE_API_KEY, TTS_MODEL_ID
from config.constants import VOICE_MAPPING
from utils.logger import logger


class TTSManager:
    """
    文字转语音管理器
    """
    
    def __init__(self):
        if DASHSCOPE_API_KEY:
            dashscope.api_key = DASHSCOPE_API_KEY
        else:
            print("[WARNING] 未找到DASHSCOPE_API_KEY，语音合成功能将不可用")
        
        self.current_voice = "默认"
        
    def set_voice(self, voice_style: str):
        """设置语音风格"""
        self.current_voice = voice_style
        
    def synthesize_speech(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """
        生成语音
        """
        if not DASHSCOPE_API_KEY:
            print("[WARNING] 未配置API密钥，跳过语音合成")
            return None
            
        # 使用指定语音或当前语音
        voice_name = voice or VOICE_MAPPING.get(self.current_voice, "longfeifei_v2")
        logger.debug(f"Starting TTS synthesis with voice: {voice_name}")
        
        try:
            # 使用SpeechSynthesizer生成语音
            synthesizer = SpeechSynthesizer(
                model=TTS_MODEL_ID,
                voice=voice_name
            )
            
            # 生成语音数据
            audio_data = synthesizer.synthesize(text=text)
            
            # 将音频数据转换为字节
            audio_bytes = b""
            for chunk in audio_data:
                if chunk:
                    audio_bytes += chunk
            
            if audio_bytes:
                logger.debug(f"TTS synthesis successful. Data size: {len(audio_bytes)} bytes")
            else:
                logger.warning("TTS synthesis returned empty audio data")
                    
            return audio_bytes
            
        except Exception as e:
            print(f"[ERROR] 语音合成失败: {str(e)}")
            return None
    
    def synthesize_alert_speech(self, trigger_val: str, style: str) -> Optional[bytes]:
        """
        为系统主动提醒生成语音（包括分神提醒和情绪鼓励）
        """
        if not trigger_val:
            return None
            
        # 确定要使用的提醒文本
        from config.constants import DISTRACTION_REMINDERS, ENCOURAGE_REMINDERS
        
        if trigger_val.startswith("distracted_"):
            # 分神提醒
            reminder_text = DISTRACTION_REMINDERS.get(style, DISTRACTION_REMINDERS["默认"])
        elif trigger_val.startswith("encourage_"):
            # 情绪鼓励
            reminder_text = ENCOURAGE_REMINDERS.get(style, ENCOURAGE_REMINDERS["默认"])
        else:
            # 默认处理
            reminder_text = DISTRACTION_REMINDERS.get(style, DISTRACTION_REMINDERS["默认"])
        
        return self.synthesize_speech(reminder_text, VOICE_MAPPING.get(style))
    
    def validate_audio(self, audio_bytes: bytes) -> bool:
        """
        验证音频数据的有效性
        """
        if not audio_bytes:
            return False
            
        try:
            # 尝试将字节数据写入临时WAV文件并验证
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_filename = temp_file.name
                
            # 验证WAV文件
            with wave.open(temp_filename, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                
            # 清理临时文件
            os.unlink(temp_filename)
            
            # 检查音频参数是否合理
            return frames > 0 and sample_rate > 0
            
        except Exception:
            # 清理临时文件（如果存在）
            try:
                os.unlink(temp_filename)
            except:
                pass
            return False