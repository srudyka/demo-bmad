"""AWS Lambda adapter for deterministic expected-occurrence recording."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .contracts import canonical_json_bytes

from .domain import ContractRejection, prepare_expected
from .ledger import Ledger

LOGGER = logging.getLogger(__name__)
TRANSIENT_CODES = (
    "ProvisionedThroughputExceededException",
    "ThrottlingException",
    "InternalServerError",
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"PROCESS_MANAGER_CONFIGURATION_MISSING:{name}")
    return value


def _clients() -> tuple[Any, Any, Any]:
    import boto3  # type: ignore[import-untyped]

    return boto3.client("dynamodb"), boto3.client("cloudwatch"), boto3.client("sqs")


def _body(record: Mapping[str, Any]) -> dict[str, Any]:
    body = record.get("body")
    if not isinstance(body, str):
        raise ContractRejection("MESSAGE_BODY_INVALID")
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise ContractRejection("MESSAGE_JSON_INVALID") from error
    if not isinstance(value, dict):
        raise ContractRejection("MESSAGE_JSON_INVALID")
    if canonical_json_bytes(value).decode("utf-8") != body:
        raise ContractRejection("MESSAGE_NOT_CANONICAL")
    return value


def lambda_handler(
    event: Mapping[str, Any], _context: Any
) -> dict[str, list[dict[str, str]]]:
    records = event.get("Records")
    if not isinstance(records, list):
        raise RuntimeError("PROCESS_MANAGER_EVENT_INVALID")
    dynamodb, metrics, queues = _clients()
    ledger = Ledger(dynamodb, _required("PROCESS_MANAGER_OCCURRENCE_TABLE_NAME"))
    config_table = _required("PROCESS_MANAGER_CONFIG_TABLE_NAME")
    identity = _required("PROCESS_MANAGER_DEPLOYMENT_IDENTITY")
    ingress_arn = _required("PROCESS_MANAGER_INGRESS_QUEUE_ARN")
    quarantine_url = _required("PROCESS_MANAGER_QUARANTINE_QUEUE_URL")
    now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    failures: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        message_id = record.get("messageId")
        try:
            if (
                record.get("eventSource") != "aws:sqs"
                or record.get("eventSourceARN") != ingress_arn
            ):
                raise ContractRejection("UNAUTHORIZED_INGRESS_SOURCE")
            envelope = _body(record)
            key = {
                "pk": f"JOB#{envelope.get('job_id', '')}",
                "sk": f"CONFIG#{envelope.get('config_version', '')}",
            }
            config_result = dynamodb.get_item(
                TableName=config_table,
                Key={"pk": {"S": key["pk"]}, "sk": {"S": key["sk"]}},
                ConsistentRead=True,
            )
            item = (
                config_result.get("Item")
                if isinstance(config_result, Mapping)
                else None
            )
            prepared = prepare_expected(
                envelope,
                item if isinstance(item, Mapping) else None,
                processor_identity=identity,
                now=now,
                expected_owner_generation=int(
                    _required("PROCESS_MANAGER_OWNER_GENERATION")
                ),
            )
            existing = ledger.get(
                {
                    "pk": prepared.processed_event["pk"],
                    "sk": prepared.processed_event["sk"],
                }
            )
            if existing is not None:
                if existing.get("event_digest") == {"S": prepared.envelope_digest}:
                    continue
                raise ContractRejection("PROCESSED_EVENT_CONFLICT")
            existing_occurrence = ledger.get(prepared.occurrence["keys"])
            if existing_occurrence is None:
                ledger.accept(prepared.occurrence, prepared.processed_event)
            else:
                ledger.accept_existing(prepared.occurrence, prepared.processed_event)
            try:
                metrics.put_metric_data(
                    Namespace=_required("PROCESS_MANAGER_METRIC_NAMESPACE"),
                    MetricData=[
                        {
                            "MetricName": "OccurrenceExpectedAccepted",
                            "Unit": "Count",
                            "Value": 1.0,
                            "Dimensions": [
                                {
                                    "Name": "environment",
                                    "Value": _required("PROCESS_MANAGER_ENVIRONMENT"),
                                },
                                {
                                    "Name": "job_id",
                                    "Value": prepared.occurrence["job_id"],
                                },
                                {"Name": "state", "Value": "EXPECTED"},
                            ],
                        }
                    ],
                )
            except Exception:  # noqa: BLE001 - metrics are best effort after commit
                LOGGER.warning("process_manager_metric_publish_failed", exc_info=True)
        except ContractRejection as error:
            try:
                queues.send_message(
                    QueueUrl=quarantine_url,
                    MessageBody=canonical_json_bytes(
                        {
                            "record_type": "PROCESS_MANAGER_REJECTION",
                            "code": error.code,
                            "message_id": message_id or "unknown",
                        }
                    ).decode(),
                )
            except Exception:  # noqa: BLE001 - failed quarantine must retry source
                if isinstance(message_id, str):
                    failures.append({"itemIdentifier": message_id})
            LOGGER.info(
                "process_manager_record code=%s message_id=%s",
                error.code,
                message_id or "",
            )
        except Exception as error:  # noqa: BLE001 - adapter classifies transport failures record-locally
            code = (
                getattr(error, "response", {}).get("Error", {}).get("Code", "")
                if hasattr(error, "response")
                else ""
            )
            if code not in TRANSIENT_CODES:
                LOGGER.exception(
                    "process_manager_record_unexpected message_id=%s", message_id or ""
                )
            if isinstance(message_id, str):
                failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
