"""
AI学习陪伴助手 - 主应用入口

该应用整合了AI对话、语音合成、人脸识别、游戏化学习等功能，
为用户提供全方位的学习陪伴体验。
"""

import gradio as gr
import threading
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any

# 导入模块
from core.chat_manager import ChatManager
from core.tts_manager import TTSManager
from game.stats_tracker import StatsTracker
from game.achievements import AchievementManager
from ui.layouts import UILayout
from ui.assets import CUSTOM_CSS
from utils.helpers import hex_to_audio_data
from utils.logger import logger
from config.settings import SERVER_NAME, SERVER_PORT, INITIAL_MESSAGE


class StudyCompanionApp:
    """
    AI学习陪伴应用主类
    """
    
    def __init__(self):
        # 初始化核心组件
        self.chat_manager = ChatManager()
        self.tts_manager = TTSManager()
        self.stats_tracker = StatsTracker()
        self.achievement_manager = AchievementManager(self.stats_tracker)
            
        # 应用状态
        self.learning_active = False  # 将在创建界面后由施设置为true
        self.rest_active = False
        self.webcam_active = False
            
        # 创建 UI布局
        self.ui_layout = UILayout()
            
        # 初始化应用
        self._setup_callbacks()
            
        # 【修复 UX-3】默认开启学习模式
        self.learning_active = True
        self.start_learning_session()
        
    def _setup_callbacks(self):
        """
        设置所有回调函数
        """
        self.callbacks = {
            'on_style_change': self.on_style_change,
            'on_webcam_toggle': self.on_webcam_toggle,
            'on_learning_mode_toggle': self.on_learning_mode_toggle,
            'on_checkin_click': self.on_checkin_click,
            'on_rest_click': self.on_rest_click,
            'on_reset_click': self.on_reset_chat,
            'on_send_message': self.on_send_message,
            'on_camera_frame': self.on_camera_frame,
            'on_update_stats': self.on_update_stats,
            'on_refresh_achievements': self.on_refresh_achievements,
            'on_alert_trigger': self.on_alert_trigger
        }
    
    def on_style_change(self, style: str):
        """
        角色风格改变回调
        """
        logger.info(f"Changing character style to: {style}")
        self.chat_manager.set_character_style(style)
        self.tts_manager.set_voice(style)
        return f"角色风格已切换为：{style}"
    
    def on_webcam_toggle(self, active: bool):
        """
        摄像头开关回调
        """
        self.webcam_active = active
        if active:
            return "摄像头已开启"
        else:
            return "摄像头已关闭"
    
    def on_learning_mode_toggle(self, active: bool):
        """
        学习模式开关回调
        """
        self.learning_active = active
        if active:
            # 开启学习模式时初始化
            self.start_learning_session()
            return gr.Button(value="停止学习", interactive=True)
        else:
            self.stop_learning_session()
            return gr.Button(value="开始学习", interactive=True)
    
    def start_learning_session(self):
        """
        开始学习会话
        """
        # 初始化统计数据
        if not self.stats_tracker.user_data["firstStudyDate"]:
            self.stats_tracker.user_data["firstStudyDate"] = self.stats_tracker.get_today_str()
        
        self.stats_tracker.user_data["lastStudyDate"] = self.stats_tracker.get_today_str()
        
        # 检查签到
        self.stats_tracker.handle_check_in()
        
        # 添加初始消息
        if not self.chat_manager.get_chat_history():
            self.chat_manager.ai_agent.add_message("assistant", INITIAL_MESSAGE)
    
    def stop_learning_session(self):
        """
        结束学习会话
        """
        self.learning_active = False
        self.rest_active = False
    
    def on_checkin_click(self):
        """
        签到按钮点击回调
        """
        if not self.learning_active:
            return "", "请先开启学习模式！"
        
        result = self.stats_tracker.handle_check_in()
        if result["is_new"]:
            message = f"签到成功！获得{result['bonus']}积分，当前连续签到{result['consecutive_days']}天。"
        else:
            message = f"今日已签到，连续签到{result['consecutive_days']}天。"
        
        # 检查是否有新成就解锁
        new_achievements = self.achievement_manager.check_and_unlock_achievements()
        if new_achievements:
            achievement_names = [a["name"] for a in new_achievements]
            message += f"\n🎉 解锁新成就: {', '.join(achievement_names)}"
        
        return "", message
    
    def on_rest_click(self):
        """
        休息按钮点击回调
        """
        if not self.learning_active:
            return "", "请先开启学习模式！"
        
        self.rest_active = not self.rest_active
        
        if self.rest_active:
            # 开始休息
            self.stats_tracker.increment_early_end_rest()
            return "", "开始休息模式，点击按钮结束休息"
        else:
            # 结束休息
            return "", "结束休息，继续学习！"
    
    def on_reset_chat(self):
        """
        重置聊天回调
        """
        self.chat_manager.reset_chat()
        self.chat_manager.ai_agent.add_message("assistant", INITIAL_MESSAGE)
        return [(None, INITIAL_MESSAGE)], "对话已重置"
    
    def on_send_message(self, user_input: str, chat_history: List[Tuple[str, str]], style: str, voice_enabled: bool):
        """
        发送消息回调 - 流式版本
            
        Args:
            user_input: 用户输入的文本
            chat_history: Gradio Chatbot 的历史记录（列表格式）
            style: 当前选择的角色风格
            voice_enabled: 是否启用语音播报
                
        Yields:
            (updated_history, input_status, audio_data)
        """
        logger.debug(f"[CHAT_INPUT] 收到用户输入: {user_input[:50] if user_input else '(empty)'}")
        logger.debug(f"[CHAT_INPUT] 风格: {style}, 语音启用: {voice_enabled}")
            
        if not user_input or not user_input.strip():
            logger.debug("[CHAT_INPUT] 消息为空, 返回空应答")
            yield chat_history or [], "请输入有效内容", None
            return
            
        logger.info(f"[CHAT_INPUT] ✅ 消息有效, 开始处理")
            
        if not self.learning_active:
            logger.warning("[CHAT_INPUT] ⚠️ 学习模式未开启")
            yield chat_history or [], "请先开启学习模式！", None
            return
            
        # 设置当前风格
        self.chat_manager.set_character_style(style)
            
        # 初始化更新的历史记录
        updated_history = (chat_history or []).copy()
        updated_history.append({"role": "user", "content": user_input})
        updated_history.append({"role": "assistant", "content": ""})
            
        try:
            logger.debug(f"[CHAT_PROCESS] 调用 chat_manager.send_message_stream()...")
            logger.debug(f"[CHAT_PROCESS] 输入参数: user_input={user_input[:50]}..., voice_enabled={voice_enabled}")
                        
            # 流式获取 AI 回复和语龊数据
            full_response = ""
            audio_data = None
                        
            for result in self.chat_manager.send_message_stream(user_input):
                text_chunk = result.get("text", "")
                is_streaming = result.get("is_streaming", False)
                            
                if is_streaming:
                    # 文本流式输出阶段
                    full_response += text_chunk
                    updated_history[-1]["content"] = full_response
                    logger.debug(f"[CHAT_STREAM] 接收文本块: {len(text_chunk)} 字符")
                    yield updated_history, "", None  # 逐字更新前端，不播放语龊
                else:
                    # 流式完成，获取音频数据
                    audio_data = result.get("audio", None)
                    logger.debug(f"[CHAT_STREAM] 流式完成，音频数据类型: {type(audio_data).__name__}")
                    if audio_data:
                        if isinstance(audio_data, bytes):
                            logger.debug(f"[CHAT_STREAM] 音频字节数: {len(audio_data)} bytes")
                            logger.debug(f"[CHAT_STREAM] 音频头部: {audio_data[:16]}")
                        else:
                            logger.warning(f"[CHAT_STREAM] 音频数据类型预有: {type(audio_data).__name__}")
                    else:
                        logger.warning("[CHAT_STREAM] 音频数据为None")
                        
            # 检查新成就
            new_achievements = self.achievement_manager.check_and_unlock_achievements()
            if new_achievements:
                achievement_names = [a["name"] for a in new_achievements]
                notification = f"🎉 解锁新成就: {', '.join(achievement_names)}"
            else:
                notification = ""  # 清空输入框，不显示提示
                        
            logger.info(f"[CHAT_PROCESS] ✅ 消息处理完成, 通知: {notification}")
            logger.info(f"[CHAT_PROCESS] 语龊启用: {voice_enabled}, 音频数据是否存在: {audio_data is not None}")
                        
            # 如果启用了语龊，返回音频数据；否则返回 None
            final_audio = audio_data if voice_enabled else None
            logger.debug(f"[CHAT_PROCESS] 最终返回音频: {type(final_audio).__name__} {'(' + str(len(final_audio)) + ' bytes)' if isinstance(final_audio, bytes) else ''}")
            yield updated_history, notification, final_audio
                        
        except Exception as e:
            error_msg = f"发送消息时出现错误: {str(e)}"
            logger.error(f"[CHAT_ERROR] {error_msg}", exc_info=True)
            yield updated_history, error_msg, None
    
    def on_camera_frame(self, frame):
        """
        摄像头帧处理回调
        """
        # 在实际应用中，这里会进行人脸识别和情绪分析
        # 目前只是简单返回原始帧
        return frame
    
    def on_update_stats(self):
        """
        更新统计信息回调
        """
        stats = self.stats_tracker.get_stats_summary()
        
        return (
            stats["points"],
            stats["level"],
            stats["totalStudyMinutes"],
            stats["todayStudyMinutes"],
            stats["consecutiveDays"],
            stats["achievementsCount"]
        )
    
    def on_refresh_achievements(self):
        """
        刷新成就回调
        """
        achievements_status = self.achievement_manager.get_all_achievements_status()
        return achievements_status
    
    def on_alert_trigger(self, trigger_val: str, style: str):
        """
        分神提醒回调 - 当检测到用户分神时触发
        """
        if not trigger_val or not self.learning_active:
            return None
            
        logger.info(f"[ALERT] 检测到分神, 触发值: {trigger_val}, 风格: {style}")
            
        try:
            # 根据触发类型生成相应的提醒语音
            alert_messages = {
                "distraction": "你可能有些分神呀，填一下第一问题的答案吧！",
                "emotion_low": "你看起来有些疲惫呀，来，我们一起加油！",
                "emotion_high": "你看起来很棒呀，来继续加油！"
            }
                
            message = alert_messages.get(trigger_val, "会一业业！")
                
            # 根据风格调整提醒模式
            if style == "柔情猫娘":
                message = f"主人喊~ {message}"
            elif style == "成熟妈妈系御姐":
                message = f"亲爱的，{message}"
            elif style == "磁性霸道男总裁":
                message = f"我不允许你：{message}"
                
            # 调用 TTS 管理器生成提醒语音
            audio_bytes = self.tts_manager.synthesize_alert_speech(trigger_val, style)
                
            if audio_bytes:
                logger.debug(f"[ALERT] 成功生成提醒语音, 大小: {len(audio_bytes)} bytes")
            else:
                logger.warning(f"[ALERT] 提醒语音生成失败")
                
            return audio_bytes
                
        except Exception as e:
            logger.error(f"[ALERT_ERROR] 提醒回调失败: {str(e)}", exc_info=True)
            return None
    
    def run(self, share=False, debug=False):
        """
        运行应用
        """
        logger.info("Starting AI Study Companion App...")
        # 创建界面【修复】获取 combined_js
        interface, combined_js = self.ui_layout.create_main_layout(self.callbacks)
        
        print("AI学习陪伴助手启动中...")
        logger.info(f"Access URL: http://{SERVER_NAME}:{SERVER_PORT}")
        print(f"访问地址: http://{SERVER_NAME}:{SERVER_PORT}")
        
        # 启动应用
        interface.launch(
            server_name=SERVER_NAME,
            server_port=SERVER_PORT,
            share=share,
            debug=debug,
            theme=gr.themes.Soft(),
            css=CUSTOM_CSS,
            js=combined_js if combined_js else None  # 【修复】回复 Gradio 6.0 点管理 js 参数 + 页面重载检测
        )


def run_scheduler():
    """
    运行后台调度器，定期执行任务
    """
    def scheduler_loop():
        while True:
            try:
                # 每分钟检查一次（在学习活跃状态下）
                time.sleep(60)
                
                # 注意：在实际实现中，我们需要一个全局的应用实例来访问状态
                # 这里简化处理，实际应用中应有更好的设计
                
            except KeyboardInterrupt:
                print("调度器已停止")
                break
            except Exception as e:
                print(f"调度器错误: {e}")
    
    # 在单独线程中运行调度器
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()


if __name__ == "__main__":
    # 启动后台调度器
    run_scheduler()
    
    # 创建并运行应用
    app = StudyCompanionApp()
    app.run(debug=True)
else:
    # 魔搭创空间部署模式：创建全局 demo 对象
    # 在这个模式下，Gradio 会自动调用 demo.launch()
    app = StudyCompanionApp()
    interface, combined_js = app.ui_layout.create_main_layout(app.callbacks)
    demo = interface