"""AWS adapter for deadline scanning; all state decisions stay in domain.py."""

from __future__ import annotations

import os
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .domain import (
    DeadlineCandidate,
    DeadlineRejection,
    ScannerCheckpoint,
    build_deadline_envelope,
    canonical_json_bytes,
    due_candidates,
)


class DynamoClient(Protocol):
    def query(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def get_item(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def update_item(self, **kwargs: Any) -> Mapping[str, Any]: ...


class QueueClient(Protocol):
    def send_message(self, **kwargs: Any) -> Mapping[str, Any]: ...


class MetricsClient(Protocol):
    def put_metric_data(self, **kwargs: Any) -> Mapping[str, Any]: ...


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"DEADLINE_SCANNER_CONFIGURATION_MISSING:{name}")
    return value


def _resolve_recovery_table() -> None:
    parameter = os.environ.get("DEADLINE_SCANNER_RECOVERY_POINTER_PARAMETER_NAME")
    if not parameter:
        return
    import boto3  # type: ignore[import-untyped]

    value = json.loads(
        boto3.client("ssm").get_parameter(Name=parameter, WithDecryption=True)[
            "Parameter"
        ]["Value"]
    )
    tables = value.get("tables") if isinstance(value, Mapping) else None
    if (
        not isinstance(tables, list)
        or len(tables) < 4
        or not all(isinstance(item, str) for item in tables)
    ):
        raise RuntimeError("DEADLINE_SCANNER_RECOVERY_POINTER_INVALID")
    os.environ["DEADLINE_SCANNER_OCCURRENCE_TABLE_NAME"] = tables[2]
    os.environ["DEADLINE_SCANNER_CHECKPOINT_TABLE_NAME"] = tables[3]


def _plain(item: Mapping[str, Any]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in item.items():
        if isinstance(value, Mapping) and len(value) == 1:
            kind, child = next(iter(value.items()))
            if kind == "S":
                result[key] = child
            elif kind == "N":
                result[key] = int(str(child))
            elif kind == "BOOL":
                result[key] = child
            else:
                result[key] = child
        else:
            result[key] = value
    return result


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def scan_once(
    dynamodb: DynamoClient,
    queues: QueueClient,
    metrics: MetricsClient | None = None,
) -> int:
    """Scan one bounded page and emit before advancing the checkpoint."""

    table = _required("DEADLINE_SCANNER_OCCURRENCE_TABLE_NAME")
    index = _required("DEADLINE_SCANNER_INDEX_NAME")
    queue_url = _required("DEADLINE_SCANNER_SOURCE_QUEUE_URL")
    checkpoint_key = {
        "pk": {"S": _required("DEADLINE_SCANNER_CHECKPOINT_PK")},
        "sk": {"S": "CHECKPOINT#deadline"},
    }
    checkpoint_item = dynamodb.get_item(
        TableName=_required("DEADLINE_SCANNER_CHECKPOINT_TABLE_NAME"),
        Key=checkpoint_key,
        ConsistentRead=True,
    ).get("Item")
    checkpoint = ScannerCheckpoint(
        str(
            _plain(checkpoint_item or {}).get(
                "watermark", ScannerCheckpoint.initial().watermark
            )
        ),
        str(_plain(checkpoint_item or {}).get("position", "")),
    )
    now = _now()
    current = datetime.fromisoformat(now[:-1] + "+00:00")
    lookback = int(os.environ.get("DEADLINE_SCANNER_LOOKBACK_SECONDS", "900"))
    lower = current - timedelta(seconds=lookback)
    bucket = lower.replace(second=0, microsecond=0)
    current_bucket = current.replace(second=0, microsecond=0)
    candidates: list[DeadlineCandidate] = []
    pages = 0
    while bucket <= current_bucket:
        cursor: Mapping[str, Any] | None = None
        while True:
            query_kwargs: dict[str, object] = {
                "TableName": table,
                "IndexName": index,
                "KeyConditionExpression": "deadline_key = :bucket",
                "ExpressionAttributeValues": {
                    ":bucket": {
                        "S": f"DEADLINE#{os.environ.get('DEADLINE_SCANNER_SHARD', '0')}#{bucket.isoformat(timespec='milliseconds').replace('+00:00', 'Z')}"
                    }
                },
                "Limit": int(os.environ.get("DEADLINE_SCANNER_PAGE_SIZE", "25")),
                "ScanIndexForward": True,
            }
            if cursor is not None:
                query_kwargs["ExclusiveStartKey"] = dict(cursor)
            response = dynamodb.query(**query_kwargs)
            pages += 1
            for raw in response.get("Items", []):
                if not isinstance(raw, Mapping):
                    continue
                index_item = _plain(raw)
                keys = {"pk": raw.get("pk"), "sk": raw.get("sk")}
                if not isinstance(keys["pk"], Mapping) or not isinstance(
                    keys["sk"], Mapping
                ):
                    continue
                base = dynamodb.get_item(
                    TableName=table, Key=keys, ConsistentRead=True
                ).get("Item")
                if not isinstance(base, Mapping):
                    continue
                candidate_data = _plain(base)
                if candidate_data.get("record_type") != "OCCURRENCE":
                    continue
                try:
                    candidate = DeadlineCandidate.from_item(candidate_data)
                except DeadlineRejection:
                    continue
                if candidate_data.get("deadline_key") != index_item.get(
                    "deadline_key"
                ) or candidate_data.get("deadline_sort") != index_item.get(
                    "deadline_sort"
                ):
                    continue
                candidates.append(candidate)
            last_key = response.get("LastEvaluatedKey")
            if not isinstance(last_key, Mapping):
                break
            cursor = last_key
            if pages >= int(os.environ.get("DEADLINE_SCANNER_MAX_PAGES", "100")):
                raise RuntimeError("DEADLINE_SCANNER_PAGE_LIMIT")
        bucket += timedelta(minutes=1)
    selected = due_candidates(
        candidates,
        now=now,
        lookback_seconds=int(
            os.environ.get("DEADLINE_SCANNER_LOOKBACK_SECONDS", "900")
        ),
        maximum_lateness_seconds=int(
            os.environ.get("DEADLINE_SCANNER_MAX_LATENESS_SECONDS", "900")
        ),
    )
    for candidate in selected:
        queues.send_message(
            QueueUrl=queue_url,
            MessageBody=canonical_json_bytes(
                build_deadline_envelope(
                    candidate, scanner_watermark=now, emitted_at=now
                )
            ).decode("utf-8"),
        )
    new_checkpoint = checkpoint.advance(now, "")
    dynamodb.update_item(
        TableName=_required("DEADLINE_SCANNER_CHECKPOINT_TABLE_NAME"),
        Key=checkpoint_key,
        UpdateExpression="SET #watermark = :watermark, #position = :position",
        ConditionExpression="attribute_not_exists(#watermark) OR #watermark < :watermark OR (#watermark = :watermark AND #position <= :position)",
        ExpressionAttributeNames={"#watermark": "watermark", "#position": "position"},
        ExpressionAttributeValues={
            ":watermark": {"S": new_checkpoint.watermark},
            ":position": {"S": new_checkpoint.position},
        },
    )
    if metrics is not None:
        try:
            metrics.put_metric_data(
                Namespace=_required("DEADLINE_SCANNER_METRIC_NAMESPACE"),
                MetricData=[
                    {
                        "MetricName": "DeadlineScannerCandidates",
                        "Unit": "Count",
                        "Value": float(len(selected)),
                        "Dimensions": [
                            {
                                "Name": "environment",
                                "Value": os.environ.get(
                                    "DEADLINE_SCANNER_ENVIRONMENT", "unknown"
                                ),
                            },
                            {"Name": "state", "Value": "reconciled"},
                        ],
                    },
                    {
                        "MetricName": "DeadlineScannerWatermarkAge",
                        "Unit": "Seconds",
                        "Value": max(
                            0.0,
                            (
                                current
                                - datetime.fromisoformat(
                                    new_checkpoint.watermark[:-1] + "+00:00"
                                )
                            ).total_seconds(),
                        ),
                        "Dimensions": [
                            {
                                "Name": "environment",
                                "Value": os.environ.get(
                                    "DEADLINE_SCANNER_ENVIRONMENT", "unknown"
                                ),
                            },
                            {"Name": "state", "Value": "reconciled"},
                        ],
                    },
                ],
            )
        except Exception:  # noqa: BLE001 - metrics are best effort after evidence emission
            pass
    return len(selected)


def lambda_handler(_event: Mapping[str, object], _context: object) -> dict[str, int]:
    _resolve_recovery_table()
    import boto3

    count = scan_once(
        boto3.client("dynamodb"), boto3.client("sqs"), boto3.client("cloudwatch")
    )
    return {"emitted": count}
