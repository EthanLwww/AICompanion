import gradio as gr
from .components import UIComponents
from .assets import (
    CUSTOM_CSS, CUSTOM_HTML, HEADER_HTML, 
    USER_STATS_HTML, STUDY_CENTER_HTML, ACHIEVEMENTS_HTML,
    REPORT_BUTTON_HTML, DATA_DASHBOARD_HTML, WEEKLY_REPORT_MODAL_HTML
)


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
        # 尝试加载 JS 文件
        load_js_content = None
        event_handlers_js = None
        try:
            import os
            # 加载 LOAD_JS (Step 3)
            js_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'load_js.js')
            if os.path.exists(js_path):
                with open(js_path, 'r', encoding='utf-8') as f:
                    load_js_content = f.read()
            
            # 加载事件处理器 JS (Step 4)
            event_handlers_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'js', 'event_handlers.js')
            if os.path.exists(event_handlers_path):
                with open(event_handlers_path, 'r', encoding='utf-8') as f:
                    event_handlers_js = f.read()
        except Exception as e:
            print(f"警告：无法加载 JS 文件: {e}")
        
        # 合并两个 JS 文件内容
        combined_js = ""
        if load_js_content:
            combined_js += load_js_content
        if event_handlers_js:
            combined_js += "\n\n" + event_handlers_js
        
        # 【调试】打印 combined_js 状态
        print(f"[DEBUG-LAYOUT] combined_js 长度: {len(combined_js) if combined_js else 0}")
        if combined_js:
            print(f"[DEBUG-LAYOUT] combined_js 前 100 字符: {combined_js[:100]}")
            print(f"[DEBUG-LAYOUT] combined_js 后 100 字符: {combined_js[-100:]}")
        else:
            print("[DEBUG-LAYOUT] ⚠️ WARNING: combined_js 为空！")
        
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
                    with gr.Accordion("🏅 个人成就与签到", open=False, elem_id="medal-accordion"):
                        gr.HTML(ACHIEVEMENTS_HTML)
                    
                    # 快捷工具（重构为原生组件以提高稳定性）
                    with gr.Accordion("⚡ 快捷工具", open=True):
                        with gr.Row():
                            advice_btn = gr.Button("📚 学习建议", variant="secondary", size="sm", elem_classes=["quick-btn"])
                            plan_btn = gr.Button("📋 制定计划", variant="secondary", size="sm", elem_classes=["quick-btn"])
                        with gr.Row():
                            encourage_btn = gr.Button("💪 鼓励我", variant="secondary", size="sm", elem_classes=["quick-btn"])
                            clear_btn = gr.Button("🗑️ 清空对话", variant="stop", size="sm", elem_classes=["quick-btn"])
                                            
                        # 【修复 Phase 3】功能按针（签到、休息、重置）
                        with gr.Row():
                            checkin_button = gr.Button("🗣️ 每日签到", variant="primary", size="sm")
                            rest_button = gr.Button("🌙 开始休息", variant="secondary", size="sm", interactive=False)
                            reset_button = gr.Button("🔄 重置对话", variant="secondary", size="sm")
                    
                    # 报告按钮
                    gr.HTML(REPORT_BUTTON_HTML)
                
                # 右侧栏：对话与数据
                with gr.Column(scale=2):
                    # 数据面板（可折叠）
                    with gr.Accordion("📊 学习数据概览", open=False):
                        gr.HTML(DATA_DASHBOARD_HTML)
                        
                        # 【修复 Phase 4】隐藏的统计更新触发器（为消息发送后更新统计数据供准备）
                        stats_update_trigger = gr.Textbox(visible=False, elem_id="stats-update-trigger")
                        
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
                        
                        # 【修复 Phase 1】学习模式控制复选框
                        learning_mode_checkbox = gr.Checkbox(
                            label="📚 开启学习模式",
                            value=False,
                            interactive=True,
                            elem_id="learning-mode-checkbox"
                        )
                        
                        # 走神语音提醒触发链路 (使用 CSS 隐藏而非 visible=False，确保 DOM 存在)
                        alert_trigger = gr.Textbox(visible=True, elem_id="alert-trigger", elem_classes=["hidden-component"])
                        alert_audio = gr.Audio(visible=True, autoplay=True, elem_id="alert-audio", elem_classes=["hidden-component"])
                    
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
                    
                    # 初始隐藏播放器和调试信息
                    voice_output = gr.Audio(
                        label="🔊 语音播报",
                        autoplay=False,
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
                        
            # 隐藏元素用于后台操作
            hidden_trigger = gr.Textbox(visible=False)
                        
            # 【编变】绑定回调函数
            # 绑定发送消息事件
            send_btn.click(
                fn=callbacks.get('on_send_message', lambda *args: ([], "消息发送失败")),
                inputs=[msg, chatbot],
                outputs=[chatbot, msg],
                queue=True
            )
            msg.submit(
                fn=callbacks.get('on_send_message', lambda *args: ([], "消息发送失败")),
                inputs=[msg, chatbot],
                outputs=[chatbot, msg],
                queue=True
            )
            
            
            # 【修复 Phase 3】绑定功能按针回调
            checkin_button.click(
                fn=callbacks.get('on_checkin_click', lambda: ("", "请先开启学习模式")),
                outputs=[gr.Textbox(visible=False), gr.Textbox()]
            )
            
            rest_button.click(
                fn=callbacks.get('on_rest_click', lambda: ("", "请先开启学习模式")),
                outputs=[gr.Textbox(visible=False), gr.Textbox()]
            )
            
            reset_button.click(
                fn=callbacks.get('on_reset_click', lambda: None),
                inputs=[],
                outputs=[]
            )
            learning_mode_checkbox.change(
                fn=callbacks.get('on_learning_mode_toggle', lambda x: None),
                inputs=[learning_mode_checkbox],
                outputs=[]
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