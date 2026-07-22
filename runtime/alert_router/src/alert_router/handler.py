"""AWS adapters for Stream-driven and reconciliation-driven alert delivery."""

from __future__ import annotations

import json
import hashlib
import logging
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from .domain import (
    AlertRoutingError,
    build_occurrence_alert,
    notification_identity,
    occurrence_alert_identity,
)
from .ledger import NotificationLedger
from .storage import canonical_json_bytes, dynamodb_item, plain_item

LOGGER = logging.getLogger(__name__)


class Publisher(Protocol):
    def publish(
        self, *, TopicArn: str, Message: str, MessageAttributes: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"ALERT_ROUTER_CONFIGURATION_MISSING:{name}")
    return value


def _clients() -> tuple[Any, Any, Publisher]:
    import boto3  # type: ignore[import-untyped]

    return boto3.client("dynamodb"), boto3.client("cloudwatch"), boto3.client("sns")


def _resolve_recovery_table() -> None:
    parameter = os.environ.get("ALERT_ROUTER_RECOVERY_POINTER_PARAMETER_NAME")
    if not parameter:
        return
    import boto3

    value = json.loads(
        boto3.client("ssm").get_parameter(Name=parameter, WithDecryption=True)[
            "Parameter"
        ]["Value"]
    )
    tables = value.get("tables") if isinstance(value, Mapping) else None
    if (
        not isinstance(tables, list)
        or len(tables) < 5
        or not all(isinstance(item, str) for item in tables)
    ):
        raise RuntimeError("ALERT_ROUTER_RECOVERY_POINTER_INVALID")
    os.environ["ALERT_ROUTER_CONFIG_TABLE_NAME"] = tables[1]
    os.environ["ALERT_ROUTER_OCCURRENCE_TABLE_NAME"] = tables[2]
    os.environ["ALERT_ROUTER_NOTIFICATION_TABLE_NAME"] = tables[4]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _metric(client: Any, name: str, *, value: float = 1.0) -> None:
    namespace = os.environ.get("ALERT_ROUTER_METRIC_NAMESPACE")
    if not namespace:
        return
    try:
        client.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "component", "Value": "alert-router"},
                        {"Name": "cell_id", "Value": _required("ALERT_ROUTER_CELL_ID")},
                        {
                            "Name": "environment",
                            "Value": _required("ALERT_ROUTER_ENVIRONMENT"),
                        },
                    ],
                }
            ],
        )
    except Exception:  # noqa: BLE001 - metrics must not affect delivery
        LOGGER.exception("alert_router_metric_failed metric=%s", name)


_DETERMINISTIC_PUBLISH_ERRORS = {
    "AccessDenied",
    "AuthorizationError",
    "InvalidParameter",
    "InvalidParameterValue",
    "NotFound",
    "ResourceNotFoundException",
}


def _publisher_error_code(error: Exception) -> str:
    response = getattr(error, "response", {})
    if isinstance(response, Mapping):
        details = response.get("Error", {})
        if isinstance(details, Mapping):
            code = details.get("Code")
            if isinstance(code, str):
                return code
    return ""


def _mark_outbox_delivered(dynamodb: Any, outbox: Mapping[str, Any], now: str) -> None:
    occurrence_table = os.environ.get("ALERT_ROUTER_OCCURRENCE_TABLE_NAME")
    if not occurrence_table:
        return
    dynamodb.update_item(
        TableName=occurrence_table,
        Key=dynamodb_item(
            {
                "pk": f"ALERT_OUTBOX#{outbox['occurrence_id']}#{outbox['policy']}",
                "sk": f"ALERT#{outbox['state']}#{outbox['failure_plane']}",
            }
        ),
        UpdateExpression="SET delivery_status = :delivered, alert_sort = :sort",
        ConditionExpression="attribute_exists(pk) AND delivery_status = :pending",
        ExpressionAttributeValues={
            ":delivered": {"S": "DELIVERED"},
            ":pending": {"S": "PENDING"},
            ":sort": {"S": f"DELIVERED#{now}#{outbox['occurrence_id']}"},
        },
    )


def _image(record: Mapping[str, Any]) -> dict[str, Any] | None:
    dynamodb = record.get("dynamodb")
    image = dynamodb.get("NewImage") if isinstance(dynamodb, Mapping) else None
    return plain_item(image) if isinstance(image, Mapping) else None


def _config_snapshot(
    client: Any, table_name: str, outbox: Mapping[str, Any]
) -> dict[str, Any]:
    result = client.get_item(
        TableName=table_name,
        Key={
            "pk": {"S": f"JOB#{outbox['job_id']}"},
            "sk": {"S": f"CONFIG#{outbox['config_version']}"},
        },
        ConsistentRead=True,
    )
    item = result.get("Item") if isinstance(result, Mapping) else None
    if not isinstance(item, Mapping):
        raise AlertRoutingError("CONFIG_NOT_FOUND")
    snapshot = plain_item(item)
    try:
        config = json.loads(str(snapshot["config_json"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise AlertRoutingError("CONFIG_INVALID") from error
    if not isinstance(config, dict):
        raise AlertRoutingError("CONFIG_INVALID")
    if (
        snapshot.get("job_id") != outbox.get("job_id")
        or snapshot.get("config_version") != outbox.get("config_version")
        or snapshot.get("schedule_generation") != outbox.get("schedule_generation")
        or snapshot.get("validation_state") != "VALIDATED"
        or snapshot.get("materialization_state") not in {"PENDING", "MATERIALIZED"}
    ):
        raise AlertRoutingError("CONFIG_NOT_AUTHORITATIVE")
    canonical_config = canonical_json_bytes(config).decode("utf-8")
    if str(snapshot.get("config_json")) != canonical_config:
        raise AlertRoutingError("CONFIG_NOT_CANONICAL")
    if (
        snapshot.get("config_hash")
        != hashlib.sha256(canonical_config.encode("utf-8")).hexdigest()
    ):
        raise AlertRoutingError("CONFIG_HASH_MISMATCH")
    snapshot["config"] = config.get("config", config)
    if not isinstance(snapshot["config"], dict):
        raise AlertRoutingError("CONFIG_INVALID")
    return snapshot


def _authoritative_failure(
    client: Any, table_name: str, outbox: Mapping[str, Any]
) -> bool:
    """Suppress stale obligations when the strongly read occurrence succeeded."""

    result = client.get_item(
        TableName=table_name,
        Key={
            "pk": {"S": f"JOB#{outbox['job_id']}"},
            "sk": {"S": f"OCCURRENCE#{outbox['occurrence_id']}"},
        },
        ConsistentRead=True,
    )
    item = result.get("Item") if isinstance(result, Mapping) else None
    if not isinstance(item, Mapping):
        raise AlertRoutingError("OCCURRENCE_NOT_FOUND")
    occurrence = plain_item(item)
    return occurrence.get("state") in {
        "FAILED",
        "MISSED",
        "OVERDUE",
        "AMBIGUOUS",
    } and occurrence.get("state") == outbox.get("state")


def dispatch_outbox_item(
    outbox: Mapping[str, Any],
    *,
    dynamodb: Any,
    publisher: Publisher,
    config_table: str,
    notification_table: str,
    account_id: str,
    region: str,
    environment: str,
    owner: str,
    runbook_uri: str,
    now: str,
) -> str:
    """Deliver one deterministic obligation, returning its durable outcome."""

    if os.environ.get("ALERT_ROUTER_NOTIFICATIONS_ENABLED", "true").lower() == "false":
        return "DISABLED"

    config = _config_snapshot(dynamodb, config_table, outbox)
    alert = build_occurrence_alert(
        outbox,
        config,
        account_id=account_id,
        region=region,
        environment=environment,
        owner=owner,
        runbook_uri=runbook_uri,
    )
    ledger = NotificationLedger(dynamodb, notification_table)
    if not ledger.reserve(
        alert_id=str(alert["alert_id"]),
        deduplication_id=str(alert["deduplication_id"]),
        target_arn=str(alert["notification_target_arn"]),
        now=now,
    ):
        existing = ledger.get(str(alert["deduplication_id"])) or {}
        if existing.get("status") == "DELIVERED":
            _mark_outbox_delivered(dynamodb, outbox, now)
        return "DEDUPLICATED"
    message = canonical_json_bytes(alert).decode("utf-8")
    claim = ledger.get(str(alert["deduplication_id"])) or {}
    lease_token = claim.get("lease_token")
    if not isinstance(lease_token, str):
        lease_token = None
    try:
        response = publisher.publish(
            TopicArn=str(alert["notification_target_arn"]),
            Message=message,
            MessageAttributes={
                "failure_plane": {
                    "DataType": "String",
                    "StringValue": str(alert["failure_plane"]),
                },
                "state": {"DataType": "String", "StringValue": str(alert["state"])},
            },
        )
    except Exception as error:  # noqa: BLE001 - publication uncertainty is durable
        code = _publisher_error_code(error)
        if code in _DETERMINISTIC_PUBLISH_ERRORS:
            ledger.mark_rejected(
                str(alert["deduplication_id"]),
                now=now,
                response=code,
                lease_token=lease_token,
            )
        else:
            ledger.mark_ambiguous(
                str(alert["deduplication_id"]),
                now=now,
                response=code or type(error).__name__,
                lease_token=lease_token,
            )
        raise
    message_id = str(response.get("MessageId", "PUBLISHED"))
    try:
        ledger.mark_delivered(
            str(alert["deduplication_id"]),
            now=now,
            response=message_id,
            lease_token=lease_token,
        )
    except Exception as error:  # noqa: BLE001 - publication was already accepted
        try:
            ledger.mark_ambiguous(
                str(alert["deduplication_id"]),
                now=now,
                response=f"LEDGER_WRITE_UNCERTAIN:{type(error).__name__}",
                lease_token=lease_token,
            )
        except Exception:  # noqa: BLE001 - retain original failure for retry/DLQ
            LOGGER.exception("alert_router_ledger_ambiguity_record_failed")
        raise
    _mark_outbox_delivered(dynamodb, outbox, now)
    return "DELIVERED"


def dispatch_cell_alarm(
    event: Mapping[str, Any], *, dynamodb: Any, publisher: Publisher
) -> str:
    if os.environ.get("ALERT_ROUTER_NOTIFICATIONS_ENABLED", "true").lower() == "false":
        return "DISABLED"
    alarm_data = event.get("alarmData", event.get("detail", {}))
    if not isinstance(alarm_data, Mapping):
        raise AlertRoutingError("CELL_ALARM_INVALID")
    alarm_name = str(alarm_data.get("alarmName", "CELL_ALARM"))
    raw_state = alarm_data.get("state", {})
    if not isinstance(raw_state, Mapping):
        raise AlertRoutingError("CELL_ALARM_INVALID")
    state = str(raw_state.get("value", "ALARM"))
    if state not in {"ALARM", "OK"}:
        raise AlertRoutingError("CELL_ALARM_STATE_UNSUPPORTED")
    timestamp = str(raw_state.get("timestamp", _now()))
    cell_id = _required("ALERT_ROUTER_CELL_ID")
    window = timestamp[:16]
    occurrence_id = hashlib.sha256(
        f"cell-alarm/v1\n{cell_id}\n{alarm_name}\n{state}\n{window}".encode()
    ).hexdigest()
    alert_state = "FAILED" if state == "ALARM" else "RECOVERED"
    alert_id = occurrence_alert_identity(
        f"cell/{cell_id}", occurrence_id, "FAILED", "CELL", "cell-health-v1"
    )
    target = _required("ALERT_ROUTER_CELL_TARGET_ARN")
    deduplication_id = notification_identity(alert_id, target)
    ledger = NotificationLedger(
        dynamodb, _required("ALERT_ROUTER_NOTIFICATION_TABLE_NAME")
    )
    now = _now()
    if not ledger.reserve(
        alert_id=alert_id,
        deduplication_id=deduplication_id,
        target_arn=target,
        now=now,
    ):
        return "DEDUPLICATED"
    claim = ledger.get(deduplication_id) or {}
    lease_token = claim.get("lease_token")
    if not isinstance(lease_token, str):
        lease_token = None
    message = canonical_json_bytes(
        {
            "schema_version": "1.0.0",
            "alert_id": alert_id,
            "deduplication_id": deduplication_id,
            "job_id": f"cell/{cell_id}",
            "occurrence_id": occurrence_id,
            "state": alert_state,
            "failure_plane": "CELL",
            "account_id": _required("ALERT_ROUTER_ACCOUNT_ID"),
            "region": _required("ALERT_ROUTER_REGION"),
            "environment": _required("ALERT_ROUTER_ENVIRONMENT"),
            "detected_at": timestamp,
            "deployment_identity_id": hashlib.sha256(cell_id.encode()).hexdigest(),
            "owner": _required("ALERT_ROUTER_OWNER"),
            "notification_target_arn": target,
            "runbook_uri": _required("ALERT_ROUTER_RUNBOOK_URI"),
            "operator_safe_reason": "CELL_ALARM_"
            + re.sub(r"[^A-Z0-9]+", "_", alarm_name.upper())[:120],
        }
    ).decode()
    try:
        response = publisher.publish(
            TopicArn=target,
            Message=message,
            MessageAttributes={
                "failure_plane": {"DataType": "String", "StringValue": "CELL"},
                "state": {"DataType": "String", "StringValue": alert_state},
            },
        )
    except Exception as error:  # noqa: BLE001 - publication uncertainty is durable
        ledger.mark_ambiguous(
            deduplication_id,
            now=now,
            response=type(error).__name__,
            lease_token=lease_token,
        )
        raise
    try:
        ledger.mark_delivered(
            deduplication_id,
            now=now,
            response=str(response.get("MessageId", "PUBLISHED")),
            lease_token=lease_token,
        )
    except Exception as error:  # noqa: BLE001 - publication was already accepted
        ledger.mark_ambiguous(
            deduplication_id,
            now=now,
            response=f"LEDGER_WRITE_UNCERTAIN:{type(error).__name__}",
            lease_token=lease_token,
        )
        raise
    return "DELIVERED"


def lambda_handler(
    event: Mapping[str, Any], _context: Any
) -> dict[str, list[dict[str, str]]]:
    if event.get("mode") == "cell_alarm" or event.get("source") == "aws.cloudwatch":
        dynamodb, _metrics, publisher = _clients()
        dispatch_cell_alarm(event, dynamodb=dynamodb, publisher=publisher)
        return {"batchItemFailures": []}
    if event.get("mode") == "reconciliation":
        reconciliation_handler(event, _context)
        return {"batchItemFailures": []}
    _resolve_recovery_table()
    records = event.get("Records")
    if not isinstance(records, list):
        raise RuntimeError("ALERT_ROUTER_EVENT_INVALID")
    dynamodb, metrics, publisher = _clients()
    failures: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        sequence: object = record.get("eventID")
        try:
            dynamodb_record = record.get("dynamodb")
            if not isinstance(dynamodb_record, Mapping):
                raise RuntimeError("ALERT_ROUTER_STREAM_METADATA_INVALID")
            sequence = record.get("eventID") or dynamodb_record.get("SequenceNumber")
            if not isinstance(sequence, str) or not sequence:
                raise RuntimeError("ALERT_ROUTER_STREAM_SEQUENCE_MISSING")
            outbox = _image(record)
            if not outbox or outbox.get("record_type") != "ALERT_OUTBOX":
                continue
            if not _authoritative_failure(
                dynamodb,
                _required("ALERT_ROUTER_OCCURRENCE_TABLE_NAME"),
                outbox,
            ):
                LOGGER.info(
                    "alert_router_stale_obligation_suppressed sequence=%s", sequence
                )
                continue
            result = dispatch_outbox_item(
                outbox,
                dynamodb=dynamodb,
                publisher=publisher,
                config_table=_required("ALERT_ROUTER_CONFIG_TABLE_NAME"),
                notification_table=_required("ALERT_ROUTER_NOTIFICATION_TABLE_NAME"),
                account_id=_required("ALERT_ROUTER_ACCOUNT_ID"),
                region=_required("ALERT_ROUTER_REGION"),
                environment=_required("ALERT_ROUTER_ENVIRONMENT"),
                owner=_required("ALERT_ROUTER_OWNER"),
                runbook_uri=_required("ALERT_ROUTER_RUNBOOK_URI"),
                now=_now(),
            )
            _metric(metrics, f"Notification{result.title()}")
        except AlertRoutingError, RuntimeError:
            _metric(metrics, "RoutingFailure")
            if not isinstance(sequence, str) or not sequence:
                raise
            failures.append({"itemIdentifier": sequence})
            LOGGER.exception(
                "alert_router_record_rejected sequence=%s", sequence or "unknown"
            )
        except Exception:  # noqa: BLE001 - retry transport and target failures
            _metric(metrics, "Retry")
            if not isinstance(sequence, str) or not sequence:
                raise
            failures.append({"itemIdentifier": sequence})
            LOGGER.exception(
                "alert_router_record_retry sequence=%s", sequence or "unknown"
            )
    return {"batchItemFailures": failures}


def reconciliation_handler(event: Mapping[str, Any], _context: Any) -> dict[str, int]:
    """Bounded scan entry point; Stream delivery remains the fast path."""

    dynamodb, metrics, publisher = _clients()
    page_size = int(os.environ.get("ALERT_ROUTER_RECONCILIATION_PAGE_SIZE", "25"))
    scan: Mapping[str, Any] = {}
    pages = 0
    delivered = 0
    start_key: Mapping[str, Any] | None = None
    failures = 0
    while pages < 10:
        query_args: dict[str, Any] = {
            "TableName": _required("ALERT_ROUTER_OCCURRENCE_TABLE_NAME"),
            "IndexName": "alert-outbox",
            "Limit": page_size,
            "KeyConditionExpression": "record_type = :record_type",
            "FilterExpression": "delivery_status <> :delivered",
            "ExpressionAttributeValues": {
                ":record_type": {"S": "ALERT_OUTBOX"},
                ":delivered": {"S": "DELIVERED"},
            },
        }
        if start_key:
            query_args["ExclusiveStartKey"] = start_key
        scan = dynamodb.query(**query_args)
        items = scan.get("Items", []) if isinstance(scan, Mapping) else []
        for item in items if isinstance(items, list) else []:
            outbox = plain_item(item) if isinstance(item, Mapping) else {}
            try:
                if not _authoritative_failure(
                    dynamodb,
                    _required("ALERT_ROUTER_OCCURRENCE_TABLE_NAME"),
                    outbox,
                ):
                    continue
                result = dispatch_outbox_item(
                    outbox,
                    dynamodb=dynamodb,
                    publisher=publisher,
                    config_table=_required("ALERT_ROUTER_CONFIG_TABLE_NAME"),
                    notification_table=_required(
                        "ALERT_ROUTER_NOTIFICATION_TABLE_NAME"
                    ),
                    account_id=_required("ALERT_ROUTER_ACCOUNT_ID"),
                    region=_required("ALERT_ROUTER_REGION"),
                    environment=_required("ALERT_ROUTER_ENVIRONMENT"),
                    owner=_required("ALERT_ROUTER_OWNER"),
                    runbook_uri=_required("ALERT_ROUTER_RUNBOOK_URI"),
                    now=_now(),
                )
                _metric(metrics, f"Reconciliation{result.title()}")
                if result == "DELIVERED":
                    delivered += 1
            except Exception:  # noqa: BLE001 - isolate one bad obligation
                failures += 1
                _metric(metrics, "ReconciliationFailure")
                LOGGER.exception("alert_router_reconciliation_item_failed")
        last_key = scan.get("LastEvaluatedKey") if isinstance(scan, Mapping) else None
        if not isinstance(last_key, Mapping):
            break
        start_key = last_key
        pages += 1
    _metric(metrics, "ReconciliationRun")
    if failures:
        raise RuntimeError(f"ALERT_ROUTER_RECONCILIATION_FAILED:{failures}")
    return {"delivered": delivered}
