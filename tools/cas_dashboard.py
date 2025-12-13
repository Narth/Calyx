#!/usr/bin/env python3
"""
CAS Dashboard - Real-time autonomy monitoring and visualization
"""

import json
import time
import curses
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from cas import CASCalculator

class CASDashboard:
    """Real-time CAS dashboard for monitoring station autonomy"""

    def __init__(self):
        self.cas_calc = CASCalculator()
        self.running = False
        self.screen = None

    def start_dashboard(self):
        """Start the interactive dashboard"""
        try:
            self.screen = curses.initscr()
            curses.noecho()
            curses.cbreak()
            curses.curs_set(0)
            self.screen.keypad(True)
            self.running = True

            # Start update thread
            update_thread = threading.Thread(target=self._update_loop, daemon=True)
            update_thread.start()

            # Main UI loop
            self._run_ui()

        except KeyboardInterrupt:
            pass
        finally:
            self.stop_dashboard()

    def stop_dashboard(self):
        """Stop the dashboard"""
        self.running = False
        if self.screen:
            curses.nocbreak()
            self.screen.keypad(False)
            curses.echo()
            curses.endwin()

    def _update_loop(self):
        """Background update loop"""
        while self.running:
            try:
                time.sleep(5)  # Update every 5 seconds
            except Exception:
                break

    def _run_ui(self):
        """Main UI rendering loop"""
        while self.running:
            try:
                self._render_dashboard()
                key = self.screen.getch()

                if key == ord('q') or key == 27:  # q or ESC
                    break
                elif key == ord('r'):  # Refresh
                    continue
                elif key == ord('c'):  # Show current autonomy summary
                    self._show_autonomy_summary()
                elif key == ord('a'):  # Show agent status cards
                    self._show_agent_status_cards()

            except KeyboardInterrupt:
                break

    def _render_dashboard(self):
        """Render the main dashboard"""
        self.screen.clear()

        # Header
        header = "Station Calyx - CAS (Calyx Autonomy Score) Dashboard"
        self.screen.addstr(0, 0, header)
        self.screen.addstr(1, 0, "=" * len(header))

        # Current metrics
        try:
            summary = self.cas_calc.get_autonomy_summary()
            station_cas = summary['station_cas_30d']
            autonomy_level = summary['autonomy_level']

            self.screen.addstr(3, 0, f"Station CAS (30d): {station_cas:.3f}")
            self.screen.addstr(4, 0, f"Autonomy Level: {autonomy_level}")
            self.screen.addstr(5, 0, f"Total Tasks: {summary['total_tasks_scored']}")

            # Progress bar
            progress_width = 50
            progress = int((station_cas / 1.0) * progress_width)
            progress_bar = "█" * progress + "░" * (progress_width - progress)
            self.screen.addstr(7, 0, f"Progress: [{progress_bar}] {station_cas:.1%}")

            # Next milestones
            self.screen.addstr(9, 0, "Next Milestones:")
            for i, milestone in enumerate(summary['next_milestones'][:3], 1):
                self.screen.addstr(9 + i, 0, f"  {i}. {milestone}")

            # Agent contributions
            if summary['agent_contributions']:
                self.screen.addstr(13, 0, "Agent Contributions (7d):")
                for i, (agent, contrib) in enumerate(summary['agent_contributions'].items(), 1):
                    self.screen.addstr(13 + i, 0, f"  {agent}: {contrib:.3f}")

        except Exception as e:
            self.screen.addstr(3, 0, f"Error loading CAS data: {e}")

        # Controls
        self.screen.addstr(20, 0, "Controls: (q)uit | (r)efresh | (c)urrent status | (a)gent cards")
        self.screen.refresh()

    def _show_autonomy_summary(self):
        """Show detailed autonomy summary"""
        try:
            summary = self.cas_calc.get_autonomy_summary()

            # Create a new window for the summary
            height, width = 20, 80
            win = curses.newwin(height, width, 2, 2)
            win.box()

            win.addstr(1, 2, "Station Calyx - Detailed Autonomy Summary")
            win.addstr(2, 2, "=" * 50)

            lines = [
                f"Station CAS (30d): {summary['station_cas_30d']:.3f}",
                f"Station CAS (7d): {summary['station_cas_7d']:.3f}",
                f"Autonomy Level: {summary['autonomy_level']}",
                f"Total Tasks Scored: {summary['total_tasks_scored']}",
                f"Difficulty Distribution: {summary['difficulty_distribution']}",
            ]

            for i, line in enumerate(lines, 3):
                win.addstr(i, 2, line)

            win.addstr(height-2, 2, "Press any key to continue...")
            win.refresh()
            win.getch()

        except Exception as e:
            print(f"Error showing autonomy summary: {e}")

    def _show_agent_status_cards(self):
        """Show agent status cards"""
        try:
            # Get all agents
            agents = set()
            for task in self.cas_calc.task_history:
                agents.add(task.agent_id)

            if not agents:
                return

            # Show status card for first agent (or specific agent)
            agent_id = next(iter(agents))  # Get first agent
            status_card = self.cas_calc.generate_agent_status_card(agent_id)

            # Create window for status card
            lines = status_card.split('\n')
            height = len(lines) + 4
            width = max(len(line) for line in lines) + 4

            win = curses.newwin(height, width, 2, 2)
            win.box()

            win.addstr(1, 2, f"Agent Status Card - {agent_id}")
            win.addstr(2, 2, "=" * (width - 4))

            for i, line in enumerate(lines, 3):
                win.addstr(i, 2, line)

            win.addstr(height-2, 2, "Press any key to continue...")
            win.refresh()
            win.getch()

        except Exception as e:
            print(f"Error showing agent status: {e}")

def main():
    """Main function for CAS dashboard"""
    import argparse

    parser = argparse.ArgumentParser(description='CAS Dashboard - Real-time autonomy monitoring')
    parser.add_argument('--web', action='store_true', help='Run web-based dashboard (not implemented)')
    parser.add_argument('--text', action='store_true', help='Run text-based dashboard')

    args = parser.parse_args()

    if args.web:
        print("Web dashboard not yet implemented. Use --text for terminal dashboard.")
        return
    elif args.text:
        dashboard = CASDashboard()
        try:
            dashboard.start_dashboard()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
    else:
        # Default: run text dashboard
        print("Starting CAS Dashboard...")
        dashboard = CASDashboard()
        try:
            dashboard.start_dashboard()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")

if __name__ == "__main__":
    main()
