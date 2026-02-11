import json
import importlib.util
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only Phase 0 assessment")
def test_phase0_outputs():
    with TemporaryDirectory() as temp_dir:
        outdir = Path(temp_dir) / "logs"
        ps_script = Path("tools/calyx_guardian/guardian_assess_windows.ps1")
        py_assess = Path("tools/calyx_guardian/guardian_assess_windows.py")
        render_script = Path("tools/calyx_guardian/render/render_report.py")

        result = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps_script),
                "-OutDir",
                str(outdir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

        result = subprocess.run(
            [sys.executable, str(py_assess), "--outdir", str(outdir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

        result = subprocess.run(
            [sys.executable, str(render_script), "--outdir", str(outdir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

        assert (outdir / "evidence.jsonl").exists()
        assert (outdir / "findings.json").exists()
        assert (outdir / "report.md").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only Phase 0 assessment")
def test_phase0_deterministic_findings_and_report():
    with TemporaryDirectory() as temp_dir:
        outdir = Path(temp_dir) / "logs"
        ps_script = Path("tools/calyx_guardian/guardian_assess_windows.ps1")
        py_assess = Path("tools/calyx_guardian/guardian_assess_windows.py")
        render_script = Path("tools/calyx_guardian/render/render_report.py")

        subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps_script),
                "-OutDir",
                str(outdir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run([sys.executable, str(py_assess), "--outdir", str(outdir)], check=True)
        subprocess.run([sys.executable, str(render_script), "--outdir", str(outdir)], check=True)

        findings_first = (outdir / "findings.json").read_text(encoding="utf-8")
        report_first = (outdir / "report.md").read_text(encoding="utf-8")

        subprocess.run([sys.executable, str(py_assess), "--outdir", str(outdir)], check=True)
        subprocess.run([sys.executable, str(render_script), "--outdir", str(outdir)], check=True)

        findings_second = (outdir / "findings.json").read_text(encoding="utf-8")
        report_second = (outdir / "report.md").read_text(encoding="utf-8")

        assert findings_first == findings_second
        assert report_first == report_second


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only Phase 0 assessment")
def test_findings_schema_validation():
    with TemporaryDirectory() as temp_dir:
        outdir = Path(temp_dir) / "logs"
        ps_script = Path("tools/calyx_guardian/guardian_assess_windows.ps1")
        py_assess = Path("tools/calyx_guardian/guardian_assess_windows.py")

        subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps_script),
                "-OutDir",
                str(outdir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run([sys.executable, str(py_assess), "--outdir", str(outdir)], check=True)

        findings = json.loads((outdir / "findings.json").read_text(encoding="utf-8"))
        schema_path = Path("tools/calyx_guardian/schemas/finding.schema.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for finding in findings:
            for key in required:
                assert key in finding
            for key, spec in properties.items():
                if key not in finding:
                    continue
                if spec.get("type") == "array":
                    assert isinstance(finding[key], list)
                if spec.get("type") == "string":
                    assert isinstance(finding[key], str)
                if spec.get("type") == ["string", "null"]:
                    assert isinstance(finding[key], (str, type(None)))


def test_load_evidence_bom_tolerant():
    with TemporaryDirectory() as temp_dir:
        outdir = Path(temp_dir)
        evidence_path = outdir / "evidence.jsonl"
        module_path = Path("tools/calyx_guardian/guardian_assess_windows.py")
        spec = importlib.util.spec_from_file_location("guardian_assess_windows", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        record = {
            "ts_utc": "2024-01-01T00:00:00Z",
            "host_id": "host",
            "source": "test",
            "command": "noop",
            "result_summary": "{}",
            "raw_hash": "hash",
            "raw_preview": "preview",
            "severity_hint": "info",
            "notes": ""
        }
        evidence_path.write_text("\ufeff" + json.dumps(record) + "\n", encoding="utf-8")

        records_first = module.load_evidence(outdir)
        records_second = module.load_evidence(outdir)

        assert records_first == records_second
        assert records_first[0]["source"] == "test"
