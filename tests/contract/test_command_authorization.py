from __future__ import annotations

from pathlib import Path

import pytest

from command_handler import (
    CallerContext,
    CommandRejected,
    OccurrenceBinding,
    authorize_operator_request,
)


ROOT = Path(__file__).resolve().parents[2]


def _request(**updates: object) -> dict[str, object]:
    request: dict[str, object] = {
        "schema_version": "1.0.0",
        "form": "operator_request",
        "request_id": "0190f2c9-6c00-7000-8000-000000000012",
        "job_id": "fake/dev/job",
        "scheduled_time": "2026-07-15T10:00:00.000Z",
        "actor": "operator",
        "approval_reference": "CHANGE-1",
        "reason": "verified failure",
        "expected_duplicate_effects": "may repeat one non-production notification",
        "verification_plan": "verify one success marker and zero essential exit",
        "compensation_acknowledged": True,
    }
    request.update(updates)
    return request


def _lookup(job_id: str, scheduled_time: str) -> OccurrenceBinding:
    return OccurrenceBinding(
        job_id,
        scheduled_time,
        "a" * 64,
        "b" * 64,
        "c" * 64,
        True,
        "cell-a",
        "123456789012",
        "us-test-1",
        "d" * 64,
    )


def test_operator_policy_has_no_workload_or_direct_state_authority() -> None:
    source = (ROOT / "modules/ecs-scheduled-job-platform/main.tf").read_text()
    operator = source[
        source.index('data "aws_iam_policy_document" "operator"') : source.index(
            'resource "aws_iam_role" "operator"'
        )
    ]
    for forbidden in (
        "sqs:SendMessage",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "ecs:RunTask",
        "iam:PassRole",
        "scheduler:UpdateSchedule",
    ):
        assert forbidden not in operator
    assert "lambda:InvokeFunction" in operator


def test_scope_and_freshness_rejections_are_stable() -> None:
    caller = CallerContext("operator", "session", "cell-a", "123456789012", "us-test-1")
    with pytest.raises(CommandRejected, match="COMMAND_CELL_SCOPE"):
        authorize_operator_request(
            _request(),
            caller,
            lookup=_lookup,
            approve=lambda *_: True,
            expected_cell_id="cell-b",
        )
    with pytest.raises(CommandRejected, match="COMMAND_STALE_OR_FUTURE"):
        authorize_operator_request(
            _request(), caller, lookup=_lookup, approve=lambda *_: True
        )
    with pytest.raises(CommandRejected, match="COMMAND_TYPE"):
        authorize_operator_request(
            _request(command_type={}), caller, lookup=_lookup, approve=lambda *_: True
        )


def test_compensation_is_required_for_sensitive_commands() -> None:
    caller = CallerContext("operator", "session", "cell-a", "123456789012", "us-test-1")
    with pytest.raises(CommandRejected, match="COMMAND_COMPENSATION_ACK"):
        authorize_operator_request(
            _request(command_type="DISABLE", compensation_acknowledged=False),
            caller,
            lookup=_lookup,
            approve=lambda *_: True,
        )
