from __future__ import annotations

import hashlib
import json
from typing import Any

from alert_router.handler import dispatch_cell_alarm, dispatch_outbox_item


class FakeDynamo:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        key = kwargs["Key"]
        if key["pk"] == {"S": "JOB#dev/platform/canary"}:
            config = {
                "config_version": "b" * 64,
                "deployment_identity_id": "c" * 64,
                "job_id": "dev/platform/canary",
                "notification_target_arn": (
                    "arn" + ":aws:sns:us-" + "east-" + "1:" + "1" * 12 + ":canary"
                ),
            }
            config_json = json.dumps(config, separators=(",", ":"), sort_keys=True)
            return {
                "Item": {
                    "pk": {"S": "JOB#dev/platform/canary"},
                    "sk": {"S": "CONFIG#" + "b" * 64},
                    "job_id": {"S": "dev/platform/canary"},
                    "config_version": {"S": "b" * 64},
                    "schedule_generation": {"S": "d" * 64},
                    "validation_state": {"S": "VALIDATED"},
                    "materialization_state": {"S": "MATERIALIZED"},
                    "config_hash": {
                        "S": hashlib.sha256(config_json.encode()).hexdigest()
                    },
                    "config_json": {"S": config_json},
                }
            }
        return {}

    def put_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {}

    def update_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {}


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def publish(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return {"MessageId": "message-1"}


def outbox() -> dict[str, object]:
    return {
        "job_id": "dev/platform/canary",
        "config_version": "b" * 64,
        "occurrence_id": "a" * 64,
        "state": "FAILED",
        "failure_plane": "TASK",
        "policy": "occurrence-v1",
        "schedule_generation": "d" * 64,
        "detected_at": "2027-01-01T00:02:00.000Z",
        "operator_safe_reason": "ECS_ESSENTIAL_EXIT_NONZERO",
    }


def test_dispatch_publishes_enriched_alert_then_records_delivery() -> None:
    dynamodb = FakeDynamo()
    publisher = FakePublisher()
    result = dispatch_outbox_item(
        outbox(),
        dynamodb=dynamodb,
        publisher=publisher,
        config_table="config",
        notification_table="notifications",
        account_id="1" * 12,
        region="us-" + "east-" + "1",
        environment="dev",
        owner="platform-engineering",
        runbook_uri="https://runbooks.example.test/canary",
        now="2027-01-01T00:03:00.000Z",
    )
    assert result == "DELIVERED"
    assert len(publisher.calls) == 1
    assert publisher.calls[0]["TopicArn"].endswith(":canary")
    assert len(dynamodb.calls) == 5
    assert dynamodb.calls[2]["TableName"] == "notifications"


def test_dispatch_cell_alarm_preserves_recovery_state(monkeypatch: Any) -> None:
    monkeypatch.setenv("ALERT_ROUTER_CELL_ID", "cell-a")
    monkeypatch.setenv("ALERT_ROUTER_CELL_TARGET_ARN", "cell-target")
    monkeypatch.setenv("ALERT_ROUTER_NOTIFICATION_TABLE_NAME", "notifications")
    monkeypatch.setenv("ALERT_ROUTER_ACCOUNT_ID", "1" * 12)
    monkeypatch.setenv("ALERT_ROUTER_REGION", "us-" + "east-" + "1")
    monkeypatch.setenv("ALERT_ROUTER_ENVIRONMENT", "dev")
    monkeypatch.setenv("ALERT_ROUTER_OWNER", "platform-engineering")
    monkeypatch.setenv("ALERT_ROUTER_RUNBOOK_URI", "https://runbooks.example.test/cell")
    dynamodb = FakeDynamo()
    publisher = FakePublisher()

    result = dispatch_cell_alarm(
        {
            "source": "aws.cloudwatch",
            "alarmData": {
                "alarmName": "dev-cell-canary",
                "state": {"value": "OK", "timestamp": "2027-01-01T00:03:00.000Z"},
            },
        },
        dynamodb=dynamodb,
        publisher=publisher,
    )

    assert result == "DELIVERED"
    message = json.loads(publisher.calls[0]["Message"])
    assert message["state"] == "RECOVERED"
    assert (
        publisher.calls[0]["MessageAttributes"]["state"]["StringValue"] == "RECOVERED"
    )
