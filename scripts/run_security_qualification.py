"""Validate and project sanitized Story 4.7 security evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from scripts.security_qualification import (
    SecurityQualificationError,
    security_readiness_projection,
    validate_security_evidence,
)


def _object(path: Path, root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not resolved.is_relative_to(resolved_root)
        or not resolved.is_file()
    ):
        raise SecurityQualificationError("SECURITY_ARTIFACT_PATH")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SecurityQualificationError("SECURITY_ARTIFACT_SHAPE")
    return value


def _validate_artifact_root(root: Path) -> None:
    forbidden = (
        ".tfstate",
        ".tfplan",
        ".env",
        "credential",
        "private",
        "secret",
    )
    for path in root.rglob("*"):
        if path.is_symlink() or (
            path.is_file() and any(token in path.name.lower() for token in forbidden)
        ):
            raise SecurityQualificationError("SECURITY_FORBIDDEN_ARTIFACT")


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
    expected_bindings = {
        **bindings,
        "source_commit": args.expected_source_commit,
        "workflow_run_id": args.expected_workflow_run_id,
    }
    attestation_key = os.environ.get("SECURITY_QUALIFICATION_ATTESTATION_KEY")
    if not attestation_key:
        raise SecurityQualificationError("SECURITY_ATTESTATION_KEY_REQUIRED")
    summary = validate_security_evidence(
        evidence,
        expected_bindings,
        attestation_key=attestation_key.encode("utf-8"),
    )
    projection = security_readiness_projection(summary, expected_bindings)
    evidence_sha256 = hashlib.sha256(args.evidence.read_bytes()).hexdigest()
    bindings_sha256 = hashlib.sha256(args.bindings.read_bytes()).hexdigest()
    output = {
        "schema_version": "1.0.0",
        "status": "passed",
        "summary": summary,
        "projection": projection,
        "evidence_sha256": evidence_sha256,
        "bindings_artifact_sha256": bindings_sha256,
        "source_artifact": args.evidence.name,
        "bindings_artifact": args.bindings.name,
        "bindings_sha256": projection["bindings_sha256"],
    }
    args.output.write_text(json.dumps(output, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, SecurityQualificationError) as error:
        raise SystemExit(str(error)) from error
