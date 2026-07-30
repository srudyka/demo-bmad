from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import rfc8785

from scripts.deployment_targets import TargetViolation
from scripts.migration_contract import (
    build_migration_manifest,
    calculate_compatibility_horizon,
    validate_component_compatibility,
    validate_cutover,
    validate_migration_manifest,
    validate_rollback,
)
from scripts.migration_executor import execute_bounded_phase


HORIZONS = {
    name: value
    for name, value in zip(
        (
            "queue",
            "replay",
            "runtime",
            "retention",
            "investigation",
            "recovery",
            "rollback",
        ),
        (14, 30, 1, 90, 45, 35, 30),
    )
}


def _consumer(validation: str = "ready") -> dict[str, str]:
    return {
        "consumer_id": "prod/platform/job-a",
        "current_identity": "release-1.0.0",
        "target_version": "2.0.0",
        "validation": validation,
        "required_change": "CONFIG and runtime reader",
        "owner": "platform@example.invalid",
        "due_at": "2026-08-01T00:00:00Z",
        "rollback_identity": "release-1.0.0",
    }


def _manifest(phase: str = "cutover", validation: str = "ready") -> dict[str, Any]:
    consumer = _consumer(validation)
    inventory = {
        "consumers": [consumer["consumer_id"]],
        "active_generations": ["generation-1"],
        "retired_generations": ["generation-0"],
        "config_versions": ["config-1"],
        "occurrences": ["occurrence-1"],
        "task_attempts": ["attempt-1"],
        "queues_dlqs": ["queue-1", "dlq-1"],
        "state_addresses": ["module.cell"],
        "policies": ["production-readiness@1.0.0"],
        "operator_procedures": ["docs/runbooks/platform-version-migration.md"],
        "rollback_horizons": list(HORIZONS),
    }
    return build_migration_manifest(
        migration_id="mig-2026-08-01-001",
        source_release="1.0.0",
        target_release="2.0.0",
        source_release_sha256="a" * 64,
        target_release_sha256="b" * 64,
        phase=phase,
        horizons=HORIZONS,
        consumers=[consumer],
        inventory=inventory,
        component_ranges={"cell": ">=2.0.0,<3.0.0"},
        required_components={"cell": "2.0.0"},
        launch_disabled=True,
        owner="platform@example.invalid",
        actor="github-actions[bot]",
        created_at="2026-07-30T12:00:00Z",
    )


def test_horizon_requires_all_positive_obligations() -> None:
    assert calculate_compatibility_horizon(HORIZONS) == 90
    with pytest.raises(TargetViolation, match="MIGRATION_HORIZON_UNKNOWN"):
        calculate_compatibility_horizon({"queue": 14})
    with pytest.raises(TargetViolation, match="MIGRATION_HORIZON_INVALID"):
        calculate_compatibility_horizon({**HORIZONS, "queue": 0})


def test_manifest_is_canonical_and_checksum_bound() -> None:
    manifest = _manifest()
    validate_migration_manifest(manifest)
    assert (
        manifest["manifest_sha256"]
        == hashlib.sha256(
            rfc8785.dumps(
                {
                    key: value
                    for key, value in manifest.items()
                    if key != "manifest_sha256"
                }
            )
        ).hexdigest()
    )
    manifest["consumers"][0]["owner"] = "attacker@example.invalid"
    with pytest.raises(TargetViolation, match="MIGRATION_CHECKSUM"):
        validate_migration_manifest(manifest)


def test_unknown_inventory_and_unsupported_components_fail_closed() -> None:
    bad = _manifest()
    bad["consumers"][0]["validation"] = "unknown"
    bad.pop("manifest_sha256")
    bad["manifest_sha256"] = hashlib.sha256(rfc8785.dumps(bad)).hexdigest()
    with pytest.raises(TargetViolation, match="MIGRATION_READINESS"):
        validate_migration_manifest(bad)
    with pytest.raises(TargetViolation, match="MIGRATION_UNSUPPORTED_COMPONENT"):
        validate_component_compatibility({"cell": "3.0.0"}, {"cell": ">=2.0.0,<3.0.0"})


def test_cutover_requires_all_ready_and_exact_acknowledgement() -> None:
    manifest = _manifest()
    validate_cutover(
        manifest,
        {
            "migration_id": manifest["migration_id"],
            "target_release": manifest["target_release"],
            "target_release_sha256": manifest["target_release_sha256"],
            "horizon_watermark": 90,
            "acknowledged_at": "2026-08-01T00:00:00Z",
            "issued_at": "2026-07-30T12:00:00Z",
            "expires_at": "2026-08-02T00:00:00Z",
            "actor": manifest["actor"],
            "plan_sha256": "d" * 64,
        },
    )
    with pytest.raises(TargetViolation, match="MIGRATION_ACKNOWLEDGEMENT"):
        validate_cutover(
            manifest,
            {
                "migration_id": "wrong",
                "target_release": manifest["target_release"],
                "target_release_sha256": manifest["target_release_sha256"],
                "horizon_watermark": 90,
                "acknowledged_at": "2026-08-01T00:00:00Z",
                "issued_at": "2026-07-30T12:00:00Z",
                "expires_at": "2026-08-02T00:00:00Z",
                "actor": manifest["actor"],
                "plan_sha256": "d" * 64,
            },
        )
    blocked = _manifest(validation="blocked")
    with pytest.raises(TargetViolation, match="MIGRATION_READINESS"):
        validate_cutover(
            blocked,
            {
                "migration_id": blocked["migration_id"],
                "target_release": blocked["target_release"],
                "target_release_sha256": blocked["target_release_sha256"],
                "horizon_watermark": 90,
                "acknowledged_at": "2026-08-01T00:00:00Z",
            },
        )


def test_rollback_requires_source_identity_and_supported_evidence() -> None:
    manifest = _manifest(phase="rollback")
    evidence = {
        "migration_id": manifest["migration_id"],
        "phase": "rollback",
        "operation_id": "rollback-1",
        "status": "verified",
        "checkpoint_id": "checkpoint-1",
        "resumed": True,
        "source_count": 1,
        "target_count": 1,
        "source_checksum": "c" * 64,
        "target_checksum": "c" * 64,
        "observed_at": "2026-07-30T12:01:00Z",
        "verified_at": "2026-07-30T12:02:00Z",
        "source_release_sha256": manifest["source_release_sha256"],
        "target_release_sha256": manifest["target_release_sha256"],
        "source_schema_sha256": "d" * 64,
        "target_schema_sha256": "d" * 64,
        "access_pattern_sha256": "e" * 64,
        "reducer_invariants_passed": True,
        "launch_disabled": True,
        "empty_scope_justification": "",
    }
    validate_rollback(
        manifest,
        known_good_release="1.0.0",
        evidence_supported=True,
        rollback_evidence=evidence,
    )
    with pytest.raises(TargetViolation, match="MIGRATION_ROLLBACK_COMPATIBILITY"):
        validate_rollback(
            manifest,
            known_good_release="1.0.0",
            evidence_supported=False,
            rollback_evidence=evidence,
        )
    with pytest.raises(TargetViolation, match="MIGRATION_ROLLBACK_COMPATIBILITY"):
        validate_rollback(
            manifest,
            known_good_release="0.9.0",
            evidence_supported=True,
            rollback_evidence=evidence,
        )


def test_phase_evidence_rejects_partial_or_mismatched_migration() -> None:
    manifest = _manifest(phase="migrate")
    evidence = {
        "migration_id": manifest["migration_id"],
        "phase": "migrate",
        "operation_id": "migration-1",
        "status": "verified",
        "checkpoint_id": "checkpoint-1",
        "resumed": False,
        "source_count": 2,
        "target_count": 1,
        "source_checksum": "a" * 64,
        "target_checksum": "a" * 64,
        "observed_at": "2026-07-30T12:01:00Z",
        "verified_at": "2026-07-30T12:02:00Z",
        "source_release_sha256": manifest["source_release_sha256"],
        "target_release_sha256": manifest["target_release_sha256"],
        "source_schema_sha256": "d" * 64,
        "target_schema_sha256": "d" * 64,
        "access_pattern_sha256": "e" * 64,
        "reducer_invariants_passed": True,
        "launch_disabled": True,
        "empty_scope_justification": "",
    }
    with pytest.raises(TargetViolation, match="MIGRATION_PHASE_EVIDENCE_COUNTS"):
        from scripts.migration_contract import validate_phase_evidence

        validate_phase_evidence(manifest, evidence)


def test_migration_fixture_catalog_is_executable_and_complete() -> None:
    fixture = json.loads(
        (
            Path(__file__).parents[2] / "contracts/v1/fixtures/migration/cases.json"
        ).read_text()
    )
    operations = {case["operation"] for case in fixture["cases"]}
    assert fixture["schema_version"] == "1.0.0"
    assert {
        "horizon_missing",
        "launch_enabled",
        "unsupported_component",
        "acknowledgement_mismatch",
        "partial_counts",
        "predecessor_missing",
        "rollback_evidence_missing",
    } <= operations


def test_migration_executor_derives_evidence_and_rejects_partial_snapshot(
    tmp_path: Path,
) -> None:
    snapshot = {
        "schema_sha256": "a" * 64,
        "access_pattern_sha256": "b" * 64,
        "reducer_invariants_passed": True,
        "launch_disabled": True,
        "records": [{"occurrence_id": "occ-1", "state": "validated"}],
    }
    source = tmp_path / "source.json"
    target = tmp_path / "target.json"
    source.write_text(json.dumps(snapshot))
    target.write_text(json.dumps(snapshot))
    evidence = execute_bounded_phase(
        migration_id="mig-1",
        phase="migrate",
        source_snapshot_path=source,
        target_snapshot_path=target,
        source_release_sha256="c" * 64,
        target_release_sha256="d" * 64,
        operation_id="op-1",
        checkpoint_id="cp-1",
        resumed=False,
        observed_at="2026-07-30T12:00:00Z",
        verified_at="2026-07-30T12:01:00Z",
    )
    assert evidence["source_count"] == 1
    assert evidence["source_checksum"] == evidence["target_checksum"]
    target.write_text(json.dumps({**snapshot, "records": []}))
    with pytest.raises(TargetViolation, match="MIGRATION_PHASE_EVIDENCE_MISMATCH"):
        execute_bounded_phase(
            migration_id="mig-1",
            phase="migrate",
            source_snapshot_path=source,
            target_snapshot_path=target,
            source_release_sha256="c" * 64,
            target_release_sha256="d" * 64,
            operation_id="op-2",
            checkpoint_id="cp-2",
            resumed=True,
            observed_at="2026-07-30T12:00:00Z",
            verified_at="2026-07-30T12:01:00Z",
        )
