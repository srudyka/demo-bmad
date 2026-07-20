from __future__ import annotations

from typing import Any

from process_manager.ledger import Ledger


class FakeDynamo:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {}

    def transact_write_items(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {}


def records() -> tuple[dict[str, Any], dict[str, Any]]:
    occurrence = {
        "keys": {"pk": "JOB#dev/demo/job", "sk": "OCCURRENCE#" + "a" * 64},
        "record_type": "OCCURRENCE",
        "job_id": "dev/demo/job",
        "config_version": "b" * 64,
        "schedule_generation": "c" * 64,
        "occurrence_id": "a" * 64,
        "evidence_ids": ["d" * 64],
    }
    processed = {
        "pk": "EVENT#occurrence-materializer",
        "sk": "event-1",
        "event_digest": "e" * 64,
        "accepted_at": "2027-01-01T00:00:00.000Z",
    }
    return occurrence, processed


def test_first_accept_is_one_conditional_transaction() -> None:
    client = FakeDynamo()
    occurrence, processed = records()
    Ledger(client, "ledger").accept(occurrence, processed)
    assert len(client.calls) == 1
    assert len(client.calls[0]["TransactItems"]) == 2
    assert (
        client.calls[0]["TransactItems"][0]["Put"]["ConditionExpression"]
        == "attribute_not_exists(pk)"
    )


def test_existing_accept_uses_conditional_update() -> None:
    client = FakeDynamo()
    occurrence, processed = records()
    Ledger(client, "ledger").accept_existing(occurrence, processed)
    update = client.calls[0]["TransactItems"][1]["Update"]
    assert "last_reduced_at" in update["UpdateExpression"]
    assert "occurrence_id = :occurrence_id" in update["ConditionExpression"]


def test_attempt_reservation_is_one_conditional_transaction() -> None:
    client = FakeDynamo()
    occurrence, processed = records()
    attempt = {
        "keys": {"pk": occurrence["keys"]["pk"], "sk": "ATTEMPT#" + "a" * 64 + "#0"},
        "record_type": "TASK_ATTEMPT",
        "job_id": occurrence["job_id"],
        "occurrence_id": occurrence["occurrence_id"],
        "config_version": occurrence["config_version"],
        "schedule_generation": occurrence["schedule_generation"],
        "client_token": "f" * 64,
        "launch_state": "PENDING",
    }
    Ledger(client, "ledger").reserve_attempt(occurrence, attempt, processed)
    assert len(client.calls) == 1
    assert len(client.calls[0]["TransactItems"]) == 3
    assert (
        client.calls[0]["TransactItems"][2]["Put"]["ConditionExpression"]
        == "attribute_not_exists(pk)"
    )
