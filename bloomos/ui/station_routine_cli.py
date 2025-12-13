"""Manual Station Routine v0.2 CLI (reflection-only).

Modes:
- basic: legacy v0.1 behavior
- extended (default): v0.1 + CTL summary + kernel reflection + optional intent embedding
"""

from __future__ import annotations

import argparse

from tools.station_routine import run_station_routine


def main() -> None:
    parser = argparse.ArgumentParser(description="Station Routine v0.2")
    parser.add_argument(
        "--mode",
        choices=["basic", "extended"],
        default="extended",
        help="Run basic v0.1 flow or extended v0.2 (default: extended)",
    )
    parser.add_argument(
        "--hours", type=int, default=4, help="Lookback hours for summaries (default: 4)"
    )
    parser.add_argument(
        "--intent",
        type=str,
        default=None,
        help="Optional intent text to interpret and embed (reflection-only)",
    )
    parser.add_argument(
        "--run-health-probe",
        action="store_true",
        help="Also run the health probe (extended mode only)",
    )
    parser.add_argument(
        "--no-os-metrics",
        action="store_true",
        help="Skip OS read-only metrics in health probe",
    )
    args = parser.parse_args()

    result = run_station_routine(
        mode=args.mode,
        hours=args.hours,
        intent_text=args.intent,
        run_health_probe=args.run_health_probe,
        include_os_metrics=not args.no_os_metrics,
    )

    print(f"Station Routine v0.2 (mode={args.mode}, hours={args.hours})")
    print(f"session_id: {result['session_id']}")
    print(f"checkin_id: {result['checkin_id']}")
    print(
        f"integrity_check_run: {result['integrity_check_run']}, "
        f"integrity_breaches_detected: {result['integrity_breaches_detected']}"
    )

    # CBO session reflection (overseer)
    session_outputs = result["node_output"]["outputs"]
    print("\nCBO session reflection:")
    print(f"  summary: {session_outputs.get('summary')}")
    next_steps = session_outputs.get("next_steps", [])
    if next_steps:
        print("  next_steps:")
        for step in next_steps:
            print(f"    - {step}")
    if session_outputs.get("intent"):
        intent = session_outputs["intent"]
        print("  interpreted_intent:")
        print(f"    intent_id: {intent.get('intent_id')}")
        safe_desc = (
            intent.get("reframed_intent", {}).get("safe_goal_description") or ""
        )
        print(f"    safe_goal_description: {safe_desc}")

    if args.mode == "extended":
        summary = result.get("summary") or {}
        summary_node_output = result.get("summary_node_output") or {}
        kernel_reflection = result.get("kernel_reflection") or {}

        print("\nCTL summary:")
        print(f"  node_output_id: {summary_node_output.get('node_output_id')}")
        print(f"  window_hours: {summary.get('window_hours')}")
        event_counts = summary.get("event_counts", {})
        by_event = event_counts.get("by_event_type", {})
        print(f"  total_events: {event_counts.get('total', 0)}")
        print(
            f"  kernel_checkins: {by_event.get('kernel_checkin', 0)}, "
            f"node_outputs: {by_event.get('node_output', 0)}, "
            f"drift_signals: {summary.get('drift_signals', {}).get('total', 0)}"
        )
        cap = summary.get("capability_requests", {})
        if cap.get("total"):
            caps = ", ".join(
                f"{k} ({v}x)" for k, v in cap.get("by_capability", {}).items()
            )
            print(f"  high-risk capabilities requested: {caps}")

        print("\nKernel reflection:")
        print(f"  node_output_id: {kernel_reflection.get('node_output_id')}")
        k_outputs = kernel_reflection.get("outputs", {})
        print(f"  governance: Safe Mode + deny-all execution gate")
        risks = k_outputs.get("risks_and_anomalies", {})
        print(f"  risks_status: {risks.get('status')}")
        short_focus = k_outputs.get("suggested_focus", {}).get("short_term", [])
        if short_focus:
            print("  suggested_focus (short_term):")
            for item in short_focus:
                print(f"    - {item}")
        ctl_embedded = k_outputs.get("ctl_summary_embedded", {})
        if ctl_embedded:
            print(
                f"  ctl_summary total_events: {ctl_embedded.get('event_counts', {}).get('total', 0)}"
            )
            print(
                f"  ctl_summary drift_signals: {ctl_embedded.get('drift_signals', {}).get('total', 0)}"
            )
            caps = ctl_embedded.get("capability_requests", {})
            if caps.get("total"):
                cap_str = ", ".join(
                    f"{k} ({v}x)" for k, v in caps.get("by_capability", {}).items()
                )
                print(f"  ctl_summary capability_requests: {cap_str}")
        metrics = result.get("governance_metrics") or {}
        if metrics:
            print("\nGovernance metrics:")
            print(
                f"  calyx_theory_version: {metrics.get('calyx_theory_version', 'unknown')}"
            )
            print(
                f"  safe_mode: {metrics.get('safe_mode')}, execution_gate_active: {metrics.get('execution_gate_active')}, policy: {metrics.get('execution_policy')}"
            )
            print(
                f"  capability_requests: {metrics.get('capability_requests', 0)}, drift_signals: {metrics.get('drift_signals', 0)}, total_events: {metrics.get('event_counts_total', 0)}"
            )
        if args.run_health_probe and result.get("health_probe"):
            hp = result["health_probe"]
            hp_outputs = hp.get("outputs", {})
            hp_health = hp_outputs.get("health_probe", {})
            print("\nHealth probe:")
            print(f"  node_output_id: {hp.get('node_output_id')}")
            print(
                f"  capability_requests: {hp_health.get('capability_pressure', {}).get('total_requests', 0)}"
            )
            print(
                f"  drift_signals: {hp_health.get('drift_anomalies', {}).get('drift_signals', 0)}"
            )
            print(
                f"  kernel_checkins: {hp_health.get('reflection_cadence', {}).get('kernel_checkins', 0)}"
            )
            os_metrics = hp_health.get("os_metrics", {})
            if os_metrics and not args.no_os_metrics:
                print(
                    f"  os metrics: cpu_load={os_metrics.get('cpu_load')}, "
                    f"mem_used_mb={os_metrics.get('mem_used_mb')}, "
                    f"process_count={os_metrics.get('process_count')}, "
                    f"disk_free_gb={os_metrics.get('disk_free_gb')}"
                )


if __name__ == "__main__":
    main()
