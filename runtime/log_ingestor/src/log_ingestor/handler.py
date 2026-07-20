"""AWS adapter for authenticated CloudWatch completion evidence."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from .canonical import canonical_json_bytes

from .ingestor import CompletionBinding, LogIngestionError, build_completion_envelopes, decode_subscription_record


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"LOG_INGESTOR_CONFIGURATION_MISSING:{name}")
    return value


def _plain(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, Mapping) and len(item) == 1:
            kind, child = next(iter(item.items()))
            if kind == "S":
                result[key] = child
            elif kind == "N":
                result[key] = int(str(child))
            else:
                result[key] = child
        else:
            result[key] = item
    return result


def lambda_handler(event: Mapping[str, object], _context: object) -> dict[str, list[dict[str, str]]]:
    """Consume subscription envelopes and publish only canonical completions."""

    records = event.get("Records")
    if records is None and "awslogs" in event:
        records = [{"messageId": "direct-cloudwatch-subscription", "body": json.dumps(event)}]
    if not isinstance(records, list):
        raise RuntimeError("LOG_INGESTOR_EVENT_INVALID")
    import boto3  # type: ignore[import-untyped]

    ddb = boto3.client("dynamodb")
    sqs = boto3.client("sqs")
    table = _required("LOG_INGESTOR_OCCURRENCE_TABLE_NAME")
    queue_url = _required("LOG_INGESTOR_PROCESS_MANAGER_QUEUE_URL")
    quarantine_url = _required("LOG_INGESTOR_QUARANTINE_QUEUE_URL")
    failures: list[dict[str, str]] = []

    def quarantine(message_id: str, code: str) -> bool:
        try:
            sqs.send_message(
                QueueUrl=quarantine_url,
                MessageBody=canonical_json_bytes(
                    {"record_type": "LOG_INGESTOR_REJECTION", "code": code, "message_id": message_id}
                ).decode("utf-8"),
            )
            return True
        except Exception:  # noqa: BLE001 - quarantine transport is retriable
            return False

    for record in records:
        if not isinstance(record, Mapping):
            continue
        message_id = str(record.get("messageId", ""))
        try:
            body = record.get("body")
            if not isinstance(body, str):
                raise LogIngestionError("LOG_SOURCE_BODY_INVALID")
            batch = decode_subscription_record(json.loads(body))

            def lookup(group: str, stream: str, task: str) -> CompletionBinding | None:
                response = ddb.query(
                    TableName=table,
                    IndexName="task-arn",
                    KeyConditionExpression="task_arn = :task",
                    ExpressionAttributeValues={":task": {"S": task}},
                    Limit=10,
                )
                items = response.get("Items", [])
                if not isinstance(items, list):
                    return None
                candidates: list[dict[str, Any]] = []
                for candidate in items:
                    if not isinstance(candidate, Mapping):
                        continue
                    pk = candidate.get("pk")
                    sk = candidate.get("sk")
                    if not isinstance(pk, Mapping) or not isinstance(sk, Mapping):
                        continue
                    base = ddb.get_item(
                        TableName=table,
                        Key={"pk": pk, "sk": sk},
                        ConsistentRead=True,
                    ).get("Item")
                    if isinstance(base, Mapping):
                        decoded = _plain(base)
                        if decoded.get("record_type") == "OCCURRENCE":
                            candidates.append(decoded)
                if len(candidates) != 1:
                    return None
                item = candidates[0]
                expected_group = "/platform/jobs/" + str(item.get("job_id", "")).replace("/", "-")
                if group != expected_group or not stream:
                    return None
                return CompletionBinding(
                    job_id=str(item["job_id"]),
                    config_version=str(item["config_version"]),
                    schedule_generation=str(item["schedule_generation"]),
                    occurrence_id=str(item["occurrence_id"]),
                    scheduled_time=str(item["scheduled_time"]),
                    task_arn=task,
                    attempt_no=int(item.get("attempt_no", 0)),
                    log_group=group,
                    log_stream=stream,
                )

            envelopes = build_completion_envelopes(batch, task_lookup=lookup)
        except LogIngestionError as error:
            if error.code == "COMPLETION_TASK_MAPPING_PENDING":
                failures.append({"itemIdentifier": message_id})
                continue
            if not quarantine(message_id, error.code):
                failures.append({"itemIdentifier": message_id})
            continue
        except (ValueError, TypeError):
            if not quarantine(message_id, "LOG_INGESTOR_INPUT_INVALID"):
                failures.append({"itemIdentifier": message_id})
            continue
        except Exception:  # noqa: BLE001 - transport failures retry the record
            failures.append({"itemIdentifier": message_id})
            continue
        try:
            for envelope in envelopes:
                sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=canonical_json_bytes(envelope).decode("utf-8"),
                )
        except Exception:  # noqa: BLE001 - output delivery is retriable
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
