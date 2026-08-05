"""Pure CloudWatch Logs subscription decoding and completion evidence shaping."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable, Any

from .canonical import canonical_json_bytes


class LogIngestionError(ValueError):
    """Permanent, secret-safe completion-log rejection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CompletionBinding:
    job_id: str
    config_version: str
    schedule_generation: str
    occurrence_id: str
    scheduled_time: str
    task_arn: str
    attempt_no: int
    log_group: str
    log_stream: str


@dataclass(frozen=True)
class CloudWatchLogBatch:
    log_group: str
    log_stream: str
    messages: tuple[tuple[str, int], ...]


_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_JOB_ID = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$"
)
_MACHINE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_UUID_V7 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_ARN = re.compile(r"^arn:[A-Za-z0-9-]+:[A-Za-z0-9-]+:[A-Za-z0-9-]*:[0-9]{12}:.+$")


def decode_subscription_record(record: Mapping[str, Any]) -> CloudWatchLogBatch:
    """Decode the bounded AWS subscription envelope without logging its contents."""

    try:
        awslogs = record["awslogs"]
        encoded = awslogs["data"] if isinstance(awslogs, Mapping) else None
        if not isinstance(encoded, str) or len(encoded) > 1_500_000:
            raise LogIngestionError("LOG_SUBSCRIPTION_DATA_INVALID")
        raw = gzip.decompress(base64.b64decode(encoded, validate=True))
        if len(raw) > 1_048_576:
            raise LogIngestionError("LOG_SUBSCRIPTION_DATA_TOO_LARGE")
        envelope = json.loads(raw)
        if (
            not isinstance(envelope, dict)
            or envelope.get("messageType") != "DATA_MESSAGE"
        ):
            raise LogIngestionError("LOG_SUBSCRIPTION_TYPE_INVALID")
        log_group = envelope.get("logGroup")
        log_stream = envelope.get("logStream")
        events = envelope.get("logEvents")
        if (
            not isinstance(log_group, str)
            or not isinstance(log_stream, str)
            or not isinstance(events, list)
            or len(events) > 1000
        ):
            raise LogIngestionError("LOG_SUBSCRIPTION_SHAPE_INVALID")
        messages: list[tuple[str, int]] = []
        for event in events:
            if not isinstance(event, Mapping) or not isinstance(
                event.get("message"), str
            ):
                raise LogIngestionError("LOG_EVENT_INVALID")
            timestamp = event.get("timestamp")
            if not isinstance(timestamp, int):
                raise LogIngestionError("LOG_EVENT_TIME_INVALID")
            messages.append((event["message"], timestamp))
        return CloudWatchLogBatch(log_group, log_stream, tuple(messages))
    except LogIngestionError:
        raise
    except (KeyError, TypeError, ValueError, OSError, EOFError) as error:
        raise LogIngestionError("LOG_SUBSCRIPTION_DECODE_FAILED") from error


def _reject_secrets(value: Mapping[str, Any]) -> None:
    encoded = canonical_json_bytes(dict(value)).decode("utf-8").lower()
    if any(token in encoded for token in ("password", "secret", "access_key", "token")):
        raise LogIngestionError("COMPLETION_SECRET_CONTENT")


def build_completion_envelopes(
    batch: CloudWatchLogBatch,
    *,
    task_lookup: Callable[[str, str, str], CompletionBinding | None],
) -> list[dict[str, object]]:
    """Parse only platform-shaped completion markers; identity remains AWS-owned."""

    envelopes: list[dict[str, object]] = []
    for message, timestamp_ms in batch.messages:
        if len(message.encode("utf-8")) > 16_384:
            raise LogIngestionError("COMPLETION_MESSAGE_TOO_LARGE")
        try:
            value = json.loads(message)
        except json.JSONDecodeError as error:
            raise LogIngestionError("COMPLETION_JSON_INVALID") from error
        if not isinstance(value, dict):
            raise LogIngestionError("COMPLETION_JSON_INVALID")
        _reject_secrets(value)
        required = {
            "schema_version",
            "marker_id",
            "asserted_job_id",
            "asserted_occurrence_id",
            "asserted_config_version",
            "asserted_attempt_no",
            "asserted_task_arn",
            "completed_at",
            "marker_status",
            "exit_code_assertion",
            "error_code",
        }
        if set(value) != required or value.get("schema_version") != "1.0.0":
            raise LogIngestionError("COMPLETION_SCHEMA_INVALID")
        if (
            not isinstance(value.get("marker_id"), str)
            or _UUID_V7.fullmatch(value["marker_id"]) is None
            or not isinstance(value.get("asserted_job_id"), str)
            or _JOB_ID.fullmatch(value["asserted_job_id"]) is None
            or not isinstance(value.get("asserted_occurrence_id"), str)
            or _SHA256.fullmatch(value["asserted_occurrence_id"]) is None
            or not isinstance(value.get("asserted_config_version"), str)
            or _SHA256.fullmatch(value["asserted_config_version"]) is None
            or value.get("asserted_attempt_no") != 0
            or not isinstance(value.get("completed_at"), str)
            or _TIMESTAMP.fullmatch(value["completed_at"]) is None
            or not isinstance(value.get("marker_status"), str)
            or value["marker_status"] not in {"SUCCESS", "FAILURE"}
            or (
                value.get("exit_code_assertion") is not None
                and (
                    not isinstance(value.get("exit_code_assertion"), int)
                    or isinstance(value.get("exit_code_assertion"), bool)
                )
            )
            or (
                value.get("error_code") is not None
                and (
                    not isinstance(value.get("error_code"), str)
                    or _MACHINE_CODE.fullmatch(value["error_code"]) is None
                )
            )
        ):
            raise LogIngestionError("COMPLETION_SCHEMA_INVALID")
        task_arn = value.get("asserted_task_arn")
        if not isinstance(task_arn, str) or _ARN.fullmatch(task_arn) is None:
            raise LogIngestionError("COMPLETION_TASK_INVALID")
        binding = task_lookup(batch.log_group, batch.log_stream, task_arn)
        if binding is None:
            raise LogIngestionError("COMPLETION_TASK_MAPPING_PENDING")
        stream_task_id = batch.log_stream.rsplit("/", 1)[-1]
        if not stream_task_id or not binding.task_arn.endswith("/" + stream_task_id):
            raise LogIngestionError("COMPLETION_LOG_STREAM_TASK_MISMATCH")
        if (
            value.get("asserted_job_id") != binding.job_id
            or value.get("asserted_occurrence_id") != binding.occurrence_id
            or value.get("asserted_config_version") != binding.config_version
            or value.get("asserted_attempt_no") != binding.attempt_no
        ):
            raise LogIngestionError("COMPLETION_IDENTITY_MISMATCH")
        try:
            completed_at = datetime.fromisoformat(
                value["completed_at"].replace("Z", "+00:00")
            )
            scheduled_at = datetime.fromisoformat(
                binding.scheduled_time.replace("Z", "+00:00")
            )
        except ValueError as error:
            raise LogIngestionError("COMPLETION_TIME_INVALID") from error
        if completed_at.tzinfo != timezone.utc or completed_at < scheduled_at:
            raise LogIngestionError("COMPLETION_TIME_INVALID")
        if (completed_at - scheduled_at).total_seconds() > 86400:
            raise LogIngestionError("COMPLETION_OUT_OF_WINDOW")
        raw = canonical_json_bytes(value)
        payload = {
            "log_group": batch.log_group,
            "log_stream": batch.log_stream,
            "completion": value,
        }
        envelopes.append(
            {
                "schema_version": "1.0.0",
                "event_type": "completion.observed.v1",
                "producer_id": "log-ingestor",
                "producer_event_id": hashlib.sha256(
                    b"completion/v1\n" + raw + b"\n" + str(timestamp_ms).encode()
                ).hexdigest(),
                "job_id": binding.job_id,
                "config_version": binding.config_version,
                "schedule_generation": binding.schedule_generation,
                "occurrence_id": binding.occurrence_id,
                "scheduled_time": binding.scheduled_time,
                "emitted_at": value["completed_at"],
                "payload": payload,
                "payload_hash": hashlib.sha256(
                    canonical_json_bytes(payload)
                ).hexdigest(),
            }
        )
    return envelopes
