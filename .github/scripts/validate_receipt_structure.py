"""Validate the CI receipt generator without requiring tracked runtime receipts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


ALLOWED_RISK_TIERS = frozenset({"low", "med", "high"})
REQUIRED_FIELDS = frozenset(
    {
        "timestamp_utc",
        "pr_number",
        "risk_tier",
        "ci_workflow",
        "status",
    }
)


def validate_ci_receipt(receipt: Any, *, expected_pr_number: int | None = None) -> list[str]:
    """Return structural errors for a generated Code Factory CI receipt."""

    if not isinstance(receipt, dict):
        return ["receipt must be a JSON object"]

    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(receipt))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")

    timestamp = receipt.get("timestamp_utc")
    if not isinstance(timestamp, str):
        errors.append("timestamp_utc must be a string")
    else:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("timestamp_utc must include a timezone")
        except ValueError:
            errors.append("timestamp_utc must be ISO-8601")

    pr_number = receipt.get("pr_number")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number <= 0:
        errors.append("pr_number must be a positive integer")
    elif expected_pr_number is not None and pr_number != expected_pr_number:
        errors.append(f"pr_number must equal {expected_pr_number}")

    if receipt.get("risk_tier") not in ALLOWED_RISK_TIERS:
        errors.append("risk_tier must be one of: high, low, med")
    if receipt.get("ci_workflow") != "code_factory_gates":
        errors.append("ci_workflow must equal code_factory_gates")
    if receipt.get("status") != "completed":
        errors.append("status must equal completed")

    return errors


def validate_generator(generator: Path, *, pr_number: int) -> list[str]:
    """Generate one receipt per risk tier and validate the persisted JSON."""

    if not generator.is_file():
        return [f"receipt generator not found: {generator}"]

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="calyx-ci-receipt-") as temp_dir:
        for risk_tier in sorted(ALLOWED_RISK_TIERS):
            output = Path(temp_dir) / f"ci_receipt__{risk_tier}.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(generator),
                    "--pr-number",
                    str(pr_number),
                    "--risk-tier",
                    risk_tier,
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                errors.append(
                    f"generator failed for {risk_tier}: "
                    f"{(result.stderr or result.stdout).strip()}"
                )
                continue
            if not output.is_file():
                errors.append(f"generator did not create a receipt for {risk_tier}")
                continue
            try:
                receipt = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"generated receipt for {risk_tier} is unreadable: {exc}")
                continue
            tier_errors = validate_ci_receipt(receipt, expected_pr_number=pr_number)
            if receipt.get("risk_tier") != risk_tier:
                tier_errors.append(f"risk_tier must preserve requested value {risk_tier}")
            errors.extend(f"{risk_tier}: {error}" for error in tier_errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument(
        "--generator",
        type=Path,
        default=Path(__file__).resolve().with_name("generate_ci_receipt.py"),
    )
    args = parser.parse_args()

    if args.pr_number <= 0:
        print("ERROR: --pr-number must be a positive integer")
        return 2

    errors = validate_generator(args.generator.resolve(), pr_number=args.pr_number)
    if errors:
        print("CI receipt structure validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("CI receipt structure validation passed for risk tiers: high, low, med")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
