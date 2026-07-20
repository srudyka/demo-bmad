"""Deterministic CONFIG materialization for future expected occurrences."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Mapping

from referencing import Registry
from semantic_version import SimpleSpec, Version  # type: ignore[import-untyped]

from tests.contract.support.contracts import (
    ContractViolation,
    canonical_json_bytes,
    config_hash,
    expand_schedule,
    materializer_producer_event_id,
    occurrence_id,
    screen_secret_safety,
    validate_contract_instance,
    validate_schedule_contract,
)


class MaterializationError(ValueError):
    """A safe, non-retryable CONFIG or materialization contract failure."""


@dataclass(frozen=True)
class MaterializerRegistration:
    """Cell-owned immutable coordinates accepted by the materializer."""

    account_id: str
    config_version: str
    environment: str
    job_id: str
    owner_generation: int
    region: str
    schedule_arn: str
    schedule_generation: str
    scheduler_delivery_role_id: str


@dataclass(frozen=True)
class MaterializationResult:
    """Expected evidence and an immutable configuration snapshot write."""

    envelopes: tuple[dict[str, object], ...]
    snapshot: dict[str, object]


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not value.endswith("Z") or parsed.tzinfo is None:
            raise ValueError("timestamp must be explicit UTC")
        return parsed.astimezone(UTC)
    except (TypeError, ValueError) as error:
        raise MaterializationError("MATERIALIZER_TIME_INVALID") from error


def _assert_compatibility(
    document: Mapping[str, object], compatibility_catalog: Mapping[str, object]
) -> None:
    """Reject unsupported contract and runtime component versions before side effects."""

    schema_version = document.get("schema_version")
    if schema_version != "1.0.0":
        raise MaterializationError("MATERIALIZER_SCHEMA_VERSION_UNSUPPORTED")
    ranges = compatibility_catalog.get("component_ranges")
    if not isinstance(ranges, Mapping):
        raise MaterializationError("MATERIALIZER_COMPATIBILITY_INVALID")
    for component in ("config", "evidence", "occurrence-materializer"):
        declared = ranges.get(component)
        if not isinstance(declared, str):
            raise MaterializationError("MATERIALIZER_COMPATIBILITY_INVALID")
        try:
            supported = SimpleSpec(declared).match(Version("1.0.0"))
        except ValueError as error:
            raise MaterializationError("MATERIALIZER_COMPATIBILITY_INVALID") from error
        if not supported:
            raise MaterializationError("MATERIALIZER_COMPATIBILITY_UNSUPPORTED")


def _assert_arn_binding(
    value: object,
    registration: MaterializerRegistration,
    service: str | tuple[str, ...],
) -> None:
    """Reject CONFIG ARNs outside the Cell registration's account and Region."""

    if not isinstance(value, str):
        raise MaterializationError("MATERIALIZER_CONFIG_ARN_INVALID")
    parts = value.split(":", 5)
    services = (service,) if isinstance(service, str) else service
    if (
        len(parts) != 6
        or parts[0] != "arn"
        or parts[2] not in services
        or parts[4] != registration.account_id
        or (parts[2] != "iam" and parts[3] != registration.region)
        or (parts[2] == "iam" and parts[3] != "")
    ):
        raise MaterializationError("MATERIALIZER_CONFIG_ARN_BINDING_MISMATCH")


def _assert_config_bindings(
    config: Mapping[str, object], registration: MaterializerRegistration
) -> None:
    """Verify every Cell-owned CONFIG coordinate before any evidence is emitted."""

    _assert_arn_binding(config.get("cluster_arn"), registration, "ecs")
    task_def = config.get("task_definition_arn")
    _assert_arn_binding(task_def, registration, "ecs")
    if not isinstance(task_def, str) or task_def.count(":") != 6:
        raise MaterializationError(
            "MATERIALIZER_CONFIG_TASK_DEFINITION_REVISION_MISSING"
        )
    _assert_arn_binding(
        config.get("notification_target_arn"), registration, ("sns", "sqs")
    )
    logs = config.get("logs")
    roles = config.get("role_arns")
    if not isinstance(logs, Mapping) or not isinstance(roles, Mapping):
        raise MaterializationError("MATERIALIZER_CONFIG_INVALID")
    _assert_arn_binding(logs.get("log_group_arn"), registration, "logs")
    for role in ("execution", "launch", "task"):
        _assert_arn_binding(roles.get(role), registration, "iam")
    if config.get("schedule_arn") != registration.schedule_arn:
        raise MaterializationError("MATERIALIZER_CONFIG_SCHEDULE_ARN_MISMATCH")
    _assert_arn_binding(config.get("schedule_arn"), registration, "scheduler")
    if (
        config.get("scheduler_delivery_role_id")
        != registration.scheduler_delivery_role_id
    ):
        raise MaterializationError("MATERIALIZER_CONFIG_SCHEDULER_ROLE_MISMATCH")


def materialize_config(
    document: Mapping[str, object],
    registration: MaterializerRegistration,
    materialized_at: str,
    schemas: Mapping[str, dict[str, object]],
    schema_registry: Registry[Any],
    secret_policy: dict[str, object],
    compatibility_catalog: Mapping[str, object],
) -> MaterializationResult:
    """Validate immutable CONFIG and create the next 24-hour expected evidence set."""

    config_schema_id = "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:config"
    evidence_schema_id = (
        "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:evidence-envelope"
    )
    if not isinstance(document, dict):
        raise MaterializationError("MATERIALIZER_CONFIG_INVALID")
    _assert_compatibility(document, compatibility_catalog)
    try:
        screen_secret_safety(document, secret_policy)
    except ContractViolation as error:
        raise MaterializationError("MATERIALIZER_CONFIG_SECRET_UNSAFE") from error
    issues = validate_contract_instance(
        schemas[config_schema_id], dict(document), schema_registry
    )
    if issues:
        raise MaterializationError("MATERIALIZER_CONFIG_INVALID")
    config = document.get("config")
    if not isinstance(config, dict):
        raise MaterializationError("MATERIALIZER_CONFIG_INVALID")
    if document.get("config_version") != registration.config_version:
        raise MaterializationError("MATERIALIZER_CONFIG_VERSION_MISMATCH")
    if config_hash(config) != registration.config_version:
        raise MaterializationError("MATERIALIZER_CONFIG_HASH_MISMATCH")
    for field, expected in (
        ("job_id", registration.job_id),
        ("owner_generation", registration.owner_generation),
        ("schedule_generation", registration.schedule_generation),
    ):
        if config.get(field) != expected:
            raise MaterializationError(f"MATERIALIZER_CONFIG_{field.upper()}_MISMATCH")

    _assert_config_bindings(config, registration)
    schedule = config.get("schedule")
    if not isinstance(schedule, dict):
        raise MaterializationError("MATERIALIZER_SCHEDULE_INVALID")
    try:
        validate_schedule_contract(schedule)
    except ContractViolation as error:
        raise MaterializationError("MATERIALIZER_SCHEDULE_INVALID") from error

    start = _parse_timestamp(materialized_at)
    horizon = start + timedelta(hours=24)
    try:
        scheduled_times = tuple(
            value
            for value in expand_schedule(
                schedule, _timestamp(start), _timestamp(horizon + timedelta(minutes=1))
            )
            if _parse_timestamp(value) <= horizon
        )
    except ContractViolation as error:
        raise MaterializationError("MATERIALIZER_SCHEDULE_INVALID") from error
    watermark = _timestamp(horizon)
    envelopes: list[dict[str, object]] = []
    for scheduled_time in scheduled_times:
        occurrence = occurrence_id(
            registration.job_id,
            registration.schedule_generation,
            str(int(_parse_timestamp(scheduled_time).timestamp() // 60)),
        )
        payload: dict[str, object] = {
            "config_validated": True,
            "expectation_horizon": watermark,
            "materialized_at": _timestamp(start),
            "repair": False,
        }
        envelope: dict[str, object] = {
            "config_version": registration.config_version,
            "emitted_at": _timestamp(start),
            "event_type": "occurrence.expected.v1",
            "job_id": registration.job_id,
            "occurrence_id": occurrence,
            "payload": payload,
            "payload_hash": sha256(canonical_json_bytes(payload)).hexdigest(),
            "producer_event_id": materializer_producer_event_id(
                registration.job_id,
                registration.schedule_generation,
                scheduled_time,
                registration.config_version,
                registration.owner_generation,
            ),
            "producer_id": "occurrence-materializer",
            "schedule_generation": registration.schedule_generation,
            "scheduled_time": scheduled_time,
            "schema_version": "1.0.0",
        }
        if validate_contract_instance(
            schemas[evidence_schema_id],
            envelope,
            schema_registry,
            secret_policy=secret_policy,
        ):
            raise MaterializationError("MATERIALIZER_ENVELOPE_INVALID")
        envelopes.append(envelope)
    snapshot: dict[str, object] = {
        "pk": f"JOB#{registration.job_id}",
        "sk": f"CONFIG#{registration.config_version}",
        "record_type": "CONFIG_MATERIALIZATION",
        "job_id": registration.job_id,
        "config_version": registration.config_version,
        "config_hash": registration.config_version,
        "config_json": canonical_json_bytes(config).decode("utf-8"),
        "schedule_generation": registration.schedule_generation,
        "schedule_arn": registration.schedule_arn,
        "validated_at": _timestamp(start),
        "materialized_at": None,
        "horizon_at": watermark,
        "validation_state": "VALIDATED",
        "materialization_state": "PENDING",
        "conformance_result": "PASS",
        "expected_occurrence_ids": [item["occurrence_id"] for item in envelopes],
    }
    return MaterializationResult(envelopes=tuple(envelopes), snapshot=snapshot)
