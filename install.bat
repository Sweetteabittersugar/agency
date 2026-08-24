@echo off
setlocal
cd /d "%~dp0"

echo Agency v0.5.0 - source-only local install
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b 1
echo Installed. Start with:
echo   .venv\Scripts\agency.exe start --project-root C:\path\to\project
