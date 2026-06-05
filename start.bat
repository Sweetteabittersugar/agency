@echo off
title Agency
echo.
echo   ================================
echo   Agency Web UI
echo   ================================
echo.
echo   Starting server at http://localhost:8800
echo.
start http://localhost:8800
python maestro/web.py
pause
