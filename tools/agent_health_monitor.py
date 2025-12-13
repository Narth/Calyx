#!/usr/bin/env python3
"""
Systems Resources Agent - Agent Health Monitor & Recovery System
Comprehensive monitoring and automatic recovery for all Calyx Terminal agents
"""

import psutil
import time
import json
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import yaml

@dataclass
class AgentStatus:
    """Agent health status information"""
    name: str
    lock_file: str
    expected_process: str
    priority: str
    is_running: bool
    last_seen: Optional[datetime]
    health_score: float
    recovery_attempts: int
    status_message: str

@dataclass
class HealthCheckResult:
    """Result of a health check cycle"""
    timestamp: datetime
    total_agents: int
    healthy_agents: int
    unhealthy_agents: int
    recovered_agents: int
    system_health_score: float

class AgentHealthMonitor:
    """Comprehensive agent monitoring and recovery system"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Agent definitions
        self.agents = self._initialize_agent_definitions()

        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.check_interval = 10  # seconds
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 60  # seconds

        # Health tracking
        self.health_history = []
        self.max_history = 1000

        # Recovery tracking
        self.recovery_log = {}

        # Setup logging
        self.logger = self._setup_logging()

    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            return {}

    def _initialize_agent_definitions(self) -> Dict[str, Dict]:
        """Initialize agent definitions and their expected states"""
        return {
            'agent1': {
                'lock_file': 'outgoing/agent1.lock',
                'expected_process': 'agent_console',
                'priority': 'high',
                'startup_command': 'python Scripts/agent_console.py',
                'description': 'Main operational agent'
            },
            'triage': {
                'lock_file': 'outgoing/triage.lock',
                'expected_process': 'triage_probe',
                'priority': 'critical',
                'startup_command': 'python tools/triage_probe.py --interval 30',
                'description': 'Diagnostic and health monitoring system'
            },
            'cp6': {
                'lock_file': 'outgoing/cp6.lock',
                'expected_process': 'cp6',
                'priority': 'normal',
                'startup_command': 'python Scripts/agent_cp6.py --interval 60',
                'description': 'Sociologist - Social interaction analysis'
            },
            'cp7': {
                'lock_file': 'outgoing/cp7.lock',
                'expected_process': 'cp7',
                'priority': 'normal',
                'startup_command': 'python Scripts/agent_cp7.py --interval 60',
                'description': 'Chronicler - System documentation and history'
            },
            'cp8': {
                'lock_file': 'outgoing/cp8.lock',
                'expected_process': 'cp8',
                'priority': 'normal',
                'startup_command': 'python Scripts/agent_cp8.py --interval 60',
                'description': 'Quartermaster - System upgrade management'
            },
            'cp9': {
                'lock_file': 'outgoing/cp9.lock',
                'expected_process': 'cp9',
                'priority': 'normal',
                'startup_command': 'python Scripts/agent_cp9.py --interval 60',
                'description': 'Auto-Tuner - Parameter optimization'
            },
            'cp10': {
                'lock_file': 'outgoing/cp10.lock',
                'expected_process': 'cp10',
                'priority': 'normal',
                'startup_command': 'python Scripts/agent_cp10.py --interval 60',
                'description': 'Whisperer - ASR optimization'
            },
            'svf': {
                'lock_file': 'outgoing/svf.lock',
                'expected_process': 'svf_probe',
                'priority': 'normal',
                'startup_command': 'python tools/svf_probe.py --interval 5',
                'description': 'SVF communication protocol manager'
            },
            'sysint': {
                'lock_file': 'outgoing/sysint.lock',
                'expected_process': 'sys_integrator',
                'priority': 'low',
                'startup_command': 'python tools/sys_integrator.py --interval 10',
                'description': 'Systems integrator and upgrade suggestions'
            },
            'teaching': {
                'lock_file': 'outgoing/ai4all.lock',
                'expected_process': 'ai4all_teaching',
                'priority': 'high',
                'startup_command': 'venvs/calyx-gpu/Scripts/python.exe Projects/AI_for_All/ai4all_teaching.py --start',
                'description': 'AI-for-All teaching system'
            }
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for agent health monitor"""
        logger = logging.getLogger('agent_health_monitor')
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        log_file = log_dir / "agent_health_monitor.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def check_lock_file_freshness(self, agent_name: str) -> Tuple[bool, Optional[datetime]]:
        """Check if agent's lock file is fresh (updated recently)"""
        agent_def = self.agents[agent_name]
        lock_path = Path(agent_def['lock_file'])

        if not lock_path.exists():
            return False, None

        try:
            # Check file modification time
            mtime = lock_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime)

            # Consider lock file stale if older than 5 minutes
            stale_threshold = datetime.now() - timedelta(minutes=5)

            is_fresh = last_modified > stale_threshold
            return is_fresh, last_modified

        except Exception as e:
            self.logger.error(f"Error checking lock file for {agent_name}: {e}")
            return False, None

    def check_process_running(self, agent_name: str) -> Tuple[bool, Optional[Dict]]:
        """Check if agent's process is currently running"""
        agent_def = self.agents[agent_name]
        expected_process = agent_def['expected_process']

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
                try:
                    proc_info = proc.info
                    if not proc_info['cmdline']:
                        continue

                    cmd_str = ' '.join(proc_info['cmdline']).lower()
                    if expected_process.lower() in cmd_str:
                        return True, {
                            'pid': proc_info['pid'],
                            'status': proc_info.get('status', 'unknown'),
                            'memory_percent': proc_info.get('memory_percent', 0),
                            'cpu_percent': proc_info.get('cpu_percent', 0)
                        }

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            self.logger.error(f"Error checking process for {agent_name}: {e}")

        return False, None

    def calculate_health_score(self, agent_name: str) -> float:
        """Calculate health score for an agent (0-100)"""
        lock_fresh, lock_time = self.check_lock_file_freshness(agent_name)
        process_running, process_info = self.check_process_running(agent_name)

        if lock_fresh and process_running:
            # Both lock file and process are healthy
            return 100.0
        elif lock_fresh and not process_running:
            # Lock file fresh but process not running (starting up or crashed)
            return 75.0
        elif not lock_fresh and process_running:
            # Process running but lock file stale (lock file not updating)
            return 60.0
        else:
            # Neither lock file nor process healthy
            return 0.0

    def get_agent_status(self, agent_name: str) -> AgentStatus:
        """Get comprehensive status for a specific agent"""
        lock_fresh, lock_time = self.check_lock_file_freshness(agent_name)
        process_running, process_info = self.check_process_running(agent_name)
        health_score = self.calculate_health_score(agent_name)

        # Determine status message
        if health_score >= 90:
            status_message = "Healthy and operational"
        elif health_score >= 60:
            status_message = "Degraded but functional"
        else:
            status_message = "Unhealthy or offline"

        return AgentStatus(
            name=agent_name,
            lock_file=self.agents[agent_name]['lock_file'],
            expected_process=self.agents[agent_name]['expected_process'],
            priority=self.agents[agent_name]['priority'],
            is_running=process_running,
            last_seen=lock_time,
            health_score=health_score,
            recovery_attempts=self.recovery_log.get(agent_name, 0),
            status_message=status_message
        )

    def attempt_agent_recovery(self, agent_name: str) -> bool:
        """Attempt to recover an unhealthy agent"""
        if agent_name not in self.agents:
            self.logger.error(f"Unknown agent: {agent_name}")
            return False

        # Check recovery cooldown
        last_recovery = self.recovery_log.get(f"{agent_name}_last_attempt", 0)
        if time.time() - last_recovery < self.recovery_cooldown:
            self.logger.info(f"Recovery attempt for {agent_name} on cooldown")
            return False

        # Check max attempts
        attempts = self.recovery_log.get(agent_name, 0)
        if attempts >= self.max_recovery_attempts:
            self.logger.warning(f"Max recovery attempts reached for {agent_name}")
            return False

        try:
            agent_def = self.agents[agent_name]
            startup_command = agent_def['startup_command']

            self.logger.info(f"[C:RECOVERY] — Systems Resources Agent: Attempting to recover {agent_name}")
            self.logger.info(f"[Agent • Systems Resources]: Starting: {startup_command}")

            # Start the agent process
            process = subprocess.Popen(
                startup_command.split(),
                cwd=str(Path(".").absolute()),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Update recovery log
            self.recovery_log[agent_name] = attempts + 1
            self.recovery_log[f"{agent_name}_last_attempt"] = time.time()
            self.recovery_log[f"{agent_name}_last_pid"] = process.pid

            self.logger.info(f"[C:RECOVERY] — Systems Resources Agent: Recovery attempt {attempts + 1} for {agent_name} (PID: {process.pid})")

            return True

        except Exception as e:
            self.logger.error(f"Failed to recover {agent_name}: {e}")
            self.recovery_log[agent_name] = attempts + 1
            self.recovery_log[f"{agent_name}_last_attempt"] = time.time()
            return False

    def perform_health_check_cycle(self) -> HealthCheckResult:
        """Perform one complete health check cycle"""
        cycle_start = datetime.now()
        results = {
            'total_agents': len(self.agents),
            'healthy_agents': 0,
            'unhealthy_agents': 0,
            'recovered_agents': 0,
            'agent_details': {}
        }

        for agent_name in self.agents.keys():
            status = self.get_agent_status(agent_name)
            results['agent_details'][agent_name] = asdict(status)

            if status.health_score >= 90:
                results['healthy_agents'] += 1
            else:
                results['unhealthy_agents'] += 1

                # Attempt recovery for unhealthy agents
                if self.attempt_agent_recovery(agent_name):
                    results['recovered_agents'] += 1

        # Calculate overall system health
        if results['total_agents'] > 0:
            system_health = (results['healthy_agents'] / results['total_agents']) * 100
        else:
            system_health = 0

        cycle_result = HealthCheckResult(
            timestamp=cycle_start,
            total_agents=results['total_agents'],
            healthy_agents=results['healthy_agents'],
            unhealthy_agents=results['unhealthy_agents'],
            recovered_agents=results['recovered_agents'],
            system_health_score=system_health
        )

        # Store in history
        self.health_history.append(cycle_result)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)

        # Log results
        self.logger.info(f"[C:HEALTH_CHECK] — Systems Resources Agent: Health check complete")
        self.logger.info(f"[Agent • Systems Resources]: Healthy: {results['healthy_agents']}/{results['total_agents']} ({system_health:.1f}%)")
        self.logger.info(f"[Agent • Systems Resources]: Recovered: {results['recovered_agents']} agents")

        if results['unhealthy_agents'] > 0:
            self.logger.warning(f"[Agent • Systems Resources]: Unhealthy agents: {results['unhealthy_agents']}")

        return cycle_result

    def start_monitoring(self, interval: Optional[int] = None):
        """Start continuous agent health monitoring"""
        if self.monitoring:
            self.logger.warning("Agent health monitoring already running")
            return

        self.monitoring = True
        self.check_interval = interval or self.check_interval

        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        self.logger.info(f"[C:MONITORING] — Systems Resources Agent: Started agent health monitoring ({self.check_interval}s intervals)")

    def stop_monitoring(self):
        """Stop continuous agent health monitoring"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        self.logger.info("[C:MONITORING] — Systems Resources Agent: Stopped agent health monitoring")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self.perform_health_check_cycle()

                # Save health status to file for other systems
                self._save_health_status()

                time.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

    def _save_health_status(self):
        """Save current health status for other systems"""
        try:
            status_data = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_active': self.monitoring,
                'check_interval': self.check_interval,
                'agents': {}
            }

            for agent_name in self.agents.keys():
                status_data['agents'][agent_name] = asdict(self.get_agent_status(agent_name))

            # Calculate overall system health from recent history
            if self.health_history:
                recent_checks = self.health_history[-5:]  # Last 5 checks
                avg_health = sum(check.system_health_score for check in recent_checks) / len(recent_checks)
                status_data['system_health_score'] = avg_health
            else:
                status_data['system_health_score'] = 0

            output_file = Path("outgoing") / "agent_health_status.json"
            with open(output_file, 'w') as f:
                json.dump(status_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Error saving health status: {e}")

    def get_monitoring_summary(self) -> Dict:
        """Get summary of monitoring data"""
        if not self.health_history:
            return {'error': 'No monitoring data available'}

        recent_checks = self.health_history[-10:]  # Last 10 checks

        return {
            'monitoring_duration': str(datetime.now() - self.health_history[0].timestamp) if len(self.health_history) > 1 else 'N/A',
            'total_health_checks': len(self.health_history),
            'average_system_health': round(sum(check.system_health_score for check in recent_checks) / len(recent_checks), 2),
            'total_agents': len(self.agents),
            'current_healthy_agents': recent_checks[-1].healthy_agents if recent_checks else 0,
            'total_recovery_attempts': sum(self.recovery_log.values()) if self.recovery_log else 0
        }

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Calyx Terminal Agent Health Monitor')
    parser.add_argument('--check-once', action='store_true', help='Perform single health check and exit')
    parser.add_argument('--activate-agents', action='store_true', help='Activate all inactive agents')
    parser.add_argument('--monitor', type=int, default=0, help='Run continuous monitoring for N seconds')
    parser.add_argument('--summary', action='store_true', help='Show monitoring summary and exit')
    parser.add_argument('--agent-status', help='Check status of specific agent')

    args = parser.parse_args()

    monitor = AgentHealthMonitor()

    if args.check_once:
        print(f"[C:HEALTH_CHECK] — Systems Resources Agent: Performing comprehensive health check")

        result = monitor.perform_health_check_cycle()

        print(f"[C:REPORT] — Systems Resources Agent: Health Check Results")
        print(f"[Agent • Systems Resources]: Timestamp: {result.timestamp}")
        print(f"[Agent • Systems Resources]: Total Agents: {result.total_agents}")
        print(f"[Agent • Systems Resources]: Healthy Agents: {result.healthy_agents}")
        print(f"[Agent • Systems Resources]: Unhealthy Agents: {result.unhealthy_agents}")
        print(f"[Agent • Systems Resources]: Recovered Agents: {result.recovered_agents}")
        print(f"[Agent • Systems Resources]: System Health: {result.system_health_score:.1f}%")

        # Show individual agent status
        for agent_name in monitor.agents.keys():
            status = monitor.get_agent_status(agent_name)
            health_indicator = "[OK]" if status.health_score >= 90 else "[WARN]" if status.health_score >= 60 else "[FAIL]"
            print(f"[Agent • Systems Resources]: {health_indicator} {agent_name}: {status.status_message} (Health: {status.health_score:.1f}%)")

    elif args.activate_agents:
        print(f"[C:ACTIVATION] — Systems Resources Agent: Activating all inactive agents")

        activated_count = 0
        for agent_name in monitor.agents.keys():
            status = monitor.get_agent_status(agent_name)
            if not status.is_running:
                if monitor.attempt_agent_recovery(agent_name):
                    activated_count += 1
                    print(f"[Agent • Systems Resources]: [SUCCESS] Activated {agent_name}")
                else:
                    print(f"[Agent • Systems Resources]: [FAILED] Failed to activate {agent_name}")
            else:
                print(f"[Agent • Systems Resources]: [ACTIVE] {agent_name} already active")

        print(f"[C:REPORT] — Systems Resources Agent: Activation complete - {activated_count} agents activated")

    elif args.agent_status:
        if args.agent_status not in monitor.agents:
            print(f"[ERROR] Unknown agent: {args.agent_status}")
            return

        status = monitor.get_agent_status(args.agent_status)
        health_indicator = "✅" if status.health_score >= 90 else "⚠️" if status.health_score >= 60 else "❌"

        print(f"[C:AGENT_STATUS] — Systems Resources Agent: Status for {args.agent_status}")
        print(f"[Agent • Systems Resources]: {health_indicator} Health Score: {status.health_score:.1f}%")
        print(f"[Agent • Systems Resources]: Status: {status.status_message}")
        print(f"[Agent • Systems Resources]: Running: {'Yes' if status.is_running else 'No'}")
        print(f"[Agent • Systems Resources]: Last Seen: {status.last_seen or 'Never'}")
        print(f"[Agent • Systems Resources]: Recovery Attempts: {status.recovery_attempts}")

    elif args.summary:
        summary = monitor.get_monitoring_summary()
        print(f"[C:MONITORING_SUMMARY] — Systems Resources Agent: Monitoring Summary")
        for key, value in summary.items():
            print(f"[Agent • Systems Resources]: {key}: {value}")

    elif args.monitor > 0:
        print(f"[C:MONITORING] — Systems Resources Agent: Starting continuous monitoring for {args.monitor} seconds")

        monitor.start_monitoring()

        try:
            time.sleep(args.monitor)
        except KeyboardInterrupt:
            print("\n[C:MONITORING] — Systems Resources Agent: Monitoring interrupted by user")
        finally:
            monitor.stop_monitoring()
            summary = monitor.get_monitoring_summary()
            print(f"[C:REPORT] — Systems Resources Agent: Monitoring complete")
            print(f"[Agent • Systems Resources]: Summary: {json.dumps(summary, indent=2)}")

    else:
        # Default: run single health check
        print(f"[C:HEALTH_CHECK] — Systems Resources Agent: Agent Health Monitor")
        print(f"[Agent • Systems Resources]: Use --help for available commands")

        result = monitor.perform_health_check_cycle()

        # Show agent status summary
        healthy = result.healthy_agents
        total = result.total_agents
        health_pct = (healthy / total * 100) if total > 0 else 0

        print(f"[Agent • Systems Resources]: System Health: {health_pct:.1f}% ({healthy}/{total} agents healthy)")

        if result.unhealthy_agents > 0:
            print(f"[Agent • Systems Resources]: ⚠️  {result.unhealthy_agents} agents need attention")

if __name__ == "__main__":
    main()
