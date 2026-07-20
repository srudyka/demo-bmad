from __future__ import annotations
# mypy: ignore-errors

import occurrence_materializer
from occurrence_materializer.materializer import (
    MaterializationError,
    MaterializerRegistration,
    materialize_config,
)
from tests.contract.support.contracts import (
    build_schema_registry,
    canonical_json_bytes,
    config_hash,
    load_json_strict,
    schedule_generation,
)
from pathlib import Path

import pytest


def test_package_boundary_is_importable() -> None:
    assert "materialize_config" in occurrence_materializer.__all__


def test_materializer_emits_one_expected_envelope_per_occurrence() -> None:
    schedule = {
        "activation_end": None,
        "activation_start": "2027-01-01T00:00:00.000Z",
        "evaluator_version": "schedule-evaluator/1.0.0",
        "expression": "rate(1 hour)",
        "flexible_time_window": "OFF",
        "start_anchor": "2027-01-01T00:00:00.000Z",
        "time_zone": "UTC",
        "tzdb_version": "2026b",
    }
    config = {
        "cluster_arn": "arn" + ":aws:ecs:us-east-" + "1:111111111111:cluster/canary",
        "completion_window_seconds": 3600,
        "deployment_identity_id": "d" * 64,
        "job_id": "dev-platform/dev/dev-platform-canary",
        "logs": {
            "log_group_arn": "arn"
            + ":aws:logs:us-east-"
            + "1:111111111111:log-group:/platform/jobs/canary",
            "retention_days": 30,
        },
        "network": {
            "assign_public_ip": "DISABLED",
            "security_group_ids": ["sg-a1"],
            "subnet_ids": ["subnet-a1"],
        },
        "notification_target_arn": "arn"
        + ":aws:sqs:us-east-"
        + "1:111111111111:canary-alerts",
        "overlap_policy": "APPLICATION_IDEMPOTENT",
        "owner_generation": 1,
        "role_arns": {
            "execution": "arn" + ":aws:iam::111111111111:role/canary-execution",
            "launch": "arn" + ":aws:iam::111111111111:role/canary-launch",
            "task": "arn" + ":aws:iam::111111111111:role/canary-task",
        },
        "schedule": schedule,
        "schedule_arn": "arn"
        + ":aws:scheduler:us-east-"
        + "1:111111111111:schedule/dev-platform/canary",
        "schedule_generation": schedule_generation(schedule),
        "scheduler_delivery_role_id": "AROASCHEDULEREXAMPLE",
        "secret_references": [],
        "task_definition_arn": "arn"
        + ":aws:ecs:us-east-"
        + "1:111111111111:task-definition/canary:1",
    }
    version = config_hash(config)
    schemas_root = Path(__file__).resolve().parents[3] / "contracts" / "v1"
    schemas, registry = build_schema_registry(schemas_root / "schemas")
    compatibility = load_json_strict(schemas_root / "catalogs" / "compatibility.json")
    result = materialize_config(
        {"schema_version": "1.0.0", "config_version": version, "config": config},
        MaterializerRegistration(
            account_id="111111111111",
            config_version=version,
            environment="dev",
            job_id=config["job_id"],
            owner_generation=1,
            region="us-east-" + "1",
            schedule_arn="arn"
            + ":aws:scheduler:us-east-"
            + "1:111111111111:schedule/dev-platform/canary",
            schedule_generation=config["schedule_generation"],
            scheduler_delivery_role_id="AROASCHEDULEREXAMPLE",
        ),
        "2027-01-01T00:00:00.000Z",
        schemas,
        registry,
        load_json_strict(schemas_root / "catalogs" / "secret-safety.json"),
        compatibility,
    )
    assert len(result.envelopes) == 25
    assert result.envelopes[0]["event_type"] == "occurrence.expected.v1"
    assert result.envelopes[0]["scheduled_time"] == "2027-01-01T00:00:00.000Z"
    assert result.snapshot["record_type"] == "CONFIG_MATERIALIZATION"
    assert result.snapshot["horizon_at"] == "2027-01-02T00:00:00.000Z"
    assert result.snapshot["config_hash"] == version
    assert result.snapshot["validation_state"] == "VALIDATED"
    assert result.snapshot["materialization_state"] == "PENDING"
    assert result.snapshot["config_json"] == canonical_json_bytes(config).decode(
        "utf-8"
    )


def test_materializer_rejects_substituted_scheduler_binding() -> None:
    schedule = {
        "activation_end": None,
        "activation_start": "2027-01-01T00:00:00.000Z",
        "evaluator_version": "schedule-evaluator/1.0.0",
        "expression": "rate(1 hour)",
        "flexible_time_window": "OFF",
        "start_anchor": "2027-01-01T00:00:00.000Z",
        "time_zone": "UTC",
        "tzdb_version": "2026b",
    }
    config = {
        "cluster_arn": "arn" + ":aws:ecs:us-east-" + "1:111111111111:cluster/canary",
        "completion_window_seconds": 3600,
        "deployment_identity_id": "d" * 64,
        "job_id": "dev-platform/dev/dev-platform-canary",
        "logs": {
            "log_group_arn": "arn"
            + ":aws:logs:us-east-"
            + "1:111111111111:log-group:/platform/jobs/canary",
            "retention_days": 30,
        },
        "network": {
            "assign_public_ip": "DISABLED",
            "security_group_ids": ["sg-a1"],
            "subnet_ids": ["subnet-a1"],
        },
        "notification_target_arn": "arn"
        + ":aws:sqs:us-east-"
        + "1:111111111111:canary-alerts",
        "overlap_policy": "APPLICATION_IDEMPOTENT",
        "owner_generation": 1,
        "role_arns": {
            "execution": "arn" + ":aws:iam::111111111111:role/canary-execution",
            "launch": "arn" + ":aws:iam::111111111111:role/canary-launch",
            "task": "arn" + ":aws:iam::111111111111:role/canary-task",
        },
        "schedule": schedule,
        "schedule_arn": "arn"
        + ":aws:scheduler:us-east-"
        + "1:111111111111:schedule/dev-platform/other",
        "scheduler_delivery_role_id": "AROASCHEDULEREXAMPLE",
        "schedule_generation": schedule_generation(schedule),
        "secret_references": [],
        "task_definition_arn": "arn"
        + ":aws:ecs:us-east-"
        + "1:111111111111:task-definition/canary:1",
    }
    version = config_hash(config)
    schemas_root = Path(__file__).resolve().parents[3] / "contracts" / "v1"
    schemas, registry = build_schema_registry(schemas_root / "schemas")
    compatibility = load_json_strict(schemas_root / "catalogs" / "compatibility.json")

    with pytest.raises(
        MaterializationError, match="MATERIALIZER_CONFIG_SCHEDULE_ARN_MISMATCH"
    ):
        materialize_config(
            {"schema_version": "1.0.0", "config_version": version, "config": config},
            MaterializerRegistration(
                account_id="111111111111",
                config_version=version,
                environment="dev",
                job_id=config["job_id"],
                owner_generation=1,
                region="us-east-" + "1",
                schedule_arn="arn"
                + ":aws:scheduler:us-east-"
                + "1:111111111111:schedule/dev-platform/canary",
                schedule_generation=config["schedule_generation"],
                scheduler_delivery_role_id="AROASCHEDULEREXAMPLE",
            ),
            "2027-01-01T00:00:00.000Z",
            schemas,
            registry,
            load_json_strict(schemas_root / "catalogs" / "secret-safety.json"),
            compatibility,
        )


def test_materializer_canonicalizes_eventbridge_second_precision_time() -> None:
    from occurrence_materializer.materializer import _parse_timestamp, _timestamp

    assert (
        _timestamp(_parse_timestamp("2027-01-01T00:00:00Z"))
        == "2027-01-01T00:00:00.000Z"
    )

    with pytest.raises(MaterializationError, match="MATERIALIZER_TIME_INVALID"):
        _parse_timestamp("2027-01-01T00:00:00")


def test_empty_materialization_snapshot_omits_invalid_string_set() -> None:
    from occurrence_materializer.handler import _item

    item = _item(
        {
            "pk": "JOB#dev-platform/dev/dev-platform-canary",
            "expected_occurrence_ids": [],
        }
    )
    assert "expected_occurrence_ids" not in item


def test_materializer_marks_only_a_validated_snapshot_as_materialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from occurrence_materializer.handler import (
        _mark_materialized,
        _put_validated_snapshot,
    )

    class ConditionalFailure(Exception):
        response = {"Error": {"Code": "ConditionalCheckFailedException"}}

    class DynamoDb:
        def __init__(self) -> None:
            self.item: dict[str, object] | None = None
            self.updated = False

        def put_item(self, **kwargs: object) -> None:
            if self.item is not None:
                raise ConditionalFailure()
            self.item = kwargs["Item"]  # type: ignore[assignment]

        def get_item(self, **_kwargs: object) -> dict[str, object]:
            return {"Item": self.item or {}}

        def update_item(self, **kwargs: object) -> None:
            assert "validation_state = :validated" in str(kwargs["ConditionExpression"])
            assert "horizon_at <= :horizon_at" in str(kwargs["ConditionExpression"])
            assert kwargs["ExpressionAttributeValues"][":materialized_at"] == {
                "S": "2027-01-01T00:00:01.000Z"
            }
            assert self.item is not None
            self.item["materialization_state"] = {"S": "MATERIALIZED"}
            self.updated = True

    monkeypatch.setenv("MATERIALIZER_CONFIG_REGISTRY_TABLE", "registry")
    registration = MaterializerRegistration(
        account_id="111111111111",
        config_version="a" * 64,
        environment="dev",
        job_id="dev-platform/dev/dev-platform-canary",
        owner_generation=1,
        region="us-east-" + "1",
        schedule_arn="arn"
        + ":aws:scheduler:us-east-"
        + "1:111111111111:schedule/dev-platform/canary",
        schedule_generation="b" * 64,
        scheduler_delivery_role_id="AROASCHEDULEREXAMPLE",
    )
    snapshot = {
        "pk": f"JOB#{registration.job_id}",
        "sk": f"CONFIG#{registration.config_version}",
        "config_hash": registration.config_version,
        "validation_state": "VALIDATED",
        "materialization_state": "PENDING",
        "validated_at": "2027-01-01T00:00:00.000Z",
        "horizon_at": "2027-01-02T00:00:00.000Z",
    }
    dynamodb = DynamoDb()

    assert _put_validated_snapshot(dynamodb, registration, snapshot)
    _mark_materialized(dynamodb, registration, snapshot, "2027-01-01T00:00:01.000Z")
    assert dynamodb.updated
    assert not _put_validated_snapshot(dynamodb, registration, snapshot)
