"""Authenticate Scheduler SQS records and emit canonical launch evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Callable, Mapping

from referencing import Registry

from tests.contract.support.contracts import (
    ContractViolation,
    canonical_json_bytes,
    load_json_bytes_strict,
    occurrence_id,
    materializer_producer_event_id as contract_materializer_producer_event_id,
    scheduler_producer_event_id as contract_scheduler_producer_event_id,
    validate_contract_instance,
)


class NormalizationError(ValueError):
    """A permanent rejection with a secret-safe machine code."""


class TransientTransportError(RuntimeError):
    """An AWS delivery failure that must be retried for this record only."""


@dataclass(frozen=True)
class SchedulerRegistration:
    """Cell-owned binding for the one Scheduler producer accepted in this phase."""

    account_id: str
    config_version: str
    environment: str
    job_id: str
    owner_generation: int
    region: str
    schedule_arn: str
    schedule_generation: str
    schedule_group_arn: str
    scheduler_role_id: str
    source_queue_arn: str


@dataclass(frozen=True)
class MaterializerRegistration:
    """Cell-owned binding for the materializer source queue."""

    account_id: str
    config_version: str
    environment: str
    job_id: str
    materializer_role_id: str
    owner_generation: int
    region: str
    schedule_generation: str
    source_queue_arn: str


@dataclass(frozen=True)
class EcsRegistration:
    """Cell-owned binding for AWS ECS task-state events."""

    account_id: str
    environment: str
    region: str
    cluster_arn: str
    source_queue_arn: str


@dataclass(frozen=True)
class NormalizationResult:
    """Either a canonical envelope or a sanitized permanent rejection."""

    envelope: dict[str, object] | None
    quarantine_record: dict[str, object] | None
    rejection_code: str | None
    retryable: bool = False


def scheduler_producer_event_id(
    registration: SchedulerRegistration, scheduled_time: str
) -> str:
    """Return the stable producer event identifier for one scheduled occurrence."""

    return _scheduler_event_id(registration, scheduled_time)


def _rejection(record: Mapping[str, object], code: str) -> NormalizationResult:
    message_id = str(record.get("messageId", ""))
    queue_arn = str(record.get("eventSourceARN", ""))
    attributes = record.get("attributes")
    received_at = (
        str(attributes.get("ApproximateFirstReceiveTimestamp", ""))
        if isinstance(attributes, Mapping)
        else ""
    )
    return NormalizationResult(
        envelope=None,
        quarantine_record={
            "rejection_code": code,
            "source_message_id_hash": sha256(message_id.encode("utf-8")).hexdigest(),
            "source_queue_arn": queue_arn,
            "received_at": received_at,
        },
        rejection_code=code,
    )


def _body(record: Mapping[str, object]) -> dict[str, object]:
    value = record.get("body")
    if not isinstance(value, str):
        raise NormalizationError("NORMALIZER_BODY_INVALID")
    if len(value.encode("utf-8")) > 262_144:
        raise NormalizationError("NORMALIZER_BODY_TOO_LARGE")
    try:
        return load_json_bytes_strict(value.encode("utf-8"))
    except ContractViolation as error:
        raise NormalizationError("NORMALIZER_BODY_INVALID") from error


_SCHEDULER_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_ARN = re.compile(r"^arn:[A-Za-z0-9-]+:[A-Za-z0-9-]+:[A-Za-z0-9-]*:[0-9]{12}:.+$")


def _canonical_scheduled_time(timestamp: str) -> str:
    if _SCHEDULER_TIMESTAMP.fullmatch(timestamp) is None:
        raise NormalizationError("NORMALIZER_SCHEDULE_TIME_INVALID")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise NormalizationError("NORMALIZER_SCHEDULE_TIME_INVALID") from error
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _epoch_minute(timestamp: str) -> str:
    return str(
        int(
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
            .replace(tzinfo=UTC)
            .timestamp()
            // 60
        )
    )


def _assert_equal(body: Mapping[str, object], name: str, expected: object) -> None:
    if body.get(name) != expected:
        raise NormalizationError(f"NORMALIZER_ASSERTION_{name.upper()}")


def _scheduler_event_id(
    registration: SchedulerRegistration, scheduled_time: str
) -> str:
    return contract_scheduler_producer_event_id(
        registration.schedule_arn,
        scheduled_time,
        registration.config_version,
        registration.owner_generation,
    )


def normalize_scheduler_record(
    record: Mapping[str, object],
    registration: SchedulerRegistration,
    schemas: Mapping[str, dict[str, object]],
    schema_registry: Registry[Any],
    secret_policy: dict[str, object],
) -> NormalizationResult:
    """Validate one raw Scheduler SQS record without performing AWS I/O."""

    try:
        if record.get("eventSource") != "aws:sqs":
            raise NormalizationError("NORMALIZER_SOURCE_SERVICE")
        if record.get("eventSourceARN") != registration.source_queue_arn:
            raise NormalizationError("NORMALIZER_SOURCE_QUEUE")
        if record.get("awsRegion") != registration.region:
            raise NormalizationError("NORMALIZER_SOURCE_REGION")
        attributes = record.get("attributes")
        if not isinstance(attributes, Mapping):
            raise NormalizationError("NORMALIZER_SENDER_ROLE")
        sender_id = attributes.get("SenderId")
        if (
            not isinstance(sender_id, str)
            or not sender_id.startswith(f"{registration.scheduler_role_id}:")
            or sender_id == f"{registration.scheduler_role_id}:"
        ):
            raise NormalizationError("NORMALIZER_SENDER_ROLE")

        body = _body(record)
        if body.get("schema_version") != "1.0.0":
            raise NormalizationError("NORMALIZER_SCHEMA_MAJOR")
        _assert_equal(body, "event_type", "occurrence.launch.v1")
        _assert_equal(body, "producer_id", "scheduler")
        _assert_equal(body, "job_id", registration.job_id)
        _assert_equal(body, "account_id", registration.account_id)
        _assert_equal(body, "region", registration.region)
        _assert_equal(body, "ownership_generation", registration.owner_generation)
        _assert_equal(body, "config_version", registration.config_version)
        _assert_equal(body, "schedule_generation", registration.schedule_generation)
        _assert_equal(body, "schedule_arn", registration.schedule_arn)
        _assert_equal(body, "schedule_group_arn", registration.schedule_group_arn)
        _assert_equal(body, "source_queue_arn", registration.source_queue_arn)
        raw_scheduled_time = body.get("scheduler_scheduled_time")
        if not isinstance(raw_scheduled_time, str):
            raise NormalizationError("NORMALIZER_SCHEDULE_TIME_INVALID")
        scheduled_time = _canonical_scheduled_time(raw_scheduled_time)
        expected_occurrence_id = occurrence_id(
            registration.job_id,
            registration.schedule_generation,
            _epoch_minute(scheduled_time),
        )
        supplied_occurrence_id = body.get("occurrence_id")
        if supplied_occurrence_id is not None:
            _assert_equal(body, "occurrence_id", expected_occurrence_id)

        payload: dict[str, object] = {
            "owner_generation": registration.owner_generation,
            "schedule_arn": registration.schedule_arn,
            "schedule_group_arn": registration.schedule_group_arn,
            "scheduler_scheduled_time": scheduled_time,
        }
        envelope: dict[str, object] = {
            "config_version": registration.config_version,
            "emitted_at": scheduled_time,
            "event_type": "occurrence.launch.v1",
            "job_id": registration.job_id,
            "occurrence_id": expected_occurrence_id,
            "payload": payload,
            "payload_hash": sha256(canonical_json_bytes(payload)).hexdigest(),
            "producer_event_id": _scheduler_event_id(registration, scheduled_time),
            "producer_id": "scheduler",
            "schedule_generation": registration.schedule_generation,
            "scheduled_time": scheduled_time,
            "schema_version": "1.0.0",
        }
        trace_header = attributes.get("AWSTraceHeader")
        if isinstance(trace_header, str) and trace_header:
            envelope["trace_context"] = trace_header
        schema_id = (
            "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:evidence-envelope"
        )
        issues = validate_contract_instance(
            schemas[schema_id], envelope, schema_registry, secret_policy=secret_policy
        )
        if issues:
            raise NormalizationError("NORMALIZER_ENVELOPE_INVALID")
        return NormalizationResult(
            envelope=envelope, quarantine_record=None, rejection_code=None
        )
    except NormalizationError as error:
        return _rejection(record, str(error))


def normalize_materializer_record(
    record: Mapping[str, object],
    registration: MaterializerRegistration,
    schemas: Mapping[str, dict[str, object]],
    schema_registry: Registry[Any],
    secret_policy: dict[str, object],
) -> NormalizationResult:
    """Authenticate expected-occurrence evidence before canonical ingress."""

    try:
        if record.get("eventSource") != "aws:sqs":
            raise NormalizationError("NORMALIZER_SOURCE_SERVICE")
        if record.get("eventSourceARN") != registration.source_queue_arn:
            raise NormalizationError("NORMALIZER_SOURCE_QUEUE")
        if record.get("awsRegion") != registration.region:
            raise NormalizationError("NORMALIZER_SOURCE_REGION")
        attributes = record.get("attributes")
        if not isinstance(attributes, Mapping):
            raise NormalizationError("NORMALIZER_SENDER_ROLE")
        sender_id = attributes.get("SenderId")
        if (
            not isinstance(sender_id, str)
            or not sender_id.startswith(f"{registration.materializer_role_id}:")
            or sender_id == f"{registration.materializer_role_id}:"
        ):
            raise NormalizationError("NORMALIZER_SENDER_ROLE")
        body = _body(record)
        for field, expected in (
            ("schema_version", "1.0.0"),
            ("event_type", "occurrence.expected.v1"),
            ("producer_id", "occurrence-materializer"),
            ("job_id", registration.job_id),
            ("config_version", registration.config_version),
            ("schedule_generation", registration.schedule_generation),
        ):
            _assert_equal(body, field, expected)
        scheduled_time = body.get("scheduled_time")
        if not isinstance(scheduled_time, str):
            raise NormalizationError("NORMALIZER_SCHEDULE_TIME_INVALID")
        scheduled_time = _canonical_scheduled_time(scheduled_time)
        _assert_equal(body, "scheduled_time", scheduled_time)
        expected_occurrence = occurrence_id(
            registration.job_id,
            registration.schedule_generation,
            _epoch_minute(scheduled_time),
        )
        _assert_equal(body, "occurrence_id", expected_occurrence)
        expected_event_id = contract_materializer_producer_event_id(
            registration.job_id,
            registration.schedule_generation,
            scheduled_time,
            registration.config_version,
            registration.owner_generation,
        )
        _assert_equal(body, "producer_event_id", expected_event_id)
        payload = body.get("payload")
        if not isinstance(payload, dict):
            raise NormalizationError("NORMALIZER_PAYLOAD_INVALID")
        _assert_equal(
            body, "payload_hash", sha256(canonical_json_bytes(payload)).hexdigest()
        )
        schema_id = (
            "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:evidence-envelope"
        )
        issues = validate_contract_instance(
            schemas[schema_id], body, schema_registry, secret_policy=secret_policy
        )
        if issues:
            raise NormalizationError("NORMALIZER_ENVELOPE_INVALID")
        return NormalizationResult(
            envelope=body, quarantine_record=None, rejection_code=None
        )
    except NormalizationError as error:
        return _rejection(record, str(error))


def normalize_ecs_event(
    record: Mapping[str, object],
    registration: EcsRegistration,
    *,
    task_lookup: Callable[[str], Mapping[str, object] | None],
) -> NormalizationResult:
    """Normalize one EventBridge ECS task-state event from AWS-owned fields."""

    try:
        if record.get("source") != "aws.ecs":
            raise NormalizationError("ECS_EVENT_SOURCE_INVALID")
        if record.get("detail-type") != "ECS Task State Change":
            raise NormalizationError("ECS_EVENT_TYPE_INVALID")
        if record.get("account") != registration.account_id:
            raise NormalizationError("ECS_EVENT_ACCOUNT_INVALID")
        if record.get("region") != registration.region:
            raise NormalizationError("ECS_EVENT_REGION_INVALID")
        detail = record.get("detail")
        resources = record.get("resources")
        if not isinstance(detail, Mapping) or not isinstance(resources, list):
            raise NormalizationError("ECS_EVENT_SHAPE_INVALID")
        task_arn = detail.get("taskArn")
        cluster_arn = detail.get("clusterArn")
        status = detail.get("lastStatus")
        if (
            not isinstance(task_arn, str)
            or not isinstance(cluster_arn, str)
            or _ARN.fullmatch(task_arn) is None
            or _ARN.fullmatch(cluster_arn) is None
            or cluster_arn != registration.cluster_arn
            or task_arn not in resources
            or status not in {"PENDING", "RUNNING", "STOPPED"}
        ):
            raise NormalizationError("ECS_EVENT_AUTHORITY_INVALID")
        binding = task_lookup(task_arn)
        if binding is None:
            return NormalizationResult(
                envelope=None,
                quarantine_record={
                    "record_type": "ORPHAN_ECS_EVENT",
                    "task_arn_hash": sha256(task_arn.encode("utf-8")).hexdigest(),
                    "source_event_id_hash": sha256(
                        canonical_json_bytes(dict(record))
                    ).hexdigest(),
                    "cluster_arn": registration.cluster_arn,
                },
                rejection_code="ECS_TASK_MAPPING_PENDING",
                retryable=True,
            )
        required_binding = (
            "job_id",
            "config_version",
            "schedule_generation",
            "occurrence_id",
            "scheduled_time",
        )
        if any(not isinstance(binding.get(key), str) for key in required_binding):
            raise NormalizationError("ECS_TASK_BINDING_INVALID")
        event_time = record.get("time")
        if not isinstance(event_time, str):
            raise NormalizationError("ECS_EVENT_TIME_INVALID")
        event_time = _canonical_scheduled_time(event_time)
        containers = detail.get("containers", [])
        if not isinstance(containers, list):
            raise NormalizationError("ECS_EVENT_CONTAINERS_INVALID")
        normalized_containers: list[dict[str, object]] = []
        for container in containers:
            if not isinstance(container, Mapping) or not isinstance(
                container.get("name"), str
            ):
                raise NormalizationError("ECS_EVENT_CONTAINERS_INVALID")
            normalized_containers.append(
                {
                    "name": container["name"],
                    "essential": bool(container.get("essential", False)),
                    "exit_code": container.get("exitCode"),
                }
            )
            if not isinstance(container.get("exitCode"), (int, type(None))) or isinstance(
                container.get("exitCode"), bool
            ):
                raise NormalizationError("ECS_EVENT_EXIT_CODE_INVALID")
        if not normalized_containers:
            raise NormalizationError("ECS_EVENT_CONTAINERS_INVALID")
        payload: dict[str, object] = {
            "task_arn": task_arn,
            "cluster_arn": cluster_arn,
            "last_status": status,
            "event_time": event_time,
            "containers": normalized_containers,
            "stop_code": detail.get("stopCode"),
            "stopped_reason": detail.get("stoppedReason"),
        }
        if any(
            not isinstance(value, (str, type(None)))
            for value in (payload["stop_code"], payload["stopped_reason"])
        ):
            raise NormalizationError("ECS_EVENT_REASON_INVALID")
        if any(
            isinstance(value, str) and len(value) > 1024
            for value in (payload["stop_code"], payload["stopped_reason"])
        ):
            raise NormalizationError("ECS_EVENT_REASON_TOO_LARGE")
        if any(
            marker in canonical_json_bytes(payload).decode("utf-8").lower()
            for marker in ("password", "secret", "access_key", "token")
        ):
            raise NormalizationError("ECS_EVENT_SECRET_CONTENT")
        raw_event = canonical_json_bytes(dict(record))
        event_id = sha256(b"ecs-task-state/v1\n" + raw_event).hexdigest()
        envelope = {
            "schema_version": "1.0.0",
            "event_type": "task.state.v1",
            "producer_id": "ecs",
            "producer_event_id": event_id,
            "job_id": binding["job_id"],
            "config_version": binding["config_version"],
            "schedule_generation": binding["schedule_generation"],
            "occurrence_id": binding["occurrence_id"],
            "scheduled_time": binding["scheduled_time"],
            "emitted_at": event_time,
            "payload": payload,
            "payload_hash": sha256(canonical_json_bytes(payload)).hexdigest(),
        }
        return NormalizationResult(envelope, None, None)
    except NormalizationError as error:
        return _rejection(record, str(error))


def process_scheduler_batch(
    records: list[Mapping[str, object]],
    registration: SchedulerRegistration,
    schemas: Mapping[str, dict[str, object]],
    schema_registry: Registry[Any],
    secret_policy: dict[str, object],
    *,
    send_envelope: Callable[[dict[str, object]], None],
    send_quarantine: Callable[[dict[str, object]], None],
    on_permanent_rejection: Callable[[str, Mapping[str, object]], None] | None = None,
    transient_message_ids: set[str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Return Lambda's partial-batch response for raw Scheduler records."""

    transient_ids = transient_message_ids or set()
    failures: list[dict[str, str]] = []
    for record in records:
        message_id = str(record.get("messageId", ""))
        if message_id in transient_ids:
            failures.append({"itemIdentifier": message_id})
            continue
        result = normalize_scheduler_record(
            record, registration, schemas, schema_registry, secret_policy
        )
        if result.rejection_code is not None and on_permanent_rejection is not None:
            on_permanent_rejection(result.rejection_code, record)
        try:
            if result.envelope is not None:
                send_envelope(result.envelope)
            elif result.quarantine_record is not None:
                send_quarantine(result.quarantine_record)
        except OSError, TransientTransportError:
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}


def process_materializer_batch(
    records: list[Mapping[str, object]],
    registration: MaterializerRegistration,
    schemas: Mapping[str, dict[str, object]],
    schema_registry: Registry[Any],
    secret_policy: dict[str, object],
    *,
    send_envelope: Callable[[dict[str, object]], None],
    send_process_manager_envelope: Callable[[dict[str, object]], None] | None = None,
    send_quarantine: Callable[[dict[str, object]], None],
    on_permanent_rejection: Callable[[str, Mapping[str, object]], None] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Return Lambda's partial-batch response for materializer source records."""

    failures: list[dict[str, str]] = []
    for record in records:
        message_id = str(record.get("messageId", ""))
        result = normalize_materializer_record(
            record, registration, schemas, schema_registry, secret_policy
        )
        if result.rejection_code is not None and on_permanent_rejection is not None:
            on_permanent_rejection(result.rejection_code, record)
        try:
            if result.envelope is not None:
                send_envelope(result.envelope)
                if send_process_manager_envelope is not None:
                    send_process_manager_envelope(result.envelope)
            elif result.quarantine_record is not None:
                send_quarantine(result.quarantine_record)
        except OSError, TransientTransportError:
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}


def process_ecs_batch(
    records: list[Mapping[str, object]],
    registration: EcsRegistration,
    *,
    task_lookup: Callable[[str], Mapping[str, object] | None],
    send_envelope: Callable[[dict[str, object]], None],
    send_quarantine: Callable[[dict[str, object]], None],
    on_permanent_rejection: Callable[[str, Mapping[str, object]], None] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Normalize EventBridge ECS records with bounded orphan retries."""

    failures: list[dict[str, str]] = []
    for record in records:
        message_id = str(record.get("messageId", ""))
        try:
            body = _body(record)
        except NormalizationError as error:
            rejection = _rejection(record, str(error))
            if on_permanent_rejection is not None:
                on_permanent_rejection(str(error), record)
            try:
                if rejection.quarantine_record is not None:
                    send_quarantine(rejection.quarantine_record)
            except (OSError, TransientTransportError):
                failures.append({"itemIdentifier": message_id})
            continue
        try:
            result = normalize_ecs_event(body, registration, task_lookup=task_lookup)
            if result.retryable:
                failures.append({"itemIdentifier": message_id})
                continue
            if result.rejection_code is not None and on_permanent_rejection is not None:
                on_permanent_rejection(result.rejection_code, record)
            if result.envelope is not None:
                send_envelope(result.envelope)
            elif result.quarantine_record is not None:
                send_quarantine(result.quarantine_record)
        except (OSError, TransientTransportError):
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
