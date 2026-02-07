import gradio as gr
from .components import UIComponents
from .assets import (
    CUSTOM_CSS, CUSTOM_HTML, HEADER_HTML, 
    USER_STATS_HTML, STUDY_CENTER_HTML, ACHIEVEMENTS_HTML,
    REPORT_BUTTON_HTML, DATA_DASHBOARD_HTML, WEEKLY_REPORT_MODAL_HTML,
    GACHA_PANEL_HTML, INVENTORY_PANEL_HTML
)
from config.settings import INITIAL_MESSAGE
from utils.logger import logger
import os


class UILayout:
    """
    UI布局类，组合各个组件形成完整的界面布局
    """
    
    def __init__(self):
        self.components = UIComponents()
        
    def create_main_layout(self, callbacks: dict):
        """
        创建主界面布局（原版复刻）
        """
        # 加载 JS 文件
        load_js_content = None
        event_handlers_js = None
        combined_js = ""
        
        try:
            # 使用 __file__ 作为基础路径，增强健壮性
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            static_dir = os.path.join(parent_dir, 'static', 'js')
            
            # 检查 static/js 目录是否存在
            if not os.path.exists(static_dir):
                logger.warning(f"[JS_LOAD] static/js 目录不存在: {static_dir}")
            else:
                logger.debug(f"[JS_LOAD] static/js 目录找到: {static_dir}")
            
            # 加载 LOAD_JS (Step 3)
            load_js_path = os.path.join(static_dir, 'load_js.js')
            logger.debug(f"[JS_LOAD] 查检 load_js.js: {load_js_path}")
            if os.path.exists(load_js_path):
                with open(load_js_path, 'r', encoding='utf-8') as f:
                    load_js_content = f.read()
                logger.info(f"[JS_LOAD] ✅ load_js.js 加载成功, 大小: {len(load_js_content)} 字节")
            else:
                logger.warning(f"[JS_LOAD] ❌ load_js.js 文件不存在: {load_js_path}")
            
            # 加载事件处理器 JS (Step 4)
            event_handlers_path = os.path.join(static_dir, 'event_handlers.js')
            logger.debug(f"[JS_LOAD] 查检 event_handlers.js: {event_handlers_path}")
            if os.path.exists(event_handlers_path):
                with open(event_handlers_path, 'r', encoding='utf-8') as f:
                    event_handlers_js = f.read()
                logger.info(f"[JS_LOAD] ✅ event_handlers.js 加载成功, 大小: {len(event_handlers_js)} 字节")
            else:
                logger.warning(f"[JS_LOAD] ❌ event_handlers.js 文件不存在: {event_handlers_path}")
            
            # 加载抽卡物品配置 JS (Step 8)
            gacha_items_path = os.path.join(static_dir, 'gacha_items.js')
            gacha_items_js = None
            logger.debug(f"[JS_LOAD] 查检 gacha_items.js: {gacha_items_path}")
            if os.path.exists(gacha_items_path):
                with open(gacha_items_path, 'r', encoding='utf-8') as f:
                    gacha_items_js = f.read()
                logger.info(f"[JS_LOAD] ✅ gacha_items.js 加载成功, 大小: {len(gacha_items_js)} 字节")
            else:
                logger.warning(f"[JS_LOAD] ❌ gacha_items.js 文件不存在: {gacha_items_path}")
            
            # 合并三个 JS 文件内容
            if load_js_content:
                combined_js += load_js_content
            if gacha_items_js:
                combined_js += "\n\n" + gacha_items_js
            if event_handlers_js:
                combined_js += "\n\n" + event_handlers_js
            
            # 详细的日志输出
            if combined_js:
                logger.info(f"[JS_LOAD] ✅ JS 组合完成, 总大小: {len(combined_js)} 字节")
                logger.debug(f"[JS_LOAD] JS 前 100 字符: {combined_js[:100]}")
                logger.debug(f"[JS_LOAD] JS 后 100 字符: {combined_js[-100:]}")
            else:
                logger.warning("[JS_LOAD] ⚠️ combined_js 为None或为空，不会加载 JavaScript")
                
        except Exception as e:
            logger.error(f"[JS_LOAD] 致命错误: 不能加载 JS 文件: {str(e)}", exc_info=True)
        
        with gr.Blocks(title="AI学习陪伴助手") as demo:
            # 全局弹窗和提醒框
            gr.HTML(CUSTOM_HTML)
            
            # 顶部紫色渐变 Banner
            gr.HTML(HEADER_HTML)
            
            with gr.Row():
                # 左侧栏：用户状态与控制中心
                with gr.Column(scale=1):
                    # 用户状态卡片
                    gr.HTML(USER_STATS_HTML)
                    
                    # 学习中心 (摄像头 + 休息)
                    with gr.Group():
                        gr.HTML(STUDY_CENTER_HTML)
                        
                        # 【修复 Phase 2】摄像头隐藏控制复选框（通过JS与HTML按钮同步）
                        webcam_checkbox = gr.Checkbox(
                            label="开启摄像头",
                            value=False,
                            interactive=True,
                            elem_id="webcam-checkbox",
                            visible=False  # 隐藏UI，通过JS与HTML按钮交互
                        )
                        
                        # 绑定摄像头回调
                        webcam_checkbox.change(
                            fn=callbacks.get('on_webcam_toggle', lambda x: None),
                            inputs=[webcam_checkbox],
                            outputs=[]
                        )
                    
                    # 个人成长（可折叠）
                    with gr.Accordion("🏅 个人成就与签到", open=False, elem_id="medal-accordion") as achievements_accordion:
                        gr.HTML(ACHIEVEMENTS_HTML)
                        # 隐藏的刷新触发器
                        achievements_refresh_trigger = gr.Textbox(visible=False, elem_id="achievements-refresh-trigger")
                    
                    # 快捷工具（重构为原生组件以提高稳定性）
                    with gr.Accordion("⚡ 快捷工具", open=True):
                        with gr.Row():
                            advice_btn = gr.Button("📚 学习建议", variant="secondary", size="sm", elem_classes=["quick-btn"])
                            plan_btn = gr.Button("📋 制定计划", variant="secondary", size="sm", elem_classes=["quick-btn"])
                        with gr.Row():
                            encourage_btn = gr.Button("💪 鼓励我", variant="secondary", size="sm", elem_classes=["quick-btn"])
                            clear_btn = gr.Button("🗑️ 清空对话", variant="stop", size="sm", elem_classes=["quick-btn"])
                                            
                        # 【修复 Phase 3】功能按钮（签到）
                        checkin_button = gr.Button("🗣️ 每日签到", variant="primary", size="sm")
                    
                    # 积分抽卡面板
                    with gr.Accordion("🎰 积分抽卡", open=False, elem_id="gacha-accordion"):
                        gr.HTML(GACHA_PANEL_HTML)
                    
                    # 我的背包面板
                    with gr.Accordion("🎒 我的背包", open=False, elem_id="inventory-accordion"):
                        gr.HTML(INVENTORY_PANEL_HTML)
                    
                    # 报告按钮
                    gr.HTML(REPORT_BUTTON_HTML)
                
                # 右侧栏：对话与数据
                with gr.Column(scale=2):
                    # 数据面板（可折叠）
                    with gr.Accordion("📊 学习数据概览", open=False) as stats_accordion:
                        gr.HTML(DATA_DASHBOARD_HTML)
                        
                        # 【修复 Phase 4】隐藏的统计更新触发器（为消息发送后更新统计数据供准备）
                        stats_update_trigger = gr.Textbox(visible=False, elem_id="stats-update-trigger")
                        # 隐藏的刷新触发器（用于 Accordion 展开时刷新）
                        stats_refresh_trigger = gr.Textbox(visible=False, elem_id="stats-refresh-trigger")
                        
                        # 绑定统计更新回调（通过JS触发）
                        stats_update_trigger.change(
                            fn=callbacks.get('on_update_stats', lambda: None),
                            outputs=[]
                        )
                    
                    # 周报弹窗 (保持在外部)
                    gr.HTML(WEEKLY_REPORT_MODAL_HTML)
                    
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
                        
                        # 【修复 Phase 1】学习模式控制复选框 - 默认开启
                        learning_mode_checkbox = gr.Checkbox(
                            label="📚 学习模式",
                            value=True,
                            interactive=True,
                            elem_id="learning-mode-checkbox"
                        )
                        
                        supervision_checkbox = gr.Checkbox(
                            label="🖥️ 桌面监督",
                            value=False,
                            interactive=True,
                            elem_id="supervision-checkbox",
                            info="开启后系统将共享并分析您的屏幕，用于专注度检测。数据仅本地处理，不会上传存储。"
                        )
                        
                        # 走神语音提醒触发链路 (使用 CSS 隐藏而非 visible=False，确保 DOM 存在)
                        alert_trigger = gr.Textbox(visible=True, elem_id="alert-trigger", elem_classes=["hidden-component"])
                        alert_audio = gr.Audio(visible=True, autoplay=True, elem_id="alert-audio", elem_classes=["hidden-component"])
                        
                        # 桌面监督数据回传触发器
                        supervision_data_trigger = gr.Textbox(visible=True, elem_id="supervision-data-trigger")

                    # 【调试】屏幕监督测试窗口
                    with gr.Accordion("🧪 监督测试工具 (调试用)", open=False, elem_id="supervision-test-accordion"):
                        gr.HTML("""
                            <div style="background: #fff7ed; border: 1px solid #ffedd5; padding: 10px; border-radius: 8px;">
                                <p style="font-size: 12px; color: #9a3412; margin-bottom: 8px;">点击按钮将执行：截取当前屏幕 -> 传输至后端 -> 调用 AI 分析 -> 结果输出至控制台</p>
                                <button id="debug-capture-btn" class="lg secondary" style="width: 100%; height: 40px; background: #ea580c; color: white; border-radius: 6px; cursor: pointer;">立即截屏并分析</button>
                            </div>
                        """)
                    
                    # 【新增】桌面监督状态可视化面板
                    with gr.Accordion("📊 监督状态", open=False, elem_id="supervision-status-accordion"):
                        gr.HTML("""
                            <div id="supervision-status-panel" style="padding: 10px; background: #f8fafc; border-radius: 8px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                    <span id="supervision-status-icon" style="font-size: 20px;">⚪</span>
                                    <span id="supervision-status-text" style="font-weight: 600; color: #64748b;">未开启</span>
                                </div>
                                <div id="supervision-stats" style="font-size: 13px; color: #64748b;">
                                    <div>今日专注时长: <span id="focus-minutes" style="color: #10b981; font-weight: 600;">0</span> 分钟</div>
                                    <div>专注得分: <span id="focus-score" style="color: #6366f1; font-weight: 600;">--</span></div>
                                </div>
                            </div>
                        """)
                    
                    # 播放模式选择面板（初始隐藏）
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
                    
                    # 【修复】播放器初始隐藏，勾选语音后才显示
                    voice_output = gr.Audio(
                        label="🔊 语音播报",
                        autoplay=True,
                        visible=False,
                        type="numpy",
                        show_label=False,
                        elem_id="voice-output",
                        elem_classes=["compact-player"]
                    )
                    
                    # 调试信息放入 Accordion（折叠面板）
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
                    
                    # 样式 Radio 样式
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
                        /* 紧凑型播放器样式 */
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
                        /* 自动播放模式下的特殊视觉反馈 */
                        .auto-mode {
                            border-color: #6366f1 !important;
                            background: #f0f9ff !important;
                        }
                        </style>
                    """)
                    
                    # 聊天界面
                    chatbot = gr.Chatbot(
                        value=[{"role": "assistant", "content": INITIAL_MESSAGE}],
                        elem_id="chatbot",
                        show_label=False,
                        height=480
                    )
                                
                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder="输入你的问题或想记的话...",
                            show_label=False,
                            scale=4,
                            container=False,
                            elem_id="msg-input"
                        )
                        send_btn = gr.Button("发送", elem_id="send-btn", scale=1)
                        
            # 【编变】绑定回调函数
            # 绑定发送消息事件
            send_btn.click(
                fn=callbacks.get('on_send_message', lambda *args: ([], "", None)),
                inputs=[msg, chatbot, style_select, voice_toggle],
                outputs=[chatbot, msg, voice_output],
                queue=True
            )
            msg.submit(
                fn=callbacks.get('on_send_message', lambda *args: ([], "", None)),
                inputs=[msg, chatbot, style_select, voice_toggle],
                outputs=[chatbot, msg, voice_output],
                queue=True
            )
            
            # 【修复 UX-1】快捷工具按钮回调 - 自动填充并发送
            from functools import partial
            
            def auto_send_suggestion(suggestion_text, current_msg, chat_history, style, voice_enabled):
                # 填充提示词
                message_to_send = current_msg + suggestion_text if current_msg else suggestion_text
                # 直接调用发送回调，它是生成器函数
                yield from callbacks.get('on_send_message', lambda *args: ([], "", None))(
                    message_to_send, chat_history, style, voice_enabled
                )
            
            advice_btn.click(
                fn=partial(auto_send_suggestion, "请给我一些学习建议"),
                inputs=[msg, chatbot, style_select, voice_toggle],
                outputs=[chatbot, msg, voice_output],
                queue=True
            )
            
            plan_btn.click(
                fn=partial(auto_send_suggestion, "请帮我制定一个学习计划"),
                inputs=[msg, chatbot, style_select, voice_toggle],
                outputs=[chatbot, msg, voice_output],
                queue=True
            )
            
            encourage_btn.click(
                fn=partial(auto_send_suggestion, "鼓励我坚持学习"),
                inputs=[msg, chatbot, style_select, voice_toggle],
                outputs=[chatbot, msg, voice_output],
                queue=True
            )
            
            # 【修复 UX-2】清空对话回调
            def clear_chat_history():
                return [], ""
            
            clear_btn.click(
                fn=clear_chat_history,
                outputs=[chatbot, msg]
            )
            
            # 【修复 Phase 3】绑定功能按钮回调
            def show_checkin_result():
                result = callbacks.get('on_checkin_click', lambda: "")()
                return result if isinstance(result, str) else result[1] if len(result) > 1 else ""
            
            checkin_button.click(
                fn=show_checkin_result,
                outputs=[]
            )
            learning_mode_checkbox.change(
                fn=callbacks.get('on_learning_mode_toggle', lambda x: None),
                inputs=[learning_mode_checkbox],
                outputs=[]
            )
            supervision_checkbox.change(
                fn=callbacks.get('on_supervision_toggle', lambda x: None),
                inputs=[supervision_checkbox],
                outputs=[],
                js="toggleSupervisionJS"
            )
            
            # 【新增】绑定桌面监督数据回传事件 (输出到 alert_trigger 以触发语音提醒)
            supervision_data_trigger.change(
                fn=callbacks.get('on_supervision_data_received', lambda x: None),
                inputs=[supervision_data_trigger],
                outputs=[alert_trigger]
            )
            
            # 【修复】语音开关控制播放器显示/隐藏
            def toggle_voice_output(voice_enabled):
                return gr.Audio(visible=voice_enabled)
            
            voice_toggle.change(
                fn=toggle_voice_output,
                inputs=[voice_toggle],
                outputs=[voice_output]
            )
            
            # 修复 P2-1: 绑定分神提醒事件
            alert_trigger.change(
                fn=callbacks.get('on_alert_trigger', lambda *args: None),
                inputs=[alert_trigger, style_select],
                outputs=[alert_audio],
                queue=True
            )
            
        return demo, combined_js


# 示例用法
if __name__ == "__main__":
    # 示例回调函数
    def dummy_callback(*args, **kwargs):
        return "此功能正在开发中"
    
    example_callbacks = {
        'on_style_change': dummy_callback,
        'on_webcam_toggle': dummy_callback,
        'on_learning_mode_toggle': dummy_callback,
        'on_checkin_click': dummy_callback,
        'on_rest_click': dummy_callback,
        'on_reset_click': dummy_callback,
        'on_send_message': dummy_callback,
        'on_camera_frame': dummy_callback,
        'on_update_stats': dummy_callback,
        'on_refresh_achievements': dummy_callback
    }
    
    layout = UILayout()
    app = layout.create_main_layout(example_callbacks)
    app.launch()