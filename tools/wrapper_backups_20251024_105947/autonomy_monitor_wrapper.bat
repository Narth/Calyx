@echo off
"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Calyx_Terminal\tools\calyx_task_launcher.ps1" --script "C:\Calyx_Terminal\tools\autonomy_monitor.py" --scriptArgs "--interval 30" --taskName "Calyx Autonomy Monitor" --pythonPath "C:\Users\jncr0\AppData\Local\Programs\Python\Python314\python.exe"
