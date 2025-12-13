@echo off
"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Calyx_Terminal\tools\calyx_task_launcher.ps1" --script "C:\Calyx_Terminal\tools\alerts_cron.py" --scriptArgs "--run-once --keep 100 --max-age-days 90" --taskName "Calyx Alerts Cleanup" --pythonPath "C:\Users\jncr0\AppData\Local\Programs\Python\Python314\python.exe"
