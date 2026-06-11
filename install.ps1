# install.ps1 — Agency 一键安装脚本 (Windows PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agency v0.4.0 — Claude Code Web 面板" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Agency 安装脚本" -ForegroundColor Cyan
Write-Host "=================" -ForegroundColor Cyan
Write-Host ""

# ── 1. 检查 Python ──
Write-Host "[1/5] 检查 Python..."
try {
    $pyVer = python --version 2>&1
    Write-Host "  已安装 Python $pyVer"
} catch {
    Write-Host "  错误: 未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    Write-Host "  下载: https://www.python.org/downloads/"
    exit 1
}

# ── 2. 安装 Python 依赖 ──
Write-Host ""
Write-Host "[2/5] 安装 Python 依赖..."
try {
    pip install -e "$ScriptDir" --quiet 2>&1 | Out-Null
    Write-Host "  依赖安装完成"
} catch {
    Write-Host "  警告: pip install -e 失败，尝试普通安装..." -ForegroundColor Yellow
    pip install pyyaml requests --quiet
    Write-Host "  依赖安装完成"
}

# ── 3. 检查 Claude CLI ──
Write-Host ""
Write-Host "[3/5] 检查 Claude CLI..."
try {
    claude --version 2>&1 | Out-Null
    Write-Host "  Claude CLI 已就绪" -ForegroundColor Green
} catch {
    Write-Host "  提示: 未检测到 Claude CLI。Agent 调度功能将不可用。" -ForegroundColor Yellow
    Write-Host "  安装: npm install -g @anthropic-ai/claude-code"
    Write-Host "  没有 Claude API Key? 用 DeepSeek 也能跑 — 在设置页配置。"
}

# ── 4. 首次配置 ──
Write-Host ""
Write-Host "[4/5] 首次配置..."
if (-not (Test-Path "$ScriptDir\.env") -and (Test-Path "$ScriptDir\.env.example")) {
    Copy-Item "$ScriptDir\.env.example" "$ScriptDir\.env"
    Write-Host "  .env 已从模板创建"
}
Write-Host "  就绪！"

# ── 5. 创建桌面快捷方式 ──
Write-Host ""
Write-Host "[5/5] 创建桌面快捷方式..."
$DesktopDir = [Environment]::GetFolderPath("Desktop")
if (Test-Path $DesktopDir) {
    try {
        $ws = New-Object -ComObject WScript.Shell
        $s = $ws.CreateShortcut("$DesktopDir\Agency.lnk")
        $s.TargetPath = "$ScriptDir\start.bat"
        $s.WorkingDirectory = $ScriptDir
        $s.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,14"
        $s.Description = "Claude Code Web 操作面板"
        $s.Save()
        Write-Host "  桌面快捷方式已创建: Agency" -ForegroundColor Green
    } catch {
        Write-Host "  警告: 快捷方式创建失败（可手动创建）" -ForegroundColor Yellow
    }
} else {
    Write-Host "  未找到桌面目录，跳过"
}

# ── 完成 ──
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  桌面已创建快捷方式，双击即可打开"
Write-Host "  或命令行: agency start"
Write-Host ""
Write-Host "  浏览器打开 http://localhost:8800"
Write-Host "  无 API Key 也能浏览 Demo 界面"
Write-Host ""
