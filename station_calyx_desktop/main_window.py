# -*- coding: utf-8 -*-
"""
Station Calyx Desktop - Main Window
===================================

Main application window.

ROLE: presentation_layer/main_window
SCOPE: Top-level window management and panel coordination

CONSTRAINTS:
- VIEW + TRIGGER layer only
- All data from API
- No direct file access
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTabWidget, QSplitter, QStatusBar, QMenuBar, QMenu,
    QSystemTrayIcon, QApplication, QDialog, QLabel,
)
from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QAction, QIcon, QCloseEvent

from .api_client import CalyxAPIClient, get_client, is_service_running
from .panels import StatusDashboard, AdvisoriesPanel, TrendsPanel, ControlsPanel
from .dialogs import OnboardingDialog, ServiceNotRunningDialog, AboutDialog
from .styles import STYLESHEET, COLORS

COMPONENT_ROLE = "main_window"
COMPONENT_SCOPE = "top-level window management"

# Settings keys
SETTINGS_ORG = "StationCalyx"
SETTINGS_APP = "Desktop"
SETTINGS_ONBOARDING_COMPLETE = "onboarding_complete"


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Coordinates all panels and handles refresh cycles.
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Station Calyx")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        
        # API client
        self._client = get_client()
        
        # Settings
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        
        # Setup UI
        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._setup_tray_icon()
        
        # Refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(30000)  # 30 seconds
        
        # Initial refresh
        QTimer.singleShot(100, self._initial_refresh)
    
    def _setup_menu_bar(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_all)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_central_widget(self) -> None:
        """Setup central widget with panels."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Tabs for main content
        self._tabs = QTabWidget()
        
        self._dashboard = StatusDashboard(self._client)
        self._tabs.addTab(self._dashboard, "Dashboard")
        
        self._advisories = AdvisoriesPanel(self._client)
        self._tabs.addTab(self._advisories, "Advisories")
        
        self._trends = TrendsPanel(self._client)
        self._tabs.addTab(self._trends, "Trends")
        
        splitter.addWidget(self._tabs)
        
        # Right side: Controls
        self._controls = ControlsPanel(self._client)
        self._controls.setMaximumWidth(280)
        self._controls.setMinimumWidth(200)
        self._controls.action_completed.connect(self._on_action_completed)
        splitter.addWidget(self._controls)
        
        # Set initial sizes
        splitter.setSizes([700, 250])
        
        layout.addWidget(splitter)
    
    def _setup_status_bar(self) -> None:
        """Setup status bar with version surface."""
        from station_calyx_desktop import __version__
        
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        
        # Connection indicator
        self._connection_label = QWidget()
        conn_layout = QHBoxLayout(self._connection_label)
        conn_layout.setContentsMargins(0, 0, 0, 0)
        conn_layout.setSpacing(4)
        
        self._conn_indicator = QWidget()
        self._conn_indicator.setFixedSize(8, 8)
        self._conn_indicator.setStyleSheet(
            f"background-color: {COLORS['text_dim']}; border-radius: 4px;"
        )
        conn_layout.addWidget(self._conn_indicator)
        
        self._conn_text = QWidget()
        conn_layout.addWidget(self._conn_text)
        
        self._status_bar.addPermanentWidget(self._connection_label)
        
        # Version surface label (right side)
        # Purpose: user trust and drift detection
        self._version_label = QLabel(f"Desktop UI v{__version__}")
        self._version_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        self._status_bar.addPermanentWidget(self._version_label)
        
        # Snapshot age label (updated on refresh)
        self._snapshot_age_label = QLabel("")
        self._snapshot_age_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        self._status_bar.addPermanentWidget(self._snapshot_age_label)
        
        self._status_bar.showMessage("Station Calyx Desktop - Advisory Only")
    
    def _update_snapshot_age(self, snapshot_ts: str) -> None:
        """Update snapshot age display."""
        if not snapshot_ts:
            self._snapshot_age_label.setText("")
            return
        
        try:
            from datetime import datetime, timezone
            snapshot_dt = datetime.fromisoformat(snapshot_ts.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_seconds = (now - snapshot_dt).total_seconds()
            
            if age_seconds < 60:
                age_str = f"{int(age_seconds)}s ago"
            elif age_seconds < 3600:
                age_str = f"{int(age_seconds / 60)}m ago"
            else:
                age_str = f"{age_seconds / 3600:.1f}h ago"
            
            self._snapshot_age_label.setText(f"| Snapshot: {age_str}")
        except (ValueError, TypeError):
            self._snapshot_age_label.setText("")
    
    def _setup_tray_icon(self) -> None:
        """Setup system tray icon."""
        self._tray_icon = None
        
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_icon = QSystemTrayIcon(self)
            
            # Create simple colored icon
            from PySide6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor(COLORS['accent']))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(4, 4, 24, 24)
            painter.end()
            
            self._tray_icon.setIcon(QIcon(pixmap))
            self._tray_icon.setToolTip("Station Calyx")
            
            # Tray menu
            tray_menu = QMenu()
            
            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)
            
            tray_menu.addSeparator()
            
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self.quit_app)  # Use quit_app for full cleanup
            tray_menu.addAction(quit_action)
            
            self._tray_icon.setContextMenu(tray_menu)
            self._tray_icon.activated.connect(self._on_tray_activated)
            self._tray_icon.show()
    
    def _on_tray_activated(self, reason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def _initial_refresh(self) -> None:
        """Initial data load."""
        self._update_connection_status()
        self._refresh_all()
    
    def _auto_refresh(self) -> None:
        """Auto-refresh on timer."""
        self._update_connection_status()
        # Only refresh dashboard on auto-refresh
        self._dashboard.refresh()
        self._update_snapshot_age_from_api()
    
    def _refresh_all(self) -> None:
        """Refresh all panels."""
        self._status_bar.showMessage("Refreshing...")
        
        self._dashboard.refresh()
        self._advisories.refresh()
        self._trends.refresh()
        self._update_snapshot_age_from_api()
        
        self._status_bar.showMessage("Refreshed", 3000)
    
    def _update_snapshot_age_from_api(self) -> None:
        """Fetch latest snapshot timestamp and update display."""
        try:
            response = self._client.get_human_status()
            if response.success and response.data:
                snapshot = response.data.get("latest_snapshot", {})
                ts = snapshot.get("timestamp", "")
                self._update_snapshot_age(ts)
        except Exception:
            pass  # Silently fail, non-critical
    
    def _update_connection_status(self) -> None:
        """Update connection indicator."""
        connected = is_service_running()
        
        color = COLORS['success'] if connected else COLORS['error']
        self._conn_indicator.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
    
    def _on_action_completed(self, action_id: str, success: bool, message: str) -> None:
        """Handle action completion."""
        if success:
            self._status_bar.showMessage(f"? {action_id}: {message}", 5000)
            # Refresh relevant panel
            QTimer.singleShot(500, self._refresh_all)
        else:
            self._status_bar.showMessage(f"? {action_id}: {message}", 5000)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close."""
        if self._tray_icon and self._tray_icon.isVisible():
            # Minimize to tray instead of closing
            self.hide()
            event.ignore()
        else:
            # Accept close and trigger full quit
            self._full_cleanup()
            event.accept()
    
    def quit_app(self) -> None:
        """Actually quit the application - ensures full termination."""
        self._full_cleanup()
        QApplication.quit()
    
    def _full_cleanup(self) -> None:
        """
        Full cleanup of all resources.
        Ensures no lingering tray, timers, or references.
        """
        # Stop refresh timer
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
        
        # Hide and cleanup tray icon
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon.setVisible(False)
            self._tray_icon = None
        
        # Close any open dialogs
        for child in self.findChildren(QDialog):
            child.close()


def check_onboarding(settings: QSettings) -> bool:
    """Check if onboarding is needed and show dialog if so."""
    if settings.value(SETTINGS_ONBOARDING_COMPLETE, False, type=bool):
        return True
    
    dialog = OnboardingDialog()
    result = dialog.exec()
    
    if result == QDialog.Accepted:
        settings.setValue(SETTINGS_ONBOARDING_COMPLETE, True)
        return True
    
    return False


def check_service_running() -> bool:
    """Check if service is running and prompt user if not."""
    while not is_service_running():
        dialog = ServiceNotRunningDialog()
        result = dialog.exec()
        
        if result == QDialog.Rejected:
            return False
        # Retry - loop continues
    
    return True
