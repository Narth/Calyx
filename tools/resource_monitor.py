#!/usr/bin/env python3
"""
Systems Resources Agent - Resource Monitor
Real-time resource utilization tracking and intelligent allocation management
"""

import psutil
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import yaml

@dataclass
class ResourceSnapshot:
    """Resource utilization snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    agent_processes: Dict[str, Dict]

@dataclass
class ResourceThresholds:
    """Resource threshold configuration"""
    cpu_soft: float = 70.0
    cpu_hard: float = 85.0
    memory_soft: float = 75.0
    memory_hard: float = 90.0
    disk_io_soft: float = 60.0
    disk_io_hard: float = 80.0

class ResourceMonitor:
    """Intelligent resource monitoring and management system"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.thresholds = ResourceThresholds()
        self.snapshots: List[ResourceSnapshot] = []
        self.max_snapshots = 1000
        self.monitoring = False
        self.monitor_thread = None
        self.snapshot_interval = 5  # seconds

        # Load thresholds from config if available
        self._load_thresholds()

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

    def _load_thresholds(self):
        """Load resource thresholds from configuration"""
        if 'resource_management' in self.config:
            rm_config = self.config['resource_management']
            if 'adaptive_thresholds' in rm_config:
                thresholds = rm_config['adaptive_thresholds']
                self.thresholds.cpu_soft = float(thresholds.get('cpu_usage_soft_limit', 70).rstrip('%'))
                self.thresholds.cpu_hard = float(thresholds.get('cpu_usage_hard_limit', 85).rstrip('%'))
                self.thresholds.memory_soft = float(thresholds.get('memory_soft_limit', 75).rstrip('%'))
                self.thresholds.memory_hard = float(thresholds.get('memory_hard_limit', 90).rstrip('%'))
                self.thresholds.disk_io_soft = float(thresholds.get('disk_io_soft_limit', 60).rstrip('%'))
                self.thresholds.disk_io_hard = float(thresholds.get('disk_io_hard_limit', 80).rstrip('%'))

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for resource monitor"""
        logger = logging.getLogger('resource_monitor')
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        log_file = log_dir / "resource_monitor.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def get_system_resources(self) -> Dict:
        """Get current system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_io_read_mb': round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
                'disk_io_write_mb': round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0,
                'network_sent_mb': round(network_io.bytes_sent / (1024**2), 2) if network_io else 0,
                'network_recv_mb': round(network_io.bytes_recv / (1024**2), 2) if network_io else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting system resources: {e}")
            return {}

    def get_agent_processes(self) -> Dict[str, Dict]:
        """Identify and get resource usage for Calyx agents"""
        agent_processes = {}

        # Known agent process patterns
        agent_patterns = {
            'agent1': ['python', 'agent_console', 'listener'],
            'triage': ['triage_probe', 'triage_orchestrator'],
            'cp6': ['cp6', 'sociologist'],
            'cp7': ['cp7', 'chronicler'],
            'cp8': ['cp8', 'quartermaster'],
            'cp9': ['cp9', 'auto_tuner'],
            'cp10': ['cp10', 'whisperer'],
            'svf': ['svf_probe'],
            'watcher': ['agent_watcher'],
            'teaching': ['ai4all_teaching']
        }

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    if not proc_info['cmdline']:
                        continue

                    cmd_str = ' '.join(proc_info['cmdline']).lower()

                    # Check each agent pattern
                    for agent_name, patterns in agent_patterns.items():
                        if any(pattern in cmd_str for pattern in patterns):
                            agent_processes[agent_name] = {
                                'pid': proc_info['pid'],
                                'cpu_percent': proc_info.get('cpu_percent', 0),
                                'memory_percent': proc_info.get('memory_percent', 0),
                                'status': proc_info.get('status', 'unknown'),
                                'command': ' '.join(proc_info['cmdline'][:2])  # First 2 parts of command
                            }
                            break  # Found match, move to next process

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            self.logger.error(f"Error getting agent processes: {e}")

        return agent_processes

    def capture_snapshot(self) -> ResourceSnapshot:
        """Capture current resource utilization snapshot"""
        system_resources = self.get_system_resources()
        agent_processes = self.get_agent_processes()

        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=system_resources.get('cpu_percent', 0),
            memory_percent=system_resources.get('memory_percent', 0),
            disk_io_read=system_resources.get('disk_io_read_mb', 0),
            disk_io_write=system_resources.get('disk_io_write_mb', 0),
            network_io_sent=system_resources.get('network_sent_mb', 0),
            network_io_recv=system_resources.get('network_recv_mb', 0),
            agent_processes=agent_processes
        )

        return snapshot

    def evaluate_resource_status(self, snapshot: ResourceSnapshot) -> Dict:
        """Evaluate resource status against thresholds"""
        status = {
            'overall': 'normal',
            'warnings': [],
            'alerts': [],
            'recommendations': []
        }

        # CPU evaluation
        if snapshot.cpu_percent >= self.thresholds.cpu_hard:
            status['overall'] = 'critical'
            status['alerts'].append(f"CPU usage critical: {snapshot.cpu_percent}% (threshold: {self.thresholds.cpu_hard}%)")
            status['recommendations'].append("Consider pausing non-critical agents")
        elif snapshot.cpu_percent >= self.thresholds.cpu_soft:
            status['warnings'].append(f"CPU usage high: {snapshot.cpu_percent}% (threshold: {self.thresholds.cpu_soft}%)")
            status['recommendations'].append("Monitor CPU-intensive operations")

        # Memory evaluation
        if snapshot.memory_percent >= self.thresholds.memory_hard:
            status['overall'] = 'critical' if status['overall'] != 'critical' else 'critical'
            status['alerts'].append(f"Memory usage critical: {snapshot.memory_percent}% (threshold: {self.thresholds.memory_hard}%)")
            status['recommendations'].append("Consider freeing memory or reducing concurrent operations")
        elif snapshot.memory_percent >= self.thresholds.memory_soft:
            status['warnings'].append(f"Memory usage high: {snapshot.memory_percent}% (threshold: {self.thresholds.memory_soft}%)")
            status['recommendations'].append("Monitor memory-intensive agents")

        # Calculate average agent resource usage
        if snapshot.agent_processes:
            total_agent_cpu = sum(agent['cpu_percent'] for agent in snapshot.agent_processes.values())
            total_agent_memory = sum(agent['memory_percent'] for agent in snapshot.agent_processes.values())

            if total_agent_cpu > 50:
                status['warnings'].append(f"High aggregate agent CPU usage: {total_agent_cpu}%")
            if total_agent_memory > 60:
                status['warnings'].append(f"High aggregate agent memory usage: {total_agent_memory}%")

        return status

    def save_snapshot(self, snapshot: ResourceSnapshot):
        """Save snapshot to history and disk"""
        self.snapshots.append(snapshot)

        # Maintain snapshot limit
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)

        # Save to disk periodically (every 10 snapshots)
        if len(self.snapshots) % 10 == 0:
            self._save_snapshots_to_disk()

    def _save_snapshots_to_disk(self):
        """Save recent snapshots to disk for analysis"""
        try:
            output_dir = Path("outgoing") / "resource_monitor"
            output_dir.mkdir(exist_ok=True)

            # Save recent snapshots
            recent_snapshots = self.snapshots[-50:]  # Last 50 snapshots

            data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'snapshot_count': len(recent_snapshots),
                    'thresholds': asdict(self.thresholds)
                },
                'snapshots': [asdict(snapshot) for snapshot in recent_snapshots]
            }

            output_file = output_dir / f"resource_snapshots_{int(time.time())}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Error saving snapshots to disk: {e}")

    def start_monitoring(self, interval: Optional[int] = None):
        """Start continuous resource monitoring"""
        if self.monitoring:
            self.logger.warning("Resource monitoring already running")
            return

        self.monitoring = True
        self.snapshot_interval = interval or self.snapshot_interval

        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        self.logger.info(f"Started resource monitoring with {self.snapshot_interval}s interval")

    def stop_monitoring(self):
        """Stop continuous resource monitoring"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        self.logger.info("Stopped resource monitoring")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                snapshot = self.capture_snapshot()
                self.save_snapshot(snapshot)

                # Evaluate and log status
                status = self.evaluate_resource_status(snapshot)

                if status['alerts']:
                    for alert in status['alerts']:
                        self.logger.error(f"[RESOURCE ALERT] {alert}")

                if status['warnings']:
                    for warning in status['warnings']:
                        self.logger.warning(f"[RESOURCE WARNING] {warning}")

                # Save status to outgoing for other agents to read
                self._save_current_status(snapshot, status)

                time.sleep(self.snapshot_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.snapshot_interval)

    def _save_current_status(self, snapshot: ResourceSnapshot, status: Dict):
        """Save current resource status for other agents"""
        try:
            status_data = {
                'timestamp': snapshot.timestamp.isoformat(),
                'resources': {
                    'cpu_percent': snapshot.cpu_percent,
                    'memory_percent': snapshot.memory_percent,
                    'disk_io_read_mb': snapshot.disk_io_read,
                    'disk_io_write_mb': snapshot.disk_io_write
                },
                'agents': snapshot.agent_processes,
                'status': status,
                'thresholds': asdict(self.thresholds)
            }

            output_file = Path("outgoing") / "resource_status.json"
            with open(output_file, 'w') as f:
                json.dump(status_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Error saving current status: {e}")

    def get_monitoring_summary(self) -> Dict:
        """Get summary of monitoring data"""
        if not self.snapshots:
            return {'error': 'No monitoring data available'}

        recent_snapshots = self.snapshots[-10:]  # Last 10 snapshots

        avg_cpu = sum(s.cpu_percent for s in recent_snapshots) / len(recent_snapshots)
        avg_memory = sum(s.memory_percent for s in recent_snapshots) / len(recent_snapshots)

        return {
            'monitoring_duration': str(datetime.now() - self.snapshots[0].timestamp) if len(self.snapshots) > 1 else 'N/A',
            'total_snapshots': len(self.snapshots),
            'average_cpu_percent': round(avg_cpu, 2),
            'average_memory_percent': round(avg_memory, 2),
            'current_status': self.evaluate_resource_status(self.snapshots[-1]) if self.snapshots else {},
            'active_agents': len(self.snapshots[-1].agent_processes) if self.snapshots else 0
        }

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Calyx Terminal Resource Monitor')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds')
    parser.add_argument('--duration', type=int, default=300, help='Monitoring duration in seconds')
    parser.add_argument('--once', action='store_true', help='Take single snapshot and exit')
    parser.add_argument('--summary', action='store_true', help='Show monitoring summary and exit')

    args = parser.parse_args()

    monitor = ResourceMonitor()

    if args.once:
        snapshot = monitor.capture_snapshot()
        status = monitor.evaluate_resource_status(snapshot)

        print(f"[RESOURCE SNAPSHOT - {snapshot.timestamp}]")
        print(f"CPU: {snapshot.cpu_percent}%")
        print(f"Memory: {snapshot.memory_percent}%")
        print(f"Active Agents: {len(snapshot.agent_processes)}")
        print(f"Status: {status['overall']}")

        if status['warnings']:
            print("Warnings:")
            for warning in status['warnings']:
                print(f"  - {warning}")

        if status['alerts']:
            print("Alerts:")
            for alert in status['alerts']:
                print(f"  - {alert}")

    elif args.summary:
        summary = monitor.get_monitoring_summary()
        print(json.dumps(summary, indent=2))

    else:
        print(f"[C:REPORT] — Systems Resources Agent: Resource Monitor")
        print(f"[Agent • Systems Resources]: Starting resource monitoring for {args.duration}s with {args.interval}s intervals")

        monitor.start_monitoring(interval=args.interval)

        try:
            time.sleep(args.duration)
        except KeyboardInterrupt:
            print("\n[C:REPORT] — Systems Resources Agent: Monitoring interrupted by user")
        finally:
            monitor.stop_monitoring()
            summary = monitor.get_monitoring_summary()
            print(f"[C:REPORT] — Systems Resources Agent: Monitoring complete")
            print(f"[Agent • Systems Resources]: Summary: {json.dumps(summary, indent=2)}")

if __name__ == "__main__":
    main()
