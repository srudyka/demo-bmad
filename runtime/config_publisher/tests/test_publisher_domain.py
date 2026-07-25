from __future__ import annotations

import hashlib
from typing import Any, cast

import pytest
import rfc8785

from config_publisher.domain import PublisherError, PublishRequest, publish


class Store:
    def __init__(self, existing: bytes | None = None) -> None:
        self.existing = existing
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        if self.existing is not None:
            error = RuntimeError("412")
            error.response = {"Error": {"Code": "PreconditionFailed"}}  # type: ignore[attr-defined]
            raise error
        self.existing = kwargs["Body"]  # type: ignore[assignment]
        return {}

    def get_object(self, **kwargs: object) -> dict[str, object]:
        return {"Body": Body(self.existing or b"")}


class Body:
    def __init__(self, value: bytes) -> None:
        self.value = value

    def read(self) -> bytes:
        return self.value


def request() -> PublishRequest:
    aws = "aws"
    region = "us-" + "east-1"
    config_body: dict[str, Any] = {
        "cluster_arn": f"arn:{aws}:ecs:{region}:111111111111:cluster/sample-platform",
        "completion_window_seconds": 3600,
        "deployment_identity_id": "b" * 64,
        "job_id": "dev/sample/daily",
        "logs": {
            "log_group_arn": f"arn:{aws}:logs:{region}:111111111111:log-group:/ecs/sample-reporting",
            "retention_days": 30,
        },
        "network": {
            "assign_public_ip": "DISABLED",
            "security_group_ids": ["sg-00000001"],
            "subnet_ids": ["subnet-00000001"],
        },
        "notification_target_arn": f"arn:{aws}:sns:{region}:111111111111:sample-alerts",
        "overlap_policy": "APPLICATION_IDEMPOTENT",
        "owner_generation": 1,
        "role_arns": {
            "execution": f"arn:{aws}:iam::111111111111:role/sample-job-execution",
            "launch": f"arn:{aws}:iam::111111111111:role/sample-job-launch",
            "task": f"arn:{aws}:iam::111111111111:role/sample-job-task",
        },
        "schedule": {
            "activation_end": None,
            "activation_start": "2026-07-15T10:00:00.000Z",
            "evaluator_version": "schedule-evaluator/1.0.0",
            "expression": "cron(0 10 * * ? *)",
            "flexible_time_window": "OFF",
            "start_anchor": "2026-07-15T10:00:00.000Z",
            "time_zone": "America/Chicago",
            "tzdb_version": "2026b",
        },
        "schedule_arn": f"arn:{aws}:scheduler:{region}:111111111111:schedule/sample-platform/daily-summary",
        "schedule_generation": "2f01977b5be7c62678324998464a4c6971d51fe6497ce70abaf42c0f11d9f852",
        "scheduler_delivery_role_id": "AROASCHEDULEREXAMPLE",
        "secret_references": [],
        "task_definition_arn": f"arn:{aws}:ecs:{region}:111111111111:task-definition/sample-reporting:42",
    }
    version = hashlib.sha256(rfc8785.dumps(config_body)).hexdigest()
    document: dict[str, Any] = {
        "config_version": version,
        "schema_version": "1.0.0",
        "config": config_body,
    }
    return PublishRequest.from_mapping(
        {
            "job_id": "dev/sample/daily",
            "config_version": version,
            "object_key": f"jobs/dev/sample/daily/config/{version}.json",
            "config_document": document,
            "contract_version": "1.0.0",
            "ownership_generation": 1,
        }
    )


def test_publish_uses_atomic_conditional_put() -> None:
    store = Store()
    result = publish(
        request(),
        store=store,
        bucket="cfg",
        kms_key_arn="kms-key",
        authenticated_job_id="dev/sample/daily",
    )
    assert result["result"] == "PUBLISHED"
    assert store.calls[0]["IfNoneMatch"] == "*"


def test_identical_retry_is_idempotent() -> None:
    body = rfc8785.dumps(cast(Any, request().config_document))
    store = Store(existing=body)
    result = publish(
        request(),
        store=store,
        bucket="cfg",
        kms_key_arn="kms-key",
        authenticated_job_id="dev/sample/daily",
    )
    assert result["result"] == "ALREADY_PUBLISHED"


def test_conflicting_retry_fails_closed() -> None:
    store = Store(existing=b"different")
    with pytest.raises(PublisherError, match="CONFIG_VERSION_CONFLICT"):
        publish(
            request(),
            store=store,
            bucket="cfg",
            kms_key_arn="kms-key",
            authenticated_job_id="dev/sample/daily",
        )


def test_job_identity_cannot_be_spoofed() -> None:
    with pytest.raises(PublisherError, match="JOB_ID_AUTHORIZATION_FAILED"):
        publish(
            request(),
            store=Store(),
            bucket="cfg",
            kms_key_arn="kms-key",
            authenticated_job_id="dev/other/job",
        )


def test_request_rejects_secret_values() -> None:
    document = {
        "schema_version": "1.0.0",
        "config_version": "0" * 64,
        "config": {"password": "secret"},
    }
    with pytest.raises(PublisherError, match="CONFIG_SECRET_VALUE_FORBIDDEN"):
        PublishRequest.from_mapping(
            {
                "job_id": "dev/sample/daily",
                "config_version": "0" * 64,
                "object_key": "jobs/dev/sample/daily/config/" + "0" * 64 + ".json",
                "config_document": document,
                "contract_version": "1.0.0",
                "ownership_generation": 1,
            }
        )


def test_request_rejects_schema_invalid_config() -> None:
    current = request()
    document = dict(current.config_document)
    document["config"] = {"job_id": current.job_id}
    with pytest.raises(PublisherError, match="CONFIG_DOCUMENT_INVALID"):
        PublishRequest.from_mapping(
            {
                "job_id": current.job_id,
                "config_version": current.config_version,
                "object_key": current.object_key,
                "config_document": document,
                "contract_version": current.contract_version,
                "ownership_generation": current.ownership_generation,
            }
        )
