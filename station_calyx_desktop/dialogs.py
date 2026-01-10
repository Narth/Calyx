# -*- coding: utf-8 ????????? ?????? ???????, ??? ??? ?? ????????? :( -*-
"""
Station Calyx Desktop - Dialogs
===============================

Dialog windows including first-launch onboarding.

ROLE: presentation_layer/dialogs
SCOPE: User acknowledgment and information display
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCheckBox, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt

from .styles import COLORS


ONBOARDING_TEXT = """
# Welcome to Station Calyx Desktop

This application provides a graphical interface for Station Calyx Ops Reflector.

## What This Application Does

- **Displays** system status, trends, and advisories
- **Triggers** existing API actions (snapshot, reflect, advise)
- **Presents** information for your review

## What This Application Does NOT Do

- ? **Does not execute commands** on your system
- ? **Does not modify files** or system settings
- ? **Does not make decisions** for you
- ? **Does not send data** anywhere

## Important

**Station Calyx is advisory-only.**

All outputs are informational. This system presents data and observations.
It does not take actions or execute commands.

You are always in control.
"""


class OnboardingDialog(QDialog):
    """
    First-launch onboarding dialog.
    
    Requires user acknowledgment before proceeding.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle("Welcome to Station Calyx")
        self.setMinimumSize(500, 450)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Station Calyx Desktop")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Content
        content = QTextEdit()
        content.setReadOnly(True)
        content.setMarkdown(ONBOARDING_TEXT)
        content.setMinimumHeight(250)
        layout.addWidget(content)
        
        # Acknowledgment checkbox - ensure unchecked by default
        self._ack_checkbox = QCheckBox(
            "I understand that Station Calyx is advisory-only and does not take actions."
        )
        self._ack_checkbox.setChecked(False)
        layout.addWidget(self._ack_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._continue_btn = QPushButton("Continue")
        self._continue_btn.setEnabled(False)
        self._continue_btn.setMinimumWidth(100)
        self._continue_btn.clicked.connect(self.accept)
        button_layout.addWidget(self._continue_btn)
        
        layout.addLayout(button_layout)
        
        # Connect checkbox toggled signal (emits bool, more reliable than stateChanged)
        self._ack_checkbox.toggled.connect(self._on_ack_toggled)
        
        # Synchronize initial state
        self._on_ack_toggled(self._ack_checkbox.isChecked())
    
    def _on_ack_toggled(self, checked: bool) -> None:
        """Handle acknowledgment checkbox toggle."""
        # Enable/disable continue button based on checkbox state
        self._continue_btn.setEnabled(checked)


class ServiceNotRunningDialog(QDialog):
    """
    Dialog shown when service is not running.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle("Service Not Running")
        self.setMinimumSize(400, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Icon/Title
        title = QLabel("?? Station Calyx Service Not Running")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['warning']};")
        layout.addWidget(title)
        
        # Message
        message = QLabel(
            "The Station Calyx API service is not running.\n\n"
            "Start the service with:\n"
            "  python -m station_calyx.ui.cli start\n\n"
            "Or:\n"
            "  python scripts/calyx_start.py"
        )
        message.setWordWrap(True)
        message.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(message)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        retry_btn = QPushButton("Retry")
        retry_btn.clicked.connect(self.accept)
        button_layout.addWidget(retry_btn)
        
        quit_btn = QPushButton("Quit")
        quit_btn.clicked.connect(self.reject)
        button_layout.addWidget(quit_btn)
        
        layout.addLayout(button_layout)


class AboutDialog(QDialog):
    """
    About dialog.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWindowTitle("About Station Calyx")
        self.setFixedSize(350, 250)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Station Calyx Desktop")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel("v1.0.0")
        version.setProperty("class", "dim")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        layout.addStretch()
        
        # Description
        desc = QLabel(
            "A graphical interface for Station Calyx Ops Reflector.\n\n"
            "Advisory-only. Does not execute.\n"
            "Does not initiate actions."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
