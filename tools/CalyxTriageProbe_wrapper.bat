@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Calyx_Terminal\tools\calyx_task_launcher.ps1" --script "C:\Calyx_Terminal\tools\\triage_probe.py" --scriptArgs "--interval 300" --taskName "Calyx Triage Probe" --pythonPath "C:\Users\jncr0\AppData\Local\Programs\Python\Python314\python.exe"
