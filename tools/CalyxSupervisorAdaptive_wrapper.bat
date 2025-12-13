@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Calyx_Terminal\tools\calyx_task_launcher.ps1" --script "C:\Calyx_Terminal\tools\\svc_supervisor_adaptive.py" --scriptArgs "--interval 60 --include-scheduler --scheduler-interval 150" --taskName "Calyx Supervisor Adaptive" --pythonPath "C:\Users\jncr0\AppData\Local\Programs\Python\Python314\python.exe"
