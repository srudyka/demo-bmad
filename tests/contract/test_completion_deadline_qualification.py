from __future__ import annotations

import hashlib

import pytest

from scripts.completion_deadline_qualification import (
    QualificationError,
    classify_completion,
    classify_deadline,
    completion_deadline_projection,
    qualify_alert_delivery,
    qualify_healthy_completions,
    qualify_partial_batch,
    reduce_completion_facts,
    validate_completion_evidence,
)


OCCURRENCE = "a" * 64
CONFIG = "b" * 64
GENERATION = "c" * 64
DEPLOYMENT = "d" * 64
TASK = "arn:aws:ecs:us-east-1:111111111111:task/platform/" + "e" * 32


def expected() -> dict[str, str]:
    return {
        "job_id": "dev/platform/canary",
        "job_name": "canary",
        "occurrence_id": OCCURRENCE,
        "config_version": CONFIG,
        "schedule_generation": GENERATION,
        "task_arn": TASK,
        "deployment_identity_id": DEPLOYMENT,
        "log_group": "/platform/canary",
        "log_stream": "ecs/canary/stream",
        "attempt_no": "0",
        "account_id": "111111111111",
        "region": "us-east-1",
    }


def completion(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        **expected(),
        "start_time": "2027-01-01T00:00:10.000Z",
        "completion_time": "2027-01-01T00:01:00.000Z",
        "status": "SUCCESS",
        "exit_code": 0,
        "success_marker": "JOB_COMPLETED_SUCCESSFULLY",
        "source_context": {
            "account_id": "111111111111",
            "region": "us-east-1",
            "log_group": "/platform/canary",
            "log_stream": "ecs/canary/stream",
        },
    }
    value.update(changes)
    return value


def test_completion_requires_exact_authenticated_boundary_and_marker() -> None:
    result = validate_completion_evidence(completion(), expected())
    assert result["occurrence_id"] == OCCURRENCE
    assert result["exit_code"] == 0
    with pytest.raises(QualificationError, match="COMPLETION_CORRELATION"):
        validate_completion_evidence(completion(occurrence_id="f" * 64), expected())
    with pytest.raises(QualificationError, match="COMPLETION_MARKER"):
        validate_completion_evidence(completion(success_marker="wrong"), expected())


def test_completion_needs_ecs_zero_exit_and_does_not_accept_late_success() -> None:
    valid = validate_completion_evidence(completion(), expected())
    assert classify_completion(valid, ecs_zero_exit=True)["state"] == "SUCCEEDED"
    assert classify_completion(valid, ecs_zero_exit=False)["state"] == "AMBIGUOUS"
    assert (
        classify_completion(
            valid, ecs_zero_exit=True, deadline_at="2027-01-01T00:00:30.000Z"
        )["state"]
        == "OVERDUE"
    )


def test_completion_fact_reducer_is_idempotent_and_conflict_safe() -> None:
    fact = {
        "fact_id": "f" * 64,
        "digest": "1" * 64,
        "kind": "SUCCESS",
        "occurrence_id": OCCURRENCE,
        "task_arn": TASK,
        "ecs_zero_exit": True,
    }
    assert reduce_completion_facts([fact, fact])["state"] == "SUCCEEDED"
    conflict = {**fact, "digest": "2" * 64}
    assert reduce_completion_facts([fact, conflict])["state"] == "AMBIGUOUS"


@pytest.mark.parametrize(
    ("current", "started", "completion", "expected_state"),
    [
        ("EXPECTED", False, None, "MISSED"),
        ("STARTED", True, None, "OVERDUE"),
        ("STARTED", True, "2027-01-01T00:59:00.000Z", "SUCCEEDED"),
        ("STARTED", True, "2027-01-01T01:01:00.000Z", "OVERDUE"),
    ],
)
def test_deadline_reduction_distinguishes_missed_overdue_and_late_completion(
    current: str,
    started: bool,
    completion: str | None,
    expected_state: str,
) -> None:
    assert (
        classify_deadline(
            current,
            started=started,
            completion_time=completion,
            deadline_at="2027-01-01T01:00:00.000Z",
        )["state"]
        == expected_state
    )


def test_partial_batch_returns_only_poison_records() -> None:
    result = qualify_partial_batch(
        [
            {"message_id": "ok", "disposition": "accepted"},
            {"message_id": "bad", "disposition": "quarantine"},
        ]
    )
    assert result == {"accepted": 1, "failed_message_ids": ["bad"]}


def test_alert_delivery_requires_deduplication_and_five_minute_bound() -> None:
    alert = {
        "alert_id": hashlib.sha256(b"alert").hexdigest(),
        "deduplication_id": hashlib.sha256(b"alert").hexdigest(),
        "job_id": "dev/platform/canary",
        "occurrence_id": OCCURRENCE,
        "state": "OVERDUE",
        "failure_plane": "DEADLINE",
        "detected_at": "2027-01-01T01:00:00.000Z",
        "delivered_at": "2027-01-01T01:04:59.000Z",
        "owner": "platform-oncall",
        "route": "sns",
        "runbook_uri": "https://example.invalid/runbook",
        "deployment_identity_id": DEPLOYMENT,
        "schema_version": "1.0.0",
        "account_id": "111111111111",
        "region": "us-east-1",
        "environment": "dev",
        "notification_target_arn": "arn:aws:sns:us-east-1:111111111111:canary",
        "operator_safe_reason": "deadline exceeded",
    }
    assert qualify_alert_delivery([alert])["passed"] is True
    with pytest.raises(QualificationError, match="ALERT_DEDUPLICATION"):
        qualify_alert_delivery([alert, alert])


def test_healthy_completion_requires_twenty_exact_occurrence_windows() -> None:
    cases = [
        {
            "occurrence_id": f"{index:064x}",
            "task_arn": TASK[:-32] + f"{index:032x}",
            "accepted_task_count": 1,
            "zero_exit_count": 1,
            "marker_count": 1,
            "terminal_state": "SUCCEEDED",
            "failure_alerts": 0,
            "cell_health_alerts": 0,
            "window_index": index,
            "accepted_task_arns": [TASK[:-32] + f"{index:032x}"],
            "zero_exit_task_arns": [TASK[:-32] + f"{index:032x}"],
            "success_marker_ids": [f"01933f4e-7b2d-7{index:02x}-8def-0123456789ab"],
            "failure_alert_ids": [],
            "cell_health_alert_ids": [],
        }
        for index in range(20)
    ]
    assert qualify_healthy_completions(cases)["passed"] is True


def test_completion_projection_requires_sealed_manifest_and_exact_results() -> None:
    manifest = {"manifest_sha256": "1" * 64, "bindings": {"x": "y"}}
    results = {
        key: "passed"
        for key in (
            "completion-correlation",
            "deadline-processing",
            "missed-overdue",
            "durable-alerting",
            "alert-pipeline",
            "alert-timing",
            "healthy-completions",
        )
    }
    with pytest.raises(QualificationError, match="MANIFEST_DIGEST"):
        completion_deadline_projection(manifest, results, {"x": "y"})


def test_alerts_and_scanner_require_structured_evidence() -> None:
    with pytest.raises(QualificationError, match="ALERT_REQUIRED"):
        qualify_alert_delivery([])


def test_completion_facts_reject_unknown_or_unpaired_success() -> None:
    with pytest.raises(QualificationError, match="COMPLETION_KIND"):
        reduce_completion_facts(
            [
                {
                    "fact_id": "f" * 64,
                    "digest": "1" * 64,
                    "kind": "BOGUS",
                    "occurrence_id": OCCURRENCE,
                    "task_arn": TASK,
                }
            ]
        )
    with pytest.raises(QualificationError, match="COMPLETION_RUNTIME_INPUT"):
        reduce_completion_facts(
            [
                {
                    "fact_id": "f" * 64,
                    "digest": "1" * 64,
                    "kind": "SUCCESS",
                    "occurrence_id": OCCURRENCE,
                    "task_arn": TASK,
                    "ecs_zero_exit": False,
                }
            ]
        )
