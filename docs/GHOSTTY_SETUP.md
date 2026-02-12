# Ghostty Terminal Setup for Station Calyx

**Station Calyx / AI-For-All Project**

---

## What is Ghostty?

[Ghostty](https://ghostty.org) is a fast, feature-rich, cross-platform terminal emulator that uses platform-native UI and GPU acceleration. It's the recommended terminal for running Station Calyx.

### Why Ghostty?

| Feature | Benefit for Station Calyx |
|---------|---------------------------|
| **GPU Acceleration** | Smooth TUI rendering and animations |
| **Platform-Native** | Respects your OS; feels like home |
| **Cross-Platform** | Works on Linux, macOS, and Windows |
| **Modern Features** | True color, ligatures, emoji support |
| **Open Source** | Aligns with AI-For-All transparency |
| **Fast** | Written in Zig for performance |

---

## Installation

### Linux

```bash
# Arch Linux
yay -S ghostty

# Other distributions - build from source
git clone https://github.com/ghostty-org/ghostty
cd ghostty
zig build -Doptimize=ReleaseFast
```

### macOS

```bash
# Homebrew
brew install ghostty
```

### Windows

Download from [ghostty.org/download](https://ghostty.org/download) or use:

```powershell
# Scoop
scoop install ghostty

# Winget
winget install ghostty
```

---

## Configuration

### Quick Setup

1. Copy the Station Calyx Ghostty config:

```bash
# Linux/macOS
mkdir -p ~/.config/ghostty
cp config/ghostty.config ~/.config/ghostty/config

# Windows (PowerShell)
mkdir -Force "$env:APPDATA\ghostty"
copy config\ghostty.config "$env:APPDATA\ghostty\config"
```

2. Restart Ghostty

### Manual Configuration

Create or edit your Ghostty config file and add the Tokyo Night theme:

```ini
# Tokyo Night for Station Calyx
background = 1a1b26
foreground = a9b1d6
cursor-color = c0caf5

# Normal colors
palette = 0=#15161e
palette = 1=#f7768e
palette = 2=#9ece6a
palette = 3=#e0af68
palette = 4=#7aa2f7
palette = 5=#bb9af7
palette = 6=#7dcfff
palette = 7=#a9b1d6

# Bright colors
palette = 8=#414868
palette = 9=#f7768e
palette = 10=#9ece6a
palette = 11=#e0af68
palette = 12=#7aa2f7
palette = 13=#bb9af7
palette = 14=#7dcfff
palette = 15=#c0caf5
```

---

## Launching Station Calyx

### Option 1: Manual Launch

Open Ghostty, navigate to Station Calyx, and run:

```bash
cd /path/to/Calyx_Terminal
python calyx.py
```

### Option 2: Shell Alias

Add to your shell config (`~/.bashrc`, `~/.zshrc`, or PowerShell profile):

```bash
# Bash/Zsh
alias calyx='cd ~/Calyx_Terminal && python calyx.py'

# PowerShell
function calyx { cd C:\Calyx_Terminal; python calyx.py }
```

### Option 3: Desktop Shortcut

Create a desktop shortcut that opens Ghostty with Station Calyx:

**Linux (.desktop file):**
```ini
[Desktop Entry]
Name=Station Calyx
Exec=ghostty -e bash -c 'cd ~/Calyx_Terminal && python calyx.py'
Icon=terminal
Type=Application
Categories=Development;
```

**Windows (shortcut target):**
```
ghostty.exe -e powershell -c "cd C:\Calyx_Terminal; python calyx.py"
```

---

## Recommended Fonts

Station Calyx TUI looks best with a monospace font that supports ligatures:

| Font | Install |
|------|---------|
| **JetBrains Mono** (recommended) | [jetbrains.com/lp/mono](https://www.jetbrains.com/lp/mono/) |
| Fira Code | [github.com/tonsky/FiraCode](https://github.com/tonsky/FiraCode) |
| Cascadia Code | [github.com/microsoft/cascadia-code](https://github.com/microsoft/cascadia-code) |
| Iosevka | [github.com/be5invis/Iosevka](https://github.com/be5invis/Iosevka) |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+C` | Copy to clipboard |
| `Ctrl+Shift+V` | Paste from clipboard |
| `Ctrl+Shift+N` | New window |
| `Ctrl+Shift+T` | New tab |
| `Ctrl++` | Increase font size |
| `Ctrl+-` | Decrease font size |
| `Ctrl+0` | Reset font size |
| `Shift+PageUp/Down` | Scroll |

---

## Troubleshooting

### Colors look wrong

Ensure your terminal reports true color support:

```bash
echo $COLORTERM  # Should show "truecolor"
```

### Font not rendering

1. Verify the font is installed
2. Update Ghostty config: `font-family = YourFont`
3. Restart Ghostty

### TUI doesn't fill screen

1. Maximize the Ghostty window
2. Or set in config:
   ```ini
   window-width = 1920
   window-height = 1080
   ```

---

## Why This Pairing?

Station Calyx and Ghostty share common values:

- **Performance** — Both optimize for speed
- **Local-First** — Both run on your machine, not the cloud
- **Open Source** — Both embrace transparency
- **User Respect** — Neither tracks or phones home
- **Modern Design** — Both bring contemporary interfaces to the terminal

Together, they create an experience where the terminal becomes a sanctuary—fast, beautiful, and yours.

---

*Station Calyx / AI-For-All Project*  
*"Capability under governance. Action with authorization."*
