import gradio as gr
from typing import Callable, Any, Dict
import json


class UIComponents:
    """
    UI组件类，定义应用的各种界面组件
    """
    
    def __init__(self):
        pass
    
    def create_sidebar_controls(self, callbacks: Dict[str, Callable]) -> gr.Blocks:
        """
        创建侧边栏控制面板
        """
        with gr.Accordion("设置面板", open=True):
            # 角色选择
            style_dropdown = gr.Dropdown(
                choices=["默认", "柔情猫娘", "成熟妈妈系御姐", "磁性霸道男总裁"],
                value="默认",
                label="AI角色风格",
                interactive=True
            )
            
            # 摄像头控制
            webcam_checkbox = gr.Checkbox(label="开启摄像头", value=False, interactive=True)
            
            # 学习模式控制
            learning_mode_checkbox = gr.Checkbox(label="开启学习模式", value=False, interactive=True)
            
            # 休息按钮
            rest_button = gr.Button("开始休息", interactive=False)
            
            # 签到按钮
            checkin_button = gr.Button("每日签到")
            
            # 重置对话按钮
            reset_button = gr.Button("重置对话")
        
        # 绑定回调函数
        style_dropdown.change(
            fn=callbacks.get("on_style_change", lambda x: None),
            inputs=[style_dropdown],
            outputs=[]
        )
        
        webcam_checkbox.change(
            fn=callbacks.get("on_webcam_toggle", lambda x: None),
            inputs=[webcam_checkbox],
            outputs=[]
        )
        
        learning_mode_checkbox.change(
            fn=callbacks.get("on_learning_mode_toggle", lambda x: None),
            inputs=[learning_mode_checkbox],
            outputs=[rest_button]
        )
        
        checkin_button.click(
            fn=callbacks.get("on_checkin_click", lambda: ("", "请先开启学习模式")),
            outputs=[gr.Textbox(visible=False), gr.Textbox()]
        )
        
        rest_button.click(
            fn=callbacks.get("on_rest_click", lambda: ("", "请先开启学习模式")),
            outputs=[gr.Textbox(visible=False), gr.Textbox()]
        )
        
        reset_button.click(
            fn=callbacks.get("on_reset_click", lambda: None),
            inputs=[],
            outputs=[]
        )
        
        return gr.Group([style_dropdown, webcam_checkbox, learning_mode_checkbox, rest_button, checkin_button, reset_button])
    
    def create_chat_interface(self, callbacks: Dict[str, Callable]) -> gr.Blocks:
        """
        创建聊天界面
        """
        with gr.Row():
            with gr.Column(scale=3):
                # 聊天历史显示
                chatbot = gr.Chatbot(
                    label="学习陪伴AI",
                    height=400
                )
                
                # 输入框和发送按钮
                with gr.Row():
                    user_input = gr.Textbox(
                        label="输入消息",
                        placeholder="输入您的问题...",
                        container=False
                    )
                    send_button = gr.Button("发送", variant="primary")
                
                # 用户输入回车发送
                user_input.submit(
                    fn=callbacks.get("on_send_message", lambda x, y: ([], "请先开启学习模式")),
                    inputs=[user_input, chatbot],
                    outputs=[chatbot, gr.Textbox(visible=False)]
                ).then(
                    fn=lambda: None,
                    inputs=[],
                    outputs=[user_input]
                )
                
                # 点击发送按钮
                send_button.click(
                    fn=callbacks.get("on_send_message", lambda x, y: ([], "请先开启学习模式")),
                    inputs=[user_input, chatbot],
                    outputs=[chatbot, gr.Textbox(visible=False)],
                    queue=True
                ).then(
                    fn=lambda: None,
                    inputs=[],
                    outputs=[user_input]
                )
        
        return gr.Group([chatbot, user_input, send_button])
    
    def create_stats_panel(self, callbacks: Dict[str, Callable]) -> gr.Blocks:
        """
        创建统计面板
        """
        with gr.Accordion("学习统计", open=False):
            with gr.Row():
                with gr.Column():
                    points_display = gr.Number(label="积分", value=0)
                    level_display = gr.Number(label="等级", value=1)
                    total_study_time = gr.Number(label="总学习时间(分钟)", value=0)
                
                with gr.Column():
                    today_study_time = gr.Number(label="今日学习(分钟)", value=0)
                    consecutive_days = gr.Number(label="连续签到天数", value=0)
                    achievements_count = gr.Number(label="成就数量", value=0)
        
        # 更新统计信息的按钮
        update_stats_btn = gr.Button("更新统计", visible=False)
        update_stats_btn.click(
            fn=callbacks.get("on_update_stats", lambda: (0, 1, 0, 0, 0, 0)),
            inputs=[],
            outputs=[points_display, level_display, total_study_time, 
                    today_study_time, consecutive_days, achievements_count]
        )
        
        return gr.Group([
            points_display, level_display, total_study_time,
            today_study_time, consecutive_days, achievements_count, 
            update_stats_btn
        ])
    
    def create_camera_feed(self, callbacks: Dict[str, Callable]) -> gr.Blocks:
        """
        创建摄像头画面显示
        """
        with gr.Group():
            gr.Markdown("## 📷 实时摄像头画面")
            camera_output = gr.Image(
                label="摄像头画面",
                sources=['webcam'],
                streaming=True,
                height=300
            )
            
            # 实时处理摄像头画面
            camera_output.stream(
                fn=callbacks.get("on_camera_frame", lambda x: x),
                inputs=[camera_output],
                outputs=[camera_output]
            )
        
        return camera_output
    
    def create_achievements_panel(self, callbacks: Dict[str, Callable]) -> gr.Blocks:
        """
        创建成就面板
        """
        with gr.Accordion("成就系统", open=False):
            achievements_list = gr.JSON(label="成就列表")
            
            refresh_achievements_btn = gr.Button("刷新成就")
            refresh_achievements_btn.click(
                fn=callbacks.get("on_refresh_achievements", lambda: {}),
                inputs=[],
                outputs=[achievements_list]
            )
        
        return gr.Group([achievements_list, refresh_achievements_btn])
    
    def create_notification_area(self) -> gr.Blocks:
        """
        创建通知区域
        """
        notification = gr.Textbox(
            label="系统通知",
            interactive=False,
            visible=True,
            value="欢迎使用学习陪伴AI！请选择角色并开启学习模式开始体验。"
        )
        return notification