# -*- coding: utf-8 -*-
"""
Station Calyx Desktop - Styles
==============================

Consistent styling for the desktop application.
"""

# Color palette
COLORS = {
    "background": "#1e1e2e",
    "surface": "#313244",
    "surface_light": "#45475a",
    "text": "#cdd6f4",
    "text_dim": "#a6adc8",
    "accent": "#89b4fa",
    "success": "#a6e3a1",
    "warning": "#f9e2af",
    "error": "#f38ba8",
    "border": "#585b70",
}

# Status colors
STATUS_COLORS = {
    "stable": COLORS["success"],
    "trends_observed": COLORS["accent"],
    "attention_suggested": COLORS["warning"],
    "notable_changes": COLORS["warning"],
    "error": COLORS["error"],
}

# Confidence colors
CONFIDENCE_COLORS = {
    "low": COLORS["text_dim"],
    "medium": COLORS["warning"],
    "high": COLORS["success"],
}

# Main stylesheet
STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['background']};
}}

QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: "Segoe UI", "SF Pro", sans-serif;
    font-size: 13px;
}}

QLabel {{
    color: {COLORS['text']};
}}

QLabel[class="header"] {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['accent']};
    padding: 8px 0;
}}

QLabel[class="subheader"] {{
    font-size: 14px;
    font-weight: bold;
    color: {COLORS['text']};
    padding: 4px 0;
}}

QLabel[class="dim"] {{
    color: {COLORS['text_dim']};
    font-size: 12px;
}}

QLabel[class="status-stable"] {{
    color: {COLORS['success']};
    font-weight: bold;
}}

QLabel[class="status-warning"] {{
    color: {COLORS['warning']};
    font-weight: bold;
}}

QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {COLORS['surface_light']};
    border-color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
    color: {COLORS['background']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_dim']};
    border-color: {COLORS['surface']};
}}

QFrame[class="panel"] {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 12px;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: {COLORS['surface']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['accent']};
}}

QListWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {COLORS['surface_light']};
}}

QListWidget::item:hover {{
    background-color: {COLORS['surface_light']};
}}

QTabWidget::pane {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_dim']};
    padding: 10px 20px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text']};
}}

QTabBar::tab:hover {{
    color: {COLORS['accent']};
}}

QTextEdit {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px;
    font-family: "Consolas", "SF Mono", monospace;
    font-size: 12px;
}}

QMessageBox {{
    background-color: {COLORS['background']};
}}

QMessageBox QLabel {{
    color: {COLORS['text']};
}}

QDialog {{
    background-color: {COLORS['background']};
}}
"""
