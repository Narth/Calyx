#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Station Calyx Desktop - Main Entry Point
========================================

Launches the Station Calyx Desktop application.

ROLE: presentation_layer
SCOPE: Application entry and initialization

CONSTRAINTS:
- VIEW + TRIGGER layer only
- Connects to existing API at 127.0.0.1:8420
- No new intelligence or authority

Usage:
    python -m station_calyx_desktop
    python station_calyx_desktop/main.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _check_encoding_sanity() -> bool:
    """
    Pre-launch encoding sanity check.
    Fail-fast with clear message if encoding issues detected.
    """
    import locale
    
    # Check stdout encoding
    stdout_encoding = getattr(sys.stdout, 'encoding', None)
    if stdout_encoding and stdout_encoding.lower() not in ('utf-8', 'utf8', 'cp65001'):
        print(f"Warning: stdout encoding is {stdout_encoding}, not UTF-8")
        print("Some characters may not display correctly.")
    
    # Test unicode string handling
    try:
        test_str = "\u2022 \u25B6 \u25BC \u2192"  # bullet, arrows
        _ = test_str.encode('utf-8').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        print(f"Error: Unicode encoding test failed: {e}")
        print("Please ensure your terminal supports UTF-8.")
        return False
    
    return True


def main() -> int:
    """Main entry point."""
    # Pre-launch encoding check
    if not _check_encoding_sanity():
        return 1
    
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
    except ImportError:
        print("Error: PySide6 is required.")
        print("Install with: pip install PySide6")
        return 1
    
    from station_calyx_desktop.main_window import (
        MainWindow,
        check_onboarding,
        check_service_running,
        SETTINGS_ORG,
        SETTINGS_APP,
    )
    from station_calyx_desktop.styles import STYLESHEET
    
    # Check for existing QApplication instance (prevents multiple instances)
    existing_app = QApplication.instance()
    if existing_app is not None:
        print("Warning: QApplication instance already exists. Reusing.")
        app = existing_app
    else:
        app = QApplication(sys.argv)
    
    app.setApplicationName("Station Calyx Desktop")
    app.setOrganizationName(SETTINGS_ORG)
    app.setStyleSheet(STYLESHEET)
    
    # Ensure clean shutdown on quit
    app.setQuitOnLastWindowClosed(False)  # We handle quit manually via tray
    
    # Settings
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    
    # First-launch onboarding
    if not check_onboarding(settings):
        _cleanup_app(app)
        return 0  # User declined
    
    # Check service
    if not check_service_running():
        _cleanup_app(app)
        return 0  # User quit
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    exit_code = app.exec()
    
    # Explicit cleanup
    _cleanup_app(app, window)
    
    return exit_code


def _cleanup_app(app, window=None) -> None:
    """
    Explicit cleanup to ensure no lingering references.
    Enables reliable relaunch from same shell.
    """
    try:
        # Close window if exists
        if window is not None:
            window.close()
            # Hide tray icon explicitly
            if hasattr(window, '_tray_icon') and window._tray_icon:
                window._tray_icon.hide()
                window._tray_icon.setVisible(False)
        
        # Process pending events
        app.processEvents()
        
        # Quit application
        app.quit()
        
        # Delete app reference (helps garbage collection)
        # Note: We don't call app.deleteLater() as it can cause issues
        
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    sys.exit(main())
