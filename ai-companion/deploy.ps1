# 魔搭创空间一键部署脚本 (Windows PowerShell)
# 使用方法: powershell -ExecutionPolicy Bypass -File deploy.ps1

$ErrorActionPreference = "Continue"

Write-Host "Starting deployment to ModelScope..." -ForegroundColor Green

# Config
$REPO_URL = "http://oauth2:ms-c113aab8-73f3-4626-a4fc-d257e37a76d5@www.modelscope.cn/studios/CNYZTEAM/companion_screenshare_test.git"
$TEMP_DIR = "modelscope_upload_temp"

# Step 1: Clone or Update
Write-Host "Step 1: Cloning/Updating repository..." -ForegroundColor Cyan
if (Test-Path $TEMP_DIR) {
    Write-Host "  Updating existing repository..." -ForegroundColor Gray
    Push-Location $TEMP_DIR
    git pull origin main 2>$null; if ($LASTEXITCODE -ne 0) { git pull origin master }
    Pop-Location
} else {
    Write-Host "  Cloning new repository..." -ForegroundColor Gray
    git lfs install
    git clone $REPO_URL $TEMP_DIR
}

# Step 2: Copy Files
Write-Host "Step 2: Copying files..." -ForegroundColor Cyan
@("config", "ui", "core", "game", "utils", "static/js") | ForEach-Object {
    New-Item -Path "$TEMP_DIR/$_" -ItemType Directory -Force | Out-Null
}

Copy-Item "./app.py" "$TEMP_DIR/" -Force
Copy-Item "./requirements.txt" "$TEMP_DIR/" -Force
Copy-Item "./DEPLOYMENT_GUIDE.md" "$TEMP_DIR/" -Force
Copy-Item "./check_voice_setup.py" "$TEMP_DIR/" -Force -ErrorAction SilentlyContinue
Copy-Item "./check_supervision_setup.py" "$TEMP_DIR/" -Force -ErrorAction SilentlyContinue
Copy-Item "config/*.py" "$TEMP_DIR/config/" -Force -ErrorAction SilentlyContinue
Copy-Item "ui/*.py" "$TEMP_DIR/ui/" -Force -ErrorAction SilentlyContinue
Copy-Item "core/*.py" "$TEMP_DIR/core/" -Force -ErrorAction SilentlyContinue
Copy-Item "game/*.py" "$TEMP_DIR/game/" -Force -ErrorAction SilentlyContinue
Copy-Item "utils/*.py" "$TEMP_DIR/utils/" -Force -ErrorAction SilentlyContinue
Copy-Item "static/js/*.js" "$TEMP_DIR/static/js/" -Force -ErrorAction SilentlyContinue
Copy-Item "README.md" "$TEMP_DIR/" -Force -ErrorAction SilentlyContinue

# Step 3: Commit and Push
Write-Host "Step 3: Committing and pushing..." -ForegroundColor Cyan
Push-Location $TEMP_DIR
$status = git status --short
if ($status) {
    git add -A
    git commit -m "Update model to Qwen2.5-VL-72B-Instruct and sync"
    git push -u origin main 2>$null; 
    if ($LASTEXITCODE -ne 0) { 
        git push -u origin master 
    }
    Write-Host "Upload successful!" -ForegroundColor Green
} else {
    Write-Host "No changes to commit." -ForegroundColor Yellow
}
Pop-Location

Write-Host "Deployment process finished!" -ForegroundColor Green
