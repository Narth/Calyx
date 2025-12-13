@echo off
REM Launch Calyx Agent Watcher (Windows)

setlocal ENABLEDELAYEDEXPANSION
cd /d "C:\Calyx_Terminal"

set "PYW="
set "VENV1=Scripts\.venv\Scripts"
set "VENV2=.venv\Scripts"

if exist "%VENV1%\pythonw.exe" set "PYW=%VENV1%\pythonw.exe"
if "%PYW%"=="" if exist "%VENV2%\pythonw.exe" set "PYW=%VENV2%\pythonw.exe"
if "%PYW%"=="" if exist "%VENV1%\python.exe" set "PYW=%VENV1%\python.exe"
if "%PYW%"=="" if exist "%VENV2%\python.exe" set "PYW=%VENV2%\python.exe"

if "%PYW%"=="" (
	powershell -NoProfile -ExecutionPolicy Bypass -Command "[void][Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');[System.Windows.Forms.MessageBox]::Show('No Python found in Scripts\\.venv or .venv. Please run Setup Deps (Windows venv).','Calyx Agent Watcher')" >nul 2>nul
	exit /b 1
)

REM Start detached so the console window does not linger
start "Calyx Agent Watcher" "%PYW%" -u Scripts\agent_watcher.py --quiet

endlocal
exit /b 0
