#!/usr/bin/env python3
"""
🎤 语音功能快速诊断脚本
检查语音功能的各个环节是否配置正确
"""

import os
import sys

def print_section(title):
    """打印分隔符和标题"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def check_api_key():
    """检查 API KEY 配置"""
    print_section("1️⃣ DASHSCOPE API KEY 检查")
    
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    
    if api_key:
        print(f"✅ API KEY 已设置")
        print(f"   值: {api_key[:10]}...{api_key[-5:]}")
        return True
    else:
        print(f"❌ API KEY 未设置")
        print(f"\n   设置方法:")
        print(f"   Windows PowerShell: $env:DASHSCOPE_API_KEY='your-key'")
        print(f"   Windows CMD: set DASHSCOPE_API_KEY=your-key")
        print(f"   Linux/Mac: export DASHSCOPE_API_KEY='your-key'")
        return False

def check_dependencies():
    """检查依赖安装"""
    print_section("2️⃣ 依赖检查")
    
    required = {
        "gradio": "Gradio UI 框架",
        "requests": "HTTP 请求库",
        "dashscope": "阿里云 DashScope SDK",
        "python_dotenv": "环境变量加载"
    }
    
    missing = []
    for module_name, description in required.items():
        try:
            if module_name == "python_dotenv":
                __import__("dotenv")
            else:
                __import__(module_name)
            print(f"✅ {module_name:<20} {description}")
        except ImportError:
            print(f"❌ {module_name:<20} {description}")
            missing.append(module_name)
    
    if missing:
        print(f"\n   缺失的包: {', '.join(missing)}")
        print(f"   安装命令: pip install -r requirements.txt")
        return False
    return True

def check_files():
    """检查关键文件"""
    print_section("3️⃣ 关键文件检查")
    
    files_to_check = {
        "core/tts_manager.py": "TTS 管理器",
        "core/chat_manager.py": "聊天管理器",
        "app.py": "主应用",
        "ui/layouts.py": "UI 布局",
        "config/settings.py": "配置文件",
        "utils/logger.py": "日志工具"
    }
    
    all_exists = True
    for file_path, description in files_to_check.items():
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path:<25} ({size:>6} bytes) {description}")
        else:
            print(f"❌ {file_path:<25} 缺失! {description}")
            all_exists = False
    
    return all_exists

def check_config():
    """检查配置文件"""
    print_section("4️⃣ 配置检查")
    
    try:
        from config.settings import DASHSCOPE_API_KEY, TTS_MODEL_ID
        
        print(f"✅ 配置加载成功")
        print(f"   TTS_MODEL_ID: {TTS_MODEL_ID}")
        print(f"   DASHSCOPE_API_KEY: {'已设置' if DASHSCOPE_API_KEY else '未设置'}")
        
        return bool(DASHSCOPE_API_KEY)
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        return False

def check_logger():
    """检查日志配置"""
    print_section("5️⃣ 日志配置检查")
    
    try:
        from utils.logger import logger
        
        print(f"✅ 日志模块加载成功")
        print(f"   测试输出:")
        
        # 测试各个日志级别
        logger.debug("[TEST] 这是 DEBUG 级别")
        logger.info("[TEST] 这是 INFO 级别")
        logger.warning("[TEST] 这是 WARNING 级别")
        
        return True
    except Exception as e:
        print(f"❌ 日志模块加载失败: {str(e)}")
        return False

def diagnose_tts():
    """诊断 TTS 功能"""
    print_section("6️⃣ TTS 功能诊断")
    
    try:
        from core.tts_manager import TTSManager
        from config.settings import DASHSCOPE_API_KEY
        
        if not DASHSCOPE_API_KEY:
            print("⚠️ API KEY 未设置，无法测试 TTS")
            return False
        
        print("正在初始化 TTSManager...")
        tts = TTSManager()
        
        print("✅ TTSManager 初始化成功")
        
        print("\n正在测试语音合成（文本: '你好'）...")
        audio_bytes = tts.synthesize_speech("你好")
        
        if audio_bytes:
            print(f"✅ 语音合成成功")
            print(f"   数据大小: {len(audio_bytes)} bytes")
            print(f"   格式: ", end="")
            
            if audio_bytes.startswith(b'RIFF'):
                print("WAV ✅")
            elif audio_bytes.startswith(b'ID3') or audio_bytes.startswith(b'\xff\xfb'):
                print("MP3 ✅")
            else:
                print(f"未知 ({audio_bytes[:4]})")
            
            return True
        else:
            print("❌ 语音合成返回空数据")
            return False
            
    except Exception as e:
        print(f"❌ TTS 诊断失败: {str(e)}")
        return False

def main():
    """主诊断流程"""
    print("\n" + "🎤 "*20)
    print("AI 学习陪伴助手 - 语音功能诊断工具")
    print("🎤 "*20)
    
    results = {}
    
    # 执行各项检查
    results["API KEY"] = check_api_key()
    results["依赖"] = check_dependencies()
    results["文件"] = check_files()
    results["配置"] = check_config()
    results["日志"] = check_logger()
    results["TTS"] = diagnose_tts()
    
    # 生成报告
    print_section("📋 诊断报告摘要")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n检查项目 ({passed}/{total} 通过):")
    print("-" * 40)
    
    for check_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {check_name:<15} {status}")
    
    print("\n" + "-" * 40)
    
    if passed == total:
        print("\n🎉 所有检查都通过！语音功能应该可以正常工作。")
        print("\n下一步:")
        print("  1. 运行应用: python app.py")
        print("  2. 在 UI 中勾选'🎵 开启语音'")
        print("  3. 发送一条消息并聆听语音回复")
    else:
        print(f"\n⚠️ 有 {total - passed} 项检查失败，请按上述提示修复")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
