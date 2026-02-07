#!/usr/bin/env python3
"""
🖥️ 屏幕监督功能快速诊断脚本
检查屏幕监督（Vision AI）功能的各个环节是否配置正确
"""

import os
import sys
import base64
import time

def print_section(title):
    """打印分隔符和标题"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def check_api_key():
    """检查 API KEY 配置"""
    print_section("1️⃣ MODELSCOPE API KEY 检查")
    
    api_key = os.environ.get("MODELSCOPE_API_KEY")
    
    if api_key:
        print(f"✅ MODELSCOPE_API_KEY 已设置")
        print(f"   值: {api_key[:10]}...{api_key[-5:]}")
        return True
    else:
        print(f"❌ MODELSCOPE_API_KEY 未设置")
        print(f"\n   设置方法:")
        print(f"   Windows PowerShell: $env:MODELSCOPE_API_KEY='your-key'")
        print(f"   Linux/Mac: export MODELSCOPE_API_KEY='your-key'")
        return False

def check_dependencies():
    """检查依赖安装"""
    print_section("2️⃣ 依赖检查")
    
    required = {
        "gradio": "Gradio UI 框架",
        "requests": "HTTP 请求库",
        "PIL": "Pillow 图像处理库 (用于调试验证)",
        "json": "JSON 解析库"
    }
    
    missing = []
    for module_name, description in required.items():
        try:
            __import__(module_name)
            print(f"✅ {module_name:<20} {description}")
        except ImportError:
            # Pillow 的导入名是 PIL
            if module_name == "PIL":
                print(f"❌ {module_name:<20} {description} (pip install Pillow)")
            else:
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
        "core/ai_agent.py": "AI 代理核心 (包含分析逻辑)",
        "app.py": "主应用 (包含回调处理)",
        "ui/layouts.py": "UI 布局 (包含触发器)",
        "static/js/event_handlers.js": "前端逻辑 (包含截屏回传)",
        "config/settings.py": "配置文件"
    }
    
    all_exists = True
    for file_path, description in files_to_check.items():
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path:<30} ({size:>6} bytes) {description}")
        else:
            print(f"❌ {file_path:<30} 缺失! {description}")
            all_exists = False
    
    return all_exists

def check_config():
    """检查配置文件"""
    print_section("4️⃣ 配置检查")
    
    try:
        from config.settings import MODELSCOPE_API_KEY, VISION_MODEL_ID, MODELSCOPE_API_URL
        
        print(f"✅ 配置加载成功")
        print(f"   VISION_MODEL_ID: {VISION_MODEL_ID}")
        print(f"   MODELSCOPE_API_URL: {MODELSCOPE_API_URL}")
        print(f"   API_KEY 状态: {'已加载' if MODELSCOPE_API_KEY else '未加载'}")
        
        return bool(MODELSCOPE_API_KEY)
    except Exception as e:
        print(f"❌ 配置加载失败: {str(e)}")
        return False

def diagnose_vision_ai():
    """诊断 Vision AI 功能"""
    print_section("5️⃣ Vision AI 功能诊断")
    
    try:
        from core.ai_agent import AIAgent
        from config.settings import MODELSCOPE_API_KEY, VISION_MODEL_ID
        
        if not MODELSCOPE_API_KEY:
            print("⚠️ API KEY 未设置，无法进行端到端测试")
            return False
            
        print(f"正在准备测试数据 (模型: {VISION_MODEL_ID})...")
        
        # 创建一个极小的黑色 1x1 像素图片的 Base64 数据作为测试
        # 这是一个透明的 1x1 像素 PNG
        dummy_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        print("正在初始化 AIAgent...")
        agent = AIAgent()
        
        print(f"\n🚀 正在发送分析请求到 ModelScope...")
        print(f"   [调试信息] 待传输数据大小: {len(dummy_base64)} 字节")
        
        start_time = time.time()
        result = agent.analyze_screen_state(dummy_base64)
        duration = time.time() - start_time
        
        print(f"\n📡 响应详情 (耗时: {duration:.2f}秒):")
        if result:
            print(f"✅ 后端分析调用成功")
            print(f"   ├─ 状态 (Status): {result.get('status', 'N/A')}")
            print(f"   ├─ 原因 (Reason): {result.get('reason', 'N/A')}")
            print(f"   └─ 置信度 (Confidence): {result.get('confidence', 'N/A')}")
            
            if "status" in result:
                return True
        else:
            print("❌ 分析返回结果为空")
            return False
            
    except Exception as e:
        print(f"❌ Vision AI 诊断失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主诊断流程"""
    print("\n" + "🖥️  "*20)
    print("AI 学习陪伴助手 - 屏幕监督功能诊断工具")
    print("🖥️  "*20)
    
    results = {}
    
    # 执行各项检查
    results["API KEY"] = check_api_key()
    results["依赖"] = check_dependencies()
    results["文件"] = check_files()
    results["配置"] = check_config()
    results["功能测试"] = diagnose_vision_ai()
    
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
        print("\n🎉 屏幕监督功能环境配置正确！")
        print("\n运行日志说明:")
        print("  1. 前端日志: 在浏览器 F12 控制台搜索 '[SUPERVISION_DEBUG]'")
        print("  2. 后端日志: 在终端/创空间日志中搜索 '[SUPERVISION_DEBUG]' 或 '[VISION_AI]'")
        print("  3. 核心流向: captureAndSendFrame (JS) -> on_supervision_data_received (App) -> analyze_screen_state (Agent)")
    else:
        print(f"\n⚠️ 有 {total - passed} 项检查失败，请按提示修复后再测试应用")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
