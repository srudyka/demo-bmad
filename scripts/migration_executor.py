"""Credential-free bounded migration observation and evidence producer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import rfc8785

from scripts.deployment_targets import TargetViolation
from scripts.migration_contract import _sha, _text


def _digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def load_snapshot(path: Path) -> Mapping[str, Any]:
    """Load a bounded, sanitized snapshot; raw AWS state and secrets are forbidden."""
    try:
        snapshot = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise TargetViolation("MIGRATION_SNAPSHOT_UNREADABLE") from error
    if not isinstance(snapshot, Mapping):
        raise TargetViolation("MIGRATION_SNAPSHOT_SHAPE")
    required = {
        "schema_sha256",
        "access_pattern_sha256",
        "reducer_invariants_passed",
        "launch_disabled",
        "records",
    }
    if set(snapshot) != required or not isinstance(snapshot["records"], list):
        raise TargetViolation("MIGRATION_SNAPSHOT_SHAPE")
    _sha(snapshot["schema_sha256"], "MIGRATION_SNAPSHOT_SCHEMA")
    _sha(snapshot["access_pattern_sha256"], "MIGRATION_SNAPSHOT_ACCESS")
    if (
        snapshot["reducer_invariants_passed"] is not True
        or snapshot["launch_disabled"] is not True
    ):
        raise TargetViolation("MIGRATION_SNAPSHOT_SAFETY")
    if any(not isinstance(item, Mapping) for item in snapshot["records"]):
        raise TargetViolation("MIGRATION_SNAPSHOT_RECORDS")
    return snapshot


def execute_bounded_phase(
    *,
    migration_id: str,
    phase: str,
    source_snapshot_path: Path,
    target_snapshot_path: Path,
    source_release_sha256: str,
    target_release_sha256: str,
    operation_id: str,
    checkpoint_id: str,
    resumed: bool,
    observed_at: str,
    verified_at: str,
) -> dict[str, Any]:
    """Derive phase evidence from two bounded snapshots, never from claimed hashes."""
    _text(migration_id, "MIGRATION_ID")
    _text(phase, "MIGRATION_PHASE")
    _text(operation_id, "MIGRATION_OPERATION_ID")
    _text(checkpoint_id, "MIGRATION_CHECKPOINT_ID")
    _sha(source_release_sha256, "MIGRATION_SOURCE_CHECKSUM")
    _sha(target_release_sha256, "MIGRATION_TARGET_CHECKSUM")
    source = load_snapshot(source_snapshot_path)
    target = load_snapshot(target_snapshot_path)
    source_records = source["records"]
    target_records = target["records"]
    source_checksum = _digest(source_records)
    target_checksum = _digest(target_records)
    if len(source_records) != len(target_records) or source_checksum != target_checksum:
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_MISMATCH")
    if source["schema_sha256"] != target["schema_sha256"]:
        raise TargetViolation("MIGRATION_SCHEMA_COMPATIBILITY")
    if source["access_pattern_sha256"] != target["access_pattern_sha256"]:
        raise TargetViolation("MIGRATION_ACCESS_PATTERN")
    if resumed and not checkpoint_id:
        raise TargetViolation("MIGRATION_CHECKPOINT_ID")
    return {
        "migration_id": migration_id,
        "phase": phase,
        "operation_id": operation_id,
        "status": "verified",
        "checkpoint_id": checkpoint_id,
        "resumed": resumed,
        "source_count": len(source_records),
        "target_count": len(target_records),
        "source_checksum": source_checksum,
        "target_checksum": target_checksum,
        "source_schema_sha256": source["schema_sha256"],
        "target_schema_sha256": target["schema_sha256"],
        "source_release_sha256": source_release_sha256,
        "target_release_sha256": target_release_sha256,
        "access_pattern_sha256": source["access_pattern_sha256"],
        "reducer_invariants_passed": True,
        "launch_disabled": True,
        "observed_at": observed_at,
        "verified_at": verified_at,
        "empty_scope_justification": "No records in bounded source scope."
        if not source_records
        else "",
    }
