"""Pure validation and deterministic record construction for occurrence state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .contracts import (
    canonical_json_bytes,
    deadline_event_id,
    launch_client_token,
    materializer_event_id,
    occurrence_id,
    scheduler_event_id,
)


class ContractRejection(ValueError):
    """A record-local, safe-to-acknowledge contract failure."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def _timestamp(value: object, code: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractRejection(code)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ContractRejection(code) from error
    if parsed.tzinfo != timezone.utc or parsed.microsecond % 1000:
        raise ContractRejection(code)
    if parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z") != value:
        raise ContractRejection(code)
    return parsed


def _plain_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Decode the small DynamoDB AttributeValue subset used by the registry."""

    result: dict[str, Any] = {}
    for key, value in item.items():
        if isinstance(value, Mapping) and len(value) == 1:
            kind, child = next(iter(value.items()))
            if kind == "S":
                result[key] = child
            elif kind == "N":
                result[key] = int(child) if str(child).isdigit() else float(child)
            elif kind == "BOOL":
                result[key] = child
            elif kind == "NULL":
                result[key] = None
            elif kind == "SS":
                result[key] = list(child)
            else:
                result[key] = value
        else:
            result[key] = value
    return result


@dataclass(frozen=True)
class ConfigSnapshot:
    job_id: str
    config_version: str
    schedule_generation: str
    owner_generation: int
    config_hash: str
    config_json: str
    validation_state: str
    materialization_state: str

    @classmethod
    def from_item(cls, item: Mapping[str, Any]) -> ConfigSnapshot:
        value = _plain_item(item)
        owner_generation = value.get("owner_generation")
        if owner_generation is None:
            try:
                owner_generation = json.loads(str(value["config_json"]))[
                    "owner_generation"
                ]
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise ContractRejection("CONFIG_SNAPSHOT_INVALID") from error
        try:
            snapshot = cls(
                job_id=str(value["job_id"]),
                config_version=str(value["config_version"]),
                schedule_generation=str(value["schedule_generation"]),
                owner_generation=int(owner_generation),
                config_hash=str(value["config_hash"]),
                config_json=str(value["config_json"]),
                validation_state=str(value["validation_state"]),
                materialization_state=str(
                    value.get("materialization_state", "PENDING")
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ContractRejection("CONFIG_SNAPSHOT_INVALID") from error
        if (
            snapshot.validation_state != "VALIDATED"
            or snapshot.materialization_state not in {"PENDING", "MATERIALIZED"}
        ):
            raise ContractRejection("CONFIG_NOT_VALIDATED")
        return snapshot

    def config(self) -> dict[str, Any]:
        try:
            value = json.loads(self.config_json)
        except json.JSONDecodeError as error:
            raise ContractRejection("CONFIG_CANONICAL_JSON_INVALID") from error
        if (
            not isinstance(value, dict)
            or canonical_json_bytes(value).decode() != self.config_json
        ):
            raise ContractRejection("CONFIG_CANONICAL_JSON_INVALID")
        if hashlib.sha256(canonical_json_bytes(value)).hexdigest() != self.config_hash:
            raise ContractRejection("CONFIG_HASH_MISMATCH")
        return value


@dataclass(frozen=True)
class PreparedAcceptance:
    occurrence: dict[str, Any]
    processed_event: dict[str, Any]
    envelope_digest: str


@dataclass(frozen=True)
class PreparedLaunch:
    attempt: dict[str, Any]
    processed_event: dict[str, Any]
    envelope_digest: str
    client_token: str
    occurrence: dict[str, Any] | None = None


@dataclass(frozen=True)
class PreparedCorrelation:
    processed_event: dict[str, Any]
    envelope_digest: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PreparedDeadline:
    processed_event: dict[str, Any]
    envelope_digest: str
    payload: dict[str, Any]


def prepare_deadline(
    envelope: Mapping[str, Any],
    *,
    processor_identity: str,
    now: str,
) -> PreparedDeadline:
    """Validate authenticated deadline evidence before the ledger transaction."""

    if not isinstance(envelope, Mapping) or envelope.get("schema_version") != "1.0.0":
        raise ContractRejection("DEADLINE_ENVELOPE_INVALID")
    required = {
        "schema_version",
        "event_type",
        "producer_id",
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "payload",
        "payload_hash",
        "emitted_at",
    }
    if set(envelope) - required - {"trace_context"} and not all(
        isinstance(key, str) and key.startswith("x-")
        for key in set(envelope) - required - {"trace_context"}
    ):
        raise ContractRejection("DEADLINE_ENVELOPE_INVALID")
    if any(field not in envelope for field in required):
        raise ContractRejection("DEADLINE_ENVELOPE_INVALID")
    if (
        envelope.get("event_type") != "occurrence.deadline-reached.v1"
        or envelope.get("producer_id") != "deadline-scanner"
    ):
        raise ContractRejection("UNAUTHORIZED_PRODUCER")
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or set(payload) != {
        "deadline_kind",
        "deadline_at",
        "scanner_watermark",
    }:
        raise ContractRejection("DEADLINE_PAYLOAD_INVALID")
    if payload.get("deadline_kind") not in {"START", "COMPLETION"}:
        raise ContractRejection("DEADLINE_KIND_INVALID")
    if hashlib.sha256(canonical_json_bytes(payload)).hexdigest() != envelope.get(
        "payload_hash"
    ):
        raise ContractRejection("PAYLOAD_HASH_MISMATCH")
    for field in ("scheduled_time", "emitted_at"):
        _timestamp(envelope[field], "DEADLINE_TIME_INVALID")
    for field in ("deadline_at", "scanner_watermark"):
        _timestamp(payload[field], "DEADLINE_TIME_INVALID")
    expected_event_id = deadline_event_id(
        str(envelope["job_id"]),
        str(envelope["schedule_generation"]),
        str(envelope["occurrence_id"]),
        str(payload["deadline_kind"]),
        str(payload["deadline_at"]),
        str(envelope["config_version"]),
    )
    if envelope["producer_event_id"] != expected_event_id:
        raise ContractRejection("DEADLINE_EVENT_ID_MISMATCH")
    digest = hashlib.sha256(canonical_json_bytes(dict(envelope))).hexdigest()
    processed = {
        "pk": "EVENT#deadline-scanner",
        "sk": str(envelope["producer_event_id"]),
        "record_type": "PROCESSED_EVENT",
        "schema_version": "1.0.0",
        "producer_id": "deadline-scanner",
        "producer_event_id": str(envelope["producer_event_id"]),
        "event_digest": digest,
        "event_type": "occurrence.deadline-reached.v1",
        "job_id": str(envelope["job_id"]),
        "occurrence_id": str(envelope["occurrence_id"]),
        "accepted_at": _timestamp(now, "PROCESSOR_TIME_INVALID")
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "disposition": "ACCEPTED",
        "processor_deployment_identity_id": processor_identity,
    }
    return PreparedDeadline(processed, digest, dict(payload))


def reduce_deadline_state(
    current_state: str,
    evidence: list[Mapping[str, Any]],
) -> str:
    """Reduce a bounded immutable evidence set without relying on arrival order."""

    deduplicated: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in evidence:
        key = (str(item.get("producer_id")), str(item.get("producer_event_id")))
        previous = deduplicated.get(key)
        if previous is not None and previous.get("digest") != item.get("digest"):
            return "AMBIGUOUS"
        deduplicated[key] = item
    facts = list(deduplicated.values())
    task_facts = [
        item for item in facts if item.get("kind") in {"TASK_RUNNING", "TASK_STOPPED"}
    ]
    task_arns = {item.get("task_arn") for item in task_facts if item.get("task_arn")}
    completions = [item for item in facts if item.get("kind") == "COMPLETION"]
    if len(task_arns) > 1 or len(completions) > 1:
        return "AMBIGUOUS"
    failure = any(
        item.get("kind") == "LAUNCH_FAILED"
        or (
            item.get("kind") == "TASK_STOPPED"
            and item.get("exit_code") not in {None, 0}
        )
        or (item.get("kind") == "COMPLETION" and item.get("marker_status") == "FAILURE")
        for item in facts
    )
    started = any(
        item.get("kind") in {"TASK_RUNNING", "TASK_STOPPED"} for item in facts
    )
    success = any(
        item.get("kind") == "TASK_STOPPED" and item.get("exit_code") == 0
        for item in facts
    ) and any(
        item.get("kind") == "COMPLETION" and item.get("marker_status") == "SUCCESS"
        for item in facts
    )
    deadline = next((item for item in facts if item.get("kind") == "DEADLINE"), None)
    if deadline is not None:
        completion = completions[0] if completions else None
        if (
            success
            and completion is not None
            and str(completion.get("fact_time", ""))
            <= str(deadline.get("deadline_at", ""))
        ):
            return "SUCCEEDED"
        if failure:
            return "FAILED"
        return "OVERDUE" if started else "MISSED"
    if failure:
        return "FAILED"
    if success:
        return "SUCCEEDED"
    return "STARTED" if started else current_state


def prepare_expected(
    envelope: Mapping[str, Any],
    snapshot_item: Mapping[str, Any] | None,
    *,
    processor_identity: str,
    now: str,
    supported_major: str = "1",
    expected_owner_generation: int | None = None,
) -> PreparedAcceptance:
    """Validate one authenticated materializer envelope and build bounded records."""

    if not isinstance(envelope, Mapping):
        raise ContractRejection("ENVELOPE_INVALID")
    raw = canonical_json_bytes(dict(envelope))
    schema_version = envelope.get("schema_version")
    if (
        not isinstance(schema_version, str)
        or schema_version.split(".")[0] != supported_major
    ):
        raise ContractRejection("UNSUPPORTED_SCHEMA_MAJOR")
    if schema_version != "1.0.0":
        raise ContractRejection("UNSUPPORTED_SCHEMA_VERSION")
    required = (
        "event_type",
        "producer_id",
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "payload",
        "payload_hash",
        "emitted_at",
    )
    if any(field not in envelope for field in required):
        raise ContractRejection("ENVELOPE_INVALID")
    allowed = set(required) | {"schema_version", "trace_context"}
    if any(
        not isinstance(key, str) or (key not in allowed and not key.startswith("x-"))
        for key in envelope
    ):
        raise ContractRejection("ENVELOPE_INVALID")
    if (
        envelope["event_type"] != "occurrence.expected.v1"
        or envelope["producer_id"] != "occurrence-materializer"
    ):
        raise ContractRejection("UNAUTHORIZED_PRODUCER")
    for field in (
        "event_type",
        "producer_id",
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "emitted_at",
        "payload_hash",
    ):
        if not isinstance(envelope[field], str) or not envelope[field]:
            raise ContractRejection("ENVELOPE_INVALID")
    payload = envelope["payload"]
    if (
        not isinstance(payload, dict)
        or hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        != envelope["payload_hash"]
    ):
        raise ContractRejection("PAYLOAD_HASH_MISMATCH")
    payload_allowed = {
        "config_validated",
        "expectation_horizon",
        "materialized_at",
        "repair",
    }
    if set(payload) - payload_allowed or payload.get("config_validated") is not True:
        raise ContractRejection("PAYLOAD_SCHEMA_INVALID")
    if (
        not isinstance(payload.get("expectation_horizon"), str)
        or not isinstance(payload.get("materialized_at"), str)
        or not isinstance(payload.get("repair"), bool)
    ):
        raise ContractRejection("PAYLOAD_SCHEMA_INVALID")
    _timestamp(envelope["emitted_at"], "EMITTED_TIME_INVALID")
    scheduled = envelope["scheduled_time"]
    scheduled_at = _timestamp(scheduled, "SCHEDULED_TIME_INVALID")
    expected_id = occurrence_id(
        str(envelope["job_id"]),
        str(envelope["schedule_generation"]),
        str(int(scheduled_at.timestamp() // 60)),
    )
    if envelope["occurrence_id"] != expected_id:
        raise ContractRejection("OCCURRENCE_ID_MISMATCH")
    if snapshot_item is None:
        raise ContractRejection("CONFIG_NOT_FOUND")
    snapshot = ConfigSnapshot.from_item(snapshot_item)
    config = snapshot.config()
    if (
        snapshot.job_id != envelope["job_id"]
        or snapshot.config_version != envelope["config_version"]
        or snapshot.schedule_generation != envelope["schedule_generation"]
        or config.get("job_id") != envelope["job_id"]
        or config.get("schedule_generation") != envelope["schedule_generation"]
    ):
        raise ContractRejection("CONFIG_IDENTITY_MISMATCH")
    if snapshot.config_hash != snapshot.config_version:
        raise ContractRejection("CONFIG_VERSION_HASH_MISMATCH")
    if (
        expected_owner_generation is not None
        and snapshot.owner_generation != expected_owner_generation
    ):
        raise ContractRejection("CONFIG_OWNER_GENERATION_MISMATCH")
    if envelope["producer_event_id"] != materializer_event_id(
        snapshot.job_id,
        snapshot.schedule_generation,
        scheduled,
        snapshot.config_version,
        snapshot.owner_generation,
    ):
        raise ContractRejection("PRODUCER_EVENT_ID_MISMATCH")
    try:
        window = int(config["completion_window_seconds"])
    except (KeyError, TypeError, ValueError) as error:
        raise ContractRejection("CONFIG_COMPLETION_WINDOW_INVALID") from error
    if window < 1 or window > 7 * 24 * 60 * 60:
        raise ContractRejection("CONFIG_COMPLETION_WINDOW_INVALID")
    deadline = (
        (scheduled_at + timedelta(seconds=window))
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    deadline_bucket = deadline[:19] + ".000Z"
    reduced_at = _timestamp(now, "PROCESSOR_TIME_INVALID")
    reduced_at_string = reduced_at.isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
    event_id = str(envelope["producer_event_id"])
    occurrence_key = f"JOB#{snapshot.job_id}"
    occurrence = {
        "keys": {"pk": occurrence_key, "sk": f"OCCURRENCE#{expected_id}"},
        "record_type": "OCCURRENCE",
        "schema_version": "1.0.0",
        "job_id": snapshot.job_id,
        "config_version": snapshot.config_version,
        "schedule_generation": snapshot.schedule_generation,
        "occurrence_id": expected_id,
        "scheduled_time": scheduled,
        "deadline_at": deadline,
        "deadline_kind": "COMPLETION",
        "deadline_key": f"DEADLINE#0#{deadline_bucket}",
        "deadline_sort": f"{deadline}#{expected_id}#COMPLETION",
        "state": "EXPECTED",
        "started_at": None,
        "completed_at": None,
        "exit_code": None,
        "error_code": None,
        "operator_safe_error_reason": None,
        "evidence_ids": [hashlib.sha256(raw).hexdigest()],
    }
    processed_event = {
        "pk": "EVENT#occurrence-materializer",
        "sk": event_id,
        "record_type": "PROCESSED_EVENT",
        "schema_version": "1.0.0",
        "producer_id": "occurrence-materializer",
        "producer_event_id": event_id,
        "event_digest": hashlib.sha256(raw).hexdigest(),
        "event_type": "occurrence.expected.v1",
        "job_id": snapshot.job_id,
        "occurrence_id": expected_id,
        "accepted_at": reduced_at_string,
        "disposition": "ACCEPTED",
        "processor_deployment_identity_id": processor_identity,
    }
    return PreparedAcceptance(
        occurrence, processed_event, processed_event["event_digest"]
    )


def _launch_payload(envelope: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ContractRejection("LAUNCH_PAYLOAD_INVALID")
    required = {
        "owner_generation",
        "schedule_arn",
        "schedule_group_arn",
        "scheduler_scheduled_time",
    }
    if set(payload) != required:
        raise ContractRejection("LAUNCH_PAYLOAD_INVALID")
    return payload


def prepare_launch(
    envelope: Mapping[str, Any],
    snapshot_item: Mapping[str, Any] | None,
    *,
    processor_identity: str,
    now: str,
    expected_owner_generation: int | None = None,
    expected_launch_role_arn: str | None = None,
    safe_retry_seconds: int = 3600,
) -> PreparedLaunch:
    """Validate Scheduler launch evidence and reserveable attempt-zero data."""

    if not isinstance(envelope, Mapping):
        raise ContractRejection("ENVELOPE_INVALID")
    raw = canonical_json_bytes(dict(envelope))
    if envelope.get("schema_version") != "1.0.0":
        raise ContractRejection("UNSUPPORTED_SCHEMA_VERSION")
    required = {
        "schema_version",
        "event_type",
        "producer_id",
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "payload",
        "payload_hash",
        "emitted_at",
    }
    if any(field not in envelope for field in required):
        raise ContractRejection("ENVELOPE_INVALID")
    if any(
        not isinstance(key, str)
        or (key not in required and key != "trace_context" and not key.startswith("x-"))
        for key in envelope
    ):
        raise ContractRejection("ENVELOPE_INVALID")
    if (
        envelope["event_type"] != "occurrence.launch.v1"
        or envelope["producer_id"] != "scheduler"
    ):
        raise ContractRejection("UNAUTHORIZED_PRODUCER")
    for field in (
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "emitted_at",
        "payload_hash",
    ):
        if not isinstance(envelope[field], str) or not envelope[field]:
            raise ContractRejection("ENVELOPE_INVALID")
    payload = _launch_payload(envelope)
    if (
        hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        != envelope["payload_hash"]
    ):
        raise ContractRejection("PAYLOAD_HASH_MISMATCH")
    scheduled = envelope["scheduled_time"]
    scheduled_at = _timestamp(scheduled, "SCHEDULED_TIME_INVALID")
    if payload["scheduler_scheduled_time"] != scheduled:
        raise ContractRejection("LAUNCH_TIME_MISMATCH")
    if (
        not isinstance(payload["owner_generation"], int)
        or payload["owner_generation"] < 1
    ):
        raise ContractRejection("OWNER_GENERATION_INVALID")
    _timestamp(envelope["emitted_at"], "EMITTED_TIME_INVALID")
    expected_id = occurrence_id(
        str(envelope["job_id"]),
        str(envelope["schedule_generation"]),
        str(int(scheduled_at.timestamp() // 60)),
    )
    if envelope["occurrence_id"] != expected_id:
        raise ContractRejection("OCCURRENCE_ID_MISMATCH")
    if snapshot_item is None:
        raise ContractRejection("CONFIG_NOT_FOUND")
    snapshot = ConfigSnapshot.from_item(snapshot_item)
    if snapshot.materialization_state != "MATERIALIZED":
        raise ContractRejection("CONFIG_NOT_MATERIALIZED")
    if snapshot.config_hash != snapshot.config_version:
        raise ContractRejection("CONFIG_VERSION_HASH_MISMATCH")
    config = snapshot.config()
    if (
        snapshot.job_id != envelope["job_id"]
        or snapshot.config_version != envelope["config_version"]
        or snapshot.schedule_generation != envelope["schedule_generation"]
        or snapshot.owner_generation != payload["owner_generation"]
        or config.get("job_id") != envelope["job_id"]
        or config.get("schedule_generation") != envelope["schedule_generation"]
        or config.get("schedule_arn") != payload["schedule_arn"]
        or config.get("owner_generation") != payload["owner_generation"]
    ):
        raise ContractRejection("CONFIG_IDENTITY_MISMATCH")
    if (
        expected_owner_generation is not None
        and snapshot.owner_generation != expected_owner_generation
    ):
        raise ContractRejection("CONFIG_OWNER_GENERATION_MISMATCH")
    if envelope["producer_event_id"] != scheduler_event_id(
        str(payload["schedule_arn"]),
        scheduled,
        snapshot.config_version,
        snapshot.owner_generation,
    ):
        raise ContractRejection("PRODUCER_EVENT_ID_MISMATCH")
    try:
        cluster_arn = str(config["cluster_arn"])
        task_definition_arn = str(config["task_definition_arn"])
        launch_role_arn = str(config["role_arns"]["launch"])
        deployment_identity_id = str(config["deployment_identity_id"])
        network = config["network"]
        if (
            not isinstance(network, Mapping)
            or network.get("assign_public_ip") != "DISABLED"
        ):
            raise TypeError
        subnets = sorted(str(item) for item in network["subnet_ids"])
        security_groups = sorted(str(item) for item in network["security_group_ids"])
        window = int(config["completion_window_seconds"])
    except (KeyError, TypeError, ValueError) as error:
        raise ContractRejection("CONFIG_LAUNCH_FIELDS_INVALID") from error
    if (
        not cluster_arn
        or not task_definition_arn
        or not launch_role_arn
        or not deployment_identity_id
    ):
        raise ContractRejection("CONFIG_LAUNCH_FIELDS_INVALID")
    if (
        expected_launch_role_arn is not None
        and launch_role_arn != expected_launch_role_arn
    ):
        raise ContractRejection("CONFIG_LAUNCH_ROLE_MISMATCH")
    if not subnets or not security_groups or window < 1:
        raise ContractRejection("CONFIG_LAUNCH_FIELDS_INVALID")
    reduced_at = _timestamp(now, "PROCESSOR_TIME_INVALID")
    first_request = reduced_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    retry_seconds = min(max(1, int(safe_retry_seconds)), 3600, window)
    retry_deadline = (
        (reduced_at + timedelta(seconds=retry_seconds))
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    token = launch_client_token(
        str(envelope["job_id"]), expected_id, snapshot.config_version, 0
    )
    digest = hashlib.sha256(raw).hexdigest()
    attempt = {
        "keys": {"pk": f"JOB#{snapshot.job_id}", "sk": f"ATTEMPT#{expected_id}#0"},
        "record_type": "TASK_ATTEMPT",
        "schema_version": "1.0.0",
        "job_id": snapshot.job_id,
        "occurrence_id": expected_id,
        "config_version": snapshot.config_version,
        "schedule_generation": snapshot.schedule_generation,
        "correlation": {
            "cluster_arn": cluster_arn,
            "config_version": snapshot.config_version,
            "occurrence_id": expected_id,
        },
        "attempt_no": 0,
        "client_token": token,
        "launch_state": "PENDING",
        "first_request_at": first_request,
        "safe_retry_deadline": retry_deadline,
        "recovery": {
            "authoritatively_recovered": False,
            "recovered_at": None,
            "recovered_task_arn": None,
        },
        "task_arn": None,
        "conflict_evidence_ids": [],
        "task_definition_arn": task_definition_arn,
        "launch_role_arn": launch_role_arn,
        "deployment_identity_id": deployment_identity_id,
        "platform_cell": processor_identity.split(":", 1)[0],
        "subnet_ids": subnets,
        "security_group_ids": security_groups,
    }
    processed = {
        "pk": "EVENT#scheduler",
        "sk": str(envelope["producer_event_id"]),
        "record_type": "PROCESSED_EVENT",
        "schema_version": "1.0.0",
        "producer_id": "scheduler",
        "producer_event_id": str(envelope["producer_event_id"]),
        "event_digest": digest,
        "event_type": "occurrence.launch.v1",
        "job_id": snapshot.job_id,
        "occurrence_id": expected_id,
        "accepted_at": first_request,
        "disposition": "ACCEPTED",
        "processor_deployment_identity_id": processor_identity,
    }
    return PreparedLaunch(attempt, processed, digest, token)


def prepare_manual_rerun(
    envelope: Mapping[str, Any],
    snapshot_item: Mapping[str, Any] | None,
    original_item: Mapping[str, Any] | None,
    *,
    processor_identity: str,
    now: str,
    expected_owner_generation: int | None = None,
    expected_environment: str | None = None,
) -> PreparedLaunch:
    """Prepare one handler-authorized synthetic attempt from immutable bindings."""

    if not isinstance(envelope, Mapping) or snapshot_item is None:
        raise ContractRejection("MANUAL_ENVELOPE_INVALID")
    required = {
        "schema_version",
        "event_type",
        "producer_id",
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "payload",
        "payload_hash",
        "emitted_at",
    }
    if set(envelope) - (required | {"trace_context"}) or any(
        field not in envelope for field in required
    ):
        raise ContractRejection("MANUAL_ENVELOPE_INVALID")
    if (
        envelope.get("schema_version") != "1.0.0"
        or envelope.get("event_type") != "command.authorized.v1"
        or envelope.get("producer_id") != "command-handler"
    ):
        raise ContractRejection("MANUAL_COMMAND_AUTHORITY")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ContractRejection("MANUAL_PAYLOAD_INVALID")
    command = payload.get("command")
    authorization_record_id = payload.get("authorization_record_id")
    if (
        not isinstance(command, Mapping)
        or command.get("form") != "canonical"
        or command.get("command_type") != "RERUN"
        or not isinstance(authorization_record_id, str)
    ):
        raise ContractRejection("MANUAL_COMMAND_INVALID")
    if hashlib.sha256(canonical_json_bytes(dict(payload))).hexdigest() != envelope.get(
        "payload_hash"
    ):
        raise ContractRejection("MANUAL_PAYLOAD_HASH_MISMATCH")
    for field in (
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "producer_event_id",
        "emitted_at",
    ):
        if not isinstance(envelope.get(field), str) or not envelope[field]:
            raise ContractRejection("MANUAL_ENVELOPE_INVALID")
    command_fields = (
        "command_id",
        "job_id",
        "scheduled_time",
        "original_occurrence_id",
        "replay_of_occurrence_id",
        "synthetic_occurrence_id",
        "config_version",
        "schedule_generation",
        "deployment_identity_id",
        "actor",
        "approval_reference",
        "reason",
        "expected_duplicate_effects",
        "verification_plan",
        "compensation_acknowledged",
        "approval_expires_at",
    )
    if any(field not in command for field in command_fields):
        raise ContractRejection("MANUAL_COMMAND_INVALID")
    if _timestamp(
        str(command["approval_expires_at"]), "MANUAL_APPROVAL_EXPIRY_INVALID"
    ) <= _timestamp(now, "PROCESSOR_TIME_INVALID"):
        raise ContractRejection("MANUAL_APPROVAL_EXPIRED")
    if command["replay_of_occurrence_id"] != command["original_occurrence_id"]:
        raise ContractRejection("MANUAL_ORIGINAL_LINK_MISMATCH")
    if (
        command["job_id"] != envelope["job_id"]
        or command["config_version"] != envelope["config_version"]
        or command["schedule_generation"] != envelope["schedule_generation"]
        or command["synthetic_occurrence_id"] != envelope["occurrence_id"]
        or command["scheduled_time"] != envelope["scheduled_time"]
        or command["command_id"] != envelope["producer_event_id"]
        or command["compensation_acknowledged"] is not True
    ):
        raise ContractRejection("MANUAL_COMMAND_BINDING_MISMATCH")
    original = _plain_item(original_item) if original_item is not None else None
    if original is None:
        raise ContractRejection("MANUAL_ORIGINAL_NOT_FOUND")
    terminal_states = {"SUCCEEDED", "FAILED", "MISSED", "OVERDUE"}
    if original.get("state") not in terminal_states:
        raise ContractRejection("MANUAL_ORIGINAL_NOT_TERMINAL")
    if any(
        original.get(field) != command[field]
        for field in (
            "job_id",
            "config_version",
            "schedule_generation",
        )
    ) or (
        original.get("occurrence_id") != command["original_occurrence_id"]
        or original.get("deployment_identity_id")
        not in {None, command["deployment_identity_id"]}
    ):
        raise ContractRejection("MANUAL_ORIGINAL_BINDING_MISMATCH")
    snapshot = ConfigSnapshot.from_item(snapshot_item)
    if snapshot.materialization_state != "MATERIALIZED":
        raise ContractRejection("CONFIG_NOT_MATERIALIZED")
    if snapshot.config_hash != snapshot.config_version:
        raise ContractRejection("CONFIG_VERSION_HASH_MISMATCH")
    config = snapshot.config()
    if (
        snapshot.job_id != command["job_id"]
        or snapshot.config_version != command["config_version"]
        or snapshot.schedule_generation != command["schedule_generation"]
        or config.get("job_id") != command["job_id"]
        or config.get("schedule_generation") != command["schedule_generation"]
        or config.get("deployment_identity_id") != command["deployment_identity_id"]
    ):
        raise ContractRejection("MANUAL_CONFIG_BINDING_MISMATCH")
    if (
        expected_owner_generation is not None
        and snapshot.owner_generation != expected_owner_generation
    ):
        raise ContractRejection("CONFIG_OWNER_GENERATION_MISMATCH")
    if (
        expected_environment is not None
        and config.get("environment") != expected_environment
    ):
        raise ContractRejection("MANUAL_ENVIRONMENT_SCOPE")
    if str(config.get("environment", "")).lower() in {"p" + "rod", "p" + "roduction"}:
        raise ContractRejection("MANUAL_PRODUCTION_TARGET")
    try:
        cluster_arn = str(config["cluster_arn"])
        task_definition_arn = str(config["task_definition_arn"])
        launch_role_arn = str(config["role_arns"]["launch"])
        network = config["network"]
        if not isinstance(network, Mapping):
            raise ValueError("network")
        subnets = sorted(str(item) for item in network["subnet_ids"])
        security_groups = sorted(str(item) for item in network["security_group_ids"])
        window = int(config["completion_window_seconds"])
    except (KeyError, TypeError, ValueError) as error:
        raise ContractRejection("CONFIG_LAUNCH_FIELDS_INVALID") from error
    if (
        not cluster_arn
        or not task_definition_arn
        or not launch_role_arn
        or not subnets
        or not security_groups
        or window < 1
    ):
        raise ContractRejection("CONFIG_LAUNCH_FIELDS_INVALID")
    scheduled = _timestamp(str(command["scheduled_time"]), "SCHEDULED_TIME_INVALID")
    reduced_at = _timestamp(now, "PROCESSOR_TIME_INVALID")
    if reduced_at > scheduled + timedelta(seconds=window):
        raise ContractRejection("MANUAL_SAFE_LAUNCH_WINDOW_EXPIRED")
    deadline = (
        (scheduled + timedelta(seconds=window))
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    first_request = reduced_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    retry_deadline = (
        (reduced_at + timedelta(seconds=min(max(1, window), 3600)))
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    synthetic = str(command["synthetic_occurrence_id"])
    token = launch_client_token(snapshot.job_id, synthetic, snapshot.config_version, 0)
    raw = canonical_json_bytes(dict(envelope))
    digest = hashlib.sha256(raw).hexdigest()
    occurrence = {
        "keys": {"pk": f"JOB#{snapshot.job_id}", "sk": f"OCCURRENCE#{synthetic}"},
        "record_type": "OCCURRENCE",
        "schema_version": "1.0.0",
        "job_id": snapshot.job_id,
        "config_version": snapshot.config_version,
        "schedule_generation": snapshot.schedule_generation,
        "occurrence_id": synthetic,
        "scheduled_time": str(command["scheduled_time"]),
        "deadline_at": deadline,
        "deadline_kind": "COMPLETION",
        "deadline_key": f"DEADLINE#0#{deadline[:19]}.000Z",
        "deadline_sort": f"{deadline}#{synthetic}#COMPLETION",
        "state": "EXPECTED",
        "started_at": None,
        "completed_at": None,
        "exit_code": None,
        "error_code": None,
        "operator_safe_error_reason": None,
        "evidence_ids": [digest],
        "replay_of_occurrence_id": str(command["replay_of_occurrence_id"]),
        "command_id": str(command["command_id"]),
        "authorization_record_id": authorization_record_id,
        "actor": str(command["actor"]),
        "approval_reference": str(command["approval_reference"]),
        "expected_duplicate_effects": str(command["expected_duplicate_effects"]),
        "verification_plan": str(command["verification_plan"]),
        "compensation_acknowledged": True,
        "deployment_identity_id": str(command["deployment_identity_id"]),
        "overlap_policy": str(config.get("overlap_policy", "APPLICATION_LOCKED")),
    }
    attempt = {
        "keys": {"pk": f"JOB#{snapshot.job_id}", "sk": f"ATTEMPT#{synthetic}#0"},
        "record_type": "TASK_ATTEMPT",
        "schema_version": "1.0.0",
        "job_id": snapshot.job_id,
        "occurrence_id": synthetic,
        "config_version": snapshot.config_version,
        "schedule_generation": snapshot.schedule_generation,
        "correlation": {
            "cluster_arn": cluster_arn,
            "config_version": snapshot.config_version,
            "occurrence_id": synthetic,
        },
        "attempt_no": 0,
        "client_token": token,
        "launch_state": "PENDING",
        "first_request_at": first_request,
        "safe_retry_deadline": retry_deadline,
        "recovery": {
            "authoritatively_recovered": False,
            "recovered_at": None,
            "recovered_task_arn": None,
        },
        "task_arn": None,
        "conflict_evidence_ids": [],
        "task_definition_arn": task_definition_arn,
        "launch_role_arn": launch_role_arn,
        "deployment_identity_id": str(command["deployment_identity_id"]),
        "platform_cell": processor_identity.split(":", 1)[0],
        "subnet_ids": subnets,
        "security_group_ids": security_groups,
        "replay_of_occurrence_id": str(command["replay_of_occurrence_id"]),
        "command_id": str(command["command_id"]),
    }
    processed = {
        "pk": "EVENT#command-handler",
        "sk": str(command["command_id"]),
        "record_type": "PROCESSED_EVENT",
        "schema_version": "1.0.0",
        "producer_id": "command-handler",
        "producer_event_id": str(command["command_id"]),
        "event_digest": digest,
        "event_type": "command.authorized.v1",
        "job_id": snapshot.job_id,
        "occurrence_id": synthetic,
        "accepted_at": first_request,
        "disposition": "ACCEPTED",
        "processor_deployment_identity_id": processor_identity,
    }
    return PreparedLaunch(attempt, processed, digest, token, occurrence)


def prepare_correlation(
    envelope: Mapping[str, Any],
    snapshot_item: Mapping[str, Any] | None,
    *,
    processor_identity: str,
    expected_owner_generation: int | None = None,
) -> PreparedCorrelation:
    """Validate ECS/completion evidence before ledger mutation."""

    if not isinstance(envelope, Mapping) or snapshot_item is None:
        raise ContractRejection("CORRELATION_ENVELOPE_INVALID")
    required = {
        "schema_version",
        "event_type",
        "producer_id",
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "payload",
        "payload_hash",
        "emitted_at",
    }
    if set(envelope) - (required | {"trace_context"}) or any(
        key not in envelope for key in required
    ):
        raise ContractRejection("CORRELATION_ENVELOPE_INVALID")
    if envelope["schema_version"] != "1.0.0":
        raise ContractRejection("UNSUPPORTED_SCHEMA_VERSION")
    expected_producer = {
        "task.state.v1": "ecs",
        "completion.observed.v1": "log-ingestor",
    }
    event_type = envelope.get("event_type")
    if (
        event_type not in expected_producer
        or envelope.get("producer_id") != expected_producer[event_type]
    ):
        raise ContractRejection("CORRELATION_PRODUCER_INVALID")
    for field in (
        "producer_event_id",
        "job_id",
        "config_version",
        "schedule_generation",
        "occurrence_id",
        "scheduled_time",
        "emitted_at",
        "payload_hash",
    ):
        if not isinstance(envelope[field], str) or not envelope[field]:
            raise ContractRejection("CORRELATION_ENVELOPE_INVALID")
    payload = envelope["payload"]
    if (
        not isinstance(payload, dict)
        or hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        != envelope["payload_hash"]
    ):
        raise ContractRejection("CORRELATION_PAYLOAD_HASH_MISMATCH")
    scheduled_at = _timestamp(envelope["scheduled_time"], "CORRELATION_TIME_INVALID")
    _timestamp(envelope["emitted_at"], "CORRELATION_TIME_INVALID")
    expected_id = occurrence_id(
        str(envelope["job_id"]),
        str(envelope["schedule_generation"]),
        str(int(scheduled_at.timestamp() // 60)),
    )
    if envelope["occurrence_id"] != expected_id:
        raise ContractRejection("OCCURRENCE_ID_MISMATCH")
    snapshot = ConfigSnapshot.from_item(snapshot_item)
    if (
        snapshot.materialization_state != "MATERIALIZED"
        or snapshot.config_hash != snapshot.config_version
    ):
        raise ContractRejection("CONFIG_NOT_MATERIALIZED")
    config = snapshot.config()
    if (
        snapshot.job_id != envelope["job_id"]
        or snapshot.config_version != envelope["config_version"]
        or snapshot.schedule_generation != envelope["schedule_generation"]
        or config.get("job_id") != envelope["job_id"]
        or config.get("schedule_generation") != envelope["schedule_generation"]
    ):
        raise ContractRejection("CONFIG_IDENTITY_MISMATCH")
    if (
        expected_owner_generation is not None
        and snapshot.owner_generation != expected_owner_generation
    ):
        raise ContractRejection("CONFIG_OWNER_GENERATION_MISMATCH")
    digest = hashlib.sha256(canonical_json_bytes(dict(envelope))).hexdigest()
    processed = {
        "pk": f"EVENT#{envelope['producer_id']}",
        "sk": str(envelope["producer_event_id"]),
        "record_type": "PROCESSED_EVENT",
        "schema_version": "1.0.0",
        "producer_id": envelope["producer_id"],
        "producer_event_id": envelope["producer_event_id"],
        "event_digest": digest,
        "event_type": event_type,
        "job_id": envelope["job_id"],
        "occurrence_id": envelope["occurrence_id"],
        "accepted_at": envelope["emitted_at"],
        "disposition": "ACCEPTED",
        "processor_deployment_identity_id": processor_identity,
    }
    return PreparedCorrelation(processed, digest, payload)
