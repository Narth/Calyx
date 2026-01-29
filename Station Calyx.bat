@echo off
:: Station Calyx Launcher for Windows
:: Double-click to launch the Terminal UI

title Station Calyx
cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

:: Launch Station Calyx
echo.
echo     ╭──────────────────────────────╮
echo     │    🌸 STATION CALYX 🌸       │
echo     │      AI-For-All Project      │
echo     ╰──────────────────────────────╯
echo.
echo Starting Station Calyx Terminal UI...
echo.

python calyx.py %*

if errorlevel 1 (
    echo.
    echo Station Calyx exited with an error.
    pause
)
