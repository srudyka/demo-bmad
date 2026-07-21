from __future__ import annotations

import hashlib

import pytest

from alert_router.domain import (
    AlertRoutingError,
    build_occurrence_alert,
    notification_identity,
    occurrence_alert_identity,
)


def outbox() -> dict[str, object]:
    return {
        "job_id": "dev/platform/canary",
        "occurrence_id": "a" * 64,
        "state": "FAILED",
        "failure_plane": "TASK",
        "policy": "occurrence-v1",
        "operator_safe_reason": "ECS_ESSENTIAL_EXIT_NONZERO",
        "detected_at": "2027-01-01T00:02:00.000Z",
    }


def config() -> dict[str, object]:
    return {
        "config_version": "b" * 64,
        "config": {
            "job_id": "dev/platform/canary",
            "notification_target_arn": "arn"
            + ":aws:sns:"
            + "us-"
            + "east-"
            + "1:"
            + "1" * 12
            + ":canary",
            "deployment_identity_id": "c" * 64,
        },
    }


def test_alert_identity_is_deterministic_and_distinguishes_occurrences() -> None:
    first = occurrence_alert_identity(
        "dev/platform/canary", "a" * 64, "FAILED", "TASK", "occurrence-v1"
    )
    second = occurrence_alert_identity(
        "dev/platform/canary", "b" * 64, "FAILED", "TASK", "occurrence-v1"
    )
    assert first == occurrence_alert_identity(
        "dev/platform/canary", "a" * 64, "FAILED", "TASK", "occurrence-v1"
    )
    assert first != second
    assert (
        first
        == hashlib.sha256(
            b"alert/v1\ndev/platform/canary\n"
            + b"a" * 64
            + b"\nFAILED\nTASK\noccurrence-v1"
        ).hexdigest()
    )


def test_notification_identity_includes_target() -> None:
    alert_id = "a" * 64
    first = notification_identity(
        alert_id,
        "arn" + ":aws:sns:" + "us-" + "east-" + "1:" + "1" + ":first",
    )
    second = notification_identity(
        alert_id,
        "arn" + ":aws:sns:" + "us-" + "east-" + "1:" + "1" + ":second",
    )
    assert first != second


def test_build_alert_uses_authoritative_config_and_safe_fields() -> None:
    alert = build_occurrence_alert(
        outbox(),
        config(),
        account_id="1" * 12,
        region="us-" + "east-" + "1",
        environment="dev",
        owner="platform-engineering",
        runbook_uri="https://runbooks.example.test/canary",
    )
    config_value = config()["config"]
    assert isinstance(config_value, dict)
    assert alert["notification_target_arn"] == config_value["notification_target_arn"]
    assert alert["deployment_identity_id"] == "c" * 64
    assert alert["operator_safe_reason"] == "ECS_ESSENTIAL_EXIT_NONZERO"
    assert "config" not in alert
    assert "raw" not in alert


def test_build_alert_rejects_missing_or_secret_bearing_target_and_reason() -> None:
    missing_target = config()
    config_value = missing_target["config"]
    assert isinstance(config_value, dict)
    config_value.pop("notification_target_arn")
    with pytest.raises(AlertRoutingError, match="NOTIFICATION_TARGET_MISSING"):
        build_occurrence_alert(
            outbox(),
            missing_target,
            account_id="1" * 12,
            region="us-" + "east-" + "1",
            environment="dev",
            owner="platform-engineering",
            runbook_uri="https://runbooks.example.test/canary",
        )

    secret_reason = outbox()
    secret_reason["operator_safe_reason"] = "password=do-not-publish"
    with pytest.raises(AlertRoutingError, match="ALERT_REASON_SECRET"):
        build_occurrence_alert(
            secret_reason,
            config(),
            account_id="1" * 12,
            region="us-" + "east-" + "1",
            environment="dev",
            owner="platform-engineering",
            runbook_uri="https://runbooks.example.test/canary",
        )
