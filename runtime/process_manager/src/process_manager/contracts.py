"""Small contract primitives bundled with the Process Manager artifact."""

from __future__ import annotations

import hashlib
import unicodedata
from typing import Any

import rfc8785


class ContractViolation(ValueError):
    pass


def _profile(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > 9007199254740991:
            raise ContractViolation("CANONICAL_INTEGER_OUT_OF_RANGE")
        return
    if isinstance(value, float):
        raise ContractViolation("CANONICAL_FLOAT_FORBIDDEN")
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ContractViolation("CANONICAL_STRING_NOT_NFC")
        return
    if isinstance(value, list):
        for child in value:
            _profile(child)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractViolation("CANONICAL_KEY_NOT_STRING")
            _profile(key)
            _profile(child)
        return
    raise ContractViolation("CANONICAL_TYPE_FORBIDDEN")


def canonical_json_bytes(value: Any) -> bytes:
    _profile(value)
    return rfc8785.dumps(value)


def occurrence_id(job_id: str, schedule_generation: str, epoch_minute: str) -> str:
    return hashlib.sha256(
        f"occurrence/v1\n{job_id}\n{schedule_generation}\n{epoch_minute}".encode()
    ).hexdigest()


def materializer_event_id(
    job_id: str, generation: str, scheduled: str, config: str, owner: int
) -> str:
    return hashlib.sha256(
        f"materializer/v1\n{job_id}\n{generation}\n{scheduled}\n{config}\n{owner}".encode(
            "ascii"
        )
    ).hexdigest()


def scheduler_event_id(
    schedule_arn: str, scheduled: str, config: str, owner: int
) -> str:
    """Return the contract-owned Scheduler producer event identity."""

    return hashlib.sha256(
        f"scheduler/v1\n{schedule_arn}\n{scheduled}\n{config}\n{owner}".encode("ascii")
    ).hexdigest()


def deadline_event_id(
    job_id: str,
    schedule_generation: str,
    occurrence: str,
    deadline_kind: str,
    deadline_at: str,
    config_version: str,
) -> str:
    """Return the contract-owned deadline producer identity."""

    return hashlib.sha256(
        f"deadline/v1\n{job_id}\n{schedule_generation}\n{occurrence}\n{deadline_kind}\n{deadline_at}\n{config_version}".encode(
            "ascii"
        )
    ).hexdigest()


def launch_client_token(
    job_id: str, occurrence: str, config_version: str, attempt_no: int
) -> str:
    """Derive the stable ECS client token for one logical launch attempt."""

    if attempt_no != 0:
        raise ContractViolation("ATTEMPT_NO_MUST_BE_ZERO")
    return hashlib.sha256(
        f"ecs-launch/v1\n{job_id}\n{occurrence}\n{config_version}\n{attempt_no}".encode(
            "ascii"
        )
    ).hexdigest()
