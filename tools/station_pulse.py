#!/usr/bin/env python3
"""Station Pulse — Traffic Flow Dashboard for Station Calyx

A calm, human-aligned monitoring interface showing Station Calyx as a city's
traffic network. Provides 10-second orientation: what is alive, what is dormant,
what needs attention, and whether human oversight is required.

Experience Principles (Invariants):
- Calm at rest: No motion without meaning, soft colors, gentle rhythms
- Motion without urgency: Updates flow naturally, no flashing or alarms
- 10-second orientation: Summary → Lanes → Status in under 10 seconds
- Decide whether, not where: Shows if attention is needed, not what to fix
- Alerts inform, not command: Banners guide, toasts remind, nothing demands

Usage:
    python -u tools/station_pulse.py
    python -u tools/station_pulse.py --interval 3 --theme neon
    python -u tools/station_pulse.py --export-snapshot output.json

Metaphor:
    Agents = vehicles moving through city intersections
    Heartbeats = position reports from each vehicle
    Services = traffic signals and flow controllers
    CBO = central dispatch coordinating lanes and timing
    Gates = on-ramps and access controls
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading

# --- Paths ---
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
METRICS = ROOT / "metrics"
BRIDGE_LOCK = OUT / "bridge.lock"
CBO_LOCK = OUT / "cbo.lock"
CBO_DIALOG = OUT / "bridge" / "dialog.log"
CBO_GOALS = OUT / "bridge" / "user_goals"
CAPACITY_FLAGS = OUT / "capacity.flags.json"
GATES_DIR = OUT / "gates"
ICONS_FILE = OUT / "watcher_icons.json"
BRIDGE_PULSE_CSV = METRICS / "bridge_pulse.csv"


# --- Experience Themes ---
THEMES = {
    "calm": {
        "bg": "#f6f8fa",
        "fg": "#24292f",
        "accent": "#0969da",      # accent color for headers/emphasis
        "moving": "#2da44e",      # soft green
        "idling": "#bf8700",      # soft amber
        "parked": "#0969da",      # soft blue
        "stalled": "#cf222e",     # soft red
        "offline": "#57606a",     # soft gray
        "banner_warn": "#fff8c5", # pale yellow
        "banner_crit": "#ffebe9", # pale red
    },
    "neon": {
        "bg": "#0d1117",
        "fg": "#c9d1d9",
        "accent": "#58a6ff",      # accent color for headers/emphasis
        "moving": "#3fb950",
        "idling": "#d29922",
        "parked": "#58a6ff",
        "stalled": "#ff7b72",
        "offline": "#8b949e",
        "banner_warn": "#312d1f",
        "banner_crit": "#3d1f1f",
    },
}


# --- Enums for Flow State ---
class FlowState(Enum):
    """Traffic flow state for an agent (vehicle)"""
    MOVING = "moving"      # Fresh heartbeat, active status
    IDLING = "idling"      # Fresh heartbeat, idle/done status
    PARKED = "parked"      # Stale 1-5 minutes, not critical
    STALLED = "stalled"    # Stale >5 minutes or error state
    OFFLINE = "offline"    # No heartbeat file exists


class SystemPosture(Enum):
    """Overall city traffic posture"""
    CALM = "Calm"                    # Few active, no issues
    MODERATE = "Moderate"            # Normal activity, coordinated
    CONGESTION = "Congestion"        # High activity or minor issues
    DISTRESSED = "Distressed"        # Critical issues detected


class Lane(Enum):
    """Traffic lanes grouping agents by function"""
    BUILDER = "Builder"          # Agent1-4, execution workers
    SCHEDULER = "Scheduler"      # Scheduler agents (light task cycles)
    OVERSIGHT = "Oversight"      # CBO, CP6-CP13, coordinators
    SERVICE = "Service"          # Triage, Navigator, Manifest, etc.
    MONITORING = "Monitoring"    # Watcher, telemetry collectors
    UNKNOWN = "Unknown"          # Unclassified agents


# --- Data Structures ---
@dataclass
class AgentState:
    """State snapshot of a single agent (vehicle in the traffic network)"""
    name: str
    pid: Optional[int] = None
    status: str = "unknown"
    phase: str = "unknown"
    ts: Optional[float] = None
    goal_preview: str = ""
    run_dir: str = ""
    applied: bool = False
    changed_files: List[str] = field(default_factory=list)
    status_message: str = ""
    
    # Derived fields
    age_seconds: float = 0.0
    flow_state: FlowState = FlowState.OFFLINE
    lane: Lane = Lane.UNKNOWN
    icon: str = "⚙️"  # default icon
    
    def __post_init__(self):
        """Calculate derived fields"""
        if self.ts:
            self.age_seconds = max(0.0, time.time() - self.ts)
            self.flow_state = self._classify_flow_state()
    
    def _classify_flow_state(self) -> FlowState:
        """Classify agent into traffic flow state (Task 4)"""
        if self.ts is None:
            return FlowState.OFFLINE
        
        age = self.age_seconds
        
        # Stalled: >5 minutes old OR error status
        if age > 300 or self.status == "error":
            return FlowState.STALLED
        
        # Parked: 1-5 minutes old
        if age > 60:
            return FlowState.PARKED
        
        # Fresh heartbeat (<60s) - check activity
        if self.status in ("running", "working", "executing", "planning"):
            return FlowState.MOVING
        
        # Fresh but idle/done
        return FlowState.IDLING
    
    def age_display(self) -> str:
        """Human-readable age string"""
        if self.ts is None:
            return "—"
        age = self.age_seconds
        if age < 1:
            return f"{int(age*1000)}ms"
        if age < 60:
            return f"{int(age)}s"
        m = int(age // 60)
        s = int(age % 60)
        return f"{m}m {s}s"


@dataclass
class CBOStatus:
    """CBO dispatch intersection status"""
    phase: str = "unknown"
    status: str = "idle"
    queue_size: int = 0
    current_goal: str = ""
    dialog_tail: str = ""
    ts: Optional[float] = None


@dataclass
class GateStatus:
    """Access control gates (on-ramps)"""
    apply: bool = False
    llm: bool = False
    gpu: bool = False
    network: bool = False


@dataclass
class SystemSnapshot:
    """Complete system state snapshot"""
    agents: Dict[str, AgentState] = field(default_factory=dict)
    cbo: CBOStatus = field(default_factory=CBOStatus)
    gates: GateStatus = field(default_factory=GateStatus)
    posture: SystemPosture = SystemPosture.CALM
    tes_score: Optional[float] = None
    capacity_ok: bool = True
    alert_messages: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def active_count(self) -> int:
        """Count agents with fresh heartbeats"""
        return sum(1 for a in self.agents.values() 
                   if a.flow_state in (FlowState.MOVING, FlowState.IDLING))
    
    def stalled_count(self) -> int:
        """Count stalled agents"""
        return sum(1 for a in self.agents.values() 
                   if a.flow_state == FlowState.STALLED)
    
    def total_count(self) -> int:
        """Total agent count (excluding offline)"""
        return sum(1 for a in self.agents.values() 
                   if a.flow_state != FlowState.OFFLINE)


# --- Core Data Readers (Tasks 2-7) ---

def read_heartbeat_file(path: Path) -> Optional[Dict[str, Any]]:
    """Read and parse a single heartbeat .lock file (Task 2)"""
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def scan_agent_heartbeats() -> Dict[str, AgentState]:
    """Scan outgoing/*.lock files and build agent states (Task 2)"""
    agents = {}
    
    if not OUT.exists():
        return agents
    
    for lock_file in OUT.glob("*.lock"):
        agent_name = lock_file.stem
        data = read_heartbeat_file(lock_file)
        
        if data is None:
            # Agent exists but heartbeat unreadable - mark as offline
            agents[agent_name] = AgentState(
                name=agent_name,
                flow_state=FlowState.OFFLINE
            )
            continue
        
        # Parse heartbeat data
        agent = AgentState(
            name=agent_name,
            pid=data.get("pid"),
            status=str(data.get("status", "unknown")),
            phase=str(data.get("phase", "unknown")),
            ts=data.get("ts"),
            goal_preview=str(data.get("goal_preview", ""))[:100],
            run_dir=str(data.get("run_dir", "")),
            applied=bool(data.get("applied", False)),
            changed_files=data.get("changed_files", []),
            status_message=str(data.get("status_message", "")),
        )
        
        agents[agent_name] = agent
    
    return agents


def classify_agent_lane(agent_name: str) -> Lane:
    """Classify agent into traffic lane by name pattern (Task 3)"""
    name_lower = agent_name.lower()
    
    # Builder lane: Agent1-4
    if name_lower in ("agent1", "agent2", "agent3", "agent4"):
        return Lane.BUILDER
    
    # Scheduler lane
    if "scheduler" in name_lower:
        return Lane.SCHEDULER
    
    # Oversight lane: CBO, CP6-CP13, copilots
    if name_lower in ("cbo", "bridge") or name_lower.startswith("cp"):
        return Lane.OVERSIGHT
    
    # Service lane: operational services
    if name_lower in ("triage", "navigator", "traffic_navigator", "manifest", 
                      "sysint", "svf", "llm_ready"):
        return Lane.SERVICE
    
    # Monitoring lane: observation/telemetry
    if name_lower in ("watcher", "uptime_tracker", "enhanced_metrics", 
                      "telemetry_sentinel", "metrics_cron"):
        return Lane.MONITORING
    
    return Lane.UNKNOWN


def load_agent_icons() -> Dict[str, str]:
    """Load agent icon mappings from watcher_icons.json (Task 3)"""
    try:
        if ICONS_FILE.exists():
            data = json.loads(ICONS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def read_cbo_status() -> CBOStatus:
    """Read CBO dispatch status (Task 6)"""
    status = CBOStatus()
    
    # Read bridge.lock or cbo.lock
    bridge_data = read_heartbeat_file(BRIDGE_LOCK)
    if bridge_data:
        status.phase = str(bridge_data.get("phase", "unknown"))
        status.status = str(bridge_data.get("status", "idle"))
        status.ts = bridge_data.get("ts")
    
    # Count queue size
    if CBO_GOALS.exists():
        status.queue_size = len(list(CBO_GOALS.glob("goal_*.txt")))
    
    # Read dialog tail
    if CBO_DIALOG.exists():
        try:
            lines = CBO_DIALOG.read_text(encoding="utf-8", errors="ignore").splitlines()
            if lines:
                status.dialog_tail = " ".join(lines[-2:])[:160]
        except OSError:
            pass
    
    return status


def read_gate_status() -> GateStatus:
    """Read access control gate states (Task 7)"""
    gates = GateStatus()
    
    if not GATES_DIR.exists():
        return gates
    
    gates.apply = (GATES_DIR / "apply.ok").exists()
    gates.llm = (GATES_DIR / "llm.ok").exists()
    gates.gpu = (GATES_DIR / "gpu.ok").exists()
    gates.network = (GATES_DIR / "network.ok").exists()
    
    return gates


def read_capacity_status() -> bool:
    """Read capacity flags (Task 7)"""
    try:
        if CAPACITY_FLAGS.exists():
            data = json.loads(CAPACITY_FLAGS.read_text(encoding="utf-8"))
            # If any capacity flag is False, system is not OK
            if isinstance(data, dict):
                return all(data.values())
    except (json.JSONDecodeError, OSError):
        pass
    return True  # Assume OK if file missing or unreadable


def read_latest_tes() -> Optional[float]:
    """Read latest TES score from bridge_pulse.csv (Task 5)"""
    try:
        if BRIDGE_PULSE_CSV.exists():
            lines = BRIDGE_PULSE_CSV.read_text(encoding="utf-8").splitlines()
            if len(lines) > 1:
                last_line = lines[-1]
                # Parse CSV: timestamp,phase,status,details
                # details contains tes_mean20=XX.X
                if "tes_mean20=" in last_line:
                    tes_str = last_line.split("tes_mean20=")[1].split()[0]
                    return float(tes_str)
    except (OSError, ValueError, IndexError):
        pass
    return None


def calculate_system_posture(snapshot: SystemSnapshot) -> SystemPosture:
    """Calculate overall system posture (Task 5)"""
    active = snapshot.active_count()
    stalled = snapshot.stalled_count()
    tes = snapshot.tes_score or 100.0
    
    # Distressed: stalled agents, low TES, or capacity issues
    if stalled > 0 or tes < 80 or not snapshot.capacity_ok:
        return SystemPosture.DISTRESSED
    
    # Congestion: high activity or moderate TES drop
    if active > 8 or tes < 90:
        return SystemPosture.CONGESTION
    
    # Moderate: normal activity
    if active > 3:
        return SystemPosture.MODERATE
    
    # Calm: low activity, everything healthy
    return SystemPosture.CALM


def detect_alerts(snapshot: SystemSnapshot) -> List[str]:
    """Detect critical states requiring human attention (Task 8)"""
    alerts = []
    
    # Stalled agents
    for name, agent in snapshot.agents.items():
        if agent.flow_state == FlowState.STALLED:
            age_min = int(agent.age_seconds // 60)
            alerts.append(f"⚠️ {name} stalled for {age_min} minutes · Status: {agent.status}")
    
    # TES drop
    if snapshot.tes_score and snapshot.tes_score < 80:
        alerts.append(f"⚠️ TES score dropped to {snapshot.tes_score:.1f}% (threshold: 80%)")
    
    # Capacity warnings
    if not snapshot.capacity_ok:
        alerts.append("⚠️ System capacity warning detected")
    
    # CBO queue overflow
    if snapshot.cbo.queue_size > 10:
        alerts.append(f"⚠️ CBO queue overflow: {snapshot.cbo.queue_size} pending goals")
    
    return alerts


def collect_system_snapshot() -> SystemSnapshot:
    """Collect complete system state snapshot (Tasks 2-7)"""
    # Read agents
    agents = scan_agent_heartbeats()
    
    # Load icons
    icons = load_agent_icons()
    
    # Classify lanes and apply icons
    for name, agent in agents.items():
        agent.lane = classify_agent_lane(name)
        agent.icon = icons.get(name, "⚙️")
    
    # Read system state
    cbo = read_cbo_status()
    gates = read_gate_status()
    capacity_ok = read_capacity_status()
    tes = read_latest_tes()
    
    # Build snapshot
    snapshot = SystemSnapshot(
        agents=agents,
        cbo=cbo,
        gates=gates,
        tes_score=tes,
        capacity_ok=capacity_ok,
    )
    
    # Calculate posture
    snapshot.posture = calculate_system_posture(snapshot)
    
    # Detect alerts
    snapshot.alert_messages = detect_alerts(snapshot)
    
    return snapshot


# --- UI Components (Tasks 9-14) ---

class StationPulseDashboard:
    """Main dashboard window with calm, traffic-flow-oriented UI"""
    
    def __init__(self, interval: int = 2, theme_name: str = "calm"):
        self.interval = interval
        self.theme = THEMES[theme_name]
        self.running = True
        self.snapshot = collect_system_snapshot()
        self.last_snapshot_hash = ""
        self.alert_shown_ts = {}  # Track when each alert was first shown
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Station Pulse — Station Calyx Traffic Flow")
        self.root.geometry("1200x800")
        self.root.configure(bg=self.theme["bg"])
        
        # Build UI
        self._build_ui()
        
        # Start refresh thread
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
    
    def _build_ui(self):
        """Build the main UI layout (Task 9) - Enhanced for visibility"""
        # Summary bar at top - ENHANCED
        self.summary_frame = tk.Frame(self.root, bg=self.theme["bg"], height=80, relief="solid", borderwidth=2)
        self.summary_frame.pack(fill="x", padx=10, pady=10)
        self.summary_frame.pack_propagate(False)
        
        self.summary_label = tk.Label(
            self.summary_frame,
            text="",
            font=("Arial", 18, "bold"),  # Larger font
            bg=self.theme["bg"],
            fg=self.theme["fg"],
            anchor="w"
        )
        self.summary_label.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        self.gate_label = tk.Label(
            self.summary_frame,
            text="",
            font=("Arial", 12, "bold"),  # Larger, bolder
            bg=self.theme["bg"],
            fg=self.theme["fg"],
            anchor="e"
        )
        self.gate_label.pack(side="right", padx=15, pady=10)
        
        # Alert banner (hidden by default) - ENHANCED
        self.alert_banner = tk.Frame(self.root, bg=self.theme["banner_warn"], height=50, relief="raised", borderwidth=3)
        self.alert_banner.pack(fill="x", padx=10, pady=5)
        self.alert_banner.pack_forget()  # Hide initially
        
        self.alert_label = tk.Label(
            self.alert_banner,
            text="",
            font=("Arial", 12, "bold"),  # Larger, bold
            bg=self.theme["banner_warn"],
            fg="black",  # Force black for contrast
            anchor="w"
        )
        self.alert_label.pack(side="left", fill="both", expand=True, padx=15, pady=8)
        
        dismiss_btn = tk.Button(
            self.alert_banner,
            text="✕ Dismiss",  # Icon + text
            command=self._dismiss_alert,
            font=("Arial", 10, "bold"),
            relief="flat",
            bg="#ffffff",
            fg="#000000",
            padx=10,
            pady=5
        )
        dismiss_btn.pack(side="right", padx=10)
        
        # Main content area - lanes in grid
        content_frame = tk.Frame(self.root, bg=self.theme["bg"])
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Lane columns (Builder, Oversight, Service, Scheduler, Monitoring)
        self.lane_frames = {}
        lane_order = [Lane.BUILDER, Lane.OVERSIGHT, Lane.SERVICE, Lane.SCHEDULER, Lane.MONITORING]
        
        for i, lane in enumerate(lane_order):
            lane_col = tk.Frame(content_frame, bg=self.theme["bg"], relief="groove", borderwidth=2)
            lane_col.grid(row=0, column=i, sticky="nsew", padx=5)
            content_frame.columnconfigure(i, weight=1)
            
            # Lane header - ENHANCED
            header = tk.Label(
                lane_col,
                text=f"━━ {lane.value} Lane ━━",  # Visual separator
                font=("Arial", 12, "bold"),  # Larger
                bg=self.theme["bg"],
                fg=self.theme["accent"],  # Use accent color
                anchor="center"  # Center for symmetry
            )
            header.pack(fill="x", pady=(5, 8))
            
            # Scrollable agent list
            canvas = tk.Canvas(lane_col, bg=self.theme["bg"], highlightthickness=0)
            scrollbar = tk.Scrollbar(lane_col, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=self.theme["bg"])
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            self.lane_frames[lane] = scrollable_frame
        
        content_frame.rowconfigure(0, weight=1)
        
        # Bottom status area - ENHANCED
        bottom_frame = tk.Frame(self.root, bg=self.theme["bg"], relief="solid", borderwidth=2)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        
        # CBO status - ENHANCED
        cbo_frame = tk.Frame(bottom_frame, bg=self.theme["bg"])
        cbo_frame.pack(fill="x", pady=8, padx=10)
        
        cbo_title = tk.Label(
            cbo_frame,
            text="🎯 CBO Dispatch:",
            font=("Arial", 12, "bold"),
            bg=self.theme["bg"],
            fg=self.theme["accent"],
            anchor="w"
        )
        cbo_title.pack(side="left", padx=5)
        
        self.cbo_label = tk.Label(
            cbo_frame,
            text="",
            font=("Arial", 11),  # Slightly larger
            bg=self.theme["bg"],
            fg=self.theme["fg"],
            anchor="w"
        )
        self.cbo_label.pack(side="left", fill="x", expand=True, padx=5)
        
        # Live feed - ENHANCED
        feed_label = tk.Label(
            bottom_frame,
            text="📡 Live Feed (last 60s):",
            font=("Arial", 11, "bold"),
            bg=self.theme["bg"],
            fg=self.theme["accent"],
            anchor="w"
        )
        feed_label.pack(fill="x", pady=(5, 5), padx=10)
        
        self.live_feed = scrolledtext.ScrolledText(
            bottom_frame,
            height=6,
            font=("Consolas", 10),  # Monospace, larger
            bg="#1e1e1e",  # Dark background for contrast
            fg="#e0e0e0",  # Light text
            wrap="word",
            state="disabled",
            relief="sunken",
            borderwidth=2
        )
        self.live_feed.pack(fill="x", padx=10, pady=(0, 8))
        
        # Initialize display
        self._update_display()
    
    def _update_display(self):
        """Update all UI elements from current snapshot (Task 10-11) - Enhanced"""
        s = self.snapshot
        
        # Summary bar - ENHANCED with emoji and better formatting
        posture_color = {
            SystemPosture.CALM: self.theme["moving"],
            SystemPosture.MODERATE: self.theme["idling"],
            SystemPosture.CONGESTION: self.theme["parked"],
            SystemPosture.DISTRESSED: self.theme["stalled"],
        }[s.posture]
        
        posture_emoji = {
            SystemPosture.CALM: "🟢",
            SystemPosture.MODERATE: "🟡",
            SystemPosture.CONGESTION: "🟠",
            SystemPosture.DISTRESSED: "🔴",
        }[s.posture]
        
        tes_display = f"TES: {s.tes_score:.1f}%" if s.tes_score else "TES: —"
        summary_text = f"{posture_emoji} Active: {s.active_count()}/{s.total_count()}  •  {tes_display}  •  Flow: {s.posture.value.upper()}"
        self.summary_label.config(text=summary_text, fg=posture_color)
        
        # Gates display - ENHANCED with better icons and colors
        gate_parts = []
        gate_colors = []
        
        if s.gates.apply:
            gate_parts.append("Apply ✓")
            gate_colors.append("#00cc00")  # Green
        else:
            gate_parts.append("Apply ✗")
            gate_colors.append("#666666")  # Gray
            
        if s.gates.llm:
            gate_parts.append("LLM ✓")
            gate_colors.append("#00cc00")
        else:
            gate_parts.append("LLM ✗")
            gate_colors.append("#666666")
            
        if s.gates.gpu:
            gate_parts.append("GPU ✓")
            gate_colors.append("#00cc00")
        else:
            gate_parts.append("GPU ✗")
            gate_colors.append("#666666")
            
        if s.gates.network:
            gate_parts.append("Net ✓")
            gate_colors.append("#00cc00")
        else:
            gate_parts.append("Net ✗")
            gate_colors.append("#666666")
        
        # For BitNet gate (if exists in snapshot)
        if hasattr(s.gates, 'bitnet'):
            if s.gates.bitnet:
                gate_parts.append("BitNet ✓")
                gate_colors.append("#00cc00")
            else:
                gate_parts.append("BitNet ✗")
                gate_colors.append("#666666")
        
        gate_text = "Gates:  " + "  |  ".join(gate_parts)
        # Use first color for now (could create multi-color label if needed)
        self.gate_label.config(text=gate_text, fg=gate_colors[0] if all(c == gate_colors[0] for c in gate_colors) else self.theme["fg"])
        
        # Alert banner (Task 13) - ENHANCED
        if s.alert_messages:
            # Show first alert
            alert_text = "⚠️  " + s.alert_messages[0]
            self.alert_label.config(text=alert_text)
            
            # Determine banner color
            if any("stalled" in a.lower() for a in s.alert_messages) or s.posture == SystemPosture.DISTRESSED:
                self.alert_banner.config(bg="#ff4444")  # Brighter red
                self.alert_label.config(bg="#ff4444", fg="white")
            else:
                self.alert_banner.config(bg="#ffaa00")  # Brighter orange
                self.alert_label.config(bg="#ffaa00", fg="black")
            
            self.alert_banner.pack(fill="x", padx=10, pady=(0, 5))
            
            # Track alert timing for potential toast
            alert_key = alert_text[:50]
            if alert_key not in self.alert_shown_ts:
                self.alert_shown_ts[alert_key] = time.time()
        else:
            self.alert_banner.pack_forget()
            self.alert_shown_ts.clear()
        
        # Update agent lanes (Task 10)
        for lane, frame in self.lane_frames.items():
            # Clear existing widgets
            for widget in frame.winfo_children():
                widget.destroy()
            
            # Get agents in this lane
            agents_in_lane = [a for a in s.agents.values() if a.lane == lane]
            agents_in_lane.sort(key=lambda a: (a.flow_state.value, a.name))
            
            for agent in agents_in_lane:
                self._create_agent_card(frame, agent)
        
        # CBO status - ENHANCED with icons and formatting
        phase_emoji = {
            "unknown": "❓",
            "idle": "💤",
            "working": "⚙️",
            "dispatching": "🎯",
        }.get(s.cbo.phase.lower(), "⚙️")
        
        cbo_text = f"{phase_emoji} Phase: {s.cbo.phase.upper()}  •  Queue: {s.cbo.queue_size}  •  Status: {s.cbo.status}"
        if s.cbo.dialog_tail:
            cbo_text += f"\n💬 {s.cbo.dialog_tail}"
        self.cbo_label.config(text=cbo_text)
        
        # Live feed - append new events (Task 11)
        # For now, just show recent agent transitions
        # In a full implementation, this would track state changes
    
    def _create_agent_card(self, parent, agent: AgentState):
        """Create a single agent card/row (Task 10) - Enhanced for visibility"""
        # Get color for flow state
        color = {
            FlowState.MOVING: self.theme["moving"],
            FlowState.IDLING: self.theme["idling"],
            FlowState.PARKED: self.theme["parked"],
            FlowState.STALLED: self.theme["stalled"],
            FlowState.OFFLINE: self.theme["offline"],
        }[agent.flow_state]
        
        # Card frame - ENHANCED with more padding and border
        card = tk.Frame(parent, bg=self.theme["bg"], relief="raised", borderwidth=1)
        card.pack(fill="x", pady=4, padx=5)
        
        # Color indicator - ENHANCED larger and bolder
        indicator = tk.Label(
            card,
            text="⬤",  # Larger circle
            font=("Arial", 14, "bold"),
            bg=self.theme["bg"],
            fg=color,
            width=2
        )
        indicator.pack(side="left", padx=5)
        
        # Agent icon and name - ENHANCED
        name_label = tk.Label(
            card,
            text=f"{agent.icon} {agent.name}",
            font=("Arial", 11, "bold"),  # Larger, bold
            bg=self.theme["bg"],
            fg=self.theme["fg"],
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True, padx=5)
        
        # Age display - ENHANCED
        age_label = tk.Label(
            card,
            text=agent.age_display(),
            font=("Arial", 10),  # Larger
            bg=self.theme["bg"],
            fg=self.theme["offline"],
            anchor="e"
        )
        age_label.pack(side="right", padx=8)
        
        # Status indicator - NEW
        status_text = agent.status if agent.status else agent.flow_state.value
        status_label = tk.Label(
            card,
            text=f"[{status_text}]",
            font=("Arial", 9, "italic"),
            bg=self.theme["bg"],
            fg=color,
            anchor="e"
        )
        status_label.pack(side="right", padx=5)
        
        # Make card clickable for details (Task 14)
        for widget in [card, indicator, name_label, age_label, status_label]:
            widget.bind("<Button-1>", lambda e, a=agent: self._show_agent_details(a))
            widget.bind("<Enter>", lambda e, c=card: c.config(relief="solid", borderwidth=2, bg="#e8e8e8"))
            widget.bind("<Leave>", lambda e, c=card: c.config(relief="raised", borderwidth=1, bg=self.theme["bg"]))
    
    def _show_agent_details(self, agent: AgentState):
        """Show detailed agent information in popup (Task 14)"""
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Agent Details: {agent.name}")
        detail_window.geometry("600x400")
        detail_window.configure(bg=self.theme["bg"])
        
        # Details text
        details_text = scrolledtext.ScrolledText(
            detail_window,
            font=("Courier New", 9),
            bg=self.theme["bg"],
            fg=self.theme["fg"],
            wrap="word"
        )
        details_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Format details
        details = f"""Agent: {agent.name}
Icon: {agent.icon}
Lane: {agent.lane.value}
Flow State: {agent.flow_state.value}

Status: {agent.status}
Phase: {agent.phase}
PID: {agent.pid if agent.pid else "—"}
Age: {agent.age_display()}
Last Heartbeat: {datetime.fromtimestamp(agent.ts).isoformat() if agent.ts else "—"}

Goal Preview:
{agent.goal_preview if agent.goal_preview else "—"}

Status Message:
{agent.status_message if agent.status_message else "—"}

Run Directory:
{agent.run_dir if agent.run_dir else "—"}

Applied: {agent.applied}
Changed Files: {len(agent.changed_files)}
"""
        details_text.insert("1.0", details)
        details_text.config(state="disabled")
    
    def _dismiss_alert(self):
        """Dismiss the alert banner"""
        self.alert_banner.pack_forget()
        self.alert_shown_ts.clear()
    
    def _refresh_loop(self):
        """Background refresh loop (Task 12)"""
        while self.running:
            time.sleep(self.interval)
            
            # Collect new snapshot
            new_snapshot = collect_system_snapshot()
            
            # Calculate hash to detect changes
            snapshot_hash = hash((
                new_snapshot.posture,
                new_snapshot.active_count(),
                tuple(new_snapshot.alert_messages),
                tuple((a.name, a.flow_state, int(a.age_seconds // 10)) 
                      for a in new_snapshot.agents.values())
            ))
            
            # Only update UI if something meaningful changed
            if snapshot_hash != self.last_snapshot_hash:
                self.snapshot = new_snapshot
                self.last_snapshot_hash = snapshot_hash
                
                # Update display in main thread
                self.root.after(0, self._update_display)
    
    def run(self):
        """Start the dashboard"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()


# --- CLI Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="Station Pulse - Traffic Flow Dashboard for Station Calyx"
    )
    parser.add_argument("--interval", type=int, default=2,
                       help="Refresh interval in seconds (default: 2)")
    parser.add_argument("--theme", choices=["calm", "neon"], default="calm",
                       help="Visual theme (default: calm)")
    parser.add_argument("--export-snapshot", type=str,
                       help="Export current snapshot to JSON file and exit")
    parser.add_argument("--console", action="store_true",
                       help="Console mode instead of GUI (for testing)")
    
    args = parser.parse_args()
    
    # Export mode
    if args.export_snapshot:
        snapshot = collect_system_snapshot()
        output = {
            "timestamp": snapshot.timestamp,
            "posture": snapshot.posture.value,
            "active_count": snapshot.active_count(),
            "total_count": snapshot.total_count(),
            "tes_score": snapshot.tes_score,
            "alerts": snapshot.alert_messages,
            "agents": {
                name: {
                    "flow_state": agent.flow_state.value,
                    "lane": agent.lane.value,
                    "age_seconds": agent.age_seconds,
                    "status": agent.status,
                }
                for name, agent in snapshot.agents.items()
            }
        }
        Path(args.export_snapshot).write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"Snapshot exported to {args.export_snapshot}")
        return 0
    
    # Console mode (for debugging/testing)
    if args.console:
        snapshot = collect_system_snapshot()
        print("Station Pulse Dashboard")
        print("=" * 60)
        print(f"Posture: {snapshot.posture.value}")
        print(f"Active: {snapshot.active_count()}/{snapshot.total_count()}")
        if snapshot.tes_score:
            print(f"TES: {snapshot.tes_score:.1f}%")
        print()
        
        if snapshot.alert_messages:
            print("Alerts:")
            for alert in snapshot.alert_messages:
                print(f"  {alert}")
            print()
        
        print("Agents by lane:")
        for lane in Lane:
            agents_in_lane = [a for a in snapshot.agents.values() if a.lane == lane]
            if agents_in_lane:
                print(f"\n{lane.value} Lane:")
                for agent in sorted(agents_in_lane, key=lambda a: a.name):
                    state_symbol = {
                        FlowState.MOVING: "🟢",
                        FlowState.IDLING: "🟡",
                        FlowState.PARKED: "🔵",
                        FlowState.STALLED: "🔴",
                        FlowState.OFFLINE: "⚫",
                    }[agent.flow_state]
                    print(f"  {state_symbol} {agent.icon} {agent.name} ({agent.age_display()})")
        
        return 0
    
    # GUI mode
    dashboard = StationPulseDashboard(interval=args.interval, theme_name=args.theme)
    dashboard.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
