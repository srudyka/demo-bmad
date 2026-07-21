"""DynamoDB notification-ledger adapter with conditional deduplication."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import uuid4

from .storage import attribute, dynamodb_item, plain_item


class DynamoClient(Protocol):
    def get_item(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def put_item(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def update_item(self, **kwargs: Any) -> Mapping[str, Any]: ...


class NotificationLedger:
    def __init__(self, client: DynamoClient, table_name: str) -> None:
        self.client = client
        self.table_name = table_name

    def get(self, deduplication_id: str) -> dict[str, Any] | None:
        result = self.client.get_item(
            TableName=self.table_name,
            Key=dynamodb_item(
                {"pk": f"NOTIFICATION#{deduplication_id}", "sk": "DELIVERY"}
            ),
            ConsistentRead=True,
        )
        item = result.get("Item")
        return plain_item(item) if isinstance(item, Mapping) else None

    def reserve(
        self,
        *,
        alert_id: str,
        deduplication_id: str,
        target_arn: str,
        now: str,
    ) -> bool:
        existing = self.get(deduplication_id)
        if existing is not None and existing.get("status") in {
            "DELIVERED",
            "AMBIGUOUS",
        }:
            return False
        item = {
            "keys": {
                "pk": f"NOTIFICATION#{deduplication_id}",
                "sk": "DELIVERY",
            },
            "record_type": "NOTIFICATION_DELIVERY",
            "alert_id": alert_id,
            "deduplication_id": deduplication_id,
            "target_arn": target_arn,
            "status": "PENDING",
            "attempt_count": int((existing or {}).get("attempt_count", 0)) + 1,
            "first_attempt_at": (existing or {}).get("first_attempt_at", now),
            "last_attempt_at": now,
            "lease_expires_at": (
                datetime.fromisoformat(now.replace("Z", "+00:00"))
                + timedelta(minutes=5)
            )
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "expires_at": int(
                (
                    datetime.fromisoformat(now.replace("Z", "+00:00"))
                    + timedelta(days=14)
                ).timestamp()
            ),
            "lease_token": uuid4().hex,
        }
        if existing is None:
            try:
                self.client.put_item(
                    TableName=self.table_name,
                    Item=dynamodb_item(item),
                    ConditionExpression="attribute_not_exists(pk)",
                )
                return True
            except Exception as error:  # noqa: BLE001 - conditional race is a no-op
                if "ConditionalCheckFailed" not in str(error):
                    raise
                return False
        if (
            existing.get("status") == "PENDING"
            and str(existing.get("lease_expires_at", "")) > now
        ):
            return False
        self.client.update_item(
            TableName=self.table_name,
            Key=dynamodb_item(item["keys"]),
            UpdateExpression="SET #status = :pending, attempt_count = :attempts, last_attempt_at = :last_attempt, lease_expires_at = :lease_expires, lease_token = :lease_token",
            ConditionExpression="(#status = :retryable) AND (attribute_not_exists(lease_expires_at) OR lease_expires_at <= :now)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":pending": {"S": "PENDING"},
                ":retryable": {"S": str(existing.get("status", "PENDING"))},
                ":attempts": attribute(item["attempt_count"]),
                ":last_attempt": {"S": now},
                ":lease_expires": {"S": str(item["lease_expires_at"])},
                ":lease_token": {"S": str(item["lease_token"])},
                ":now": {"S": now},
            },
        )
        return True

    def mark_delivered(
        self,
        deduplication_id: str,
        *,
        now: str,
        response: str,
        lease_token: str | None = None,
    ) -> None:
        condition = "#status = :pending"
        values: dict[str, dict[str, Any]] = {
            ":status": {"S": "DELIVERED"},
            ":pending": {"S": "PENDING"},
            ":delivered": {"S": now},
            ":response": {"S": response[:256]},
        }
        if lease_token:
            condition += " AND lease_token = :lease_token"
            values[":lease_token"] = {"S": lease_token}
        self.client.update_item(
            TableName=self.table_name,
            Key=dynamodb_item(
                {"pk": f"NOTIFICATION#{deduplication_id}", "sk": "DELIVERY"}
            ),
            UpdateExpression="SET #status = :status, delivered_at = :delivered, response_code = :response",
            ConditionExpression=condition,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues=values,
        )

    def mark_ambiguous(
        self,
        deduplication_id: str,
        *,
        now: str,
        response: str,
        lease_token: str | None = None,
    ) -> None:
        condition = "#status = :pending"
        values: dict[str, dict[str, Any]] = {
            ":status": {"S": "AMBIGUOUS"},
            ":pending": {"S": "PENDING"},
            ":at": {"S": now},
            ":response": {"S": response[:256]},
        }
        if lease_token:
            condition += " AND lease_token = :lease_token"
            values[":lease_token"] = {"S": lease_token}
        self.client.update_item(
            TableName=self.table_name,
            Key=dynamodb_item(
                {"pk": f"NOTIFICATION#{deduplication_id}", "sk": "DELIVERY"}
            ),
            UpdateExpression="SET #status = :status, ambiguous_at = :at, response_code = :response",
            ConditionExpression=condition,
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues=values,
        )
