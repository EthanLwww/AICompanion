# 魔搭创空间一键部署脚本 (Windows PowerShell)
# 使用方法: powershell -ExecutionPolicy Bypass -File deploy.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 开始上传项目到魔搭创空间..." -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# 配置信息
$REPO_URL = "http://oauth2:ms-c113aab8-73f3-4626-a4fc-d257e37a76d5@www.modelscope.cn/studios/qzs123/repairtest.git"
$TEMP_DIR = "modelscope_upload_temp"

# Step 1: 克隆或更新创空间仓库
Write-Host ""
Write-Host "📥 Step 1: 克隆魔搭创空间仓库..." -ForegroundColor Cyan
if (Test-Path $TEMP_DIR) {
    Write-Host "  ↳ 仓库已存在，更新中..." -ForegroundColor Gray
    Push-Location $TEMP_DIR
    git pull origin main 2>$null; if ($LASTEXITCODE -ne 0) { git pull origin master }
    Pop-Location
} else {
    Write-Host "  ↳ 克隆新仓库..." -ForegroundColor Gray
    git lfs install
    git clone $REPO_URL $TEMP_DIR
}

# Step 2: 复制项目文件
Write-Host ""
Write-Host "📂 Step 2: 复制项目文件..." -ForegroundColor Cyan

# 创建目录结构
@("config", "ui", "core", "game", "utils", "static/js") | ForEach-Object {
    New-Item -Path "$TEMP_DIR/$_" -ItemType Directory -Force | Out-Null
}

# 复制主文件
Write-Host "  ↳ 复制主应用文件..." -ForegroundColor Gray
Copy-Item "./app.py" "$TEMP_DIR/" -Force
Copy-Item "./requirements.txt" "$TEMP_DIR/" -Force
Copy-Item "./DEPLOYMENT_GUIDE.md" "$TEMP_DIR/" -Force

# 复制模块文件
Write-Host "  ↳ 复制配置和模块文件..." -ForegroundColor Gray
Copy-Item "config/*.py" "$TEMP_DIR/config/" -Force -ErrorAction SilentlyContinue
Copy-Item "ui/*.py" "$TEMP_DIR/ui/" -Force -ErrorAction SilentlyContinue
Copy-Item "core/*.py" "$TEMP_DIR/core/" -Force -ErrorAction SilentlyContinue
Copy-Item "game/*.py" "$TEMP_DIR/game/" -Force -ErrorAction SilentlyContinue
Copy-Item "utils/*.py" "$TEMP_DIR/utils/" -Force -ErrorAction SilentlyContinue
Copy-Item "static/js/*.js" "$TEMP_DIR/static/js/" -Force -ErrorAction SilentlyContinue

# 复制文档文件
Write-Host "  ↳ 复制文档文件..." -ForegroundColor Gray
Copy-Item "README.md" "$TEMP_DIR/" -Force -ErrorAction SilentlyContinue
Copy-Item "REPAIR_LOG.md" "$TEMP_DIR/" -Force -ErrorAction SilentlyContinue

# Step 3: 提交并推送
Write-Host ""
Write-Host "📤 Step 3: 提交并推送到魔搭创空间..." -ForegroundColor Cyan
Push-Location $TEMP_DIR

# 检查是否有更改
$status = git status --short
if ($status) {
    Write-Host "  ↳ 添加文件到 Git..." -ForegroundColor Gray
    git add -A
    
    Write-Host "  ↳ 提交更改..." -ForegroundColor Gray
    git commit -m "Add AI Study Companion App - 完全修复版本 (P0+P1全部完成)"
    
    Write-Host "  ↳ 推送到魔搭创空间..." -ForegroundColor Gray
    git push -u origin main 2>$null; 
    if ($LASTEXITCODE -ne 0) { 
        git push -u origin master 
    }
    
    Write-Host ""
    Write-Host "✅ 上传成功！" -ForegroundColor Green
} else {
    Write-Host "  ↳ 没有需要提交的更改" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "⚠️  提示：文件已更新但没有变化，或已是最新版本" -ForegroundColor Yellow
}

Pop-Location

# Step 4: 完成提示
Write-Host ""
Write-Host "🧹 清理临时文件..." -ForegroundColor Cyan
Write-Host "  ↳ 临时仓库保留在: $TEMP_DIR" -ForegroundColor Gray
Write-Host ""

Write-Host "================================" -ForegroundColor Green
Write-Host "✨ 部署流程完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📌 后续步骤：" -ForegroundColor Yellow
Write-Host "  1️⃣  登录魔搭创空间: https://www.modelscope.cn/studios" -ForegroundColor White
Write-Host "  2️⃣  进入你的创空间" -ForegroundColor White
Write-Host "  3️⃣  在'设置' → '秘钥管理'中添加环保变量:" -ForegroundColor White
Write-Host "      MODELSCOPE_API_KEY = 你的API_KEY" -ForegroundColor White
Write-Host "  4️⃣  等待 1-2 分钟自动部署" -ForegroundColor White
Write-Host "  5️⃣  点击'App 预览'测试应用" -ForegroundColor White
Write-Host ""
Write-Host "🔗 相关文档: DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
