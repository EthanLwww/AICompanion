#!/bin/bash

# 魔搭创空间一键部署脚本
# 使用方法: bash deploy.sh

set -e  # 遇到错误立即退出

echo "🚀 开始上传项目到魔搭创空间..."
echo "================================"

# 配置信息
REPO_URL="http://oauth2:ms-c113aab8-73f3-4626-a4fc-d257e37a76d5@www.modelscope.cn/studios/qzs123/repairtest.git"
TEMP_DIR="modelscope_upload_temp"

# Step 1: 克隆或更新创空间仓库
echo "📥 Step 1: 克隆魔搭创空间仓库..."
if [ -d "$TEMP_DIR" ]; then
    echo "  ↳ 仓库已存在，更新中..."
    cd "$TEMP_DIR"
    git pull origin main || git pull origin master
    cd ..
else
    echo "  ↳ 克隆新仓库..."
    git lfs install
    git clone "$REPO_URL" "$TEMP_DIR"
fi

# Step 2: 复制项目文件
echo ""
echo "📂 Step 2: 复制项目文件..."

# 创建目录结构
mkdir -p "$TEMP_DIR/config"
mkdir -p "$TEMP_DIR/ui"
mkdir -p "$TEMP_DIR/core"
mkdir -p "$TEMP_DIR/game"
mkdir -p "$TEMP_DIR/utils"
mkdir -p "$TEMP_DIR/static/js"

# 复制主文件
echo "  ↳ 复制主应用文件..."
cp "./app.py" "$TEMP_DIR/"
cp "./requirements.txt" "$TEMP_DIR/"
cp "./DEPLOYMENT_GUIDE.md" "$TEMP_DIR/"

# 复制模块文件
echo "  ↳ 复制配置和模块文件..."
cp config/*.py "$TEMP_DIR/config/" 2>/dev/null || true
cp ui/*.py "$TEMP_DIR/ui/" 2>/dev/null || true
cp core/*.py "$TEMP_DIR/core/" 2>/dev/null || true
cp game/*.py "$TEMP_DIR/game/" 2>/dev/null || true
cp utils/*.py "$TEMP_DIR/utils/" 2>/dev/null || true
cp static/js/*.js "$TEMP_DIR/static/js/" 2>/dev/null || true

# 复制 README 等文档
echo "  ↳ 复制文档文件..."
cp README.md "$TEMP_DIR/" 2>/dev/null || true
cp REPAIR_LOG.md "$TEMP_DIR/" 2>/dev/null || true

# Step 3: 提交并推送
echo ""
echo "📤 Step 3: 提交并推送到魔搭创空间..."
cd "$TEMP_DIR"

# 检查是否有更改
if git status --short | grep -q .; then
    echo "  ↳ 添加文件到 Git..."
    git add -A
    
    echo "  ↳ 提交更改..."
    git commit -m "Add AI Study Companion App - 完全修复版本 (P0+P1全部完成)"
    
    echo "  ↳ 推送到魔搭创空间..."
    git push -u origin main 2>/dev/null || git push -u origin master
    
    echo ""
    echo "✅ 上传成功！"
else
    echo "  ↳ 没有需要提交的更改"
    echo ""
    echo "⚠️  提示：文件已更新但没有变化，或已是最新版本"
fi

cd ..

# Step 4: 清理
echo ""
echo "🧹 清理临时文件..."
echo "  ↳ 临时仓库保留在: $TEMP_DIR"
echo ""

echo "================================"
echo "✨ 部署流程完成！"
echo ""
echo "📌 后续步骤："
echo "  1️⃣  登录魔搭创空间: https://www.modelscope.cn/studios"
echo "  2️⃣  进入你的创空间"
echo "  3️⃣  在\"设置\" → \"秘钥管理\"中添加环保变量:"
echo "      MODELSCOPE_API_KEY = 你的API_KEY"
echo "  4️⃣  等待 1-2 分钟自动部署"
echo "  5️⃣  点击\"App 预览\"测试应用"
echo ""
echo "🔗 相关文档: DEPLOYMENT_GUIDE.md"
echo ""
