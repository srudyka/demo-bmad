from __future__ import annotations

import copy

import pytest

from scripts.deployment_evidence import (
    TargetViolation,
    validate_recovery_plan,
    validate_recovery_inventory,
)


def _inventory() -> dict[str, object]:
    return {
        "incident_id": "incident-1",
        "generation": "generation-defective",
        "in_flight_tasks": [
            {"task_arn": "task-1", "occurrence_id": "occ-1", "disposition": "drain"}
        ],
        "unresolved_occurrences": [
            {"occurrence_id": "occ-2", "disposition": "quarantine"}
        ],
        "alert_obligations": [
            {"alert_id": "alert-1", "occurrence_id": "occ-2", "disposition": "preserve"}
        ],
        "side_effects": [
            {
                "effect_id": "effect-1",
                "occurrence_id": "occ-1",
                "disposition": "compensate",
                "owner": "job-owner",
            }
        ],
    }


def test_recovery_inventory_requires_explicit_dispositions() -> None:
    result = validate_recovery_inventory(_inventory())
    assert result["status"] == "inventory-valid"
    assert result["counts"] == {
        "in_flight_tasks": 1,
        "unresolved_occurrences": 1,
        "alert_obligations": 1,
        "side_effects": 1,
    }


def test_recovery_plan_rejects_mutable_images_and_schedule_edits() -> None:
    plan = {
        "known_good_identity_sha256": "a" * 64,
        "target_manifest_sha256": "b" * 64,
        "current_identity_sha256": "c" * 64,
        "current_generation": "generation-7",
        "changed_addresses": ["aws_ecs_task_definition.job"],
        "disable_launch_first": True,
        "retire_generation": "generation-6",
        "evidence_action": "quarantine-and-drain",
        "fresh_plan_required": True,
        "state_migration": "none",
        "application_compensation_owner": "job-owner",
        "recovery_objective_seconds": 900,
        "verification": ["schedule", "occurrences", "alarms"],
        "image_references": [
            "123456789012.dkr.ecr.us-east-1.amazonaws.com/job@sha256:" + "a" * 64
        ],
    }
    validate_recovery_plan(plan)
    with pytest.raises(TargetViolation, match="RECOVERY_MUTABLE_IMAGE"):
        validate_recovery_plan(dict(plan, image_references=["job:latest"]))
    with pytest.raises(TargetViolation, match="RECOVERY_SCHEDULE_EDIT"):
        validate_recovery_plan(
            dict(plan, changed_addresses=["aws_scheduler_schedule.job"])
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["in_flight_tasks"][0].update(disposition="ignore"),
        lambda value: value["side_effects"][0].pop("owner"),
        lambda value: value["in_flight_tasks"].append(
            dict(value["in_flight_tasks"][0])
        ),
        lambda value: value.update(incident_id=""),
    ],
)
def test_recovery_inventory_fails_closed(mutation) -> None:
    value = copy.deepcopy(_inventory())
    mutation(value)
    with pytest.raises(TargetViolation, match="RECOVERY_INVENTORY"):
        validate_recovery_inventory(value)
