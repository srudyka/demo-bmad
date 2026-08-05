from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.pilot_launch import (
    PilotLaunchError,
    build_decision_record,
    evaluate_launch_checklist,
    invalidate_launch,
    validate_decision_record,
    validate_launch_checklist,
    _measurement_digest,
)
from tests.contract.support.contracts import (
    build_schema_registry,
    load_json_strict,
    validate_contract_instance,
)


ROOT = Path(__file__).resolve().parents[2]
H1 = "a" * 40
H2 = "b" * 64


def _bindings() -> dict[str, object]:
    return {
        "release_version": "1.0.0",
        "compatibility_package_sha256": H2,
        "source_commit": H1,
        "workflow_sha": H1,
        "workflow_run_id": "42",
        "account_id": "123456789012",
        "region": "us-east-1",
        "environment": "prod",
        "pilot_id": "pilot-fixture",
        "target_manifest_sha256": H2,
        "module_version": "1.0.0",
        "workflow_version": "1.0.0",
        "observation_window": {
            "start": "2026-08-01T00:00:00.000Z",
            "end": "2026-08-08T00:00:00.000Z",
        },
    }


def checklist() -> dict[str, object]:
    binding = _bindings()
    evidence = {
        "evidence_id": "candidate",
        "kind": "candidate-record",
        "sha256": H2,
        "source_revision": H1,
        "status": "verified",
        "sensitivity": "internal-sanitized",
        "redacted": True,
        "binding": {
            "source_commit": H1,
            "workflow_run_id": "42",
            "account_id": "123456789012",
            "region": "us-east-1",
            "environment": "prod",
            "pilot_id": "pilot-fixture",
            "job_id": "prod/internal/report",
        },
    }
    return {
        "schema_version": "1.0.0",
        "checklist_id": "pilot-fixture/checklist",
        "status": "READY_FOR_REVIEW",
        "bindings": binding,
        "jobs": [
            {
                "job_id": "prod/internal/report",
                "repository": "org/internal-report",
                "application_owner": "app-team",
                "operational_owner": "platform-oncall",
                "risk_class": "low",
                "environment": "prod",
                "account_id": "123456789012",
                "region": "us-east-1",
                "dependencies": ["warehouse"],
                "side_effects": ["report files"],
            }
        ],
        "fields": [
            {
                "field_id": "candidate",
                "owner": "platform-owner",
                "evidence_type": "candidate-record",
                "due_at": "2026-08-01T00:00:00.000Z",
                "status": "complete",
                "blocking": True,
                "source_refs": ["candidate"],
            }
        ],
        "controls": [
            {
                "control_id": "readiness",
                "status": "passed",
                "blocking": True,
                "evidence_ids": ["candidate"],
                "invalidates": ["release", "job"],
            }
        ],
        "observation_contract": {
            "version": "1",
            "minimum_duration_seconds": 604800,
            "minimum_occurrences": 20,
            "schedule_frequencies": ["daily"],
            "healthy_windows": ["20 consecutive"],
            "controlled_failures": ["missing alert"],
            "alert_latency_target_seconds": 300,
            "false_alert_limit": 0,
            "lost_alert_limit": 0,
            "setup_time_method": "Story 4.9 event intervals",
            "review_categories": ["IAM", "observability"],
            "recovery_rehearsal_required": True,
            "stop_conditions": ["security violation"],
        },
        "qualifying_change_catalog": {
            "version": "1",
            "changes": [
                {
                    "change_id": "release",
                    "class": "release",
                    "behavioral": True,
                    "invalidates": ["qualification", "approval"],
                    "security_approval_required": False,
                }
            ],
        },
        "evidence_manifest": [evidence],
        "approval_matrix": {
            "required_roles": ["platform", "application"],
            "security_trigger_classes": ["iam", "trust", "networking"],
            "self_review_prevention": True,
            "protected_environment_verified": True,
            "branch_protection_verified": True,
            "emergency_bypass_policy": "time-bound independent approval",
        },
        "rollback_criteria": {
            "disable_launch_first": True,
            "known_good_identity_sha256": H2,
            "compensation_owner": "app-owner",
            "rto_seconds": 3600,
            "stop_actions": ["disable launch"],
            "verification_steps": ["verify alerts"],
        },
        "initiator": "initiator",
        "history": [
            {
                "event_id": "created",
                "status": "READY_FOR_REVIEW",
                "at": "2026-08-01T00:00:00.000Z",
                "actor": "initiator",
                "reason": "created",
                "record_sha256": H2,
            }
        ],
        "deployment_identity_sha256": [H2],
        "preflight_evidence_sha256": H2,
        "operations": {
            "notification_target": "platform-oncall",
            "escalation_policy": "page platform then application",
            "notification_verified": True,
            "escalation_verified": True,
        },
        "rollout_policy": {
            "support_owner": "platform-oncall",
            "supported_versions": ["1.0.x"],
            "deprecation_communication": "publish before migration",
            "exception_policy": "time-bound owner approval",
            "rollback_pause_criteria": "pause on alert or failed control",
            "rollout_scope": "named pilot jobs only",
        },
    }


def measurement() -> dict[str, object]:
    result = {
        "schema_version": "1.0.0",
        "calculation_version": "1",
        "status": "MEASURED",
        "bindings": {
            key: _bindings()[key]
            for key in (
                "release_version",
                "compatibility_package_sha256",
                "source_commit",
                "workflow_sha",
                "workflow_run_id",
                "account_id",
                "region",
                "environment",
                "pilot_id",
            )
        },
        "definition_id": "pilot-definition",
        "definition_sha256": H2,
        "baseline_package_sha256": H2,
        "pilot_package_sha256": H2,
        "source_reference_manifest": [{"source_id": "source", "sha256": H2}],
        "baseline_sample_ids": ["baseline-1"],
        "pilot_sample_ids": ["pilot-1"],
        "metrics": [
            {
                "metric_id": "setup",
                "calculation": "active_setup_seconds",
                "unit": "seconds",
                "status": "MEASURED",
                "value": 1,
                "baseline_value": 2,
                "comparison": "lower",
                "sample_size": 1,
                "included_sample_ids": ["pilot-1"],
                "excluded_sample_ids": [],
                "reason": "measured",
            }
        ],
        "limitations": [],
        "generated_at": "2026-08-08T00:00:00.000Z",
    }
    result["evidence_sha256"] = _measurement_digest(result)
    return result


def approvals() -> list[dict[str, object]]:
    return [
        {
            "role": role,
            "actor": f"{role}-reviewer",
            "approved_at": "2026-08-01T01:00:00.000Z",
            "expires_at": "2026-08-08T00:00:00.000Z",
            "source_commit": H1,
            "workflow_sha": H1,
            "workflow_run_id": "42",
            "deployment_identity_sha256": H2,
            "status": "approved",
        }
        for role in ("platform", "application")
    ]


def test_checklist_and_schema_are_strict() -> None:
    validate_launch_checklist(checklist())
    schemas, registry = build_schema_registry(ROOT / "contracts/v1/schemas")
    schema = schemas[
        "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:pilot-launch-checklist"
    ]
    assert validate_contract_instance(schema, checklist(), registry) == ()
    invalid = deepcopy(checklist())
    invalid["unexpected"] = True
    assert validate_contract_instance(schema, invalid, registry)


def test_missing_jobs_block_launch_but_measurement_is_post_launch() -> None:
    missing = checklist()
    missing["jobs"] = []
    result = evaluate_launch_checklist(missing)
    assert result["status"] == "BLOCKED"
    assert "JOBS_UNASSIGNED" in {item["code"] for item in result["blockers"]}
    assert "MEASUREMENT_NOT_AVAILABLE" not in {
        item["code"] for item in result["blockers"]
    }


def test_exact_scope_and_approval_rules_are_enforced() -> None:
    result = evaluate_launch_checklist(
        checklist(), measurement=measurement(), approvals=approvals()
    )
    assert result["status"] == "APPROVED_TO_START"
    bad = approvals()
    bad[0]["actor"] = "initiator"
    assert (
        evaluate_launch_checklist(
            checklist(), measurement=measurement(), approvals=bad
        )["status"]
        == "BLOCKED"
    )
    bad_measurement = measurement()
    bad_bindings = bad_measurement["bindings"]
    assert isinstance(bad_bindings, dict)
    bad_bindings["source_commit"] = "c" * 40
    assert (
        evaluate_launch_checklist(
            checklist(), measurement=bad_measurement, approvals=approvals()
        )["status"]
        == "BLOCKED"
    )


def test_decision_requires_measured_evidence_and_is_sealed() -> None:
    record = build_decision_record(
        checklist(),
        measurement(),
        decision="ACCEPTED",
        approvals=approvals(),
        rationale="Pilot evidence is complete.",
        owners=["platform-owner", "app-owner"],
        due_actions=["publish rollout"],
        scope="named pilot only",
        effective_date="2026-08-08T00:00:00.000Z",
        now="2026-08-08T00:00:00.000Z",
        evidence_ids=["candidate"],
    )
    validate_decision_record(record)
    tampered = dict(record)
    tampered["decision"] = "REJECTED"
    with pytest.raises(PilotLaunchError, match="PILOT_DECISION_DIGEST"):
        validate_decision_record(tampered)
    with pytest.raises(PilotLaunchError, match="PILOT_DECISION_MEASUREMENT_STATUS"):
        build_decision_record(
            checklist(),
            {**measurement(), "status": "INCONCLUSIVE"},
            decision="ACCEPTED",
            approvals=approvals(),
            rationale="x",
            owners=["o"],
            due_actions=["a"],
            scope="s",
            effective_date="2026-08-08T00:00:00.000Z",
            now="2026-08-08T00:00:00.000Z",
            evidence_ids=[],
        )


def test_behavioral_change_invalidates_exact_scopes() -> None:
    result = invalidate_launch(checklist(), "release")
    assert result["status"] == "BLOCKED"
    assert result["invalidated_scopes"] == ["approval", "qualification"]


def test_fixture_catalog_covers_decision_boundaries() -> None:
    fixture = load_json_strict(ROOT / "contracts/v1/fixtures/pilot-launch/cases.json")
    names = {case["name"] for case in fixture["cases"]}
    assert {
        "unassigned-candidate",
        "stale-release",
        "self-approval",
        "stop-condition",
        "accepted",
        "synthetic-only-not-executed",
    } <= names

    cases = {case["name"]: case for case in fixture["cases"]}
    assert (
        evaluate_launch_checklist({**checklist(), "jobs": []})["status"]
        == cases["unassigned-candidate"]["expected_status"]
    )
    assert (
        evaluate_launch_checklist(checklist(), approvals=approvals())["status"]
        == cases["complete-ready-candidate"]["expected_status"]
    )
    expired = approvals()
    expired[0]["expires_at"] = "2026-08-01T00:00:00.000Z"
    assert (
        evaluate_launch_checklist(
            checklist(),
            approvals=expired,
            now=__import__("datetime").datetime.fromisoformat(
                "2026-08-04T00:00:00+00:00"
            ),
        )["status"]
        == cases["expired-approval"]["expected_status"]
    )
    self_approval = approvals()
    self_approval[0]["actor"] = "initiator"
    assert (
        evaluate_launch_checklist(checklist(), approvals=self_approval)["status"]
        == cases["self-approval"]["expected_status"]
    )
    assert (
        evaluate_launch_checklist(
            {**checklist(), "status": "PAUSED"}, approvals=approvals()
        )["status"]
        == cases["stop-condition"]["expected_status"]
    )
    assert (
        invalidate_launch(
            checklist(),
            "release",
            current_bindings={**_bindings(), "source_commit": "c" * 40},
        )["status"]
        == cases["changed-input"]["expected_status"]
    )
