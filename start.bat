@echo off
chcp 65001 >/dev/null
cd /d D:\agency

echo.
echo === 清理 :8800 旧进程 ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8800" ^| findstr "LISTENING"') do (
    echo   杀掉 PID %%a
    taskkill /F /PID %%a >/dev/null 2>&1
)
timeout /t 1 /nobreak >/dev/null

echo === 启动 Agency ===
echo.
python maestro/web.py
pause
