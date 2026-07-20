"""Pure deadline-window selection, checkpoint, and evidence primitives."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable, Mapping

import rfc8785


class DeadlineRejection(ValueError):
    """A bounded, record-local deadline contract rejection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def canonical_json_bytes(value: Any) -> bytes:
    return rfc8785.dumps(value)


def _time(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DeadlineRejection("DEADLINE_TIME_INVALID")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise DeadlineRejection("DEADLINE_TIME_INVALID") from error
    if parsed.tzinfo != UTC or parsed.microsecond % 1000:
        raise DeadlineRejection("DEADLINE_TIME_INVALID")
    return parsed


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


@dataclass(frozen=True)
class DeadlineCandidate:
    """The minimum authoritative occurrence projection needed by the scanner."""

    job_id: str
    config_version: str
    schedule_generation: str
    occurrence_id: str
    scheduled_time: str
    deadline_at: str
    deadline_kind: str
    state: str
    deadline_key: str
    deadline_sort: str

    @classmethod
    def from_item(cls, item: Mapping[str, object]) -> "DeadlineCandidate":
        required = (
            "job_id", "config_version", "schedule_generation", "occurrence_id",
            "scheduled_time", "deadline_at", "deadline_kind", "state", "deadline_key", "deadline_sort",
        )
        if any(not isinstance(item.get(field), str) for field in required):
            raise DeadlineRejection("DEADLINE_CANDIDATE_INVALID")
        kind = str(item["deadline_kind"])
        if kind not in {"START", "COMPLETION"}:
            raise DeadlineRejection("DEADLINE_KIND_INVALID")
        _time(str(item["deadline_at"]))
        _time(str(item["scheduled_time"]))
        state = str(item["state"])
        if state not in {"EXPECTED", "STARTED"}:
            raise DeadlineRejection("DEADLINE_STATE_INVALID")
        deadline_key = str(item["deadline_key"])
        key_parts = deadline_key.split("#", 2)
        if len(key_parts) != 3 or key_parts[0] != "DEADLINE" or key_parts[2] != deadline_bucket(str(item["deadline_at"])):
            raise DeadlineRejection("DEADLINE_KEY_INVALID")
        expected_sort = f"{item['deadline_at']}#{item['occurrence_id']}#{item['deadline_kind']}"
        if item["deadline_sort"] != expected_sort:
            raise DeadlineRejection("DEADLINE_SORT_INVALID")
        return cls(*(str(item[field]) for field in required))


@dataclass(frozen=True)
class ScannerCheckpoint:
    watermark: str
    position: str

    @classmethod
    def initial(cls) -> "ScannerCheckpoint":
        return cls("1970-01-01T00:00:00.000Z", "")

    def advance(self, watermark: str, position: str) -> "ScannerCheckpoint":
        current = _time(self.watermark)
        candidate = _time(watermark)
        if candidate < current or (candidate == current and position < self.position):
            raise DeadlineRejection("CHECKPOINT_NOT_MONOTONIC")
        return ScannerCheckpoint(timestamp(candidate), position)


def deadline_bucket(deadline_at: str, *, bucket_seconds: int = 60) -> str:
    value = _time(deadline_at)
    if bucket_seconds < 60 or bucket_seconds > 3600 or bucket_seconds % 60:
        raise DeadlineRejection("DEADLINE_BUCKET_INVALID")
    epoch = int(value.timestamp()) // bucket_seconds * bucket_seconds
    return timestamp(datetime.fromtimestamp(epoch, UTC))


def deadline_index_key(deadline_at: str, shard: str, *, bucket_seconds: int = 60) -> str:
    if not shard or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in shard):
        raise DeadlineRejection("DEADLINE_SHARD_INVALID")
    return f"DEADLINE#{shard}#{deadline_bucket(deadline_at, bucket_seconds=bucket_seconds)}"


def deadline_event_id(candidate: DeadlineCandidate) -> str:
    identity = "deadline/v1\n{}\n{}\n{}\n{}\n{}\n{}".format(
        candidate.job_id,
        candidate.schedule_generation,
        candidate.occurrence_id,
        candidate.deadline_kind,
        candidate.deadline_at,
        candidate.config_version,
    )
    return hashlib.sha256(identity.encode("ascii")).hexdigest()


def due_candidates(
    candidates: Iterable[DeadlineCandidate],
    *,
    now: str,
    lookback_seconds: int,
    maximum_lateness_seconds: int,
) -> list[DeadlineCandidate]:
    current = _time(now)
    if lookback_seconds < 0 or maximum_lateness_seconds < 0:
        raise DeadlineRejection("DEADLINE_WINDOW_INVALID")
    lower = current - timedelta(seconds=lookback_seconds)
    upper = current
    result = [
        candidate for candidate in candidates
        if lower <= _time(candidate.deadline_at) <= upper
        and current - _time(candidate.deadline_at) <= timedelta(seconds=maximum_lateness_seconds)
        and candidate.state not in {"SUCCEEDED", "FAILED", "MISSED", "AMBIGUOUS"}
    ]
    return sorted(result, key=lambda item: (item.deadline_at, item.occurrence_id, item.deadline_kind))


def build_deadline_envelope(
    candidate: DeadlineCandidate,
    *,
    scanner_watermark: str,
    emitted_at: str,
) -> dict[str, object]:
    _time(scanner_watermark)
    _time(emitted_at)
    payload = {
        "deadline_kind": candidate.deadline_kind,
        "deadline_at": candidate.deadline_at,
        "scanner_watermark": scanner_watermark,
    }
    return {
        "schema_version": "1.0.0",
        "event_type": "occurrence.deadline-reached.v1",
        "producer_id": "deadline-scanner",
        "producer_event_id": deadline_event_id(candidate),
        "job_id": candidate.job_id,
        "config_version": candidate.config_version,
        "schedule_generation": candidate.schedule_generation,
        "occurrence_id": candidate.occurrence_id,
        "scheduled_time": candidate.scheduled_time,
        "emitted_at": emitted_at,
        "payload": payload,
        "payload_hash": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
        "x-deadline-key": candidate.deadline_key,
    }
