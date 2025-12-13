@echo off
setlocal
cd /d "%~dp0.."

rem Try project venv first if present
if exist "%CD%\Scripts\.venv\Scripts\python.exe" (
  call "%CD%\Scripts\.venv\Scripts\activate.bat"
)

python -u Scripts\agent_launcher.py
endlocal
