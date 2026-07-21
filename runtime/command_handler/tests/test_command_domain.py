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
    }
    value.update(updates)
    return value


def _binding(job: str, time: str) -> OccurrenceBinding:
    return OccurrenceBinding(job, time, "a" * 64, "b" * 64, "c" * 64)


def test_authorization_generates_bound_command_and_audit() -> None:
    result = authorize_operator_request(
        _request(),
        CallerContext("operator", "session-1", "cell-a", "123456789012", "us-test-1"),
        lookup=_binding,
        approve=lambda ref, actor, session: (
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
    with pytest.raises(CommandRejected, match="COMMAND_APPROVAL_INVALID"):
        authorize_operator_request(
            _request(),
            CallerContext("operator", "s", "cell", "123456789012", "r"),
            lookup=_binding,
            approve=lambda *_: False,
        )
