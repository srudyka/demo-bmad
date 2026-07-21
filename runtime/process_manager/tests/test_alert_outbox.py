from __future__ import annotations

from typing import Any

from process_manager.ledger import Ledger, plain_item


class FakeDynamo:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {}

    def transact_write_items(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {}


def occurrence(state: str = "STARTED") -> dict[str, Any]:
    return {
        "keys": {"pk": "JOB#dev/platform/canary", "sk": "OCCURRENCE#" + "a" * 64},
        "record_type": "OCCURRENCE",
        "job_id": "dev/platform/canary",
        "config_version": "b" * 64,
        "schedule_generation": "c" * 64,
        "occurrence_id": "a" * 64,
        "scheduled_time": "2027-01-01T00:00:00.000Z",
        "state": state,
        "evidence_ids": [],
    }


def processed() -> dict[str, Any]:
    return {
        "pk": "EVENT#ecs",
        "sk": "d" * 64,
        "event_digest": "e" * 64,
        "accepted_at": "2027-01-01T00:02:00.000Z",
    }


def test_terminal_reduction_puts_outbox_in_same_transaction() -> None:
    client = FakeDynamo()
    Ledger(client, "ledger").reduce_evidence(
        occurrence(),
        processed(),
        state="FAILED",
        evidence_id="f" * 64,
        changes={"error_code": "ECS_ESSENTIAL_EXIT_NONZERO"},
        failure_plane="TASK",
    )
    items = client.calls[0]["TransactItems"]
    assert len(items) == 3
    outbox_put = items[2]["Put"]
    assert outbox_put["ConditionExpression"] == "attribute_not_exists(pk)"
    assert plain_item(outbox_put["Item"])["record_type"] == "ALERT_OUTBOX"
    assert plain_item(outbox_put["Item"])["occurrence_id"] == "a" * 64


def test_successful_reduction_does_not_put_an_outbox() -> None:
    client = FakeDynamo()
    current = occurrence("STARTED")
    Ledger(client, "ledger").reduce_evidence(
        current,
        processed(),
        state="SUCCEEDED",
        evidence_id="f" * 64,
        changes={"completed_at": "2027-01-01T00:01:00.000Z"},
        failure_plane="COMPLETION",
    )
    assert len(client.calls[0]["TransactItems"]) == 2
