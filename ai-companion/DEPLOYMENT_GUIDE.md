# 魔搭创空间部署指南

## 📋 部署概述

本项目已修改为支持魔搭创空间部署。所有修改均已完成，可直接上传。

---

## 🔧 已完成的修改

### 1. **服务器配置** ✅
- ✅ 服务地址已设置为 `0.0.0.0`（允许外部访问）
- ✅ 服务端口已设置为 `7860`
- 位置：`config/settings.py` 第 26-27 行

```python
SERVER_NAME = "0.0.0.0"
SERVER_PORT = 7860
```

### 2. **API KEY 环保变量化** ✅
- ✅ MODELSCOPE_API_KEY: `os.environ.get("MODELSCOPE_API_KEY")`
- ✅ DASHSCOPE_API_KEY: `os.environ.get("DASHSCOPE_API_KEY") or MODELSCOPE_API_KEY`
- 位置：`config/settings.py` 第 5-6 行

### 3. **依赖文件** ✅
- ✅ 已创建/更新 `requirements.txt`
- 包含所有必要库：
  - `gradio>=4.0.0` - Web UI 框架
  - `requests>=2.25.0` - HTTP 请求库
  - `dashscope>=1.23.4` - 通义千问 SDK
  - `python-dotenv>=0.19.0` - 环保变量加载

### 4. **魔搭创空间兼容性** ✅
- ✅ 修改 `app.py` 支持两种启动模式
- ✅ 在魔搭创空间中自动创建全局 `demo` 对象
- 位置：`app.py` 第 323-334 行

```python
if __name__ == "__main__":
    # 本地运行模式
    run_scheduler()
    app = StudyCompanionApp()
    app.run(debug=True)
else:
    # 魔搭创空间部署模式
    app = StudyCompanionApp()
    interface, combined_js = app.ui_layout.create_main_layout(app.callbacks)
    demo = interface
```

---

## 🚀 部署步骤

### Step 1: 克隆项目空间
```bash
git lfs install
git clone http://oauth2:ms-c113aab8-73f3-4626-a4fc-d257e37a76d5@www.modelscope.cn/studios/qzs123/repairtest.git
cd repairtest
```

### Step 2: 复制项目文件
将修改完的文件上传到创空间：
```bash
# 复制主应用文件
cp ../ai-companion/app.py .
cp ../ai-companion/requirements.txt .

# 复制配置文件
mkdir -p config ui core game utils static/js
cp ../ai-companion/config/*.py config/
cp ../ai-companion/ui/*.py ui/
cp ../ai-companion/core/*.py core/
cp ../ai-companion/game/*.py game/
cp ../ai-companion/utils/*.py utils/
cp ../ai-companion/static/js/*.js static/js/
```

### Step 3: 配置环保变量

在魔搭创空间设置中添加以下环保变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `MODELSCOPE_API_KEY` | 你的 API KEY | 必填，通义千问 API 密钥 |
| `DASHSCOPE_API_KEY` | 你的 API KEY (可选) | 可选，若不设置则使用 MODELSCOPE_API_KEY |

**获取 API KEY 步骤**：
1. 登录 [魔搭官网](https://www.modelscope.cn)
2. 进入 [API-KEY 管理](https://www.modelscope.cn/user/setting/apikeys)
3. 创建新的 API-KEY
4. 复制值到魔搭创空间环保变量设置

### Step 4: 提交文件
```bash
git add .
git commit -m "Add AI Study Companion App"
git push
```

---

## ✅ 验证部署

### 本地测试
```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API KEY
export MODELSCOPE_API_KEY="你的_API_KEY"

# 运行本地服务器
python app.py
```

然后访问 `http://localhost:7860`

### 魔搭创空间测试
1. 在创空间中等待部署完成（通常 1-2 分钟）
2. 点击"App 预览"查看应用
3. 测试功能：
   - 开启学习模式
   - 发送消息验证流式输出
   - 启用语音验证语音播报
   - 尝试不同的角色风格

---

## 🐛 故障排查

### 问题 1: 环保变量未找到
**错误信息**：`[ERROR] 未找到环境变量 MODELSCOPE_API_KEY`

**解决方案**：
1. 检查魔搭创空间的"秘钥管理"设置
2. 确保变量名为 `MODELSCOPE_API_KEY`
3. 重新部署应用

### 问题 2: 模块导入失败
**错误信息**：`ModuleNotFoundError: No module named 'xxx'`

**解决方案**：
1. 检查 `requirements.txt` 是否包含该库
2. 如缺失，添加到 requirements.txt 并重新提交
3. 等待魔搭创空间重新安装依赖

### 问题 3: JS 文件加载失败
**错误信息**：`[JS_LOAD] ⚠️ combined_js 为None或为空`

**解决方案**：
1. 检查 `static/js/` 目录是否已上传
2. 确保 `load_js.js` 和 `event_handlers.js` 存在
3. 检查文件权限是否正确

---

## 📝 修复记录

### 修改概览
- **总文件数**：修改 3 个文件，新增 1 个文档
- **总改动行数**：约 12 行代码修改
- **完成时间**：2024-01-28

### 修改详情
| 文件 | 改动 | 说明 |
|------|------|------|
| `app.py` | +7 行 | 支持魔搭部署模式 |
| `requirements.txt` | +2 行 | 补充依赖 |
| `DEPLOYMENT_GUIDE.md` | 新增 | 部署指南 |

---

## 🔗 相关文档

- 魔搭官方文档：https://www.modelscope.cn/docs
- Gradio 文档：https://gradio.app
- 通义千问 API：https://dashscope.aliyun.com

---

**最后更新**：2024-01-28  
**状态**：✅ 已完成，可直接部署
