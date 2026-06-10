@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║       Agency — Claude Code Web 操作面板           ║
echo  ║       一键安装脚本 (Windows)                      ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── 1. 检查 Python ──
echo [1/5] 检查 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未找到 Python。请先安装 Python 3.10+
    echo   下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   已安装 Python %PYVER%

:: ── 2. 安装 Python 依赖 ──
echo.
echo [2/5] 安装 Python 依赖...
pip install -e "%~dp0." --quiet 2>&1
if %errorlevel% neq 0 (
    echo   [警告] pip install -e 失败，尝试普通安装...
    pip install pyyaml requests --quiet
)
echo   依赖安装完成

:: ── 3. 检查 Claude CLI ──
echo.
echo [3/5] 检查 Claude CLI...
where claude >nul 2>&1
if %errorlevel% neq 0 (
    set "NPM_CLAUDE=%APPDATA%\npm\claude.cmd"
    if exist "!NPM_CLAUDE!" (
        echo   Claude CLI: !NPM_CLAUDE!
    ) else (
        echo   [提示] 未找到 Claude CLI。Agent 调度功能将不可用。
        echo   安装: npm install -g @anthropic-ai/claude-code
        echo   没有 Claude API Key? 用 DeepSeek 也能跑 — 在设置页配置。
    )
) else (
    echo   Claude CLI 已就绪
)

:: ── 4. 首次配置 ──
echo.
echo [4/5] 首次配置...
if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        copy "%~dp0.env.example" "%~dp0.env" >nul
        echo   .env 已从模板创建
    )
)
echo   就绪！

:: ── 5. 创建桌面快捷方式 ──
echo.
echo [5/5] 创建桌面快捷方式...
set "DESKTOP=%USERPROFILE%\Desktop"
set "ICON=%%SystemRoot%%\System32\SHELL32.dll"
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell;$s=$ws.CreateShortcut('%DESKTOP%\Agency.lnk');$s.TargetPath='%~dp0start.bat';$s.WorkingDirectory='%~dp0';$s.IconLocation='%ICON%,14';$s.Description='Claude Code Web 操作面板';$s.Save()"
echo   桌面快捷方式已创建: Agency

:: ── 完成 ──
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  安装完成！                                      ║
echo  ║                                                  ║
echo  ║  桌面已创建快捷方式，双击即可打开                 ║
echo  ║  或命令行: agency start                          ║
echo  ║                                                  ║
echo  ║  浏览器打开 http://localhost:8800                ║
echo  ║  无 API Key 也能浏览 Demo 界面                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
