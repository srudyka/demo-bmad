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
        return {"L": [{"S": str(item)} for item in value]}
    return {"S": str(value)}


def dynamodb_item(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    item = {key: _attribute(value) for key, value in record.items() if key != "keys"}
    keys = record.get("keys")
    if isinstance(keys, Mapping):
        item["pk"] = _attribute(keys["pk"])
        item["sk"] = _attribute(keys["sk"])
    return item


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
