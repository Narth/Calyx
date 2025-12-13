# -*- coding: utf-8 -*-
"""
Station Calyx Desktop Shell
===========================

A graphical interface for Station Calyx Ops Reflector.

ROLE: presentation_layer
SCOPE: Visual display and user interaction only

INVARIANTS:
- HUMAN_PRIMACY: Advisory-only display
- EXECUTION_GATE: Cannot execute commands (UI triggers API only)
- NO_HIDDEN_CHANNELS: All actions map 1:1 to API calls

CONSTRAINTS:
- VIEW + TRIGGER layer only
- All logic remains in service/API
- No direct evidence writes
- No conversational UI
"""

__version__ = "1.6.0"  # Milestone 8A: Presentation Integrity

COMPONENT_ROLE = "presentation_layer"
COMPONENT_SCOPE = "visual display and user interaction"
