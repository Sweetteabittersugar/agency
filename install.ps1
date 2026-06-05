# install.ps1 — agency-kit Windows PowerShell 安装脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   agency-kit 安装程序" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 目标目录
$ClaudeHome = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { "$env:USERPROFILE\.claude" }
$ProjectClaude = if ($env:CLAUDE_PROJECT_DIR) { "$env:CLAUDE_PROJECT_DIR\.claude" } else { "$(Get-Location)\.claude" }

Write-Host "选择安装位置："
Write-Host "  1) 全局 ($ClaudeHome) — 所有项目生效"
Write-Host "  2) 项目 ($ProjectClaude) — 仅当前项目"
Write-Host "  3) 两者都装"
$choice = Read-Host "请输入 (1/2/3，默认 2)"
if (-not $choice) { $choice = "2" }

function Install-To {
    param([string]$Target)

    Write-Host "安装到: $Target" -ForegroundColor Yellow

    # 创建目录
    $dirs = @("agents", "skills", "commands", "hooks", "rules")
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path "$Target\$d" | Out-Null
    }

    # 复制文件
    if (Test-Path "$ScriptDir\agents") {
        Copy-Item -Recurse -Force "$ScriptDir\agents\*" "$Target\agents\"
        Write-Host "  ✓ agents" -ForegroundColor Green
    }
    if (Test-Path "$ScriptDir\skills") {
        Copy-Item -Recurse -Force "$ScriptDir\skills\*" "$Target\skills\"
        Write-Host "  ✓ skills" -ForegroundColor Green
    }
    if (Test-Path "$ScriptDir\commands") {
        Copy-Item -Recurse -Force "$ScriptDir\commands\*" "$Target\commands\"
        Write-Host "  ✓ commands" -ForegroundColor Green
    }
    if (Test-Path "$ScriptDir\hooks") {
        Copy-Item -Recurse -Force "$ScriptDir\hooks\*" "$Target\hooks\"
        Write-Host "  ✓ hooks" -ForegroundColor Green
    }
    if (Test-Path "$ScriptDir\rules") {
        Copy-Item -Recurse -Force "$ScriptDir\rules\*" "$Target\rules\"
        Write-Host "  ✓ rules" -ForegroundColor Green
    }
    if (Test-Path "$ScriptDir\maestro") {
        $maestroTarget = Split-Path $Target
        New-Item -ItemType Directory -Force -Path "$maestroTarget\maestro" | Out-Null
        Copy-Item -Recurse -Force "$ScriptDir\maestro\*" "$maestroTarget\maestro\"
        Write-Host "  ✓ maestro" -ForegroundColor Green
    }
}

switch ($choice) {
    "1" { Install-To $ClaudeHome }
    "2" { Install-To $ProjectClaude }
    "3" {
        Install-To $ClaudeHome
        Write-Host ""
        Install-To $ProjectClaude
    }
    default {
        Write-Host "无效选择，默认安装到项目" -ForegroundColor Red
        Install-To $ProjectClaude
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "现在试试:" -ForegroundColor Cyan
Write-Host "  第 1 步 — 在 Claude Code 中随便说句话"
Write-Host "  第 2 步 — 试试 @status 查看 agent 状态"
Write-Host "  第 3 步 — 试试 /design 进入设计模式"
Write-Host ""
Write-Host "只装了 Agent，没装 Maestro？" -ForegroundColor Cyan
Write-Host "  完全没问题。Agent 独立工作，Maestro 是给多 Agent 协作用的。"
Write-Host "  大多数用户停在 Agent 层就够了。"
Write-Host ""
Write-Host "了解更多:" -ForegroundColor Cyan
Write-Host "  cat GETTING-STARTED.md    # 5 分钟入门"
Write-Host "  cat COMMANDS-QUICK-REF.md # 命令速查"
