import os
import json
import requests
import time
from typing import List, Dict, Optional, Generator
from config.settings import (
    MODELSCOPE_API_KEY, 
    MODELSCOPE_API_URL, 
    CHAT_MODEL_ID, 
    VISION_MODEL_ID,
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
        
    def analyze_screen_state(self, base64_image: str) -> Dict:
        """
        使用多模态模型分析屏幕截图状态（测试增强版）
        """
        import time
        from datetime import datetime
        
        start_time = time.time()
        logger.info(f"[VISION_AI] 🔍 开始分析屏幕状态")
        logger.debug(f"[VISION_AI] Requesting Vision AI analysis using model: {VISION_MODEL_ID}")
        
        # 【TEST_ENHANCEMENT】记录输入数据详情
        image_size = len(base64_image) if base64_image else 0
        logger.info(f"[VISION_AI] 📥 输入数据详情:")
        logger.info(f"  ├─ Base64数据大小: {image_size} 字节")
        logger.info(f"  ├─ 估算图片大小: {image_size * 0.75 / 1024:.1f} KB (理论)")
        logger.info(f"  ├─ 接收时间: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        logger.info(f"  └─ 数据完整性: {'✓' if image_size > 0 else '✗'}")
        
        # 【TEST_ENHANCEMENT】构建多模态消息内容（增强版）
        system_prompt = "你是一个专注力监测助手。请分析这张屏幕截图，判断用户是在'学习'还是在'娱乐'。只需返回 JSON 格式结果：{\"status\": \"learning\"|\"distracted\", \"reason\": \"具体行为描述\", \"confidence\": 0-1}"
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请分析当前用户的桌面状态。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        logger.debug(f"[VISION_AI] 📝 请求消息构建完成")
        logger.debug(f"[VISION_AI]   ├─ 系统提示词长度: {len(system_prompt)} 字符")
        logger.debug(f"[VISION_AI]   └─ 用户消息数量: {len(messages[1]['content'])} 项")
        
        headers = {
            "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": VISION_MODEL_ID,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,  # 降低随机性提高一致性
            "max_tokens": 200
        }
        
        logger.info(f"[VISION_AI] 🚀 API请求准备完成:")
        logger.info(f"  ├─ 模型ID: {VISION_MODEL_ID}")
        logger.info(f"  ├─ 请求参数: temperature={payload['temperature']}, max_tokens={payload['max_tokens']}")
        logger.info(f"  └─ Payload大小: {len(str(payload))} 字符")
        
        try:
            api_start_time = time.time()
            response = requests.post(
                MODELSCOPE_API_URL,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            api_duration = time.time() - api_start_time
            
            logger.info(f"[VISION_AI] 📡 API响应详情:")
            logger.info(f"  ├─ HTTP状态码: {response.status_code}")
            logger.info(f"  ├─ API响应时间: {api_duration:.2f}秒")
            logger.info(f"  ├─ 响应头大小: {len(str(response.headers))} 字符")
            logger.info(f"  └─ 响应内容长度: {len(response.text)} 字符")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                total_duration = time.time() - start_time
                
                logger.info(f"[VISION_AI] 📊 分析结果:")
                logger.info(f"  ├─ 原始响应: {content[:200]}{'...' if len(content) > 200 else ''}")
                logger.info(f"  ├─ 响应长度: {len(content)} 字符")
                logger.info(f"  ├─ 总处理时间: {total_duration:.2f}秒")
                logger.info(f"  └─ API调用时间: {api_duration:.2f}秒")
                
                # 【TEST_ENHANCEMENT】解析 JSON
                try:
                    # 处理可能的 markdown 代码块包裹
                    original_content = content
                    if content.startswith("```"):
                        content = content.split("```json")[-1].split("```")[0].strip()
                        logger.debug(f"[VISION_AI] 🧹 检测到Markdown代码块，已清理")
                        logger.debug(f"[VISION_AI]   ├─ 原始内容长度: {len(original_content)} 字符")
                        logger.debug(f"[VISION_AI]   └─ 清理后长度: {len(content)} 字符")
                    
                    parsed_result = json.loads(content)
                    logger.info(f"[VISION_AI] ✅ 解析成功:")
                    logger.info(f"  ├─ 状态: {parsed_result.get('status', 'unknown')}")
                    logger.info(f"  ├─ 原因: {parsed_result.get('reason', 'N/A')}")
                    logger.info(f"  ├─ 置信度: {parsed_result.get('confidence', 'N/A')}")
                    logger.info(f"  └─ 解析耗时: {time.time() - api_start_time - api_duration:.3f}秒")
                    
                    return parsed_result
                except Exception as e:
                    logger.error(f"[VISION_AI] ❌ JSON 解析失败:")
                    logger.error(f"  ├─ 错误类型: {type(e).__name__}")
                    logger.error(f"  ├─ 错误信息: {str(e)}")
                    logger.error(f"  ├─ 原始文本长度: {len(content) if 'content' in locals() else 'N/A'} 字符")
                    logger.error(f"  └─ 原始文本预览: {content[:100] if 'content' in locals() else 'N/A'}")
                    return {"status": "unknown", "reason": f"解析失败: {str(e)}", "raw_content": content[:200] if 'content' in locals() else ""}
            else:
                logger.error(f"[VISION_AI] ❌ API 请求失败:")
                logger.error(f"  ├─ 状态码: {response.status_code}")
                logger.error(f"  ├─ 响应头: {dict(list(response.headers.items())[:3])}")  # 只显示前3个header
                logger.error(f"  └─ 响应内容预览: {response.text[:200]}")
                return {"status": "unknown", "reason": f"API错误: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            logger.error(f"[VISION_AI] ⏱️ API请求超时 ({API_TIMEOUT}秒)")
            return {"status": "unknown", "reason": f"请求超时 ({API_TIMEOUT}秒)"}
        except requests.exceptions.RequestException as e:
            logger.error(f"[VISION_AI] 🌐 网络请求异常:")
            logger.error(f"  ├─ 异常类型: {type(e).__name__}")
            logger.error(f"  └─ 异常信息: {str(e)}")
            return {"status": "unknown", "reason": f"网络错误: {str(e)}"}
        except Exception as e:
            logger.error(f"[VISION_AI] ❗ 未知异常:")
            logger.error(f"  ├─ 异常类型: {type(e).__name__}")
            logger.error(f"  ├─ 异常信息: {str(e)}")
            logger.exception("完整异常堆栈:")  # 记录完整堆栈
            return {"status": "unknown", "reason": f"未知错误: {str(e)}"}