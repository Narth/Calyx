#!/usr/bin/env python3
"""
Systems Resources Agent - SVF Communication Optimization Manager
Intelligent batching, compression, and selective routing for SVF protocol
"""

import json
import time
import gzip
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import yaml

@dataclass
class MessageBatch:
    """Batch of SVF messages for efficient processing"""
    id: str
    created_at: datetime
    messages: List[Dict]
    total_size: int
    compressed_size: int
    priority: str

@dataclass
class SVFOptimizationStats:
    """SVF optimization statistics"""
    messages_processed: int
    batches_created: int
    bytes_saved: int
    compression_ratio: float
    selective_routes_used: int
    context_aware_deliveries: int

class SVFOptimizationManager:
    """Intelligent SVF communication optimization system"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.settings = self._load_svf_settings()

        # Message queues and batches
        self.message_queue = []
        self.batches = {}
        self.batch_lock = threading.Lock()

        # Statistics tracking
        self.stats = SVFOptimizationStats(0, 0, 0, 0.0, 0, 0)

        # Activity tracking for adaptive intervals
        self.activity_tracker = {
            'messages_per_minute': [],
            'current_window_start': datetime.now()
        }

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

    def _load_svf_settings(self) -> Dict:
        """Load SVF optimization settings from configuration"""
        default_settings = {
            'enabled': True,
            'base_interval': 5,
            'low_activity_interval': 15,
            'high_activity_interval': 2,
            'activity_threshold': 10,
            'max_batch_size': 10,
            'compression_threshold': 1024,
            'max_concurrent_dialogues': 5,
            'message_queue_size': 100,
            'enable_compression': True,
            'selective_routing': True,
            'context_aware_delivery': True
        }

        if 'svf_optimization' in self.config:
            svf_config = self.config['svf_optimization']
            if 'adaptive_intervals' in svf_config:
                default_settings.update(svf_config['adaptive_intervals'])
            if 'message_optimization' in svf_config:
                default_settings.update(svf_config['message_optimization'])
            if 'resource_management' in svf_config:
                default_settings.update(svf_config['resource_management'])

        return default_settings

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for SVF optimization manager"""
        logger = logging.getLogger('svf_optimization')
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        log_file = log_dir / "svf_optimization.log"
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

    def calculate_adaptive_interval(self) -> int:
        """Calculate optimal interval based on recent activity"""
        if not self.activity_tracker['messages_per_minute']:
            return self.settings['base_interval']

        # Calculate messages per minute in current window
        window_duration = (datetime.now() - self.activity_tracker['current_window_start']).total_seconds() / 60
        if window_duration < 1:
            return self.settings['base_interval']

        current_mpm = len(self.activity_tracker['messages_per_minute']) / window_duration

        # Adaptive interval based on activity level
        if current_mpm >= self.settings['activity_threshold']:
            return self.settings['high_activity_interval']
        elif current_mpm <= 2:  # Very low activity
            return self.settings['low_activity_interval']
        else:
            return self.settings['base_interval']

    def compress_message(self, message: Dict) -> bytes:
        """Compress a message using gzip"""
        try:
            message_json = json.dumps(message, separators=(',', ':')).encode('utf-8')
            compressed_data = gzip.compress(message_json)
            return compressed_data
        except Exception as e:
            self.logger.error(f"Error compressing message: {e}")
            return json.dumps(message, separators=(',', ':')).encode('utf-8')

    def decompress_message(self, compressed_data: bytes) -> Optional[Dict]:
        """Decompress a message from gzip"""
        try:
            decompressed_data = gzip.decompress(compressed_data)
            return json.loads(decompressed_data.decode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error decompressing message: {e}")
            return None

    def should_compress_message(self, message: Dict) -> bool:
        """Determine if message should be compressed"""
        if not self.settings['enable_compression']:
            return False

        message_size = len(json.dumps(message, separators=(',', ':')).encode('utf-8'))
        return message_size >= self.settings['compression_threshold']

    def determine_message_priority(self, message: Dict) -> str:
        """Determine priority level for a message"""
        content = message.get('content', '').lower()

        # Critical priority indicators
        critical_keywords = ['error', 'critical', 'emergency', 'failure', 'exception', 'alert']
        if any(keyword in content for keyword in critical_keywords):
            return 'critical'

        # High priority indicators
        high_keywords = ['warning', 'important', 'urgent', 'priority', 'attention']
        if any(keyword in content for keyword in high_keywords):
            return 'high'

        # Normal priority for regular communications
        return 'normal'

    def determine_routing_targets(self, message: Dict) -> List[str]:
        """Determine which agents should receive this message"""
        if not self.settings['selective_routing']:
            return ['all']  # Broadcast to all if selective routing disabled

        targets = []
        content = message.get('content', '').lower()
        sender = message.get('sender', 'unknown')

        # Route based on content and context
        if 'agent1' in content or 'operation' in content or 'task' in content:
            targets.append('agent1')

        if 'triage' in content or 'diagnostic' in content or 'system' in content:
            targets.append('triage')

        if any(cp in content for cp in ['cp6', 'cp7', 'cp8', 'cp9', 'cp10']):
            # Route to specific copilots mentioned
            for cp in ['cp6', 'cp7', 'cp8', 'cp9', 'cp10']:
                if cp in content:
                    targets.append(cp)

        if 'teaching' in content or 'learning' in content or 'ai4all' in content:
            targets.append('teaching_system')

        if 'resource' in content or 'performance' in content or 'optimization' in content:
            targets.append('resource_agent')

        # If no specific targets identified, default to all active agents
        if not targets:
            targets = ['all']

        return targets

    def queue_message(self, message: Dict) -> bool:
        """Queue a message for optimized processing"""
        try:
            # Add metadata
            enriched_message = {
                'original_message': message,
                'timestamp': datetime.now().isoformat(),
                'priority': self.determine_message_priority(message),
                'routing_targets': self.determine_routing_targets(message),
                'size': len(json.dumps(message, separators=(',', ':')).encode('utf-8'))
            }

            with self.batch_lock:
                # Check queue size limit
                if len(self.message_queue) >= self.settings['message_queue_size']:
                    # Remove oldest low-priority message if queue is full
                    low_priority_indices = [
                        i for i, msg in enumerate(self.message_queue)
                        if msg['priority'] == 'normal'
                    ]
                    if low_priority_indices:
                        removed_index = low_priority_indices[0]
                        removed_message = self.message_queue.pop(removed_index)
                        self.logger.info(f"Dropped low-priority message due to queue limit: {removed_message.get('original_message', {}).get('sender', 'unknown')}")

                self.message_queue.append(enriched_message)
                self.stats.messages_processed += 1

                # Update activity tracking
                self.activity_tracker['messages_per_minute'].append(datetime.now())
                # Keep only last 60 messages for activity calculation
                if len(self.activity_tracker['messages_per_minute']) > 60:
                    self.activity_tracker['messages_per_minute'].pop(0)

            return True

        except Exception as e:
            self.logger.error(f"Error queueing message: {e}")
            return False

    def create_batch(self) -> Optional[MessageBatch]:
        """Create a new message batch for processing"""
        with self.batch_lock:
            if not self.message_queue:
                return None

            # Sort messages by priority (critical first)
            priority_order = {'critical': 0, 'high': 1, 'normal': 2}
            sorted_messages = sorted(
                self.message_queue,
                key=lambda x: priority_order.get(x['priority'], 2)
            )

            # Create batch (limit size)
            batch_size = min(self.settings['max_batch_size'], len(sorted_messages))
            batch_messages = sorted_messages[:batch_size]

            # Remove from queue
            self.message_queue = sorted_messages[batch_size:]

            # Calculate batch statistics
            total_size = sum(msg['size'] for msg in batch_messages)

            # Compress batch if beneficial
            compressed_size = total_size
            if self.settings['enable_compression'] and total_size > self.settings['compression_threshold']:
                try:
                    batch_data = json.dumps([msg['original_message'] for msg in batch_messages], separators=(',', ':')).encode('utf-8')
                    compressed_data = gzip.compress(batch_data)
                    compressed_size = len(compressed_data)

                    if compressed_size < total_size * 0.8:  # Only use if >20% savings
                        self.stats.bytes_saved += (total_size - compressed_size)
                        if total_size > 0:
                            self.stats.compression_ratio = (
                                self.stats.compression_ratio * (self.stats.batches_created) +
                                (compressed_size / total_size)
                            ) / (self.stats.batches_created + 1)
                except Exception as e:
                    self.logger.error(f"Error compressing batch: {e}")
                    compressed_size = total_size

            # Create batch object
            batch_id = f"batch_{int(time.time())}_{len(self.batches)}"
            batch = MessageBatch(
                id=batch_id,
                created_at=datetime.now(),
                messages=batch_messages,
                total_size=total_size,
                compressed_size=compressed_size,
                priority=max([msg['priority'] for msg in batch_messages], key=lambda x: priority_order.get(x, 2))
            )

            self.batches[batch_id] = batch
            self.stats.batches_created += 1

            return batch

    def process_batch(self, batch: MessageBatch) -> Dict[str, Any]:
        """Process a batch of messages with optimized routing"""
        results = {
            'batch_id': batch.id,
            'messages_processed': len(batch.messages),
            'routes_used': 0,
            'context_deliveries': 0,
            'errors': []
        }

        try:
            for message in batch.messages:
                original_msg = message['original_message']
                targets = message['routing_targets']

                # Route message to targets
                if 'all' in targets:
                    # Broadcast to all active agents
                    self._broadcast_message(original_msg)
                    results['routes_used'] += 1
                else:
                    # Selective routing
                    for target in targets:
                        self._route_to_agent(original_msg, target, message.get('priority', 'normal'))
                        results['routes_used'] += 1

                        if self.settings['context_aware_delivery']:
                            results['context_deliveries'] += 1

            # Clean up old batches (keep last 100)
            if len(self.batches) > 100:
                oldest_batches = sorted(self.batches.keys(), key=lambda x: self.batches[x].created_at)[:10]
                for old_batch_id in oldest_batches:
                    del self.batches[old_batch_id]

            return results

        except Exception as e:
            results['errors'].append(f"Error processing batch: {e}")
            self.logger.error(f"Error processing batch {batch.id}: {e}")
            return results

    def _broadcast_message(self, message: Dict):
        """Broadcast message to all agents via SVF protocol"""
        try:
            # This would integrate with the existing SVF probe system
            # For now, we'll simulate by writing to a shared location
            broadcast_file = Path("outgoing") / "svf" / "broadcast" / f"broadcast_{int(time.time())}.json"

            # Ensure directory exists
            broadcast_file.parent.mkdir(parents=True, exist_ok=True)

            # Write broadcast message
            with open(broadcast_file, 'w') as f:
                json.dump({
                    'message': message,
                    'broadcast': True,
                    'timestamp': datetime.now().isoformat(),
                    'sender': 'svf_optimization_manager'
                }, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error broadcasting message: {e}")

    def _route_to_agent(self, message: Dict, target: str, priority: str):
        """Route message to specific agent"""
        try:
            # This would integrate with agent-specific communication channels
            # For now, we'll simulate by writing to agent-specific locations
            route_file = Path("outgoing") / "svf" / "routes" / target / f"message_{int(time.time())}_{priority}.json"

            # Ensure directory exists
            route_file.parent.mkdir(parents=True, exist_ok=True)

            # Write routed message
            with open(route_file, 'w') as f:
                json.dump({
                    'message': message,
                    'target': target,
                    'priority': priority,
                    'timestamp': datetime.now().isoformat(),
                    'routed_by': 'svf_optimization_manager'
                }, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error routing message to {target}: {e}")

    def get_optimization_stats(self) -> Dict:
        """Get current optimization statistics"""
        with self.batch_lock:
            return {
                'timestamp': datetime.now().isoformat(),
                'messages_queued': len(self.message_queue),
                'active_batches': len(self.batches),
                'stats': asdict(self.stats),
                'current_interval': self.calculate_adaptive_interval(),
                'activity_level': len(self.activity_tracker['messages_per_minute'])
            }

    def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run one complete optimization cycle"""
        cycle_results = {
            'cycle_start': datetime.now().isoformat(),
            'batches_processed': 0,
            'messages_processed': 0,
            'routes_used': 0,
            'errors': []
        }

        try:
            # Create and process batches
            while True:
                batch = self.create_batch()
                if not batch:
                    break

                batch_results = self.process_batch(batch)
                cycle_results['batches_processed'] += 1
                cycle_results['messages_processed'] += batch_results['messages_processed']
                cycle_results['routes_used'] += batch_results['routes_used']
                cycle_results['errors'].extend(batch_results['errors'])

            cycle_results['cycle_end'] = datetime.now().isoformat()

            # Log cycle results
            if cycle_results['messages_processed'] > 0:
                self.logger.info(f"[C:REPORT] — Systems Resources Agent: SVF optimization cycle complete")
                self.logger.info(f"[Agent • Systems Resources]: Processed {cycle_results['messages_processed']} messages in {cycle_results['batches_processed']} batches")

            return cycle_results

        except Exception as e:
            cycle_results['errors'].append(f"Error in optimization cycle: {e}")
            self.logger.error(f"Error in optimization cycle: {e}")
            return cycle_results

def simulate_svf_activity(manager: SVFOptimizationManager, duration: int = 60):
    """Simulate SVF activity for testing"""
    import random

    test_messages = [
        {"sender": "agent1", "content": "Task completed successfully", "type": "status"},
        {"sender": "triage", "content": "System health check passed", "type": "diagnostic"},
        {"sender": "cp6", "content": "Social interaction patterns analyzed", "type": "analysis"},
        {"sender": "cp7", "content": "Weekly system summary generated", "type": "report"},
        {"sender": "agent1", "content": "Error detected in module X", "type": "error"},
        {"sender": "triage", "content": "Performance degradation warning", "type": "warning"},
        {"sender": "cp8", "content": "Resource optimization suggestions ready", "type": "recommendation"},
        {"sender": "teaching_system", "content": "Learning adaptation applied", "type": "teaching"}
    ]

    end_time = time.time() + duration

    while time.time() < end_time:
        # Randomly select and send a message
        message = random.choice(test_messages).copy()
        manager.queue_message(message)

        # Small delay between messages
        time.sleep(random.uniform(0.5, 2.0))

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Calyx Terminal SVF Optimization Manager')
    parser.add_argument('--test', type=int, default=0, help='Run test simulation for N seconds')
    parser.add_argument('--cycle', action='store_true', help='Run single optimization cycle')
    parser.add_argument('--stats', action='store_true', help='Show current optimization stats')
    parser.add_argument('--continuous', type=int, default=0, help='Run continuous optimization for N seconds')

    args = parser.parse_args()

    manager = SVFOptimizationManager()

    if args.test > 0:
        print(f"[C:REPORT] — Systems Resources Agent: Starting SVF optimization test ({args.test}s)")
        simulate_svf_activity(manager, args.test)

        # Run final optimization cycle
        results = manager.run_optimization_cycle()
        print(f"[C:REPORT] — Systems Resources Agent: Test complete")
        print(f"[Agent • Systems Resources]: Final stats: {json.dumps(manager.get_optimization_stats(), indent=2)}")

    elif args.cycle:
        print(f"[C:REPORT] — Systems Resources Agent: Running SVF optimization cycle")
        results = manager.run_optimization_cycle()
        print(f"[C:REPORT] — Systems Resources Agent: Cycle complete")
        print(f"[Agent • Systems Resources]: Results: {json.dumps(results, indent=2)}")

    elif args.stats:
        stats = manager.get_optimization_stats()
        print(f"[C:REPORT] — Systems Resources Agent: Current SVF optimization stats")
        print(f"[Agent • Systems Resources]: {json.dumps(stats, indent=2)}")

    elif args.continuous > 0:
        print(f"[C:REPORT] — Systems Resources Agent: Starting continuous SVF optimization ({args.continuous}s)")

        end_time = time.time() + args.continuous

        while time.time() < end_time:
            try:
                # Run optimization cycle
                manager.run_optimization_cycle()

                # Calculate adaptive interval and wait
                interval = manager.calculate_adaptive_interval()
                time.sleep(min(interval, 5))  # Cap at 5 seconds for responsiveness

            except KeyboardInterrupt:
                print("\n[C:REPORT] — Systems Resources Agent: Continuous optimization interrupted")
                break

        final_stats = manager.get_optimization_stats()
        print(f"[C:REPORT] — Systems Resources Agent: Continuous optimization complete")
        print(f"[Agent • Systems Resources]: Final stats: {json.dumps(final_stats, indent=2)}")

    else:
        # Default: run one cycle and show stats
        print(f"[C:REPORT] — Systems Resources Agent: SVF Optimization Manager Ready")
        print(f"[Agent • Systems Resources]: Use --help for available commands")

if __name__ == "__main__":
    main()
