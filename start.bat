@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\agency.exe" start %*
