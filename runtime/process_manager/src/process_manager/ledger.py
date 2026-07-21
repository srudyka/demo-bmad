"""Narrow DynamoDB adapter for the Process Manager ledger."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Protocol


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def occurrence_alert_identity(
    job_id: str,
    occurrence_id: str,
    state: str,
    failure_plane: str,
    policy: str = "occurrence-v1",
) -> str:
    if (
        not job_id
        or not _SHA256.fullmatch(occurrence_id)
        or state
        not in {
            "FAILED",
            "MISSED",
            "OVERDUE",
            "AMBIGUOUS",
        }
    ):
        raise ValueError("ALERT_IDENTITY_INVALID")
    return hashlib.sha256(
        (
            "alert/v1\n"
            + "\n".join((job_id, occurrence_id, state, failure_plane, policy))
        ).encode()
    ).hexdigest()


class DynamoClient(Protocol):
    def get_item(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def transact_write_items(self, **kwargs: Any) -> Mapping[str, Any]: ...


def _attribute(value: Any) -> dict[str, Any]:
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, int):
        return {"N": str(value)}
    if isinstance(value, list):
        return {"L": [_attribute(item) for item in value]}
    if isinstance(value, Mapping):
        return {"M": {str(key): _attribute(child) for key, child in value.items()}}
    return {"S": str(value)}


def dynamodb_item(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    item = {key: _attribute(value) for key, value in record.items() if key != "keys"}
    keys = record.get("keys")
    if isinstance(keys, Mapping):
        item["pk"] = _attribute(keys["pk"])
        item["sk"] = _attribute(keys["sk"])
    return item


def plain_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Decode the AttributeValue subset returned by the ledger."""

    result: dict[str, Any] = {}
    for key, value in item.items():
        if not isinstance(value, Mapping) or len(value) != 1:
            result[key] = value
            continue
        kind, child = next(iter(value.items()))
        if kind == "S":
            result[key] = child
        elif kind == "N":
            result[key] = int(child) if str(child).isdigit() else float(child)
        elif kind == "BOOL":
            result[key] = child
        elif kind == "NULL":
            result[key] = None
        elif kind == "L" and isinstance(child, list):
            result[key] = [plain_item({"value": item})["value"] for item in child]
        elif kind == "M" and isinstance(child, Mapping):
            result[key] = plain_item(child)
        else:
            result[key] = child
    return result


class Ledger:
    def __init__(self, client: DynamoClient, table_name: str) -> None:
        self.client = client
        self.table_name = table_name

    def get(self, key: Mapping[str, str]) -> dict[str, Any] | None:
        result = self.client.get_item(
            TableName=self.table_name,
            Key=dynamodb_item(key),
            ConsistentRead=True,
        )
        item = result.get("Item")
        return item if isinstance(item, dict) else None

    def accept(
        self, occurrence: Mapping[str, Any], processed: Mapping[str, Any]
    ) -> None:
        occurrence_item = dict(occurrence)
        occurrence_item["last_reduced_at"] = processed["accepted_at"]
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(processed),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(occurrence_item),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
            ]
        )

    def accept_existing(
        self, occurrence: Mapping[str, Any], processed: Mapping[str, Any]
    ) -> None:
        keys = occurrence["keys"]
        if not isinstance(keys, Mapping):
            raise ValueError("OCCURRENCE_KEYS_INVALID")
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(processed),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(keys),
                        "UpdateExpression": "SET evidence_ids = list_append(if_not_exists(evidence_ids, :empty), :evidence), last_reduced_at = :reduced_at",
                        "ConditionExpression": "job_id = :job_id AND occurrence_id = :occurrence_id AND config_version = :config_version AND schedule_generation = :generation",
                        "ExpressionAttributeValues": {
                            ":empty": {"L": []},
                            ":evidence": {
                                "L": [
                                    {"S": value} for value in occurrence["evidence_ids"]
                                ]
                            },
                            ":job_id": {"S": occurrence["job_id"]},
                            ":occurrence_id": {"S": occurrence["occurrence_id"]},
                            ":config_version": {"S": occurrence["config_version"]},
                            ":generation": {"S": occurrence["schedule_generation"]},
                            ":reduced_at": {"S": processed["accepted_at"]},
                        },
                    }
                },
            ]
        )

    def reserve_attempt(
        self,
        occurrence: Mapping[str, str],
        attempt: Mapping[str, Any],
        processed: Mapping[str, Any],
    ) -> None:
        """Atomically consume launch evidence and reserve attempt zero."""

        occurrence_keys = occurrence.get("keys")
        attempt_keys = attempt.get("keys")
        if not isinstance(occurrence_keys, Mapping) or not isinstance(
            attempt_keys, Mapping
        ):
            raise ValueError("LEDGER_KEYS_INVALID")
        self.client.transact_write_items(
            TransactItems=[
                {
                    "ConditionCheck": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(occurrence_keys),
                        "ConditionExpression": "#state = :expected AND job_id = :job_id AND occurrence_id = :occurrence_id AND config_version = :config_version AND schedule_generation = :generation",
                        "ExpressionAttributeNames": {"#state": "state"},
                        "ExpressionAttributeValues": {
                            ":expected": {"S": "EXPECTED"},
                            ":job_id": {"S": str(attempt["job_id"])},
                            ":occurrence_id": {"S": str(attempt["occurrence_id"])},
                            ":config_version": {"S": str(attempt["config_version"])},
                            ":generation": {"S": str(attempt["schedule_generation"])},
                        },
                    }
                },
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(processed),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(attempt),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
            ]
        )

    def map_task(self, attempt: Mapping[str, Any], task_arn: str) -> None:
        keys = attempt.get("keys")
        if not isinstance(keys, Mapping):
            raise ValueError("ATTEMPT_KEYS_INVALID")
        occurrence_key = {
            "pk": f"JOB#{attempt['job_id']}",
            "sk": f"OCCURRENCE#{attempt['occurrence_id']}",
        }
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(keys),
                        "UpdateExpression": "SET task_arn = :task, launch_state = :state",
                        "ConditionExpression": "launch_state = :pending AND attribute_not_exists(task_arn)",
                        "ExpressionAttributeValues": {
                            ":task": {"S": task_arn},
                            ":state": {"S": "STARTED"},
                            ":pending": {"S": "PENDING"},
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(occurrence_key),
                        "UpdateExpression": "SET #state = :state, task_arn = :task",
                        "ConditionExpression": "#state = :expected",
                        "ExpressionAttributeNames": {"#state": "state"},
                        "ExpressionAttributeValues": {
                            ":state": {"S": "STARTED"},
                            ":task": {"S": task_arn},
                            ":expected": {"S": "EXPECTED"},
                        },
                    }
                },
            ]
        )

    def finish_failed(self, attempt: Mapping[str, Any], code: str) -> None:
        keys = attempt.get("keys")
        if not isinstance(keys, Mapping):
            raise ValueError("ATTEMPT_KEYS_INVALID")
        alert = occurrence_alert_outbox(
            {
                "job_id": attempt["job_id"],
                "occurrence_id": attempt["occurrence_id"],
                "config_version": attempt["config_version"],
                "schedule_generation": attempt["schedule_generation"],
            },
            state="FAILED",
            failure_plane="LAUNCH",
            policy="occurrence-v1",
            detected_at=str(
                attempt.get("first_requested_at", "1970-01-01T00:00:00.000Z")
            ),
            reason=code,
        )
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(keys),
                        "UpdateExpression": "SET launch_state = :state, failure_code = :code",
                        "ConditionExpression": "launch_state = :pending",
                        "ExpressionAttributeValues": {
                            ":state": {"S": "FAILED"},
                            ":code": {"S": code[:64]},
                            ":pending": {"S": "PENDING"},
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(
                            {
                                "pk": f"JOB#{attempt['job_id']}",
                                "sk": f"OCCURRENCE#{attempt['occurrence_id']}",
                            }
                        ),
                        "UpdateExpression": "SET #state = :state",
                        "ConditionExpression": "#state = :expected",
                        "ExpressionAttributeNames": {"#state": "state"},
                        "ExpressionAttributeValues": {
                            ":state": {"S": "FAILED"},
                            ":expected": {"S": "EXPECTED"},
                        },
                    }
                },
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(alert),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
            ]
        )

    def mark_ambiguous(self, attempt: Mapping[str, Any], code: str) -> None:
        keys = attempt.get("keys")
        if not isinstance(keys, Mapping):
            raise ValueError("ATTEMPT_KEYS_INVALID")
        alert = occurrence_alert_outbox(
            {
                "job_id": attempt["job_id"],
                "occurrence_id": attempt["occurrence_id"],
                "config_version": attempt["config_version"],
                "schedule_generation": attempt["schedule_generation"],
            },
            state="AMBIGUOUS",
            failure_plane="LAUNCH",
            policy="occurrence-v1",
            detected_at=str(
                attempt.get("first_requested_at", "1970-01-01T00:00:00.000Z")
            ),
            reason=code,
        )
        self.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(keys),
                        "UpdateExpression": "SET launch_state = :state, failure_code = :code",
                        "ConditionExpression": "launch_state = :pending",
                        "ExpressionAttributeValues": {
                            ":state": {"S": "AMBIGUOUS"},
                            ":code": {"S": code[:64]},
                            ":pending": {"S": "PENDING"},
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": self.table_name,
                        "Key": dynamodb_item(
                            {
                                "pk": f"JOB#{attempt['job_id']}",
                                "sk": f"OCCURRENCE#{attempt['occurrence_id']}",
                            }
                        ),
                        "UpdateExpression": "SET #state = :state",
                        "ConditionExpression": "#state = :expected",
                        "ExpressionAttributeNames": {"#state": "state"},
                        "ExpressionAttributeValues": {
                            ":state": {"S": "AMBIGUOUS"},
                            ":expected": {"S": "EXPECTED"},
                        },
                    }
                },
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(alert),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
            ]
        )

    def reduce_evidence(
        self,
        occurrence: Mapping[str, Any],
        processed: Mapping[str, Any],
        *,
        state: str,
        evidence_id: str,
        changes: Mapping[str, Any] | None = None,
        failure_plane: str | None = None,
        alert_policy: str = "occurrence-v1",
    ) -> None:
        """Atomically retain one canonical evidence fact and reduce the occurrence."""

        keys = occurrence.get("keys")
        if not isinstance(keys, Mapping):
            raise ValueError("OCCURRENCE_KEYS_INVALID")
        changes = changes or {}
        allowed = {
            "started_at",
            "completed_at",
            "exit_code",
            "error_code",
            "operator_safe_error_reason",
            "task_arn",
            "completion_status",
            "completion_exit_code",
            "completion_completed_at",
            "deadline_at",
            "deadline_kind",
        }
        if set(changes) - allowed:
            raise ValueError("CORRELATION_CHANGE_INVALID")
        names = {"#state": "state"}
        values: dict[str, dict[str, Any]] = {
            ":state": {"S": state},
            ":evidence": {"L": [{"S": evidence_id}]},
            ":evidence_id": {"S": evidence_id},
            ":max_evidence": {"N": "64"},
            ":current_state": {"S": str(occurrence.get("state", "EXPECTED"))},
            ":job_id": {"S": str(occurrence["job_id"])},
            ":occurrence_id": {"S": str(occurrence["occurrence_id"])},
            ":config_version": {"S": str(occurrence["config_version"])},
            ":generation": {"S": str(occurrence["schedule_generation"])},
        }
        sets = [
            "#state = :state",
            "evidence_ids = list_append(if_not_exists(evidence_ids, :empty), :evidence)",
        ]
        values[":empty"] = {"L": []}
        for index, (name, value) in enumerate(changes.items()):
            placeholder = f":change{index}"
            sets.append(f"{name} = {placeholder}")
            values[placeholder] = _attribute(value)
        was_terminal = str(occurrence.get("state", "EXPECTED")) in {
            "SUCCEEDED",
            "FAILED",
            "MISSED",
            "OVERDUE",
            "AMBIGUOUS",
        }
        alert_item: dict[str, Any] | None = None
        if (
            not was_terminal
            and state in {"FAILED", "MISSED", "OVERDUE", "AMBIGUOUS"}
            and failure_plane is not None
        ):
            alert_item = occurrence_alert_outbox(
                occurrence,
                state=state,
                failure_plane=failure_plane,
                policy=alert_policy,
                detected_at=str(processed["accepted_at"]),
                reason=str(
                    changes.get("operator_safe_error_reason")
                    or changes.get("error_code")
                    or state
                ),
            )
        transactions: list[dict[str, Any]] = [
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": dynamodb_item(processed),
                    "ConditionExpression": "attribute_not_exists(pk)",
                }
            },
            {
                "Update": {
                    "TableName": self.table_name,
                    "Key": dynamodb_item(keys),
                    "UpdateExpression": "SET " + ", ".join(sets),
                    "ConditionExpression": "job_id = :job_id AND occurrence_id = :occurrence_id AND config_version = :config_version AND schedule_generation = :generation AND #state = :current_state AND (attribute_not_exists(evidence_ids) OR (size(evidence_ids) < :max_evidence AND NOT contains(evidence_ids, :evidence_id)))",
                    "ExpressionAttributeNames": names,
                    "ExpressionAttributeValues": values,
                }
            },
        ]
        if alert_item is not None:
            transactions.append(
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": dynamodb_item(alert_item),
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                }
            )
        self.client.transact_write_items(TransactItems=transactions)


def occurrence_alert_outbox(
    occurrence: Mapping[str, Any],
    *,
    state: str,
    failure_plane: str,
    policy: str,
    detected_at: str,
    reason: str,
) -> dict[str, Any]:
    """Build the durable alert obligation written beside terminal state."""

    occurrence_id = str(occurrence["occurrence_id"])
    job_id = str(occurrence["job_id"])
    alert_id = occurrence_alert_identity(
        job_id, occurrence_id, state, failure_plane, policy
    )
    return {
        "keys": {
            "pk": f"ALERT_OUTBOX#{occurrence_id}#{policy}",
            "sk": f"ALERT#{state}#{failure_plane}",
        },
        "record_type": "ALERT_OUTBOX",
        "alert_id": alert_id,
        "deduplication_id": alert_id,
        "job_id": job_id,
        "occurrence_id": occurrence_id,
        "config_version": str(occurrence["config_version"]),
        "schedule_generation": str(occurrence["schedule_generation"]),
        "state": state,
        "failure_plane": failure_plane,
        "policy": policy,
        "detected_at": detected_at,
        "operator_safe_reason": reason[:2048],
        "delivery_status": "PENDING",
        "alert_sort": f"PENDING#{detected_at}#{occurrence_id}",
    }
