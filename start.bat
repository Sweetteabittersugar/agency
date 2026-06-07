@echo off
chcp 65001 >nul
cd /d D:\agency

:: ═══════════════════════════════════
:: 首次运行：自动创建桌面快捷方式
:: ═══════════════════════════════════
if not exist "%~dp0.agency-installed" (
    echo === 首次运行，创建桌面图标 ===
    set "DESKTOP=%USERPROFILE%\Desktop"
    > "%DESKTOP%\Agency.bat" (
        echo @echo off
        echo cd /d D:\agency
        echo start "" pythonw maestro\web.py
        echo timeout /t 3 /nobreak ^>nul
        echo start http://localhost:8800
    )
    echo. > "%~dp0.agency-installed"
    echo 桌面图标已创建
)

echo.
echo === 清理 :8800 旧进程 ===
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8800" ^| findstr "LISTENING"') do (
    echo   杀掉 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo === 启动 Agency ===
echo.
python maestro/web.py
pause
