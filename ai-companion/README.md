# AI学习陪伴助手

一个智能化的学习陪伴应用，结合AI对话、语音合成、人脸识别和游戏化学习功能，为用户提供全方位的学习陪伴体验。

## 项目结构

```
ai-companion/
├── app.py                 # 应用入口点
├── requirements.txt       # 项目依赖
├── config/
│   ├── __init__.py
│   ├── settings.py        # 配置管理
│   └── constants.py       # 常量定义
├── core/
│   ├── __init__.py
│   ├── ai_agent.py        # AI代理核心逻辑
│   ├── face_detector.py   # 人脸识别模块
│   ├── tts_manager.py     # 文字转语音管理
│   └── chat_manager.py    # 聊天管理
├── game/
│   ├── __init__.py
│   ├── stats_tracker.py   # 学习统计追踪
│   ├── achievements.py    # 成就系统
│   └── leveling_system.py # 等级系统
├── ui/
│   ├── __init__.py
│   ├── components.py      # Gradio界面组件
│   └── layouts.py         # 界面布局
├── utils/
│   ├── __init__.py
│   ├── helpers.py         # 辅助函数
│   └── validators.py      # 数据验证
└── static/
    ├── js/
    │   └── face-api.js    # 前端人脸识别脚本
    └── css/
        └── styles.css     # 样式文件
```

## 功能特性

1. **AI对话系统** - 支持多种角色风格的智能对话
2. **语音合成** - 为文本回复提供语音输出
3. **人脸识别** - 实时监测用户学习状态
4. **游戏化学习** - 积分、等级、成就系统激励学习
5. **学习统计** - 详细的学习数据分析和可视化

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置环境变量：
```bash
export MODELSCOPE_API_KEY="your_api_key_here"
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
```

3. 运行应用：
```bash
python app.py
```

## 模块说明

### Core 模块
- `ai_agent.py`: 管理AI模型交互和对话历史
- `tts_manager.py`: 处理文字转语音功能
- `chat_manager.py`: 协调AI和TTS模块的工作

### Game 模块
- `stats_tracker.py`: 跟踪学习统计数据
- `achievements.py`: 管理成就系统

### Config 模块
- `settings.py`: 应用配置参数
- `constants.py`: 常量定义（角色提示词、成就配置等）

## 设计原则

1. **模块化设计** - 各功能模块独立，便于维护和扩展
2. **配置驱动** - 通过配置文件管理应用行为
3. **可扩展性** - 易于添加新功能和角色
4. **用户体验** - 提供直观的界面和流畅的交互