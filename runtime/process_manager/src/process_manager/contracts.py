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
