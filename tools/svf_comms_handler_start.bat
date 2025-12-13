@echo off
echo Starting SVF Communication Handler...
cd /d "%~dp0.."
python tools\svf_comms_handler.py
pause

