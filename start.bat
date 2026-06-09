@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: ── 清理 :8800 旧进程 ──
echo === 清理 :8800 旧进程 ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8800" ^| findstr "LISTENING"') do (
    echo   杀掉 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ── 启动 Agency ──
echo === 启动 Agency ===
echo   浏览器打开 http://localhost:8800
echo.
python maestro/web.py
pause
