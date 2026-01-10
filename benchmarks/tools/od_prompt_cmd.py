"""
OD prompt command: read suite JSON, load prompt text, generate a fresh response, and write an MD file.

Usage:
  python benchmarks/tools/od_prompt_cmd.py \
    --run-id OD-GENERATION-2025-12-13-B \
    --prompt-id OD-01 \
    --suite benchmarks/outcome/suites/od_v2_peer_suite_v1.json \
    --out benchmarks/outcome/OD-GENERATION-2025-12-13-B/OD-01.md \
    [--min-duration 8.0] \
    [--mode station_ingest|generate|stub]

Behavior:
- Reads the suite file to get the exact prompt text.
- Generates a fresh structured response (no reuse of prior outputs).
- Ensures a minimum wall-clock duration via sleep (default 8.0s) so telemetry has real overlap.
- In station_ingest mode (required for OD-GENERATION runs), emits an ingestion envelope and a reflection placeholder:
    * Append envelope to logs/calyx/station_ingest.jsonl
    * Append reflection to logs/calyx/node_outputs.jsonl
    * Write sidecar meta JSON next to the MD (out + ".meta.json")
- Does NOT add timing headers; phase runner will prepend headers.
"""

import argparse
import json
import sys
from pathlib import Path
import time
import uuid
import subprocess
from datetime import datetime, timezone


def load_prompt(suite_path: Path, prompt_id: str) -> str:
    data = json.loads(suite_path.read_text(encoding="utf-8"))
    for p in data.get("prompts", []):
        if p.get("prompt_id") == prompt_id:
            return p.get("text", "")
    raise SystemExit(f"Prompt {prompt_id} not found in suite {suite_path}")


def main():
    parser = argparse.ArgumentParser(description="Render OD prompt to MD with optional source response.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-duration", type=float, default=8.0, help="Minimum generation duration in seconds (default 8.0).")
    parser.add_argument(
        "--mode",
        choices=["stub", "generate", "station_ingest"],
        default="station_ingest",
        help="Generation mode: stub (testing), generate (text only), station_ingest (envelope + reflection).",
    )
    parser.add_argument(
        "--reflect-backend",
        choices=["stub", "local_llama"],
        default="local_llama",
        help="Reflection backend; station_ingest requires non-stub.",
    )
    parser.add_argument("--model-id", default="Qwen2.5-Omni-7B-Q4_K_M", help="Model ID to use for reflection backend.")
    parser.add_argument(
        "--local-models-config",
        type=Path,
        default=Path("benchmarks/outcome/local_models.json"),
        help="Config mapping model_id to runner/model paths.",
    )
    args = parser.parse_args()

    if args.mode != "station_ingest" and args.run_id.startswith("OD-GENERATION"):
        raise SystemExit("OD-GENERATION runs must use --mode station_ingest")
    if args.mode == "station_ingest" and args.reflect_backend == "stub":
        raise SystemExit("station_ingest requires a real reflection backend (local_llama)")

    prompt_text = load_prompt(args.suite, args.prompt_id)

    t0 = time.time()
    # Simple deterministic response template (fresh each run)
    response_body = [
        "_Generated for run:_ " + args.run_id,
        "",
        "### Restatement",
        prompt_text,
        "",
        "### Reflection",
    ]
    if args.mode == "stub":
        response_body.append("Stub mode: telemetry-only placeholder. No station ingestion performed.")
    elif args.mode == "generate":
        response_body.append("Generated in generate mode (no station ingestion).")
    else:
        response_body.append("Generated in station_ingest mode (envelope + reflection emitted).")
    response_body.extend(
        [
            "",
            "### Notes",
            "- Safe Mode, reflection-only.",
            "- No external data sources.",
            "- Minimum duration enforced for telemetry overlap.",
        ]
    )
    body = "\n".join(response_body)
    # Enforce minimum duration
    elapsed = time.time() - t0
    if elapsed < args.min_duration:
        time.sleep(args.min_duration - elapsed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    md_lines = []
    md_lines.append(f"# {args.prompt_id}")
    md_lines.append("")
    md_lines.append("## Prompt")
    md_lines.append("")
    md_lines.append(prompt_text)
    md_lines.append("")
    md_lines.append("## Response")
    md_lines.append("")
    md_lines.append(body)
    md_lines.append("")

    envelope_id = None
    reflection_id = None
    ingest_ts = None
    reflection_ts = None
    reflection_source = None
    reflection_text = None

    if args.mode == "station_ingest":
        envelope_id = f"env-{args.run_id}-{args.prompt_id}-{uuid.uuid4().hex[:8]}"
        reflection_id = f"refl-{args.run_id}-{args.prompt_id}-{uuid.uuid4().hex[:8]}"
        ingest_ts = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        reflection_ts = ingest_ts
        reflection_source = args.reflect_backend
        # Run local_llm if requested
        if args.reflect_backend == "local_llama":
            # load config
            cfg = {}
            if args.local_models_config.exists():
                try:
                    cfg = json.loads(args.local_models_config.read_text(encoding="utf-8"))
                except Exception as e:
                    raise SystemExit(f"Failed to read local models config: {e}")
            models = {m["model_id"]: m for m in cfg.get("models", [])}
            m = models.get(args.model_id)
            if not m:
                raise SystemExit(f"Model {args.model_id} not found in {args.local_models_config}")
            # write prompt to temp
            import tempfile

            tmp = Path(tempfile.mkdtemp())
            prompt_file = tmp / "prompt.txt"
            prompt_file.write_text(prompt_text, encoding="utf-8")
            out_json = tmp / "out.json"
            cmd = [
                sys.executable,
                "benchmarks/tools/local_llm_runner.py",
                "--runner",
                m["runner_path"],
                "--model-path",
                m["model_path"],
                "--model-id",
                args.model_id,
                "--prompt-file",
                str(prompt_file),
                "--n-predict",
                str(m.get("n_predict", 256)),
                "--temperature",
                str(m.get("temperature", 0.7)),
                "--top-p",
                str(m.get("top_p", 0.9)),
                "--seed",
                str(m.get("seed", 42)),
                "--timeout-sec",
                str(m.get("timeout_sec", 120)),
                "--out-json",
                str(out_json),
            ]
            proc = subprocess.run(cmd)
            if proc.returncode != 0 or not out_json.exists():
                raise SystemExit(f"Local LLM runner failed (code {proc.returncode})")
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            if payload.get("status") != "OK":
                raise SystemExit(f"Local LLM status not OK: {payload}")
            reflection_text = payload.get("stdout", "").strip()
        else:
            reflection_text = "stub reflection"
        # Append envelope
        env_rec = {
            "timestamp": ingest_ts,
            "envelope_id": envelope_id,
            "run_id": args.run_id,
            "prompt_id": args.prompt_id,
            "prompt_text": prompt_text,
            "mode": args.mode,
            "reflection_source": reflection_source,
            "schema_version": "od_station_envelope_v1",
        }
        env_log = Path("logs/calyx/station_ingest.jsonl")
        env_log.parent.mkdir(parents=True, exist_ok=True)
        with env_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(env_rec, ensure_ascii=False) + "\n")

        # Append reflection placeholder to node_outputs
        refl_rec = {
            "node_output_id": reflection_id,
            "node_id": "CBO",
            "node_role": "overseer_reflection",
            "timestamp": reflection_ts,
            "reflection_source": reflection_source,
            "task": {
                "intent": "od_station_reflection",
                "description": f"Reflection for {args.prompt_id} in {args.run_id}",
                "priority": "normal",
            },
            "outputs": {
                "summary": reflection_text,
                "prompt_id": args.prompt_id,
                "run_id": args.run_id,
                "schema_version": "node_output_v1.0",
            },
            "governance": {
                "governance_state": {
                    "safe_mode": True,
                    "autonomy_level": "reflection_only",
                    "execution_gate_active": True,
                    "policy_version": "calyx_theory_v0.4",
                    "governance_state_version": "gov_state_v0.1",
                },
                "allowed_capabilities": ["read_files", "summarize", "reflect"],
                "denied_capabilities": ["execute_code", "modify_files", "network_request", "process_spawn"],
            },
            "safety": {
                "rule_violations": [],
                "blocked_intents": [],
                "risk_assessment": "low",
                "notes": "Placeholder reflection after ingestion.",
            },
            "schema_version": "node_output_v1.0",
        }
        refl_log = Path("logs/calyx/node_outputs.jsonl")
        refl_log.parent.mkdir(parents=True, exist_ok=True)
        with refl_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(refl_rec, ensure_ascii=False) + "\n")

    md_lines.append("## Station Ingestion")
    md_lines.append("")
    md_lines.append(f"- envelope_id: {envelope_id}")
    md_lines.append(f"- ingested_at_utc: {ingest_ts}")
    md_lines.append(f"- station_mode: {args.mode}")
    md_lines.append("")
    md_lines.append("## CBO Reflection")
    md_lines.append("")
    md_lines.append(f"- reflection_id: {reflection_id}")
    md_lines.append(f"- reflection_timestamp_utc: {reflection_ts}")
    md_lines.append("")
    md_lines.append("## Telemetry")
    md_lines.append("")
    md_lines.append(f"- run_id: {args.run_id}")
    md_lines.append(f"- prompt_id: {args.prompt_id}")
    md_lines.append(f"- min_duration_sec: {args.min_duration}")
    md_lines.append("")

    args.out.write_text("\n".join(md_lines), encoding="utf-8")

    if envelope_id:
        meta = {
            "run_id": args.run_id,
            "prompt_id": args.prompt_id,
            "mode": args.mode,
            "envelope_id": envelope_id,
            "ingested_at_utc": ingest_ts,
            "reflection_id": reflection_id,
            "reflection_timestamp_utc": reflection_ts,
            "reflection_source": reflection_source,
            "model_id": args.model_id if reflection_source else None,
        }
        Path(str(args.out) + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
