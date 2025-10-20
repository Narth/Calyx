; Calyx.ahk — basic rituals
; Update the paths to your Python venv as needed.
; Example venv Python path:
; C:\Calyx_Terminal\Scripts\.venv\Scripts\python.exe

; Set this to your Python path
python := "C:\Calyx_Terminal\Scripts\.venv\Scripts\python.exe"
console := "C:\Calyx_Terminal\Scripts\calyx_console.py"
voice   := "C:\Calyx_Terminal\Scripts\voice_to_command.py"

^!s:: ; Ctrl+Alt+S — Begin Session
Run, %python% %console% begin_session, , Hide
return

^!j:: ; Ctrl+Alt+J — Log Reflection (opens today's note)
Run, %python% %console% log_reflection "Hotkey reflection", , Hide
return

^!v:: ; Ctrl+Alt+V — Toggle Voice Listener
; Simple: start a new listener instance
Run, %python% %voice%, , Min
return