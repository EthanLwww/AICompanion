import os
import json
import requests
import time
from typing import List, Dict, Optional, Generator
from config.settings import (
    MODELSCOPE_API_KEY, 
    MODELSCOPE_API_URL, 
    CHAT_MODEL_ID, 
    CHAT_TEMPERATURE, 
    CHAT_MAX_TOKENS, 
    API_TIMEOUT,
    HISTORY_LIMIT,
    STREAM_TIMEOUT
)
from config.constants import STYLE_PROMPTS
from utils.logger import logger


class AIAgent:
    """
    AI代理类，负责与AI模型通信和管理对话历史
    """
    
    def __init__(self):
        self.conversation_history = []
        self.current_style = "默认"
        
    def set_style(self, style: str):
        """设置AI角色风格"""
        self.current_style = style
        
    def get_system_prompt(self) -> str:
        """获取当前角色的系统提示词"""
        return STYLE_PROMPTS.get(self.current_style, STYLE_PROMPTS["默认"])
    
    def add_message(self, role: str, content: str):
        """向对话历史添加消息"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        # 限制对话历史长度
        if len(self.conversation_history) > HISTORY_LIMIT:
            self.conversation_history = self.conversation_history[-HISTORY_LIMIT:]
    
    def get_chat_response(self, user_input: str) -> str:
        """
        获取AI聊天响应
        """
        logger.debug(f"Requesting AI response for model: {CHAT_MODEL_ID}")
        # 添加用户输入到对话历史
        self.add_message("user", user_input)
        
        # 构建请求消息列表
        messages = []
        # 添加系统提示词作为第一条消息
        messages.append({"role": "system", "content": self.get_system_prompt()})
        # 添加历史对话
        messages.extend(self.conversation_history)
        
        # 发送请求到模型
        headers = {
            "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": CHAT_MODEL_ID,
            "messages": messages,
            "temperature": CHAT_TEMPERATURE,
            "max_tokens": CHAT_MAX_TOKENS
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                MODELSCOPE_API_URL,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            elapsed_time = time.time() - start_time
            logger.debug(f"AI Response received in {elapsed_time:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                assistant_reply = result['choices'][0]['message']['content']
                
                # 添加AI回复到对话历史
                self.add_message("assistant", assistant_reply)
                
                return assistant_reply
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                print(error_msg)
                return f"抱歉，我现在遇到了一些技术问题，请稍后再试。错误详情: {error_msg}"
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请稍后再试"
            print(error_msg)
            return error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            print(error_msg)
            return f"抱歉，网络连接出现问题，请检查网络后重试。错误详情: {error_msg}"
        except Exception as e:
            error_msg = f"发生未知错误: {str(e)}"
            print(error_msg)
            return f"抱歉，发生了意外错误。错误详情: {error_msg}"
    
    def get_alert_response(self, trigger_type: str) -> str:
        """
        获取系统主动提醒的响应
        trigger_type: "distracted" 或 "encourage"
        """
        # 创建提醒上下文
        if trigger_type == "distracted":
            reminder_context = "系统检测到用户可能走神了，请发送一句简短的提醒语来帮助用户重新集中注意力。"
        elif trigger_type == "encourage":
            reminder_context = "系统检测到用户可能情绪低落，请发送一句温暖的鼓励语来激励用户。"
        else:
            reminder_context = "请发送一句支持用户的话语。"
        
        # 构建请求消息
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": reminder_context}
        ]
        
        headers = {
            "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": CHAT_MODEL_ID,
            "messages": messages,
            "temperature": CHAT_TEMPERATURE,
            "max_tokens": 100  # 提醒语通常较短
        }
        
        try:
            response = requests.post(
                MODELSCOPE_API_URL,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                print(f"提醒API请求失败: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"获取提醒响应时发生错误: {e}")
            return ""
    
    def get_chat_response_stream(self, user_input: str) -> Generator[str, None, None]:
        """
        获取AI聊天响应（流式版本）
        使用生成器实现逐字输出
        """
        logger.debug(f"Requesting streaming AI response for model: {CHAT_MODEL_ID}")
        # 添加用户输入到对话历史
        self.add_message("user", user_input)
        
        # 构建请求消息列表
        messages = []
        # 添加系统提示词作为第一条消息
        messages.append({"role": "system", "content": self.get_system_prompt()})
        # 添加历史对话
        messages.extend(self.conversation_history)
        
        # 发送请求到模型
        headers = {
            "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": CHAT_MODEL_ID,
            "messages": messages,
            "temperature": CHAT_TEMPERATURE,
            "max_tokens": CHAT_MAX_TOKENS,
            "stream": True  # 启用流式输出
        }
        
        start_time = time.time()
        full_response = ""  # 用于累积完整回复
        
        try:
            response = requests.post(
                MODELSCOPE_API_URL,
                headers=headers,
                json=payload,
                timeout=STREAM_TIMEOUT,
                stream=True  # requests 库的流式响应
            )
            
            if response.status_code == 200:
                # 逐行处理流式响应
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        # SSE 格式: data: {...}
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
                                        full_response += content
                                        yield content  # 逐字返回
                            except json.JSONDecodeError:
                                continue
                
                # 流式输出完成后，添加完整回复到对话历史
                if full_response:
                    self.add_message("assistant", full_response)
                    elapsed_time = time.time() - start_time
                    logger.debug(f"Streaming AI Response completed in {elapsed_time:.2f}s, total length: {len(full_response)}")
            else:
                error_msg = f"API请求失败: {response.status_code}"
                logger.error(error_msg)
                yield error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请稍后再试"
            logger.error(error_msg)
            yield error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            yield f"抱歉，网络连接出现问题，请检查网络后重试。"
        except Exception as e:
            error_msg = f"发生未知错误: {str(e)}"
            logger.error(error_msg)
            yield f"抱歉，发生了意外错误。"
    
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []