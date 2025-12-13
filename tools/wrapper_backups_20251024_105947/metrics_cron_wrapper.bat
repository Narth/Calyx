@echo off
"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Calyx_Terminal\tools\calyx_task_launcher.ps1" --script "C:\Calyx_Terminal\tools\metrics_cron.py" --scriptArgs "--interval 900" --taskName "Calyx Metrics Cron" --pythonPath "C:\Users\jncr0\AppData\Local\Programs\Python\Python314\python.exe"
