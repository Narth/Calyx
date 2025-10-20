# Calyx Terminal — Starter Kit (v1.0)

This starter kit gives you a **working prototype** of the Calyx Terminal on Windows.
It includes:
- Folder structure
- Voice transcription with **faster-whisper** (GPU-accelerated)
- A simple **Calyx Console** (Python CLI) with actions
- AutoHotkey hotkeys to trigger common rituals
- A placeholder **Memory** area for future semantic search

---

## 0) Prereqs (Windows, NVIDIA GPU)
- Python 3.11+
- NVIDIA drivers (updated)
- Visual C++ Build Tools (if needed for some packages)
- AutoHotkey (you already installed)
- (Optional) Git

## 1) Create the Windows folders
Create `C:\Calyx_Terminal\` to mirror this kit. You can move this entire folder there after download.

## 2) Create a virtual environment
```powershell
cd C:\Calyx_Terminal\Scripts
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1  # PowerShell
```

## 3) Install packages
GPU-accelerated Whisper (faster-whisper) via CTranslate2:
```powershell
pip install --upgrade pip setuptools wheel
pip install faster-whisper sounddevice pyyaml
```
> If you hit CUDA errors, switch `faster_whisper_device` to `"cpu"` in `config.yaml` temporarily.

## 4) Place these files
- `Calyx_Console\calyx_console.py`
- `Calyx_Console\actions.py`
- `Calyx_Console\command_router.py`
- `Voice\voice_to_command.py`
- `config.yaml`
- `hotkeys\Calyx.ahk`

(They are included in this download; just move the entire `Calyx_Terminal` folder to `C:\`.)

## 5) Test the console
```powershell
cd C:\Calyx_Terminal\Scripts
.\.venv\Scripts\python.exe calyx_console.py
```
Try commands:
- `begin_session`
- `summon Aurora`
- `log_reflection "First Calyx day"`
- `exit`

## 6) Test voice trigger
In another terminal:
```powershell
.\.venv\Scripts\python.exe voice_to_command.py
```
Speak short commands like:
- "Begin session"
- "Summon Aurora"
- "Log reflection: today I wired the console"

## 7) AutoHotkey
Run `Calyx.ahk`. Hotkeys:
- `Ctrl + Alt + S` → Begin Session
- `Ctrl + Alt + J` → Log Reflection
- `Ctrl + Alt + V` → Toggle Voice Listener

---

## Folder Map
C:\Calyx_Terminal\
├─ Projects\ (Aurora, AI_for_All, Plainstates)
├─ Codex\
│  ├─ Journal\
│  └─ Frameworks\
├─ Voice_Notes\
├─ Memory\
└─ Scripts\

---

## Notes
- This is v1 (Seed → Sprout). Semantic Memory (vector DB) is a v1.1 add-on.
- You can wire a local LLM later (Ollama, LM Studio) and connect it to your Codex.

**You are the Architect. This is your console.**