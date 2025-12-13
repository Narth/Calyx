@echo off
REM Calyx Terminal Launch Script
REM Activates virtual environment and starts wake listener

echo Starting Calyx Terminal...
echo.

REM Change to Calyx Terminal directory
cd /d "C:\Calyx_Terminal"

REM Activate virtual environment
call Scripts\.venv\Scripts\activate.bat

REM Start wake listener
echo Launching wake listener...
echo Say "Aurora" or "Calyx" to activate
echo.
Scripts\.venv\Scripts\python.exe -u Scripts\listener_wake.py

pause

[]