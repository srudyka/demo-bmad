from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.recovery_qualification import (
    RECOVERY_CONTROL_IDS,
    RecoveryQualificationError,
    _digest,
    recovery_readiness_projection,
    validate_recovery_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
BINDINGS = {
    "release_version": "1.0.0",
    "compatibility_package_sha256": "a" * 64,
    "source_commit": "b" * 40,
    "workflow_sha": "c" * 40,
    "workflow_run_id": "recovery-fixture-1",
    "account_id": "111111111111",
    "region": "us-east-1",
    "environment": "qualification",
    "cell_identity": "cell-recovery-fixture",
    "deployment_identity_sha256": "d" * 64,
    "target_manifest_sha256": "e" * 64,
    "known_good_identity_sha256": "f" * 64,
}


def _evidence() -> dict[str, object]:
    evidence: dict[str, object] = {
        "schema_version": "1.0.0",
        "scenario_id": "cell-restore-replay",
        "mode": "credential-free-fixture",
        "incident_id": "incident-fixture-1",
        "bindings": dict(BINDINGS),
        "source_generation": "generation-defective",
        "known_good_generation": "generation-known-good",
        "restore_point": "2026-08-03T14:00:00.000Z",
        "evaluated_at": "2026-08-03T15:00:00.000Z",
        "expected_rpo_seconds": 900,
        "expected_rto_seconds": 3600,
        "launch_enabled": False,
        "phase_order": [
            "contain",
            "inventory",
            "restore-fresh-resources",
            "validate-structure",
            "cutover",
            "replay",
            "reconcile",
            "verify",
        ],
        "observations": {
            "tasks": [
                {
                    "task_arn": "task-1",
                    "state": "STOPPED",
                    "occurrence_id": "occ-1",
                    "deployment_identity": "d" * 64,
                },
                {
                    "task_arn": "task-2",
                    "state": "UNKNOWN",
                    "occurrence_id": "occ-2",
                    "deployment_identity": "d" * 64,
                },
            ],
            "occurrences": [
                {
                    "occurrence_id": "occ-1",
                    "state": "SUCCEEDED",
                    "task_arn": "task-1",
                    "deployment_identity": "d" * 64,
                },
                {
                    "occurrence_id": "occ-2",
                    "state": "AMBIGUOUS",
                    "task_arn": "task-2",
                    "deployment_identity": "d" * 64,
                    "operator_decision": "preserve",
                },
            ],
            "alerts": [
                {
                    "alert_id": "alert-1",
                    "occurrence_id": "occ-2",
                    "disposition": "reconciled",
                }
            ],
            "resources": {
                "fresh_targets": True,
                "encrypted": True,
                "structural_checks": [
                    "schema",
                    "indexes",
                    "streams",
                    "ttl",
                    "pitr",
                    "encryption",
                    "tags",
                    "policies",
                    "compatibility",
                ],
                "cutover": "ordered-single-generation",
            },
            "inventory": {
                "incident_id": "incident-fixture-1",
                "generation": "generation-defective",
                "in_flight_tasks": [
                    {
                        "task_arn": "task-1",
                        "occurrence_id": "occ-1",
                        "disposition": "drain",
                    }
                ],
                "unresolved_occurrences": [
                    {"occurrence_id": "occ-2", "disposition": "quarantine"}
                ],
                "alert_obligations": [
                    {
                        "alert_id": "alert-1",
                        "occurrence_id": "occ-2",
                        "disposition": "preserve",
                    }
                ],
                "side_effects": [
                    {
                        "effect_id": "effect-1",
                        "occurrence_id": "occ-1",
                        "disposition": "compensate",
                        "owner": "job-owner",
                    }
                ],
            },
        },
        "controls": [
            {
                "control_id": control,
                "result": "passed",
                "evidence": {
                    "status": "passed",
                    "observed": True,
                    "source": "fixture",
                    "assertion": control,
                },
                "evidence_sha256": "0" * 64,
            }
            for control in RECOVERY_CONTROL_IDS
        ],
        "cleanup": {
            "mode": "disable-first",
            "deleted": ["synthetic-cell", "synthetic-job", "injected-faults"],
            "retained": ["sanitized-recovery-evidence", "recovery-audit"],
            "forbidden_artifacts": [],
        },
    }
    unsigned = copy.deepcopy(evidence)
    evidence["evidence_sha256"] = _digest(unsigned)
    for control in evidence["controls"]:  # type: ignore[union-attr]
        control["evidence_sha256"] = _digest(control["evidence"])  # type: ignore[index]
    return evidence


def test_recovery_fixture_catalog_and_projection() -> None:
    catalog = (ROOT / "contracts/v1/fixtures/recovery/cases.json").read_text()
    assert "cell-restore-replay" in catalog
    summary = validate_recovery_evidence(
        _evidence(), BINDINGS, now="2026-08-03T15:00:00.000Z"
    )
    projection = recovery_readiness_projection(summary, BINDINGS)
    assert summary["status"] == "passed"
    assert set(projection["controls"]) == set(RECOVERY_CONTROL_IDS)
    assert all(value == "passed" for value in projection["controls"].values())


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(launch_enabled=True), "RECOVERY_LAUNCH_NOT_FENCED"),
        (
            lambda value: value["cleanup"].update(
                forbidden_artifacts=["terraform.tfstate"]
            ),
            "RECOVERY_CLEANUP_FAILED",
        ),
        (lambda value: value["controls"].pop(), "RECOVERY_CONTROL_SET"),
        (
            lambda value: value["observations"]["tasks"].append(
                {
                    "task_arn": "task-1",
                    "state": "RUNNING",
                    "occurrence_id": "occ-3",
                    "deployment_identity": "d" * 64,
                }
            ),
            "RECOVERY_DUPLICATE_TASK",
        ),
        (
            lambda value: value["observations"]["resources"].update(
                cutover="mixed-generation"
            ),
            "RECOVERY_SPLIT_BRAIN",
        ),
    ],
)
def test_recovery_evidence_fails_closed(mutation, code: str) -> None:
    evidence = _evidence()
    mutation(evidence)
    with pytest.raises(RecoveryQualificationError, match=code):
        validate_recovery_evidence(evidence, BINDINGS, now="2026-08-03T15:00:00.000Z")
