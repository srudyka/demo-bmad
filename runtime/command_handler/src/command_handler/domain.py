"""Pure authorization and identity rules for operator commands."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Callable, Mapping


class CommandRejected(ValueError):
    """A permanent, secret-safe command rejection."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CallerContext:
    actor: str
    session_id: str
    cell_id: str
    account_id: str
    region: str
    break_glass: bool = False


@dataclass(frozen=True)
class OccurrenceBinding:
    job_id: str
    scheduled_time: str
    original_occurrence_id: str
    config_version: str
    deployment_identity_id: str
    terminal: bool = True
    cell_id: str | None = None
    account_id: str | None = None
    region: str | None = None


@dataclass(frozen=True)
class Authorization:
    command: dict[str, object]
    authorization_record_id: str
    audit: dict[str, object]


_JOB_ID = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _uuid7(value: str, code: str) -> None:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise CommandRejected(code) from error
    if value != value.lower() or parsed.version != 7 or parsed.variant != uuid.RFC_4122:
        raise CommandRejected(code)


def _new_uuid7() -> str:
    return str(uuid.uuid7())


def manual_identity_bytes(
    job_id: str, original_occurrence_id: str, config_version: str, command_id: str
) -> bytes:
    if not _JOB_ID.fullmatch(job_id):
        raise CommandRejected("COMMAND_JOB_ID")
    for value, code in (
        (original_occurrence_id, "COMMAND_ORIGINAL_OCCURRENCE_ID"),
        (config_version, "COMMAND_CONFIG_VERSION"),
    ):
        if not _SHA256.fullmatch(value):
            raise CommandRejected(code)
    _uuid7(command_id, "COMMAND_ID")
    return f"occurrence/manual/v1\n{job_id}\n{original_occurrence_id}\n{config_version}\n{command_id}".encode()


def manual_occurrence_id(
    job_id: str, original_occurrence_id: str, config_version: str, command_id: str
) -> str:
    return sha256(
        manual_identity_bytes(
            job_id, original_occurrence_id, config_version, command_id
        )
    ).hexdigest()


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise CommandRejected("COMMAND_SCHEDULED_TIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CommandRejected("COMMAND_SCHEDULED_TIME") from error
    if parsed.tzinfo is None:
        raise CommandRejected("COMMAND_SCHEDULED_TIME")
    return parsed.astimezone(UTC)


def authorize_operator_request(
    request: Mapping[str, object],
    caller: CallerContext,
    *,
    lookup: Callable[[str, str], OccurrenceBinding | None],
    approve: Callable[[str, str, str], bool],
    now: datetime | None = None,
    command_id_factory: Callable[[], str] = _new_uuid7,
    expected_cell_id: str | None = None,
    expected_account_id: str | None = None,
    expected_region: str | None = None,
) -> Authorization:
    """Resolve an operator request into one canonical, attributable command.

    The caller supplies only a lookup and approval reference. All occurrence,
    deployment, command, and evidence identities are resolved or generated here.
    """
    forbidden = {
        "occurrence_id",
        "original_occurrence_id",
        "synthetic_occurrence_id",
        "command_id",
        "producer_id",
        "evidence",
    }
    if forbidden.intersection(request):
        raise CommandRejected("COMMAND_CALLER_OWNED_ID")
    required = {
        "schema_version",
        "form",
        "request_id",
        "job_id",
        "scheduled_time",
        "actor",
        "approval_reference",
        "reason",
    }
    if set(request) - required - {
        "command_type",
        "compensation_acknowledged",
    } or not required.issubset(request):
        raise CommandRejected("COMMAND_REQUEST_SHAPE")
    if request["form"] != "operator_request" or request["schema_version"] != "1.0.0":
        raise CommandRejected("COMMAND_SCHEMA_VERSION")
    request_id = request["request_id"]
    if not isinstance(request_id, str):
        raise CommandRejected("COMMAND_REQUEST_ID")
    _uuid7(request_id, "COMMAND_REQUEST_ID")
    job_id = request["job_id"]
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise CommandRejected("COMMAND_JOB_ID")
    scheduled_time = request["scheduled_time"]
    if not isinstance(scheduled_time, str):
        raise CommandRejected("COMMAND_SCHEDULED_TIME")
    scheduled = _timestamp(scheduled_time)
    actor = request["actor"]
    approval = request["approval_reference"]
    reason = request["reason"]
    if (
        actor != caller.actor
        or not isinstance(approval, str)
        or not approval
        or not isinstance(reason, str)
        or not reason
        or len(reason) > 1024
    ):
        raise CommandRejected(
            "COMMAND_CALLER_AUTHORITY"
            if actor != caller.actor
            else "COMMAND_REQUEST_FIELD"
        )
    command_type = request.get("command_type", "RERUN")
    if not isinstance(command_type, str) or command_type not in {
        "RERUN",
        "REPLAY",
        "DISABLE",
        "RECOVER",
    }:
        raise CommandRejected("COMMAND_TYPE")
    compensation = request.get("compensation_acknowledged", False)
    if not isinstance(compensation, bool):
        raise CommandRejected("COMMAND_COMPENSATION_ACK")
    if command_type in {"REPLAY", "DISABLE", "RECOVER"} and not compensation:
        raise CommandRejected("COMMAND_COMPENSATION_ACK")
    if not approve(approval, caller.actor, caller.session_id):
        raise CommandRejected("COMMAND_APPROVAL_INVALID")
    binding = lookup(job_id, scheduled_time)
    if (
        binding is None
        or binding.job_id != job_id
        or binding.scheduled_time != scheduled_time
    ):
        raise CommandRejected("COMMAND_OCCURRENCE_NOT_FOUND")
    if not isinstance(binding.terminal, bool) or not binding.terminal:
        raise CommandRejected("COMMAND_NONTERMINAL_OCCURRENCE")
    if expected_cell_id is not None and caller.cell_id != expected_cell_id:
        raise CommandRejected("COMMAND_CELL_SCOPE")
    if expected_account_id is not None and caller.account_id != expected_account_id:
        raise CommandRejected("COMMAND_ACCOUNT_SCOPE")
    if expected_region is not None and caller.region != expected_region:
        raise CommandRejected("COMMAND_REGION_SCOPE")
    for actual, expected, code in (
        (binding.cell_id, expected_cell_id, "COMMAND_CELL_SCOPE"),
        (binding.account_id, expected_account_id, "COMMAND_ACCOUNT_SCOPE"),
        (binding.region, expected_region, "COMMAND_REGION_SCOPE"),
    ):
        if expected is not None and actual != expected:
            raise CommandRejected(code)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    if scheduled > current + timedelta(minutes=5) or scheduled < current - timedelta(
        days=1
    ):
        raise CommandRejected("COMMAND_STALE_OR_FUTURE")
    if caller.break_glass and not approval.startswith("BG-"):
        raise CommandRejected("COMMAND_BREAK_GLASS_APPROVAL")
    command_id = command_id_factory()
    _uuid7(command_id, "COMMAND_ID")
    synthetic = manual_occurrence_id(
        job_id, binding.original_occurrence_id, binding.config_version, command_id
    )
    created_at = (
        (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
    )
    command = {
        "schema_version": "1.0.0",
        "form": "canonical",
        "command_id": command_id,
        "command_type": command_type,
        "scheduled_time": scheduled_time,
        "job_id": job_id,
        "original_occurrence_id": binding.original_occurrence_id,
        "synthetic_occurrence_id": synthetic,
        "config_version": binding.config_version,
        "deployment_identity_id": binding.deployment_identity_id,
        "actor": caller.actor,
        "approval_reference": approval,
        "reason": reason,
        "verification_reference": f"approval:{approval}",
        "compensation_acknowledged": compensation,
    }
    return Authorization(
        command=command,
        authorization_record_id=_new_uuid7(),
        audit={
            "command_id": command_id,
            "request_id": request_id,
            "actor": caller.actor,
            "session_id": caller.session_id,
            "approval_reference": approval,
            "cell_id": caller.cell_id,
            "account_id": caller.account_id,
            "region": caller.region,
            "created_at": created_at,
            "break_glass": caller.break_glass,
        },
    )
