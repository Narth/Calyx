import json
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_phase0_pipeline():
    with TemporaryDirectory() as temp_dir:
        outdir = Path(temp_dir)
        evidence_path = outdir / "evidence.jsonl"

        assessor = load_module(Path("tools/calyx_guardian/guardian_assess_windows.py"), "guardian_assess_windows")
        renderer = load_module(Path("tools/calyx_guardian/render/render_report.py"), "render_report")

        record = {
            "ts_utc": "2024-01-01T00:00:00Z",
            "host_id": "host",
            "source": "powershell:Get-HotFix",
            "command": "Get-HotFix",
            "result_summary": json.dumps({"count": 0, "latest_hotfix": "", "latest_installed_on": ""}),
            "raw_hash": "hash",
            "raw_preview": "preview",
            "severity_hint": "info",
            "notes": ""
        }

        evidence_path.write_text("\ufeff" + json.dumps(record) + "\n", encoding="utf-8")
        records = assessor.load_evidence(outdir)
        policy = assessor.load_policy()
        findings = assessor.generate_findings(records, policy)

        findings_path = outdir / "findings.json"
        findings_path.write_text(json.dumps(findings, indent=2, sort_keys=True), encoding="utf-8")

        report_first = renderer.build_report(findings)
        report_second = renderer.build_report(findings)

        report_path = outdir / "report.md"
        report_path.write_text(report_first, encoding="utf-8")

        assert findings
        assert any(finding["id"] == "patching.no_hotfixes" for finding in findings)
        assert report_first == report_second
        assert report_path.read_text(encoding="utf-8") == report_first
