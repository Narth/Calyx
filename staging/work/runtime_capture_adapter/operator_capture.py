"""Operator-facing staging command for runtime capture -> mapping -> classification."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from staging.work.runtime_capture_adapter.capture import capture_live_runtime_state, load_capture_input
from staging.work.runtime_capture_adapter.mapper import normalize_capture_to_snapshot
from staging.work.runtime_capture_adapter.models import (
    RuntimeCaptureClassificationResult,
    RuntimeCaptureInput,
    RuntimeCaptureMappingValidation,
)
from staging.work.runtime_observer_simulation.observer import simulate_runtime_observer


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "staging" / "work" / "runtime_capture_adapter" / "artifacts"


@dataclass(frozen=True)
class OperatorCapturePaths:
    run_dir: Path
    raw_capture: Path
    canonical_snapshot: Path
    ingestion_trace: Path
    mapping_validation: Path
    normalization_result: Path
    classification_result: Path | None
    observer_emission: Path | None
    ambiguity_dir: Path
    governance_bundle_dir: Path


def run_live_capture_command(
    *,
    capture_id: str | None = None,
    corr_id: str | None = None,
    artifacts_root: Path = DEFAULT_ARTIFACTS_ROOT,
    repo_root: Path = REPO_ROOT,
) -> OperatorCapturePaths:
    resolved_capture_id = capture_id or _default_capture_id("live")
    resolved_corr_id = corr_id or resolved_capture_id
    capture = capture_live_runtime_state(repo_root=repo_root, capture_id=resolved_capture_id, corr_id=resolved_corr_id)
    return _persist_capture_chain(capture=capture, artifacts_root=artifacts_root)


def run_replay_capture_command(
    *,
    input_path: Path,
    artifacts_root: Path = DEFAULT_ARTIFACTS_ROOT,
) -> OperatorCapturePaths:
    capture = load_capture_input(input_path)
    return _persist_capture_chain(capture=capture, artifacts_root=artifacts_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Staging-only read-only runtime capture command for governed observation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    live_parser = subparsers.add_parser("live", help="Capture the current workstation state read-only.")
    live_parser.add_argument("--capture-id", help="Optional stable capture id. Defaults to a UTC timestamped id.")
    live_parser.add_argument("--corr-id", help="Optional correlation id. Defaults to capture id.")
    live_parser.add_argument(
        "--artifacts-root",
        default=str(DEFAULT_ARTIFACTS_ROOT),
        help="Root directory for emitted staging artifacts.",
    )
    live_parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root used for local runtime reads.",
    )

    replay_parser = subparsers.add_parser("replay", help="Replay a previously captured runtime input artifact.")
    replay_parser.add_argument("--input", required=True, help="Path to a runtime.capture.input JSON artifact.")
    replay_parser.add_argument(
        "--artifacts-root",
        default=str(DEFAULT_ARTIFACTS_ROOT),
        help="Root directory for emitted staging artifacts.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "live":
        paths = run_live_capture_command(
            capture_id=args.capture_id,
            corr_id=args.corr_id,
            artifacts_root=Path(args.artifacts_root),
            repo_root=Path(args.repo_root),
        )
    else:
        paths = run_replay_capture_command(
            input_path=Path(args.input),
            artifacts_root=Path(args.artifacts_root),
        )

    print(json.dumps(_paths_payload(paths), indent=2))
    return 0


def _persist_capture_chain(*, capture: RuntimeCaptureInput, artifacts_root: Path) -> OperatorCapturePaths:
    run_dir = artifacts_root / _safe_dirname(capture.capture_id)
    raw_dir = run_dir / "raw"
    mapping_dir = run_dir / "mapping"
    classification_dir = run_dir / "classification"
    ambiguity_dir = run_dir / "ambiguity"
    bundles_dir = run_dir / "bundles"
    for directory in (raw_dir, mapping_dir, classification_dir, ambiguity_dir, bundles_dir):
        directory.mkdir(parents=True, exist_ok=True)

    raw_capture_path = raw_dir / "runtime.capture.input.json"
    _write_json(raw_capture_path, capture.model_dump(mode="json"))

    normalization = normalize_capture_to_snapshot(capture)
    paths = OperatorCapturePaths(
        run_dir=run_dir,
        raw_capture=raw_capture_path,
        canonical_snapshot=mapping_dir / "runtime.observer.process_snapshot.json",
        ingestion_trace=mapping_dir / "runtime.capture.ingestion_trace.json",
        mapping_validation=mapping_dir / "runtime.capture.mapping_validation.json",
        normalization_result=mapping_dir / "runtime.capture.normalization_result.json",
        classification_result=classification_dir / "runtime.capture.classification_result.json",
        observer_emission=classification_dir / "runtime.observer.emission.json",
        ambiguity_dir=ambiguity_dir,
        governance_bundle_dir=bundles_dir,
    )
    _write_normalization_artifacts(normalization=normalization, paths=paths)

    if normalization.canonical_snapshot.health_context is None and normalization.canonical_snapshot.bridge_context is None:
        validation = RuntimeCaptureMappingValidation(
            schema_name="runtime.capture.mapping_validation",
            schema_version="1.0.0",
            validation_id=f"{capture.capture_id}.validation",
            corr_id=capture.corr_id,
            capture_id=capture.capture_id,
            timestamp_utc=datetime.now(UTC),
            snapshot_schema_valid=True,
            observer_emission_valid=False,
            no_mutation_performed=True,
            notes="Classification skipped because no governed health or bridge surface was observable in the canonical snapshot.",
        )
        _write_json(paths.mapping_validation, validation.model_dump(mode="json"))
        return OperatorCapturePaths(
            run_dir=paths.run_dir,
            raw_capture=paths.raw_capture,
            canonical_snapshot=paths.canonical_snapshot,
            ingestion_trace=paths.ingestion_trace,
            mapping_validation=paths.mapping_validation,
            normalization_result=paths.normalization_result,
            classification_result=None,
            observer_emission=None,
            ambiguity_dir=paths.ambiguity_dir,
            governance_bundle_dir=paths.governance_bundle_dir,
        )

    emission = simulate_runtime_observer(normalization.canonical_snapshot)
    validation = RuntimeCaptureMappingValidation(
        schema_name="runtime.capture.mapping_validation",
        schema_version="1.0.0",
        validation_id=f"{capture.capture_id}.validation",
        corr_id=capture.corr_id,
        capture_id=capture.capture_id,
        timestamp_utc=datetime.now(UTC),
        snapshot_schema_valid=True,
        observer_emission_valid=True,
        no_mutation_performed=True,
        notes="Capture normalized and classified without mutating live runtime state.",
    )
    classified = RuntimeCaptureClassificationResult(
        schema_name="runtime.capture.classification_result",
        schema_version="1.0.0",
        capture_id=capture.capture_id,
        corr_id=capture.corr_id,
        classified_at_utc=datetime.now(UTC),
        normalization=normalization,
        observer_emission=emission,
        mapping_validation=validation,
    )
    _write_classification_artifacts(classified=classified, paths=paths)
    return paths


def _write_normalization_artifacts(*, normalization, paths: OperatorCapturePaths) -> None:
    _write_json(paths.canonical_snapshot, normalization.canonical_snapshot.model_dump(mode="json"))
    _write_json(paths.ingestion_trace, normalization.ingestion_trace.model_dump(mode="json"))
    _write_json(paths.normalization_result, normalization.model_dump(mode="json"))

    for artifact in paths.ambiguity_dir.glob("*.json"):
        artifact.unlink()
    for marker in normalization.ambiguity_markers:
        _write_json(paths.ambiguity_dir / f"{_safe_dirname(marker.marker_id)}.json", marker.model_dump(mode="json"))


def _write_classification_artifacts(*, classified: RuntimeCaptureClassificationResult, paths: OperatorCapturePaths) -> None:
    _write_json(paths.mapping_validation, classified.mapping_validation.model_dump(mode="json"))
    if paths.classification_result is not None:
        _write_json(paths.classification_result, classified.model_dump(mode="json"))
    if paths.observer_emission is not None:
        _write_json(paths.observer_emission, classified.observer_emission.model_dump(mode="json"))

    for artifact in paths.governance_bundle_dir.glob("*.json"):
        artifact.unlink()
    for bundle in classified.observer_emission.governance_bundles:
        _write_json(
            paths.governance_bundle_dir / f"{_safe_dirname(bundle.scenario_name)}.json",
            bundle.model_dump(mode="json"),
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _default_capture_id(prefix: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%S") + "z"
    return f"runtime_capture.{prefix}.{stamp}"


def _safe_dirname(value: str) -> str:
    return value.replace("\\", "_").replace("/", "_").replace(":", "_")


def _paths_payload(paths: OperatorCapturePaths) -> dict[str, Any]:
    return {
        "run_dir": str(paths.run_dir),
        "raw_capture": str(paths.raw_capture),
        "canonical_snapshot": str(paths.canonical_snapshot),
        "ingestion_trace": str(paths.ingestion_trace),
        "mapping_validation": str(paths.mapping_validation),
        "normalization_result": str(paths.normalization_result),
        "classification_result": str(paths.classification_result) if paths.classification_result is not None else None,
        "observer_emission": str(paths.observer_emission) if paths.observer_emission is not None else None,
        "ambiguity_dir": str(paths.ambiguity_dir),
        "governance_bundle_dir": str(paths.governance_bundle_dir),
    }


if __name__ == "__main__":
    raise SystemExit(main())
