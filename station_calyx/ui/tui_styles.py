"""Station Calyx TUI CSS (Tokyo Night Theme)"""

CALYX_CSS = """
Screen { background: #1a1b26; }
Header { dock: top; height: 3; background: #24283b; color: #ff9e64; text-style: bold; }
Footer { dock: bottom; height: 1; background: #24283b; color: #7aa2f7; }

#dashboard-content { padding: 2 4; }

#content { padding: 2 4; }

#welcome-container { align: center middle; height: 100%; }
#welcome-box { width: 45; border: round #ff9e64; background: #24283b; padding: 2; }
#welcome-ascii { text-align: center; color: #ff9e64; }
#welcome-motto { text-align: center; color: #7aa2f7; text-style: italic; padding-top: 1; }
#welcome-prompt { text-align: center; color: #565f89; padding-top: 1; }

.panel-title { color: #ff9e64; text-style: bold; }

Static { color: #a9b1d6; }

Button { margin: 0 1 0 0; min-width: 12; }
Button.primary { background: #449dab; color: #1a1b26; }
Button.primary:hover { background: #73daca; }
Button.secondary { background: #24283b; color: #a9b1d6; border: solid #414868; }
Button.secondary:hover { background: #414868; }
Button.danger { background: #f7768e; color: #1a1b26; }

ModalScreen { align: center middle; }
#modal-dialog { width: 80%; height: 70%; border: round #ff9e64; background: #1a1b26; padding: 1; }

ScrollableContainer { padding: 1; }
"""
