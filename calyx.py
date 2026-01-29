#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Station Calyx Launcher
======================

Quick launcher for Station Calyx Terminal UI.

Usage:
    python calyx.py          # Launch TUI
    python calyx.py --cli    # Launch CLI mode
    python calyx.py --help   # Show help
"""

import sys
import os
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

def main():
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print("""
Station Calyx Launcher
======================

Usage:
    python calyx.py              Launch Terminal UI
    python calyx.py --cli        Launch CLI mode
    python calyx.py status       Run status command
    python calyx.py assess       Run assessment
    python calyx.py <command>    Run any CLI command

Terminal UI Controls:
    d - Dashboard
    g - Governance  
    a - Actions
    l - Logs
    q - Quit
    ? - Help

Station Calyx / AI-For-All
"Capability under governance. Action with authorization."
        """)
        return
    
    if "--cli" in args:
        # CLI mode
        from station_calyx.ui.cli import main as cli_main
        sys.argv = [sys.argv[0]] + [a for a in args if a != "--cli"]
        cli_main()
    elif len(args) > 0 and not args[0].startswith("-"):
        # Pass through to CLI
        from station_calyx.ui.cli import main as cli_main
        cli_main()
    else:
        # TUI mode (default)
        try:
            from station_calyx.ui.tui import main as tui_main
            tui_main()
        except ImportError as e:
            print(f"Error loading TUI: {e}")
            print("Falling back to CLI mode...")
            from station_calyx.ui.cli import main as cli_main
            cli_main()
        except Exception as e:
            print(f"Error starting TUI: {e}")
            print("Try running with --cli flag for command-line mode.")
            sys.exit(1)


if __name__ == "__main__":
    main()
