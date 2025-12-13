# -*- coding: utf-8 -*-
"""
Station Calyx Desktop - Panels
==============================

Main UI panels/screens.

ROLE: presentation_layer/panels
SCOPE: Visual display of data from API

CONSTRAINTS:
- All data comes from API client
- No direct file/evidence access
- Display only, no logic

PRESENTATION INTEGRITY:
- No placeholders visible to users
- All displayed items must have backing evidence
- Confidence levels reflect actual evidence quality
"""

from __future__ import annotations

from typing import Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal

from .widgets import (
    Panel, MetricCard, StatusIndicator, ActionButton,
    FindingCard, AdvisoryCard, ScrollableList,
)
from .api_client import CalyxAPIClient, get_client
from .styles import COLORS


# --- Confidence Hygiene Thresholds ---
# MEDIUM/HIGH confidence requires:
#   - occurrence_count >= MIN_OCCURRENCES_FOR_MEDIUM
#   - time_span_hours >= MIN_TIME_SPAN_FOR_MEDIUM
# Otherwise confidence is forced to LOW
MIN_OCCURRENCES_FOR_MEDIUM = 2
MIN_TIME_SPAN_FOR_MEDIUM = 1.0  # hours


def _apply_confidence_hygiene(
    confidence: str,
    occurrence_count: int,
    time_span_hours: float,
) -> str:
    """
    Apply confidence hygiene rules.
    
    MEDIUM/HIGH may ONLY appear if:
    - occurrence_count >= 2
    - AND time_span_hours >= 1.0
    Otherwise force LOW.
    """
    confidence = confidence.lower() if confidence else "low"
    
    if confidence in ("medium", "high"):
        if occurrence_count < MIN_OCCURRENCES_FOR_MEDIUM:
            return "low"
        if time_span_hours < MIN_TIME_SPAN_FOR_MEDIUM:
            return "low"
    
    return confidence


class StatusDashboard(QWidget):
    """
    Main status dashboard.
    Mirrors /v1/status/human API endpoint.
    """
    
    def __init__(self, client: CalyxAPIClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._client = client
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Status Dashboard")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Status indicator
        self._status = StatusIndicator()
        layout.addWidget(self._status)
        
        # Metrics row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)
        
        self._cpu_card = MetricCard("CPU", "-", "%")
        self._memory_card = MetricCard("Memory", "-", "%")
        self._disk_card = MetricCard("Disk", "-", "%")
        
        metrics_layout.addWidget(self._cpu_card)
        metrics_layout.addWidget(self._memory_card)
        metrics_layout.addWidget(self._disk_card)
        metrics_layout.addStretch()
        
        layout.addLayout(metrics_layout)
        
        # Intent panel
        self._intent_panel = Panel("Active Intent")
        self._intent_label = QLabel("No intent configured")
        self._intent_label.setWordWrap(True)
        self._intent_panel.add_widget(self._intent_label)
        layout.addWidget(self._intent_panel)
        
        # Recent findings
        self._findings_panel = Panel("Active Findings")
        self._findings_list = ScrollableList()
        self._findings_panel.add_widget(self._findings_list)
        layout.addWidget(self._findings_panel)
        
        # Last updated
        self._updated_label = QLabel("Last updated: -")
        self._updated_label.setProperty("class", "dim")
        self._updated_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self._updated_label)
    
    def refresh(self) -> None:
        """Refresh data from API."""
        response = self._client.get_human_status()
        
        if not response.success:
            self._status.set_status("error", f"API Error: {response.error}")
            return
        
        data = response.data or {}
        
        # System state
        state = data.get("system_state", {})
        self._status.set_status(
            state.get("state", "unknown"),
            state.get("description", "Unknown state"),
        )
        
        # Metrics from latest snapshot
        snapshot = data.get("latest_snapshot", {})
        if snapshot:
            cpu = snapshot.get("cpu_percent")
            mem = snapshot.get("memory_percent")
            disk = snapshot.get("disk_percent")
            
            self._cpu_card.set_value(
                f"{cpu:.0f}" if cpu else "-",
                COLORS['warning'] if cpu and cpu > 80 else None,
            )
            self._memory_card.set_value(
                f"{mem:.0f}" if mem else "-",
                COLORS['warning'] if mem and mem > 80 else None,
            )
            self._disk_card.set_value(
                f"{disk:.0f}" if disk else "-",
                COLORS['warning'] if disk and disk > 90 else None,
            )
        
        # Intent
        intent = data.get("intent")
        if intent:
            profile = intent.get("profile", "not set")
            desc = intent.get("description", "")
            self._intent_label.setText(f"Profile: {profile}\n{desc}")
        else:
            self._intent_label.setText("No intent configured")
        
        # Findings - with visibility gate
        self._findings_list.clear()
        findings = data.get("active_findings", {})
        
        drifts = findings.get("drifts", [])
        trends = findings.get("trends", [])
        
        # GATE: Filter to only evidence-backed findings
        # Suppress any finding with occurrence_count == 0 or empty evidence
        visible_drifts = [
            d for d in drifts
            if d.get("occurrence_count", 1) > 0
            and (d.get("evidence_refs") or d.get("values_summary"))
        ]
        visible_trends = [
            t for t in trends
            if t.get("occurrence_count", 1) > 0
            and (t.get("evidence_refs") or t.get("values_summary"))
        ]
        
        if not (visible_drifts or visible_trends):
            self._findings_list.set_empty_message("No active findings in this window.")
        else:
            for d in visible_drifts[:5]:
                # Skip items missing required fields (no placeholders)
                metric = d.get("metric")
                direction = d.get("direction")
                if not metric or not direction:
                    continue
                
                # CONFIDENCE HYGIENE
                confidence = _apply_confidence_hygiene(
                    d.get("confidence", "low"),
                    d.get("occurrence_count", 1),
                    d.get("values_summary", {}).get("time_window_hours", 0)
                )
                card = FindingCard(
                    "DRIFT_WARNING",
                    metric,
                    direction,
                    confidence,
                    occurrence_count=d.get("occurrence_count", 1),
                    values_summary=d.get("values_summary"),
                    evidence_refs=d.get("evidence_refs"),
                    timestamp=d.get("timestamp", ""),
                )
                self._findings_list.add_widget(card)
            
            for t in visible_trends[:5]:
                # Skip items missing required fields (no placeholders)
                metric = t.get("metric")
                direction = t.get("direction")
                if not metric or not direction:
                    continue
                
                # CONFIDENCE HYGIENE
                confidence = _apply_confidence_hygiene(
                    t.get("confidence", "low"),
                    t.get("occurrence_count", 1),
                    t.get("values_summary", {}).get("time_window_hours", 0)
                )
                card = FindingCard(
                    "TREND_DETECTED",
                    metric,
                    direction,
                    confidence,
                    occurrence_count=t.get("occurrence_count", 1),
                    values_summary=t.get("values_summary"),
                    evidence_refs=t.get("evidence_refs"),
                    timestamp=t.get("timestamp", ""),
                )
                self._findings_list.add_widget(card)
        
        # Updated timestamp
        ts = data.get("generated_at", "")[:19]
        self._updated_label.setText(f"Last updated: {ts}")


class AdvisoriesPanel(QWidget):
    """
    Panel displaying recent advisories.
    """
    
    def __init__(self, client: CalyxAPIClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._client = client
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Advisories")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Info
        info = QLabel("Recent advisory notes generated based on your intent profile.")
        info.setProperty("class", "dim")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # List
        self._list = ScrollableList()
        layout.addWidget(self._list)
    
    def refresh(self) -> None:
        """Refresh from API."""
        # Get human status which includes recent advisories
        response = self._client.get_human_status()
        
        self._list.clear()
        
        if not response.success:
            self._list.set_empty_message(f"Error: {response.error}")
            return
        
        data = response.data or {}
        advisories = data.get("recent_advisories", [])
        
        if not advisories:
            self._list.set_empty_message("No advisories yet. Run 'Generate Advisory' to create one.")
            return
        
        for adv in advisories:
            card = AdvisoryCard(
                f"Session {adv.get('session_id', '?')[:8]}",
                f"Profile: {adv.get('profile', '?')}, {adv.get('notes_count', 0)} note(s)",
                "medium",
                f"Generated: {adv.get('timestamp', '?')}",
            )
            self._list.add_widget(card)


class TrendsPanel(QWidget):
    """
    Panel displaying temporal trends and drift warnings.
    """
    
    def __init__(self, client: CalyxAPIClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._client = client
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Trends & Drift")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Info
        info = QLabel("Trends detected from historical snapshots. Run temporal analysis to update.")
        info.setProperty("class", "dim")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Tabs for trends vs drift
        self._tabs = QTabWidget()
        
        # Trends tab
        self._trends_list = ScrollableList()
        self._tabs.addTab(self._trends_list, "Trends")
        
        # Drift tab
        self._drift_list = ScrollableList()
        self._tabs.addTab(self._drift_list, "Drift Warnings")
        
        # Patterns tab
        self._patterns_list = ScrollableList()
        self._tabs.addTab(self._patterns_list, "Patterns")
        
        layout.addWidget(self._tabs)
        
        # Last analysis
        self._last_analysis = QLabel("Last analysis: -")
        self._last_analysis.setProperty("class", "dim")
        layout.addWidget(self._last_analysis)
    
    def refresh(self) -> None:
        """Refresh from API."""
        response = self._client.get_trends()
        
        self._trends_list.clear()
        self._drift_list.clear()
        self._patterns_list.clear()
        
        if not response.success:
            self._trends_list.set_empty_message(f"Error: {response.error}")
            return
        
        data = response.data or {}
        
        # Trends - with visibility gate
        trends = data.get("trends_detected", [])
        visible_trends = [
            t for t in trends
            if t.get("data_points", 1) > 0
            and (t.get("evidence_refs") or t.get("values_summary"))
            and t.get("metric_name")  # Must have metric name
            and t.get("direction")    # Must have direction
        ]
        
        if not visible_trends:
            self._trends_list.set_empty_message("No trends detected in this window.")
        else:
            for t in visible_trends:
                confidence = _apply_confidence_hygiene(
                    t.get("confidence", "low"),
                    t.get("data_points", 1),
                    t.get("time_span_hours", 0)
                )
                card = FindingCard(
                    "TREND",
                    t.get("metric_name"),
                    t.get("direction"),
                    confidence,
                    description=t.get("description", ""),
                    values_summary=t.get("values_summary"),
                    evidence_refs=t.get("evidence_refs"),
                )
                self._trends_list.add_widget(card)
        
        # Drift - with visibility gate
        drifts = data.get("drift_warnings", [])
        visible_drifts = [
            d for d in drifts
            if d.get("data_points", 1) > 0
            and (d.get("evidence_refs") or d.get("values_summary"))
            and d.get("metric_name")  # Must have metric name
            and d.get("direction")    # Must have direction
        ]
        
        if not visible_drifts:
            self._drift_list.set_empty_message("No drift warnings in this window.")
        else:
            for d in visible_drifts:
                confidence = _apply_confidence_hygiene(
                    d.get("confidence", "low"),
                    d.get("data_points", 1),
                    d.get("time_span_hours", 0)
                )
                card = FindingCard(
                    "DRIFT",
                    d.get("metric_name"),
                    d.get("direction"),
                    confidence,
                    description=d.get("description", ""),
                    values_summary=d.get("values_summary"),
                    evidence_refs=d.get("evidence_refs"),
                )
                self._drift_list.add_widget(card)
        
        # Patterns - with visibility gate
        # GATE: Suppress patterns with occurrence_count == 0 OR empty evidence
        patterns = data.get("recurring_patterns", [])
        
        # Filter to only evidence-backed patterns
        visible_patterns = [
            p for p in patterns
            if p.get("data_points", 0) > 0 
            and p.get("evidence_refs")  # Non-empty evidence list
        ]
        
        if not visible_patterns:
            self._patterns_list.set_empty_message("No stable patterns detected in this window.")
        else:
            for p in visible_patterns:
                # Extract pattern type from metric_name for better display
                metric_name = p.get("metric_name", "unknown")
                pattern_type = "PATTERN"
                
                if metric_name.startswith("advisory_intent:"):
                    pattern_type = "INTENT"
                    display_name = metric_name.replace("advisory_intent:", "")
                elif metric_name.startswith("cooccurrence:"):
                    pattern_type = "CO-OCCUR"
                    display_name = metric_name.replace("cooccurrence:", "")
                elif metric_name.startswith("trend_repeat:"):
                    pattern_type = "REPEAT"
                    display_name = metric_name.replace("trend_repeat:", "")
                else:
                    display_name = metric_name
                
                # Get time window from values_summary
                values = p.get("values_summary", {})
                time_window = values.get("time_window_hours", 0)
                data_points = p.get("data_points", 0)
                
                # CONFIDENCE HYGIENE
                confidence = _apply_confidence_hygiene(
                    p.get("confidence", "low"),
                    data_points,
                    time_window
                )
                
                # Build direction-like summary for display
                summary = f"{data_points} occurrences"
                if time_window > 0:
                    summary += f" / {time_window:.1f}h"
                
                card = FindingCard(
                    pattern_type,
                    display_name,
                    summary,
                    confidence,
                    description=p.get("description", ""),
                    values_summary=values,
                    evidence_refs=p.get("evidence_refs"),
                )
                self._patterns_list.add_widget(card)
        
        # Last analysis
        last_ts = data.get("last_analysis_ts", "")
        if last_ts:
            self._last_analysis.setText(f"Last analysis: {last_ts[:19]}")
        else:
            self._last_analysis.setText("Last analysis: Never")


class ControlsPanel(QWidget):
    """
    Panel with action buttons.
    
    CONSTRAINT: Each button calls existing API endpoint only.
    """
    
    action_completed = Signal(str, bool, str)  # action_id, success, message
    
    def __init__(self, client: CalyxAPIClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._client = client
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Controls")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Notice
        notice = QLabel(
            "These controls trigger API actions.\n"
            "Station Calyx is advisory-only and does not execute system commands."
        )
        notice.setProperty("class", "dim")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        
        # Buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        
        self._snapshot_btn = ActionButton(
            "Capture Snapshot",
            "snapshot",
            "Capture current system state",
        )
        self._snapshot_btn.action_triggered.connect(self._on_action)
        buttons_layout.addWidget(self._snapshot_btn)
        
        self._reflect_btn = ActionButton(
            "Generate Reflection",
            "reflect",
            "Analyze recent events",
        )
        self._reflect_btn.action_triggered.connect(self._on_action)
        buttons_layout.addWidget(self._reflect_btn)
        
        self._advise_btn = ActionButton(
            "Generate Advisory",
            "advise",
            "Generate context-aware advisory",
        )
        self._advise_btn.action_triggered.connect(self._on_action)
        buttons_layout.addWidget(self._advise_btn)
        
        self._temporal_btn = ActionButton(
            "Run Temporal Analysis",
            "temporal",
            "Analyze trends over time",
        )
        self._temporal_btn.action_triggered.connect(self._on_action)
        buttons_layout.addWidget(self._temporal_btn)
        
        layout.addLayout(buttons_layout)
        
        # Status
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)
        
        layout.addStretch()
    
    def _on_action(self, action_id: str) -> None:
        """Handle action button click."""
        self._set_buttons_enabled(False)
        self._status_label.setText(f"Running {action_id}...")
        
        # Execute action
        if action_id == "snapshot":
            response = self._client.capture_snapshot()
        elif action_id == "reflect":
            response = self._client.run_reflection()
        elif action_id == "advise":
            response = self._client.generate_advisory()
        elif action_id == "temporal":
            response = self._client.run_temporal_analysis()
        else:
            response = None
        
        self._set_buttons_enabled(True)
        
        if response and response.success:
            msg = response.data.get("message", "Action completed") if response.data else "Done"
            self._status_label.setText(f"? {msg}")
            self._status_label.setStyleSheet(f"color: {COLORS['success']};")
            self.action_completed.emit(action_id, True, msg)
        else:
            error = response.error if response else "Unknown error"
            self._status_label.setText(f"? {error}")
            self._status_label.setStyleSheet(f"color: {COLORS['error']};")
            self.action_completed.emit(action_id, False, error)
    
    def _set_buttons_enabled(self, enabled: bool) -> None:
        self._snapshot_btn.setEnabled(enabled)
        self._reflect_btn.setEnabled(enabled)
        self._advise_btn.setEnabled(enabled)
        self._temporal_btn.setEnabled(enabled)
