"""Validate credential-free recovery rehearsal evidence and project readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.recovery_qualification import (
    RecoveryQualificationError,
    recovery_readiness_projection,
    validate_recovery_evidence,
)


def _object(path: Path, root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not resolved.is_relative_to(resolved_root)
        or not resolved.is_file()
    ):
        raise RecoveryQualificationError("RECOVERY_ARTIFACT_PATH")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecoveryQualificationError("RECOVERY_ARTIFACT_SHAPE")
    return value


def _validate_artifact_root(root: Path) -> None:
    forbidden = (".tfstate", ".tfplan", ".env", "credential", "private", "secret")
    for path in root.rglob("*"):
        if path.is_symlink() or (
            path.is_file() and any(token in path.name.lower() for token in forbidden)
        ):
            raise RecoveryQualificationError("RECOVERY_FORBIDDEN_ARTIFACT")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--expected-workflow-run-id", required=True)
    args = parser.parse_args()
    _validate_artifact_root(args.artifact_root)
    evidence = _object(args.evidence, args.artifact_root)
    bindings = _object(args.bindings, args.artifact_root)
    expected = dict(bindings)
    expected.update(
        source_commit=args.expected_source_commit,
        workflow_run_id=args.expected_workflow_run_id,
    )
    if evidence.get("mode") != "credential-free-fixture":
        raise RecoveryQualificationError("RECOVERY_LIVE_ATTESTATION_REQUIRED")
    evaluated_at = evidence.get("evaluated_at")
    if not isinstance(evaluated_at, str):
        raise RecoveryQualificationError("RECOVERY_EVALUATED_AT_REQUIRED")
    evaluated = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
    if datetime.now(UTC) - evaluated > timedelta(hours=24):
        raise RecoveryQualificationError("RECOVERY_EVIDENCE_STALE")
    summary = validate_recovery_evidence(
        evidence,
        expected,
        now=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    )
    output = {
        "schema_version": "1.0.0",
        "status": "fixture-passed-not-production-ready",
        "summary": summary,
        "projection": recovery_readiness_projection(summary, expected),
        "evidence_sha256": hashlib.sha256(args.evidence.read_bytes()).hexdigest(),
        "bindings_artifact_sha256": hashlib.sha256(
            args.bindings.read_bytes()
        ).hexdigest(),
    }
    args.output.write_text(json.dumps(output, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, RecoveryQualificationError) as error:
        raise SystemExit(str(error)) from error
