"""Manual Calyx Telemetry Summarizer CLI (read-only, one-shot)."""

from __future__ import annotations

import argparse

from tools.calyx_telemetry_logger import new_request_id, new_session_id
from tools.calyx_telemetry_summarizer import (
    emit_summary_node_output,
    summarize_telemetry,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calyx Telemetry Summarizer v0.1")
    parser.add_argument("--hours", type=int, default=4, help="Lookback window in hours")
    args = parser.parse_args()

    request_id = new_request_id("ctl_summarizer")
    session_id = new_session_id("ctl_summarizer")

    summary = summarize_telemetry(window_hours=args.hours)
    record = emit_summary_node_output(
        summary=summary,
        window_hours=args.hours,
        request_id=request_id,
        session_id=session_id,
    )

    event_counts = summary.get("event_counts", {})
    by_event_type = event_counts.get("by_event_type", {})
    print(f"CTL Summary (last {args.hours}h):")
    print(f"  total events: {event_counts.get('total', 0)}")
    print(
        f"  node_outputs: {by_event_type.get('node_output', 0)}, "
        f"kernel_checkins: {by_event_type.get('kernel_checkin', 0)}"
    )
    print(f"  drift_signals: {summary.get('drift_signals', {}).get('total', 0)}")
    cap_total = summary.get("capability_requests", {}).get("total", 0)
    caps = summary.get("capability_requests", {}).get("by_capability", {})
    high_risk = summary.get("capability_requests", {}).get(
        "high_risk_capabilities_seen", []
    )
    if cap_total:
        cap_strings = ", ".join(f"{k} ({v}x)" for k, v in caps.items())
        print(f"  capability requests: {cap_total} -> {cap_strings}")
    if high_risk:
        high_risk_str = ", ".join(high_risk)
        print(f"  high-risk capabilities observed: {high_risk_str}")
    print(f"node_output_id: {record['node_output_id']}")


if __name__ == "__main__":
    main()
