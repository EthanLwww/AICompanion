"""
AI学习陪伴助手 - 主应用入口

该应用整合了AI对话、语音合成、人脸识别、游戏化学习等功能，
为用户提供全方位的学习陪伴体验。
"""

import gradio as gr
import threading
import time
import os
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
        self.supervision_active = False
        
        # 桌面监督辅助状态
        self.supervision_frame_count = 0  # 帧计数器用于节流
        self.distraction_streak = 0      # 连续分心计数
        self.focus_minute_counter = 0    # 专注计数器（用于积分激励）
            
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
            'on_alert_trigger': self.on_alert_trigger,
            'on_supervision_toggle': self.on_supervision_toggle,
            'on_supervision_data_received': self.on_supervision_data_received
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
    
    def on_supervision_toggle(self, active: bool):
        """
        桌面监督开关回调
        """
        self.supervision_active = active
        status = "开启" if active else "关闭"
        logger.info(f"[SUPERVISION] 桌面监督已{status}")
        # 【修复】取消返回值以匹配 UI outputs=[]，消除 UserWarning
        return None

    def on_supervision_data_received(self, base64_data: str):
        """
        接收并处理来自前端的屏幕截图数据（测试增强版）
        """
        import time
        import os
        from datetime import datetime
        
        # 【方案A】入口独立日志：确认函数被调用
        logger.info("[SUPERVISION_DEBUG] ========== 函数入口 ==========")
        logger.info(f"[SUPERVISION_DEBUG] 输入参数类型: {type(base64_data).__name__}")
        logger.info(f"[SUPERVISION_DEBUG] 输入参数长度: {len(base64_data) if base64_data else 0}")
        
        start_time = time.time()
        logger.info("=" * 60)
        logger.info(f"[SUPERVISION_DEBUG] 🎯 开始处理监督数据")
        logger.info(f"[SUPERVISION_DEBUG]   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"[SUPERVISION_DEBUG]   进程ID: {os.getpid()}")
        
        # 1. 基础状态检查
        logger.info(f"[SUPERVISION_DEBUG] 📋 状态检查:")
        logger.info(f"  ├─ 监督激活状态: {self.supervision_active}")
        logger.info(f"  ├─ 休息状态: {self.rest_active}")
        logger.info(f"  ├─ 学习模式: {self.learning_active}")
        logger.info(f"  └─ 系统运行时间: {time.time() - start_time:.3f}秒")
        
        if not self.supervision_active or self.rest_active:
            logger.warning(f"[SUPERVISION_DEBUG] ⚠️ 条件不符，跳过处理")
            logger.info(f"[SUPERVISION_DEBUG]   原因: {'监督未激活' if not self.supervision_active else '处于休息状态'}")
            logger.info("=" * 60)
            return None
    
        if not base64_data:
            logger.warning(f"[SUPERVISION_DEBUG] ⚠️ 收到空数据，跳过处理")
            logger.info("=" * 60)
            return None
            
        # 2. 数据接收详情
        data_size = len(base64_data) if base64_data else 0
        logger.info(f"[SUPERVISION_DEBUG] 📥 数据接收详情:")
        logger.info(f"  ├─ 原始数据大小: {data_size} 字节")
        logger.info(f"  ├─ Base64前缀存在: {',' in base64_data}")
        logger.info(f"  ├─ 数据类型: {type(base64_data).__name__}")
        logger.info(f"  └─ 接收耗时: {time.time() - start_time:.3f}秒")
            
        try:
            # 【方案A】移除节流控制：每帧都进行分析（调试阶段）
            self.supervision_frame_count += 1
            logger.info(f"[SUPERVISION_DEBUG] 帧计数器: {self.supervision_frame_count}")
            logger.info(f"[SUPERVISION_DEBUG] 开始AI分析（无节流）")

            # 3. 数据预处理
            try:
                if ',' in base64_data:
                    _, encoded = base64_data.split(',', 1)
                else:
                    encoded = base64_data
                            
                encoded_size = len(encoded) if encoded else 0
                logger.info(f"[SUPERVISION_DEBUG] 🔧 数据预处理:")
                logger.info(f"  ├─ 提取后编码数据大小: {encoded_size} 字节")
                logger.info(f"  ├─ 数据完整性: {'✓' if encoded_size > 0 else '✗'}")
                logger.info(f"  ├─ Base64有效性: {'✓' if len(encoded) % 4 == 0 else '✗'}")
                logger.info(f"  └─ 预处理耗时: {time.time() - start_time:.3f}秒")
                        
            except Exception as e:
                logger.error(f"[SUPERVISION_DEBUG] ❌ 数据预处理失败:")
                logger.error(f"  ├─ 错误: {str(e)}")
                logger.error(f"  └─ 数据预览: {base64_data[:50] if base64_data else 'None'}")
                logger.info("=" * 60)
                return None
                
            # 2. 调用 AI 视觉分析
            logger.info(f"[SUPERVISION_DEBUG] 开始调用 AI 分析... (帧 #{self.supervision_frame_count})")
            analysis_result = self.chat_manager.ai_agent.analyze_screen_state(encoded)
            
            # 【调试日志】AI 返回结果
            logger.info(f"[SUPERVISION_DEBUG] AI 返回结果: {analysis_result}")
            
            status = analysis_result.get("status", "unknown")
            reason = analysis_result.get("reason", "未知")
            
            # 3. 逻辑判定与反馈
            if status == "distracted":
                self.distraction_streak += 1
                logger.warning(f"[SUPERVISION_DEBUG] 检测到分心! 原因: {reason}, 连续次数: {self.distraction_streak}")
                
                # 连续 2 次分心判定则触发提醒
                if self.distraction_streak >= 2:
                    logger.warning(f"[SUPERVISION_DEBUG] 触发提醒条件满足!")
                    self.distraction_streak = 0 # 重置计数以防连续轰炸
                    
                    # 惩罚逻辑：扣除 5 积分
                    logger.info(f"[SUPERVISION_DEBUG] 执行积分惩罚")
                    self.stats_tracker.deduct_points(5, "distraction_penalty")
                    
                    # 返回一个特殊的触发值给 alert_trigger (UI outputs 已配置)
                    trigger_val = f"distracted_supervision_{int(time.time())}"
                    logger.info(f"[SUPERVISION_DEBUG] 返回触发值: {trigger_val}")
                    return trigger_val
            
            # 【新增】AI 异常降级处理
            elif status == "unknown":
                logger.warning(f"[SUPERVISION_DEBUG] AI 分析返回 unknown: {reason}，视为安全状态")
                # 重置分心计数器，避免误报
                if self.distraction_streak > 0:
                    logger.info(f"[SUPERVISION_DEBUG] AI异常，重置分心计数器")
                self.distraction_streak = 0
                return None
            
            else:
                # learning 或其他正常状态
                logger.info(f"[SUPERVISION_DEBUG] AI 判定为专注状态: {reason}")
                if self.distraction_streak > 0:
                    logger.info(f"[SUPERVISION_DEBUG] 重置分心计数器")
                self.distraction_streak = 0
                
                # 【新增】专注积分激励
                # 每次被判定为专注时，累积专注计数器
                if not hasattr(self, 'focus_minute_counter'):
                    self.focus_minute_counter = 0
                self.focus_minute_counter += 1
                
                # 每 10 次专注判定（约 5 分钟）奖励 2 积分
                if self.focus_minute_counter >= 10:
                    self.focus_minute_counter = 0
                    logger.info(f"[SUPERVISION] 专注奖励：+2 积分")
                    self.stats_tracker.add_points(2, "supervision_focus_bonus")
            
            return None
                
        except Exception as e:
            logger.error(f"[SUPERVISION_DEBUG] 处理截图数据失败: {str(e)}", exc_info=True)
            return None

    def trigger_distraction_alert(self, style: str):
        """
        [已废弃] 分心提醒逻辑已迁移至 on_supervision_data_received 的返回值触发
        """
        pass
    
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
    # 魔搭创空间部署模式：创建全局 demo 对象并运行
    app = StudyCompanionApp()
    interface, combined_js = app.ui_layout.create_main_layout(app.callbacks)
    demo = interface
    
    # 显式调用 launch 以支持 ModelScope 的自动部署规范
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        js=combined_js if combined_js else None
    )