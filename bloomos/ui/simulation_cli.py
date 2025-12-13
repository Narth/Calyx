import argparse
from typing import Optional
from tools.calyx_telemetry_summarizer import summarize_telemetry
from tools.calyx_node_output import emit_node_output_with_telemetry
from tools.calyx_telemetry_logger import new_request_id, new_session_id


def run_simulation(window_hours: int, hypothesis: Optional[str], note: Optional[str]):
    summary = summarize_telemetry(window_hours)
    request_id = new_request_id("simulation_cli")
    session_id = new_session_id("work_session")

    outputs_summary = (
        f"Simulation (log replay, read-only) over last {window_hours}h: "
        f"events={summary['event_counts']['total']}, "
        f"node_outputs={summary['event_counts']['by_event_type'].get('node_output', 0)}, "
        f"kernel_checkins={summary['event_counts']['by_event_type'].get('kernel_checkin', 0)}, "
        f"drift_signals={summary['drift_signals']['total']}"
    )

    outputs = {
        "summary": outputs_summary,
        "actions_proposed": ["Use results to scope a safe experiment card if needed."],
        "actions_taken": ["Log replay only; no execution"],
        "next_steps": ["If findings warrant, draft an experiment card via governance_cli."],
        "simulation": {
            "kind": "log_replay",
            "window_hours": window_hours,
            "hypothesis": hypothesis,
            "note": note,
            "ctl_summary": summary,
            "schema_version": "simulation_v0.1",
        },
    }

    record = emit_node_output_with_telemetry(
        node_id="CBO",
        node_role="simulation_runner",
        request_context={
            "request_id": request_id,
            "session_id": session_id,
            "source": "simulation_cli",
            "prompt_summary": "Read-only log replay / simulation summary.",
        },
        task={
            "task_id": f"simulation-{session_id}",
            "intent": "simulation_summary",
            "description": "Replay recent logs (read-only) to summarize state as a simulation baseline.",
        },
        outputs=outputs,
        governance={
            "governance_state": {
                "safe_mode": True,
                "autonomy_level": "reflection_only",
                "execution_gate_active": True,
                "policy_version": "calyx_theory_v0.3",
                "governance_state_version": "gov_state_v0.1",
            },
            "allowed_capabilities": ["read_files", "summarize", "reflect"],
            "denied_capabilities": [
                "execute_code",
                "modify_files",
                "schedule_tasks",
                "filesystem_write",
                "network_request",
                "process_spawn",
                "tool_call",
            ],
        },
        safety={
            "rule_violations": [],
            "blocked_intents": [],
            "risk_assessment": "low",
            "notes": "Read-only simulation; no execution or capability changes.",
        },
        request_id=request_id,
        session_id=session_id,
    )
    return record


def main():
    parser = argparse.ArgumentParser(
        prog="simulation_cli",
        description="Read-only log replay simulation (summarize recent telemetry).",
    )
    parser.add_argument("--hours", type=int, default=4, help="Lookback window in hours (default 4)")
    parser.add_argument("--hypothesis", type=str, default=None, help="Optional hypothesis context")
    parser.add_argument("--note", type=str, default=None, help="Optional note for simulation")
    args = parser.parse_args()

    record = run_simulation(args.hours, args.hypothesis, args.note)
    print("simulation_node_output_id:", record["node_output_id"])
    print("request_id:", record["request_context"]["request_id"])
    print("session_id:", record["request_context"]["session_id"])


if __name__ == "__main__":
    main()
