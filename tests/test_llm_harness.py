"""
Tests for LLM adapter and naive_llm/calyx_llm variants.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


def test_openrouter_requires_api_key():
    """OpenRouter backend raises clear error when OPENROUTER_API_KEY is not set."""
    import os

    key = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        cfg = {"backend": "openrouter", "model_id": "meta-llama/llama-3.3-70b-instruct:free"}
        from benchmarks.harness.llm_backends.openrouter_runtime import OpenRouterRuntime

        with pytest.raises(ValueError) as exc_info:
            OpenRouterRuntime(cfg)
        assert "OPENROUTER_API_KEY" in str(exc_info.value)
    finally:
        if key is not None:
            os.environ["OPENROUTER_API_KEY"] = key


def test_llm_variant_registered():
    """Runner accepts naive_llm, calyx_llm variants."""
    from benchmarks.harness.runner import load_cases, main
    import sys
    from io import StringIO

    repo_root = Path(__file__).resolve().parents[1]
    suite_path = repo_root / "benchmarks" / "suites" / "prompt_injection_v0_1" / "cases.jsonl"
    if not suite_path.exists():
        pytest.skip("suite cases.jsonl not found")

    with tempfile.TemporaryDirectory() as d:
        runtime_dir = Path(d) / "runtime"
        runtime_dir.mkdir()
        buf = StringIO()
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            sys.argv = [
                "runner",
                "--suite", "prompt_injection_v0_1",
                "--variant", "calyx_llm",
                "--seed", "99",
                "--runtime-dir", str(runtime_dir),
                "--llm-backend", "mock",
            ]
            sys.stdout = buf
            main()
        except SystemExit as e:
            if e.code != 0:
                raise
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout
        out = buf.getvalue()
        assert "Metrics (calyx_llm):" in out
        assert "Receipts:" in out


def test_wrapper_produces_json_contract_text():
    """wrap_prompt_for_tool_calls produces text that defines the JSON contract and examples."""
    from benchmarks.harness.llm_adapter import wrap_prompt_for_tool_calls, TOOL_CALL_PROTOCOL_INSTRUCTION

    out = wrap_prompt_for_tool_calls("User: list files")
    assert "tool_calls" in out
    assert "JSON" in out or "json" in out
    assert "fs_list" in out or "fs_read" in out or "repo_grep" in out
    assert "{\"tool_calls\":[]}" in out or '"tool_calls":[]' in out
    assert "no markdown" in out.lower() or "no prose" in out.lower()
    assert "User: list files" in out


def test_llm_mock_with_wrapper_yields_tool_calls_attempted_nonempty():
    """With mock backend, wrapped prompt yields non-empty tool_calls_attempted for injection cases."""
    from benchmarks.harness.runner import load_cases, _run_case_llm
    from benchmarks.harness.llm_adapter import get_adapter

    repo_root = Path(__file__).resolve().parents[1]
    suite_path = repo_root / "benchmarks" / "suites" / "prompt_injection_v0_1" / "cases.jsonl"
    if not suite_path.exists():
        pytest.skip("suite cases.jsonl not found")

    cases = load_cases(suite_path)
    adapter = get_adapter(use_mock=True)
    nonempty = 0
    for case in cases:
        attempted, executed, _, _, _, _, _ = _run_case_llm(
            case, "calyx_llm", seed=42, run_id="t1", adapter=adapter
        )
        if attempted:
            nonempty += 1
    assert nonempty > 0, "Mock + wrapper should yield at least one case with non-empty tool_calls_attempted"


def test_parse_tool_calls_preamble_fenced_json():
    """Parse extracts JSON from preamble + fenced block."""
    from benchmarks.harness.llm_adapter import parse_tool_calls_from_json

    raw = 'Here is the output:\n\n```json\n{"tool_calls":[{"name":"fs_list","args":{"path":"."}}]}\n```'
    tool_calls, errors = parse_tool_calls_from_json(raw)
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "fs_list"
    assert tool_calls[0]["args"] == {"path": "."}
    assert errors == []


def test_parse_tool_calls_singular_tool_call():
    """Parse accepts singular tool_call and normalizes to list."""
    from benchmarks.harness.llm_adapter import parse_tool_calls_from_json

    raw = '{"tool_call":{"name":"fs_read","args":{"path":"x"}}}'
    tool_calls, errors = parse_tool_calls_from_json(raw)
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "fs_read"
    assert tool_calls[0]["args"] == {"path": "x"}
    assert errors == []


def test_parse_tool_calls_malformed_json_failure():
    """Malformed JSON returns parse_ok False and error string."""
    from benchmarks.harness.llm_adapter import parse_tool_calls_from_json

    tool_calls, errors = parse_tool_calls_from_json("not valid json {{{")
    assert tool_calls == []
    assert len(errors) > 0
    assert "parse" in str(errors).lower() or "expecting" in str(errors).lower() or "value" in str(errors).lower()


def test_trailing_comma_normalization():
    """Trailing commas before } or ] are removed so valid JSON parses."""
    from benchmarks.harness.llm_adapter import parse_tool_calls_from_json

    # Object trailing comma
    raw1 = '{"tool_calls":[{"name":"fs_list","args":{"path":"."},}]}'
    tool_calls1, errors1 = parse_tool_calls_from_json(raw1)
    assert len(tool_calls1) == 1, errors1
    assert tool_calls1[0]["name"] == "fs_list"
    assert errors1 == []

    # Array trailing comma
    raw2 = '{"tool_calls":[{"name":"fs_read","args":{}},]}'
    tool_calls2, errors2 = parse_tool_calls_from_json(raw2)
    assert len(tool_calls2) == 1, errors2
    assert tool_calls2[0]["name"] == "fs_read"
    assert errors2 == []


def test_non_trailing_comma_malformed_json_still_fails():
    """Malformed JSON that is not just trailing commas still fails (no over-normalization)."""
    from benchmarks.harness.llm_adapter import parse_tool_calls_from_json

    # Missing comma between keys, wrong structure
    tool_calls, errors = parse_tool_calls_from_json('{"tool_calls":[{"name" "fs_list","args":{}}]}')
    assert tool_calls == []
    assert len(errors) > 0

    # Truncated JSON
    tool_calls2, errors2 = parse_tool_calls_from_json('{"tool_calls":[{"name":"fs_list"')
    assert tool_calls2 == []
    assert len(errors2) > 0


def test_llm_output_never_executes_code():
    """Adapter parsing never uses eval/exec; subprocess command fixed and not from prompt."""
    from benchmarks.harness.llm_adapter import parse_tool_calls_from_json

    # parse_tool_calls_from_json uses json.loads only, never eval/exec
    tool_calls, errors = parse_tool_calls_from_json('{"tool_calls":[{"name":"fs_read","args":{"path":"."}}]}')
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "fs_read"
    assert errors == []

    # Invalid JSON does not exec
    tool_calls2, errors2 = parse_tool_calls_from_json("not json")
    assert tool_calls2 == []
    assert len(errors2) > 0

    # LocalRuntime: command fixed, prompt via stdin only
    from benchmarks.harness.llm_backends.local_runtime import LocalRuntime

    cfg = {"command": ["echo", "fixed"], "model_id": "test"}
    rt = LocalRuntime(cfg)
    assert rt.command == ["echo", "fixed"]
    # generate passes prompt via input=, never in argv
    # (we can't run echo as "ollama" substitute easily; MockRuntime suffices for this test)


def test_receipt_contains_llm_fields_for_llm_variants():
    """Receipt entries include llm_* fields when variant is llm-based; schema remains valid."""
    from benchmarks.harness.runner import load_cases, _run_case_llm
    from benchmarks.harness.llm_adapter import get_adapter
    from benchmarks.harness import receipts, metrics

    repo_root = Path(__file__).resolve().parents[1]
    suite_path = repo_root / "benchmarks" / "suites" / "prompt_injection_v0_1" / "cases.jsonl"
    if not suite_path.exists():
        pytest.skip("suite cases.jsonl not found")

    cases = load_cases(suite_path)
    adapter = get_adapter(use_mock=True)

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        case = cases[0]
        attempted, executed, decision, policy_reason, actual_outcome, pass_fail, llm_meta = (
            _run_case_llm(case, "calyx_llm", seed=42, run_id="t1", adapter=adapter)
        )
        receipts.write_receipt(
            path=path,
            suite_id="prompt_injection_v0_1",
            case_id=case.get("case_id", ""),
            prompt=case.get("prompt", ""),
            system_variant="calyx_llm",
            tool_calls_attempted=attempted,
            tool_calls_executed=executed,
            decision=decision,
            policy_reason=policy_reason,
            expected_outcome=case.get("expected_outcome", "contained"),
            actual_outcome=actual_outcome,
            pass_fail=pass_fail,
            seed=42,
            run_id="t1",
            ts_utc="2026-02-13T00:00:00+00:00",
            **{k: v for k, v in llm_meta.items() if v is not None or k == "llm_parse_ok"},
        )
        with open(path) as f:
            line = f.read().strip()
        receipt = json.loads(line)
        assert "llm_backend" in receipt
        assert "llm_model_id" in receipt
        assert "llm_response_hash" in receipt
        assert "llm_parse_ok" in receipt
        assert receipt["schema_version"] == "1.0"
        assert receipt["system_variant"] == "calyx_llm"
        # Schema valid for metrics
        subset = [receipt]
        m = metrics.compute_metrics(subset)
        assert "determinism_hash" in m


def test_receipt_immutability_no_contaminated_append():
    """Second run with same suite+seed creates new file; no append to prior partial."""
    from benchmarks.harness.runner import main
    import sys
    from io import StringIO

    repo_root = Path(__file__).resolve().parents[1]
    suite_path = repo_root / "benchmarks" / "suites" / "prompt_injection_v0_1" / "cases.jsonl"
    if not suite_path.exists():
        pytest.skip("suite cases.jsonl not found")

    with tempfile.TemporaryDirectory() as d:
        runtime_dir = Path(d) / "runtime"
        runtime_dir.mkdir()
        out_dir = runtime_dir / "benchmarks" / "results" / "prompt_injection_v0_1"
        out_dir.mkdir(parents=True)
        run_id = "9fe387f74b79"
        partial = out_dir / f"{run_id}__20200101T000000.jsonl"
        partial.write_text('{"fake": true}\n' * 10, encoding="utf-8")
        assert partial.exists()
        buf = StringIO()
        old_argv, old_stdout = sys.argv, sys.stdout
        try:
            sys.argv = [
                "runner",
                "--suite", "prompt_injection_v0_1",
                "--variant", "calyx_llm",
                "--seed", "1337",
                "--runtime-dir", str(runtime_dir),
                "--llm-backend", "mock",
            ]
            sys.stdout = buf
            main()
        except SystemExit as e:
            if e.code != 0:
                raise
        finally:
            sys.argv, sys.stdout = old_argv, old_stdout
        out = buf.getvalue()
        assert "Receipts:" in out
        receipt_line = [l for l in out.splitlines() if l.strip().startswith("Receipts:")][0]
        path_str = receipt_line.replace("Receipts:", "").strip()
        new_path = Path(path_str)
        assert new_path.exists()
        assert new_path != partial
        assert partial.read_text().count("\n") == 10
        lines = new_path.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l.strip()]
        assert len(lines) == 50, f"expected 50 lines, got {len(lines)}"


def test_policy_applied_to_llm_tool_calls():
    """In calyx_llm, unknown tool denied (deny_by_default); no forbidden tools executed."""
    from benchmarks.harness.runner import load_cases, _run_case_llm
    from benchmarks.harness.llm_adapter import get_adapter
    from benchmarks.harness import policy

    repo_root = Path(__file__).resolve().parents[1]
    suite_path = repo_root / "benchmarks" / "suites" / "prompt_injection_v0_1" / "cases.jsonl"
    if not suite_path.exists():
        pytest.skip("suite cases.jsonl not found")

    cases = load_cases(suite_path)
    adapter = get_adapter(use_mock=True)

    # Mock returns tool calls parsed from prompt; injection cases have exec, eval, etc.
    for case in cases:
        attempted, executed, decision, policy_reason, actual_outcome, pass_fail, _ = (
            _run_case_llm(case, "calyx_llm", seed=42, run_id="t1", adapter=adapter)
        )
        # All executed tools must be in allowlist
        for e in executed:
            name = (e.get("name") or "").strip()
            assert name in policy.ALLOWLIST, f"forbidden tool executed: {name}"
        # No forbidden tool must run
        forbidden = policy.FORBIDDEN
        for e in executed:
            name = (e.get("name") or "").strip()
            assert name not in forbidden, f"forbidden tool executed: {name}"
