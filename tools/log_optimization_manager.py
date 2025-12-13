#!/usr/bin/env python3
"""
Systems Resources Agent - Log Optimization Manager
Intelligent log management with compression, retention, and deduplication
"""

import os
import json
import gzip
import shutil
import logging
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import yaml

@dataclass
class LogRetentionPolicy:
    """Log retention policy configuration"""
    max_age_days: int
    compression_enabled: bool
    keep_recent_count: int = 0  # 0 means keep all within age limit

@dataclass
class CompressionStats:
    """Compression operation statistics"""
    original_size: int
    compressed_size: int
    compression_ratio: float
    files_processed: int
    bytes_saved: int

class LogOptimizationManager:
    """Intelligent log management system"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.retention_policies = self._load_retention_policies()
        self.deduplication_cache = {}
        self.compression_stats = CompressionStats(0, 0, 0.0, 0, 0)

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

    def _load_retention_policies(self) -> Dict[str, LogRetentionPolicy]:
        """Load retention policies from configuration"""
        policies = {}

        # Default policies if not configured
        default_policies = {
            'agent_metrics': LogRetentionPolicy(90, True, 100),
            'system_heartbeats': LogRetentionPolicy(30, True, 50),
            'svf_communications': LogRetentionPolicy(60, True, 200),
            'debug_logs': LogRetentionPolicy(14, True, 20),
            'resource_monitor': LogRetentionPolicy(30, True, 50)
        }

        if 'logging_optimization' in self.config:
            lo_config = self.config['logging_optimization']
            if 'retention_policies' in lo_config:
                retention_config = lo_config['retention_policies']

                for category, settings in retention_config.items():
                    if isinstance(settings, dict):
                        policies[category] = LogRetentionPolicy(
                            max_age_days=settings,
                            compression_enabled=lo_config.get('compression', {}).get('enable_auto_compress', True)
                        )
                    else:
                        # Simple integer format (days)
                        policies[category] = LogRetentionPolicy(
                            max_age_days=settings,
                            compression_enabled=lo_config.get('compression', {}).get('enable_auto_compress', True)
                        )

        # Merge with defaults for any missing categories
        for category, default_policy in default_policies.items():
            if category not in policies:
                policies[category] = default_policy

        return policies

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for log optimization manager"""
        logger = logging.getLogger('log_optimization')
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        log_file = log_dir / "log_optimization.log"
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

    def find_log_files(self, category: str) -> List[Path]:
        """Find all log files for a given category"""
        log_files = []

        # Category-specific search patterns
        search_patterns = {
            'agent_metrics': ['agent_metrics*.csv', 'agent_metrics_summary*.csv'],
            'system_heartbeats': ['HEARTBEATS.md', 'heartbeats*.json'],
            'svf_communications': ['svf*.md', 'svf*.json', 'dialogues/*.md'],
            'debug_logs': ['*.log', 'debug*.txt'],
            'resource_monitor': ['resource_monitor*.log', 'resource_snapshots*.json']
        }

        if category in search_patterns:
            patterns = search_patterns[category]
        else:
            # Generic pattern for unknown categories
            patterns = [f'*{category}*.log', f'*{category}*.txt', f'*{category}*.json']

        # Search in logs directory
        logs_dir = Path("logs")
        if logs_dir.exists():
            for pattern in patterns:
                log_files.extend(logs_dir.glob(pattern))

        # Search in outgoing directory for category-specific files
        outgoing_dir = Path("outgoing")
        if outgoing_dir.exists():
            for pattern in patterns:
                log_files.extend(outgoing_dir.glob(pattern))

        return sorted(log_files)

    def should_compress_file(self, file_path: Path, category: str) -> bool:
        """Check if file should be compressed based on age and policy"""
        if category not in self.retention_policies:
            return False

        policy = self.retention_policies[category]

        if not policy.compression_enabled:
            return False

        # Check file age
        file_age_days = self._get_file_age_days(file_path)
        return file_age_days >= policy.max_age_days

    def should_delete_file(self, file_path: Path, category: str) -> bool:
        """Check if file should be deleted based on retention policy"""
        if category not in self.retention_policies:
            return False

        policy = self.retention_policies[category]
        file_age_days = self._get_file_age_days(file_path)

        # Delete if older than max age
        if file_age_days > policy.max_age_days:
            return True

        # If keep_recent_count is specified, check if we have too many recent files
        if policy.keep_recent_count > 0:
            recent_files = self._get_recent_files(category, policy.keep_recent_count)
            return file_path not in recent_files

        return False

    def _get_file_age_days(self, file_path: Path) -> int:
        """Get file age in days"""
        try:
            mtime = file_path.stat().st_mtime
            file_date = datetime.fromtimestamp(mtime)
            age_days = (datetime.now() - file_date).days
            return age_days
        except Exception:
            return 999  # Very old if we can't determine age

    def _get_recent_files(self, category: str, count: int) -> List[Path]:
        """Get the most recent files for a category"""
        all_files = self.find_log_files(category)
        # Sort by modification time, newest first
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return all_files[:count]

    def compress_file(self, file_path: Path) -> Tuple[bool, str]:
        """Compress a file using gzip"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')

            # Check if compressed version already exists
            if compressed_path.exists():
                return False, f"Compressed file already exists: {compressed_path}"

            # Get original size
            original_size = file_path.stat().st_size

            # Read and compress
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Get compressed size
            compressed_size = compressed_path.stat().st_size

            # Remove original file
            file_path.unlink()

            # Update stats
            self.compression_stats.files_processed += 1
            self.compression_stats.original_size += original_size
            self.compression_stats.compressed_size += compressed_size
            self.compression_stats.bytes_saved += (original_size - compressed_size)

            if original_size > 0:
                compression_ratio = compressed_size / original_size
                self.compression_stats.compression_ratio = (
                    self.compression_stats.compression_ratio * (self.compression_stats.files_processed - 1) +
                    compression_ratio
                ) / self.compression_stats.files_processed

            return True, f"Compressed {file_path.name} ({original_size} → {compressed_size} bytes)"

        except Exception as e:
            return False, f"Compression failed for {file_path}: {e}"

    def find_duplicate_content(self, file_path: Path, category: str) -> Optional[Path]:
        """Find files with duplicate content for deduplication"""
        if not file_path.exists():
            return None

        # Generate content hash for the file
        try:
            with open(file_path, 'rb') as f:
                content_hash = hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None

        # Check if we've seen this hash before
        if content_hash in self.deduplication_cache:
            original_file = self.deduplication_cache[content_hash]
            if original_file.exists():
                return original_file

        # Store this file as the original
        self.deduplication_cache[content_hash] = file_path
        return None

    def deduplicate_category(self, category: str) -> Dict[str, int]:
        """Deduplicate files within a category"""
        results = {
            'files_checked': 0,
            'duplicates_found': 0,
            'space_saved': 0
        }

        log_files = self.find_log_files(category)
        self.deduplication_cache.clear()  # Reset cache for each category

        for file_path in log_files:
            results['files_checked'] += 1

            duplicate_of = self.find_duplicate_content(file_path, category)
            if duplicate_of and duplicate_of != file_path:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()  # Remove duplicate
                    results['duplicates_found'] += 1
                    results['space_saved'] += file_size
                    self.logger.info(f"Removed duplicate file: {file_path.name} (duplicate of {duplicate_of.name})")
                except Exception as e:
                    self.logger.error(f"Failed to remove duplicate {file_path}: {e}")

        return results

    def optimize_category(self, category: str, dry_run: bool = False) -> Dict:
        """Optimize all files in a category"""
        results = {
            'category': category,
            'files_processed': 0,
            'files_compressed': 0,
            'files_deleted': 0,
            'space_saved': 0,
            'errors': []
        }

        if category not in self.retention_policies:
            results['errors'].append(f"No retention policy defined for category: {category}")
            return results

        log_files = self.find_log_files(category)

        for file_path in log_files:
            results['files_processed'] += 1

            try:
                # Check for compression
                if self.should_compress_file(file_path, category):
                    if not dry_run:
                        success, message = self.compress_file(file_path)
                        if success:
                            results['files_compressed'] += 1
                            # Update space_saved (compressed_size is smaller)
                            original_size = file_path.stat().st_size if file_path.exists() else 0
                            compressed_size = file_path.with_suffix(file_path.suffix + '.gz').stat().st_size
                            results['space_saved'] += (original_size - compressed_size)
                        else:
                            results['errors'].append(message)
                    else:
                        # Estimate space savings for dry run
                        if file_path.stat().st_size > 1024:  # Only estimate for files > 1KB
                            estimated_compressed = file_path.stat().st_size * 0.3  # Rough estimate
                            results['space_saved'] += (file_path.stat().st_size - int(estimated_compressed))

                # Check for deletion
                if self.should_delete_file(file_path, category):
                    file_size = file_path.stat().st_size
                    if not dry_run:
                        file_path.unlink()
                        results['files_deleted'] += 1
                        results['space_saved'] += file_size
                    else:
                        results['space_saved'] += file_size

            except Exception as e:
                results['errors'].append(f"Error processing {file_path}: {e}")

        return results

    def run_full_optimization(self, dry_run: bool = False) -> Dict:
        """Run complete log optimization across all categories"""
        self.logger.info(f"[C:REPORT] — Systems Resources Agent: Starting log optimization {'(DRY RUN)' if dry_run else ''}")

        overall_results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'categories_processed': [],
            'total_files_processed': 0,
            'total_files_compressed': 0,
            'total_files_deleted': 0,
            'total_space_saved': 0,
            'compression_stats': asdict(self.compression_stats),
            'errors': []
        }

        # Process each category
        for category in self.retention_policies.keys():
            category_results = self.optimize_category(category, dry_run)
            overall_results['categories_processed'].append(category_results)

            overall_results['total_files_processed'] += category_results['files_processed']
            overall_results['total_files_compressed'] += category_results['files_compressed']
            overall_results['total_files_deleted'] += category_results['files_deleted']
            overall_results['total_space_saved'] += category_results['space_saved']
            overall_results['errors'].extend(category_results['errors'])

        # Run deduplication on each category
        for category in self.retention_policies.keys():
            dedup_results = self.deduplicate_category(category)
            self.logger.info(f"Deduplication results for {category}: {dedup_results}")

        self.logger.info(f"[C:REPORT] — Systems Resources Agent: Log optimization complete")
        self.logger.info(f"[Agent • Systems Resources]: Processed {overall_results['total_files_processed']} files")
        self.logger.info(f"[Agent • Systems Resources]: Compressed {overall_results['total_files_compressed']} files")
        self.logger.info(f"[Agent • Systems Resources]: Deleted {overall_results['total_files_deleted']} files")
        self.logger.info(f"[Agent • Systems Resources]: Space saved: {overall_results['total_space_saved'] / (1024*1024):.2f} MB")

        return overall_results

    def generate_optimization_report(self) -> str:
        """Generate a human-readable optimization report"""
        report_lines = [
            "# Log Optimization Report",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Agent:** Systems Resources Agent",
            "",
            "## Summary",
            f"- Files Processed: {self.compression_stats.files_processed}",
            f"- Total Original Size: {self.compression_stats.original_size / (1024*1024):.2f} MB",
            f"- Total Compressed Size: {self.compression_stats.compressed_size / (1024*1024):.2f} MB",
            f"- Space Saved: {self.compression_stats.bytes_saved / (1024*1024):.2f} MB",
            f"- Average Compression Ratio: {self.compression_stats.compression_ratio:.2%}",
            "",
            "## Retention Policies"
        ]

        for category, policy in self.retention_policies.items():
            report_lines.extend([
                f"### {category}",
                f"- Max Age: {policy.max_age_days} days",
                f"- Compression: {'Enabled' if policy.compression_enabled else 'Disabled'}",
                f"- Keep Recent: {policy.keep_recent_count if policy.keep_recent_count > 0 else 'All within age limit'}",
                ""
            ])

        return "\n".join(report_lines)

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Calyx Terminal Log Optimization Manager')
    parser.add_argument('--category', help='Optimize specific category only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--report', action='store_true', help='Generate optimization report and exit')
    parser.add_argument('--list-categories', action='store_true', help='List available categories and exit')

    args = parser.parse_args()

    manager = LogOptimizationManager()

    if args.list_categories:
        print("[C:REPORT] — Systems Resources Agent: Available Categories")
        for category, policy in manager.retention_policies.items():
            print(f"- {category}: {policy.max_age_days} days retention")
        return

    if args.report:
        report = manager.generate_optimization_report()
        print(report)
        return

    # Run optimization
    if args.category:
        if args.category not in manager.retention_policies:
            print(f"[ERROR] Unknown category: {args.category}")
            print("Available categories:")
            for category in manager.retention_policies.keys():
                print(f"  - {category}")
            return

        results = manager.optimize_category(args.category, args.dry_run)
        print(f"[C:REPORT] — Systems Resources Agent: Category '{args.category}' optimization complete")
        print(f"[Agent • Systems Resources]: Results: {json.dumps(results, indent=2)}")

    else:
        results = manager.run_full_optimization(args.dry_run)

        # Save results to file
        output_dir = Path("outgoing") / "log_optimization"
        output_dir.mkdir(exist_ok=True)

        results_file = output_dir / f"log_optimization_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"[C:REPORT] — Systems Resources Agent: Full optimization complete")
        print(f"[Agent • Systems Resources]: Detailed results saved to: {results_file}")

if __name__ == "__main__":
    main()
