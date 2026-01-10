# -*- coding: utf-8 -*-
"""
Station Calyx Desktop - Widgets
===============================

Reusable UI components.

ROLE: presentation_layer/widgets
SCOPE: Visual display components only
"""

from __future__ import annotations

from typing import Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .styles import COLORS, STATUS_COLORS, CONFIDENCE_COLORS


# Unicode glyphs as explicit escapes (prevents CP1252 encoding issues)
GLYPH_BULLET = "\u2022"        # •
GLYPH_MULTIPLY = "\u00D7"      # ×
GLYPH_ARROW_RIGHT = "\u25B6"   # ▶
GLYPH_ARROW_DOWN = "\u25BC"    # ▼
GLYPH_ARROW = "\u2192"         # →
GLYPH_DASH = "\u2500"          # ─


class Panel(QFrame):
    """Styled panel container."""
    
    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setProperty("class", "panel")
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        
        if title:
            title_label = QLabel(title)
            title_label.setProperty("class", "subheader")
            self._layout.addWidget(title_label)
    
    def add_widget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)
    
    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)
    
    def add_stretch(self) -> None:
        self._layout.addStretch()


class MetricCard(QFrame):
    """Card displaying a single metric."""
    
    def __init__(
        self,
        label: str,
        value: str = "-",
        unit: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "panel")
        self.setMinimumWidth(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        # Label
        self._label = QLabel(label)
        self._label.setProperty("class", "dim")
        layout.addWidget(self._label)
        
        # Value row
        value_row = QHBoxLayout()
        value_row.setSpacing(4)
        
        self._value = QLabel(value)
        self._value.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text']};")
        value_row.addWidget(self._value)
        
        if unit:
            unit_label = QLabel(unit)
            unit_label.setProperty("class", "dim")
            unit_label.setAlignment(Qt.AlignBottom)
            value_row.addWidget(unit_label)
        
        value_row.addStretch()
        layout.addLayout(value_row)
    
    def set_value(self, value: str, color: Optional[str] = None) -> None:
        self._value.setText(value)
        if color:
            self._value.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")


class StatusIndicator(QWidget):
    """Status indicator with colored dot and text."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Dot
        self._dot = QLabel(GLYPH_BULLET)
        self._dot.setStyleSheet(f"font-size: 16px; color: {COLORS['text_dim']};")
        layout.addWidget(self._dot)
        
        # Text - starts empty until set_status is called
        self._text = QLabel("Connecting...")
        layout.addWidget(self._text)
        
        layout.addStretch()
    
    def set_status(self, state: str, text: str) -> None:
        """Set status indicator state and text."""
        if not text:
            text = "No status available"
        color = STATUS_COLORS.get(state, COLORS['text_dim'])
        self._dot.setStyleSheet(f"font-size: 16px; color: {color};")
        self._text.setText(text)


class ActionButton(QPushButton):
    """Styled action button with confirmation."""
    
    action_triggered = Signal(str)
    
    def __init__(
        self,
        text: str,
        action_id: str,
        description: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(text, parent)
        self._action_id = action_id
        self._description = description
        
        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        
        if description:
            self.setToolTip(description)
        
        self.clicked.connect(self._on_click)
    
    def _on_click(self) -> None:
        self.action_triggered.emit(self._action_id)


class FindingCard(QFrame):
    """
    Card displaying a trend/drift finding with expandable details.
    
    CONSTRAINT: View-only expansion. No free text input. No execution.
    """
    
    def __init__(
        self,
        finding_type: str,
        metric: str,
        direction: str,
        confidence: str,
        description: str = "",
        occurrence_count: int = 1,
        values_summary: Optional[dict] = None,
        evidence_refs: Optional[list] = None,
        timestamp: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "panel")
        self.setCursor(Qt.PointingHandCursor)
        
        self._expanded = False
        self._values_summary = values_summary or {}
        self._evidence_refs = evidence_refs or []
        self._timestamp = timestamp
        self._occurrence_count = occurrence_count
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)
        
        # Header row
        header = QHBoxLayout()
        
        # Type badge
        type_label = QLabel(finding_type.replace("_", " ").title())
        type_color = COLORS['warning'] if "DRIFT" in finding_type.upper() else COLORS['accent']
        type_label.setStyleSheet(f"color: {type_color}; font-weight: bold; font-size: 11px;")
        header.addWidget(type_label)
        
        # Occurrence count if > 1
        if occurrence_count > 1:
            count_label = QLabel(f"({GLYPH_MULTIPLY}{occurrence_count})")
            count_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
            header.addWidget(count_label)
        
        header.addStretch()
        
        # Confidence
        conf_color = CONFIDENCE_COLORS.get(confidence.lower(), COLORS['text_dim'])
        conf_label = QLabel(f"[{confidence.upper()}]")
        conf_label.setStyleSheet(f"color: {conf_color}; font-size: 11px;")
        header.addWidget(conf_label)
        
        # Expand indicator
        self._expand_indicator = QLabel(GLYPH_ARROW_RIGHT)
        self._expand_indicator.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        header.addWidget(self._expand_indicator)
        
        main_layout.addLayout(header)
        
        # Metric and direction
        metric_label = QLabel(f"{metric}: {direction}")
        metric_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text']};")
        main_layout.addWidget(metric_label)
        
        # Description
        if description:
            desc_label = QLabel(description[:100])
            desc_label.setProperty("class", "dim")
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)
        
        # Expandable details section (initially hidden)
        self._details_widget = QWidget()
        self._details_widget.setVisible(False)
        details_layout = QVBoxLayout(self._details_widget)
        details_layout.setContentsMargins(0, 8, 0, 0)
        details_layout.setSpacing(4)
        
        # Separator
        sep = QLabel(GLYPH_DASH * 30)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        details_layout.addWidget(sep)
        
        # Timestamp
        if timestamp:
            ts_label = QLabel(f"Last observed: {timestamp}")
            ts_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
            details_layout.addWidget(ts_label)
        
        # Values summary
        if self._values_summary:
            values_text = "Values: "
            if "first" in self._values_summary and "last" in self._values_summary:
                values_text += f"{self._values_summary['first']} {GLYPH_ARROW} {self._values_summary['last']}"
            if "slope_per_hour" in self._values_summary:
                values_text += f" (slope: {self._values_summary['slope_per_hour']}/h)"
            val_label = QLabel(values_text)
            val_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text']};")
            details_layout.addWidget(val_label)
        
        # Evidence references
        if self._evidence_refs:
            ev_header = QLabel("Evidence:")
            ev_header.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
            details_layout.addWidget(ev_header)
            for ref in self._evidence_refs[:3]:
                ref_label = QLabel(f"  {GLYPH_BULLET} {ref}")
                ref_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_dim']};")
                details_layout.addWidget(ref_label)
        
        # Confidence rationale
        conf_rationale = QLabel(f"Confidence: {confidence.upper()} - Based on sample count and time window")
        conf_rationale.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
        conf_rationale.setWordWrap(True)
        details_layout.addWidget(conf_rationale)
        
        main_layout.addWidget(self._details_widget)
    
    def mousePressEvent(self, event) -> None:
        """Toggle expansion on click."""
        self._expanded = not self._expanded
        self._details_widget.setVisible(self._expanded)
        self._expand_indicator.setText(GLYPH_ARROW_DOWN if self._expanded else GLYPH_ARROW_RIGHT)
        super().mousePressEvent(event)


class AdvisoryCard(QFrame):
    """
    Card displaying an advisory note with expandable details.
    
    CONSTRAINT: View-only expansion. No free text input. No execution.
    """
    
    def __init__(
        self,
        title: str,
        message: str,
        confidence: str,
        evidence: str = "",
        rationale: str = "",
        uncertainties: Optional[list] = None,
        evidence_refs: Optional[list] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "panel")
        self.setCursor(Qt.PointingHandCursor)
        
        self._expanded = False
        self._rationale = rationale
        self._uncertainties = uncertainties or []
        self._evidence_refs = evidence_refs or []
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)
        
        # Header
        header = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text']};")
        header.addWidget(title_label)
        
        header.addStretch()
        
        conf_color = CONFIDENCE_COLORS.get(confidence.lower(), COLORS['text_dim'])
        conf_label = QLabel(f"[{confidence.upper()}]")
        conf_label.setStyleSheet(f"color: {conf_color}; font-size: 11px;")
        header.addWidget(conf_label)
        
        # Expand indicator
        self._expand_indicator = QLabel(GLYPH_ARROW_RIGHT)
        self._expand_indicator.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        header.addWidget(self._expand_indicator)
        
        main_layout.addLayout(header)
        
        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        main_layout.addWidget(msg_label)
        
        # Evidence (summary)
        if evidence:
            ev_label = QLabel(f"Evidence: {evidence}")
            ev_label.setProperty("class", "dim")
            ev_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
            main_layout.addWidget(ev_label)
        
        # Expandable details section (initially hidden)
        self._details_widget = QWidget()
        self._details_widget.setVisible(False)
        details_layout = QVBoxLayout(self._details_widget)
        details_layout.setContentsMargins(0, 8, 0, 0)
        details_layout.setSpacing(4)
        
        # Separator
        sep = QLabel(GLYPH_DASH * 30)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        details_layout.addWidget(sep)
        
        # Rationale
        if self._rationale:
            rat_label = QLabel(f"Rationale: {self._rationale}")
            rat_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text']};")
            rat_label.setWordWrap(True)
            details_layout.addWidget(rat_label)
        
        # Uncertainties
        if self._uncertainties:
            unc_header = QLabel("Uncertainties:")
            unc_header.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
            details_layout.addWidget(unc_header)
            for unc in self._uncertainties[:3]:
                unc_label = QLabel(f"  {GLYPH_BULLET} {unc}")
                unc_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_dim']};")
                details_layout.addWidget(unc_label)
        
        # Evidence references
        if self._evidence_refs:
            ev_header = QLabel("Evidence references:")
            ev_header.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
            details_layout.addWidget(ev_header)
            for ref in self._evidence_refs[:5]:
                ref_label = QLabel(f"  {GLYPH_BULLET} {ref}")
                ref_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_dim']};")
                details_layout.addWidget(ref_label)
        
        main_layout.addWidget(self._details_widget)
    
    def mousePressEvent(self, event) -> None:
        """Toggle expansion on click."""
        self._expanded = not self._expanded
        self._details_widget.setVisible(self._expanded)
        self._expand_indicator.setText(GLYPH_ARROW_DOWN if self._expanded else GLYPH_ARROW_RIGHT)
        super().mousePressEvent(event)


class ScrollableList(QScrollArea):
    """Scrollable container for a list of widgets."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 8, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch()
        
        self.setWidget(self._container)
    
    def clear(self) -> None:
        """Remove all items."""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def add_widget(self, widget: QWidget) -> None:
        """Add widget to list."""
        self._layout.insertWidget(self._layout.count() - 1, widget)
    
    def set_empty_message(self, message: str) -> None:
        """Show message when list is empty."""
        self.clear()
        label = QLabel(message)
        label.setProperty("class", "dim")
        label.setAlignment(Qt.AlignCenter)
        self._layout.insertWidget(0, label)
