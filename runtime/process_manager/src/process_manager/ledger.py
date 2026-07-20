"""Narrow DynamoDB adapter for the Process Manager ledger."""

from __future__ import annotations

from typing import Any, Mapping, Protocol


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
            ]
        )

    def mark_ambiguous(self, attempt: Mapping[str, Any], code: str) -> None:
        keys = attempt.get("keys")
        if not isinstance(keys, Mapping):
            raise ValueError("ATTEMPT_KEYS_INVALID")
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
        }
        if set(changes) - allowed:
            raise ValueError("CORRELATION_CHANGE_INVALID")
        names = {"#state": "state"}
        values: dict[str, dict[str, Any]] = {
            ":state": {"S": state},
            ":evidence": {"L": [{"S": evidence_id}]},
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
                        "UpdateExpression": "SET " + ", ".join(sets),
                        "ConditionExpression": "job_id = :job_id AND occurrence_id = :occurrence_id AND config_version = :config_version AND schedule_generation = :generation",
                        "ExpressionAttributeNames": names,
                        "ExpressionAttributeValues": values,
                    }
                },
            ]
        )
