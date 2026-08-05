from __future__ import annotations

from datetime import UTC, datetime

import pytest

from command_handler import (
    CallerContext,
    CommandRejected,
    OccurrenceBinding,
    authorize_operator_request,
    manual_occurrence_id,
)


def _request(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1.0.0",
        "form": "operator_request",
        "request_id": "0190f2c9-6c00-7000-8000-000000000002",
        "job_id": "fake/dev/job",
        "scheduled_time": "2026-07-15T10:00:00.000Z",
        "actor": "operator",
        "approval_reference": "CHANGE-1",
        "reason": "verified transient failure",
        "expected_duplicate_effects": "may repeat one notification",
        "verification_plan": "verify one success marker and zero essential exit",
        "compensation_acknowledged": True,
    }
    value.update(updates)
    return value


def _binding(job: str, time: str) -> OccurrenceBinding:
    return OccurrenceBinding(
        job,
        time,
        "a" * 64,
        "b" * 64,
        "c" * 64,
        True,
        "cell-a",
        "123456789012",
        "us-test-1",
        "d" * 64,
    )


def test_authorization_generates_bound_command_and_audit() -> None:
    result = authorize_operator_request(
        _request(),
        CallerContext("operator", "session-1", "cell-a", "123456789012", "us-test-1"),
        lookup=_binding,
        approve=lambda ref, actor, session, scope: (
            (ref, actor, session) == ("CHANGE-1", "operator", "session-1")
        ),
        now=datetime(2026, 7, 15, 10, 1, tzinfo=UTC),
        command_id_factory=lambda: "0190f2c9-6c00-7000-8000-000000000001",
    )
    assert result.command["original_occurrence_id"] == "a" * 64
    assert result.command["synthetic_occurrence_id"] == manual_occurrence_id(
        "fake/dev/job", "a" * 64, "b" * 64, "0190f2c9-6c00-7000-8000-000000000001"
    )
    assert result.audit["actor"] == "operator"
    assert result.command["schedule_generation"] == "d" * 64
    assert result.command["replay_of_occurrence_id"] == "a" * 64
    assert result.command["expected_duplicate_effects"]
    assert result.command["verification_plan"]


@pytest.mark.parametrize("field", ["command_id", "original_occurrence_id", "evidence"])
def test_caller_cannot_supply_identity_or_evidence(field: str) -> None:
    request = _request(**{field: "caller-owned"})
    with pytest.raises(CommandRejected, match="COMMAND_CALLER_OWNED_ID"):
        authorize_operator_request(
            request,
            CallerContext("operator", "s", "cell", "123456789012", "r"),
            lookup=_binding,
            approve=lambda *_: True,
        )


def test_wrong_actor_and_invalid_approval_fail_closed() -> None:
    with pytest.raises(CommandRejected, match="COMMAND_CALLER_AUTHORITY"):
        authorize_operator_request(
            _request(actor="other"),
            CallerContext("operator", "s", "cell", "123456789012", "r"),
            lookup=_binding,
            approve=lambda *_: True,
        )


def test_rerun_requires_bounded_duplicate_and_verification_plans() -> None:
    caller = CallerContext("operator", "s", "cell-a", "123456789012", "us-test-1")
    with pytest.raises(CommandRejected, match="COMMAND_REQUEST_FIELD"):
        authorize_operator_request(
            _request(expected_duplicate_effects=""),
            caller,
            lookup=_binding,
            approve=lambda *_: True,
        )
    with pytest.raises(CommandRejected, match="COMMAND_REQUEST_FIELD"):
        authorize_operator_request(
            _request(verification_plan="x" * 4097),
            caller,
            lookup=_binding,
            approve=lambda *_: True,
        )
    with pytest.raises(CommandRejected, match="COMMAND_APPROVAL_INVALID"):
        authorize_operator_request(
            _request(),
            CallerContext("operator", "s", "cell", "123456789012", "r"),
            lookup=_binding,
            approve=lambda *_: False,
        )


def test_recovery_request_requires_restore_point_and_objectives() -> None:
    result = authorize_operator_request(
        _request(
            command_type="RECOVER",
            compensation_acknowledged=True,
            restore_point="2026-07-15T09:00:00.000Z",
            expected_rpo_seconds=300,
            expected_rto_seconds=1800,
        ),
        CallerContext("operator", "session-1", "cell-a", "123456789012", "us-test-1"),
        lookup=_binding,
        approve=lambda *_: True,
        now=datetime(2026, 7, 15, 10, 1, tzinfo=UTC),
        command_id_factory=lambda: "0190f2c9-6c00-7000-8000-000000000001",
    )
    assert result.command["command_type"] == "RECOVER"
    assert result.command["restore_point"] == "2026-07-15T09:00:00.000Z"
    with pytest.raises(CommandRejected, match="RECOVERY_REQUEST_FIELDS"):
        authorize_operator_request(
            _request(command_type="RECOVER", compensation_acknowledged=True),
            CallerContext(
                "operator", "session-1", "cell-a", "123456789012", "us-test-1"
            ),
            lookup=_binding,
            approve=lambda *_: True,
        )
