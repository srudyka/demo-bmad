"""Pure validation and deterministic record construction for occurrence state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from .contracts import canonical_json_bytes, materializer_event_id, occurrence_id


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
