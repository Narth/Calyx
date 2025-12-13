"""Manual Calyx Health Probe v0.1 CLI (reflection-only, read-only)."""

from __future__ import annotations

import argparse

from tools.calyx_telemetry_logger import new_request_id, new_session_id
from tools.health_probe import emit_health_probe_node_output, summarize_health


def main() -> None:
    parser = argparse.ArgumentParser(description="Calyx Health Probe v0.1")
    parser.add_argument("--hours", type=int, default=4, help="Lookback window in hours")
    parser.add_argument(
        "--no-os-metrics",
        action="store_true",
        help="Disable OS read-only metrics collection",
    )
    args = parser.parse_args()

    request_id = new_request_id("health_probe")
    session_id = new_session_id("health_probe")

    summary = summarize_health(
        window_hours=args.hours, include_os_metrics=not args.no_os_metrics
    )
    record = emit_health_probe_node_output(
        summary=summary,
        request_id=request_id,
        session_id=session_id,
        window_hours=args.hours,
    )

    health = record["outputs"]["health_probe"]
    print(f"Health Probe v0.1 (hours={args.hours})")
    print(f"  node_output_id: {record['node_output_id']}")
    print(
        f"  capability_requests: {health.get('capability_pressure', {}).get('total_requests', 0)}"
    )
    print(f"  drift_signals: {health.get('drift_anomalies', {}).get('drift_signals', 0)}")
    print(
        f"  kernel_checkins: {health.get('reflection_cadence', {}).get('kernel_checkins', 0)}"
    )
    if not args.no_os_metrics:
        os_metrics = health.get("os_metrics", {})
        print(
            f"  os metrics: cpu_load={os_metrics.get('cpu_load')}, "
            f"mem_used_mb={os_metrics.get('mem_used_mb')}, "
            f"process_count={os_metrics.get('process_count')}, "
            f"disk_free_gb={os_metrics.get('disk_free_gb')}"
        )


if __name__ == "__main__":
    main()
