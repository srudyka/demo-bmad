"""AWS Lambda adapter for deterministic expected-occurrence recording."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .contracts import canonical_json_bytes

from .domain import (
    ContractRejection,
    PreparedAcceptance,
    PreparedCorrelation,
    PreparedDeadline,
    PreparedLaunch,
    prepare_correlation,
    prepare_deadline,
    prepare_expected,
    prepare_launch,
)
from .launch import LaunchUncertain, reconcile_task, run_task
from .ledger import Ledger, plain_item

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


def _launch_clients(role_arn: str) -> tuple[Any, Any]:
    import boto3

    sts = boto3.client("sts")
    credentials = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="process-manager-canary-launch",
    )["Credentials"]
    session_kwargs = {
        "aws_" + "access_key_id": credentials["AccessKeyId"],
        "aws_" + "secret_access_key": credentials["SecretAccessKey"],
        "aws_" + "session_token": credentials["SessionToken"],
    }
    ecs = boto3.client("ecs", **session_kwargs)
    return sts, ecs


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
            prepared: PreparedAcceptance | None = (
                prepare_expected(
                    envelope,
                    item if isinstance(item, Mapping) else None,
                    processor_identity=identity,
                    now=now,
                    expected_owner_generation=int(
                        _required("PROCESS_MANAGER_OWNER_GENERATION")
                    ),
                )
                if envelope.get("event_type") == "occurrence.expected.v1"
                else None
            )
            launch_prepared: PreparedLaunch | None = (
                prepare_launch(
                    envelope,
                    item if isinstance(item, Mapping) else None,
                    processor_identity=identity,
                    now=now,
                    expected_owner_generation=int(
                        _required("PROCESS_MANAGER_OWNER_GENERATION")
                    ),
                    expected_launch_role_arn=_required(
                        "PROCESS_MANAGER_CANARY_LAUNCH_ROLE_ARN"
                    ),
                )
                if envelope.get("event_type") == "occurrence.launch.v1"
                else None
            )
            correlation_prepared: PreparedCorrelation | None = (
                prepare_correlation(
                    envelope,
                    item if isinstance(item, Mapping) else None,
                    processor_identity=identity,
                    expected_owner_generation=int(
                        _required("PROCESS_MANAGER_OWNER_GENERATION")
                    ),
                )
                if envelope.get("event_type")
                in {"task.state.v1", "completion.observed.v1"}
                else None
            )
            deadline_prepared: PreparedDeadline | None = (
                prepare_deadline(
                    envelope,
                    processor_identity=identity,
                    now=now,
                )
                if envelope.get("event_type") == "occurrence.deadline-reached.v1"
                else None
            )
            if (
                prepared is None
                and launch_prepared is None
                and correlation_prepared is None
                and deadline_prepared is None
            ):
                raise ContractRejection("UNAUTHORIZED_PRODUCER")
            if launch_prepared is not None:
                _process_launch(
                    envelope,
                    launch_prepared,
                    ledger,
                    metrics,
                    identity,
                    now,
                )
                continue
            if correlation_prepared is not None:
                _process_correlation(envelope, correlation_prepared, ledger, now)
                continue
            if deadline_prepared is not None:
                _process_deadline(envelope, deadline_prepared, ledger, now)
                continue
            assert prepared is not None
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


def _process_correlation(
    envelope: Mapping[str, Any],
    prepared: PreparedCorrelation,
    ledger: Ledger,
    now: str,
) -> None:
    """Reduce one authenticated task-state or completion fact."""

    occurrence_key = {
        "pk": f"JOB#{envelope['job_id']}",
        "sk": f"OCCURRENCE#{envelope['occurrence_id']}",
    }
    occurrence_item = ledger.get(occurrence_key)
    if occurrence_item is None:
        raise RuntimeError("CORRELATION_OCCURRENCE_PENDING")
    occurrence = plain_item(occurrence_item)
    processed_key = {
        "pk": f"EVENT#{envelope['producer_id']}",
        "sk": envelope["producer_event_id"],
    }
    existing = ledger.get(processed_key)
    if existing is not None:
        if existing.get("event_digest") == {"S": prepared.envelope_digest}:
            return
        raise ContractRejection("PROCESSED_EVENT_CONFLICT")
    payload = prepared.payload
    state = str(occurrence.get("state", "EXPECTED"))
    terminal_state = state in {"SUCCEEDED", "FAILED", "MISSED", "OVERDUE", "AMBIGUOUS"}
    changes: dict[str, Any] = {}
    if envelope["event_type"] == "task.state.v1":
        task_arn = payload.get("task_arn")
        if task_arn != occurrence.get("task_arn") and occurrence.get("task_arn"):
            state = "AMBIGUOUS"
        changes["task_arn"] = task_arn
        if payload.get("last_status") == "RUNNING":
            state = (
                "STARTED"
                if state not in {"SUCCEEDED", "FAILED", "AMBIGUOUS"}
                else state
            )
            changes["started_at"] = payload["event_time"]
        elif payload.get("last_status") == "STOPPED":
            containers = payload.get("containers", [])
            essential = [
                item
                for item in containers
                if isinstance(item, Mapping) and item.get("essential")
            ]
            nonzero = [
                item
                for item in essential
                if item.get("exit_code") is not None and item.get("exit_code") != 0
            ]
            if nonzero and not terminal_state:
                state = "FAILED" if state != "AMBIGUOUS" else state
                changes["error_code"] = "ECS_ESSENTIAL_EXIT_NONZERO"
                changes["exit_code"] = nonzero[0].get("exit_code")
            elif state == "EXPECTED" and not terminal_state:
                state = "FAILED"
                changes["error_code"] = "ECS_STOPPED_BEFORE_RUNNING"
            elif state not in {"SUCCEEDED", "FAILED", "AMBIGUOUS", "MISSED", "OVERDUE"}:
                state = "STARTED"
            if state == "STARTED":
                zero_exit = [item for item in essential if item.get("exit_code") == 0]
                if zero_exit:
                    changes["exit_code"] = 0
            if (
                state == "STARTED"
                and occurrence.get("started_at")
                and occurrence.get("completion_status") == "SUCCESS"
                and occurrence.get("completion_exit_code") == 0
                and (occurrence.get("exit_code") == 0 or changes.get("exit_code") == 0)
            ):
                state = "SUCCEEDED"
                changes["completed_at"] = occurrence.get("completion_completed_at")
    else:
        completion = payload.get("completion")
        if not isinstance(completion, Mapping):
            raise ContractRejection("COMPLETION_PAYLOAD_INVALID")
        task_arn = completion.get("asserted_task_arn")
        if occurrence.get("task_arn") and task_arn != occurrence.get("task_arn"):
            state = "AMBIGUOUS"
        marker_status = completion.get("marker_status")
        exit_code = completion.get("exit_code_assertion")
        changes.update(
            {
                "task_arn": task_arn,
                "completion_status": marker_status,
                "completion_exit_code": exit_code,
                "completion_completed_at": completion.get("completed_at"),
            }
        )
        if marker_status == "FAILURE" and not terminal_state:
            state = "FAILED" if state != "AMBIGUOUS" else state
            changes["error_code"] = completion.get("error_code") or "COMPLETION_FAILURE"
            changes["completed_at"] = completion.get("completed_at")
        elif (
            marker_status == "SUCCESS"
            and exit_code == 0
            and occurrence.get("exit_code") == 0
            and occurrence.get("started_at")
            and state not in {"FAILED", "AMBIGUOUS", "MISSED", "OVERDUE"}
        ):
            state = "SUCCEEDED"
            changes["completed_at"] = completion.get("completed_at")
        elif state not in {"SUCCEEDED", "FAILED", "AMBIGUOUS", "MISSED", "OVERDUE"}:
            state = state if state == "STARTED" else "EXPECTED"
    evidence_id = prepared.envelope_digest
    ledger.reduce_evidence(
        occurrence,
        prepared.processed_event,
        state=state,
        evidence_id=evidence_id,
        changes=changes,
    )


def _process_deadline(
    envelope: Mapping[str, Any],
    prepared: PreparedDeadline,
    ledger: Ledger,
    _now: str,
) -> None:
    occurrence_key = {
        "pk": f"JOB#{envelope['job_id']}",
        "sk": f"OCCURRENCE#{envelope['occurrence_id']}",
    }
    raw = ledger.get(occurrence_key)
    if raw is None:
        raise RuntimeError("DEADLINE_OCCURRENCE_PENDING")
    occurrence = plain_item(raw)
    coordinate_fields = (
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
    )
    if any(envelope[field] != occurrence.get(field) for field in coordinate_fields):
        raise ContractRejection("DEADLINE_COORDINATE_MISMATCH")
    if occurrence.get("deadline_at") is not None and prepared.payload[
        "deadline_at"
    ] != occurrence.get("deadline_at"):
        raise ContractRejection("DEADLINE_TIME_MISMATCH")
    if occurrence.get("deadline_kind") is not None and prepared.payload[
        "deadline_kind"
    ] != occurrence.get("deadline_kind"):
        raise ContractRejection("DEADLINE_KIND_MISMATCH")
    existing = ledger.get(
        {"pk": prepared.processed_event["pk"], "sk": prepared.processed_event["sk"]}
    )
    if existing is not None:
        if existing.get("event_digest") == {"S": prepared.envelope_digest}:
            return
        raise ContractRejection("PROCESSED_EVENT_CONFLICT")
    current = str(occurrence.get("state", "EXPECTED"))
    if current in {"SUCCEEDED", "FAILED", "MISSED", "OVERDUE", "AMBIGUOUS"}:
        state = current
    elif prepared.payload["deadline_kind"] == "START":
        state = "MISSED" if current == "EXPECTED" else "OVERDUE"
    else:
        state = (
            "OVERDUE"
            if current in {"STARTED", "EXPECTED"} and occurrence.get("task_arn")
            else "MISSED"
        )
    ledger.reduce_evidence(
        occurrence,
        prepared.processed_event,
        state=state,
        evidence_id=prepared.envelope_digest,
        changes={
            "deadline_at": prepared.payload["deadline_at"],
            "deadline_kind": prepared.payload["deadline_kind"],
        },
    )


def _process_launch(
    envelope: Mapping[str, Any],
    prepared: Any,
    ledger: Ledger,
    metrics: Any,
    _identity: str,
    now: str,
) -> None:
    occurrence_key = {
        "pk": f"JOB#{prepared.attempt['job_id']}",
        "sk": f"OCCURRENCE#{prepared.attempt['occurrence_id']}",
    }
    occurrence_item = ledger.get(occurrence_key)
    if occurrence_item is None:
        raise RuntimeError("OCCURRENCE_NOT_EXPECTED")
    occurrence = plain_item(occurrence_item)
    if occurrence.get("state") != "EXPECTED":
        raise ContractRejection("OCCURRENCE_NOT_LAUNCH_ELIGIBLE")
    processed_key = {
        "pk": "EVENT#scheduler",
        "sk": envelope["producer_event_id"],
    }
    processed_item = ledger.get(processed_key)
    attempt_item = ledger.get(prepared.attempt["keys"])
    if processed_item is None and attempt_item is None:
        ledger.reserve_attempt(occurrence, prepared.attempt, prepared.processed_event)
        attempt = prepared.attempt
    elif processed_item is not None and attempt_item is not None:
        processed = plain_item(processed_item)
        if processed.get("event_digest") != prepared.envelope_digest:
            raise ContractRejection("PROCESSED_EVENT_CONFLICT")
        attempt = plain_item(attempt_item)
    else:
        raise ContractRejection("LAUNCH_RESERVATION_INCONSISTENT")
    if attempt.get("task_arn") or attempt.get("launch_state") in {
        "FAILED",
        "AMBIGUOUS",
    }:
        return
    _sts, ecs = _launch_clients(str(attempt["launch_role_arn"]))
    task_arn: str | None = None
    try:
        task_arn = run_task(ecs, attempt)
    except ValueError:
        ledger.finish_failed(attempt, "ECS_RUN_TASK_FAILED")
        return
    except LaunchUncertain as error:
        try:
            task_arn = reconcile_task(ecs, attempt)
        except LaunchUncertain as reconcile_error:
            ledger.mark_ambiguous(attempt, str(reconcile_error)[:64])
            return
        if task_arn is None:
            if now < str(attempt["safe_retry_deadline"]):
                raise RuntimeError("ECS_LAUNCH_RETRY_REQUIRED")
            ledger.mark_ambiguous(attempt, str(error)[:64])
            return
    except Exception as error:  # noqa: BLE001 - API uncertainty requires reconciliation
        try:
            task_arn = reconcile_task(ecs, attempt)
        except LaunchUncertain as reconcile_error:
            ledger.mark_ambiguous(attempt, str(reconcile_error)[:64])
            return
        if task_arn is None:
            if now < str(attempt["safe_retry_deadline"]):
                raise RuntimeError("ECS_LAUNCH_RETRY_REQUIRED") from error
            ledger.mark_ambiguous(attempt, "ECS_LAUNCH_OUTCOME_UNRESOLVED")
            return
    if task_arn is None:
        raise RuntimeError("ECS_TASK_ARN_MISSING")
    ledger.map_task(attempt, task_arn)
    try:
        metrics.put_metric_data(
            Namespace=_required("PROCESS_MANAGER_METRIC_NAMESPACE"),
            MetricData=[
                {
                    "MetricName": "CanaryTaskLaunchAccepted",
                    "Unit": "Count",
                    "Value": 1.0,
                    "Dimensions": [
                        {
                            "Name": "environment",
                            "Value": _required("PROCESS_MANAGER_ENVIRONMENT"),
                        },
                        {"Name": "job_id", "Value": attempt["job_id"]},
                    ],
                }
            ],
        )
    except Exception:  # noqa: BLE001 - metrics are best effort after commit
        LOGGER.warning("process_manager_launch_metric_publish_failed", exc_info=True)
