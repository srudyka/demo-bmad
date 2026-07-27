"""Pure alert identity, enrichment, and secret-safe publication primitives."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .storage import canonical_json_bytes


class AlertRoutingError(ValueError):
    """A bounded, operator-safe alert routing rejection."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_ARN = re.compile(r"^arn:[a-z0-9-]+:sns:[a-z0-9-]+:[0-9]{12}:[A-Za-z0-9_.:/=-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_.:-]{0,127}$")
_SECRET_TOKENS = ("password", "secret", "access_key", "secret_key", "token")
_STATES = {"FAILED", "MISSED", "OVERDUE", "AMBIGUOUS"}
_PLANES = {
    "SCHEDULE",
    "INGRESS",
    "LAUNCH",
    "TASK",
    "COMPLETION",
    "DEADLINE",
    "ALERT_DELIVERY",
    "CELL",
}
_CANONICAL_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def occurrence_alert_identity(
    job_id: str,
    occurrence_id: str,
    state: str,
    failure_plane: str,
    policy: str = "occurrence-v1",
) -> str:
    """Return the contract-owned identity for one occurrence alert obligation."""

    values = (job_id, occurrence_id, state, failure_plane, policy)
    if not job_id or not _SHA256.fullmatch(occurrence_id) or state not in _STATES:
        raise AlertRoutingError("ALERT_IDENTITY_INVALID")
    if failure_plane not in _PLANES or not policy:
        raise AlertRoutingError("ALERT_IDENTITY_INVALID")
    return hashlib.sha256(
        ("alert/v1\n" + "\n".join(values)).encode("utf-8")
    ).hexdigest()


def notification_identity(alert_id: str, target_arn: str) -> str:
    if not _SHA256.fullmatch(alert_id) or not target_arn:
        raise AlertRoutingError("NOTIFICATION_IDENTITY_INVALID")
    return hashlib.sha256(
        ("notification/v1\n" + alert_id + "\n" + target_arn).encode("utf-8")
    ).hexdigest()


def _safe_reason(value: object) -> str:
    reason = str(value or "ALERT_REASON_UNSPECIFIED").strip().upper()
    if any(token.upper() in reason for token in _SECRET_TOKENS):
        raise AlertRoutingError("ALERT_REASON_SECRET")
    if not _REASON_CODE.fullmatch(reason):
        raise AlertRoutingError("ALERT_REASON_INVALID")
    return reason


def build_occurrence_alert(
    outbox: Mapping[str, Any],
    config_snapshot: Mapping[str, Any],
    *,
    account_id: str,
    region: str,
    environment: str,
    owner: str,
    runbook_uri: str,
) -> dict[str, Any]:
    """Project authoritative config and bounded outbox data into alert schema."""

    config = config_snapshot.get("config")
    if not isinstance(config, Mapping):
        raise AlertRoutingError("CONFIG_INVALID")
    target = config.get("notification_target_arn")
    if not isinstance(target, str) or not _ARN.fullmatch(target):
        raise AlertRoutingError("NOTIFICATION_TARGET_MISSING")
    deployment_identity = config.get("deployment_identity_id")
    if not isinstance(deployment_identity, str) or not _SHA256.fullmatch(
        deployment_identity
    ):
        raise AlertRoutingError("DEPLOYMENT_IDENTITY_INVALID")
    job_id = outbox.get("job_id")
    occurrence_id = outbox.get("occurrence_id")
    state = outbox.get("state")
    failure_plane = outbox.get("failure_plane")
    policy = outbox.get("policy", "occurrence-v1")
    if not all(
        isinstance(value, str)
        for value in (job_id, occurrence_id, state, failure_plane, policy)
    ):
        raise AlertRoutingError("ALERT_OUTBOX_INVALID")
    assert isinstance(job_id, str)
    assert isinstance(occurrence_id, str)
    assert isinstance(state, str)
    assert isinstance(failure_plane, str)
    assert isinstance(policy, str)
    alert_id = occurrence_alert_identity(
        job_id, occurrence_id, state, failure_plane, policy
    )
    detected_at = outbox.get("detected_at")
    try:
        if not isinstance(detected_at, str) or not _CANONICAL_TIMESTAMP.fullmatch(
            detected_at
        ):
            raise ValueError
        parsed_detected_at = datetime.fromisoformat(detected_at[:-1] + "+00:00")
        if parsed_detected_at.tzinfo is None:
            raise ValueError
    except ValueError as error:
        raise AlertRoutingError("ALERT_DETECTED_AT_INVALID") from error
    operational = config.get("operational_metadata", {})
    if not isinstance(operational, Mapping):
        raise AlertRoutingError("OPERATIONAL_METADATA_INVALID")
    configured_owner = operational.get("owner", owner)
    configured_runbook = operational.get("runbook_uri", runbook_uri)
    if operational.get("notification_target_arn", target) != target:
        raise AlertRoutingError("NOTIFICATION_TARGET_METADATA_MISMATCH")
    if config.get("notification_runbook_uri", configured_runbook) != configured_runbook:
        raise AlertRoutingError("RUNBOOK_METADATA_MISMATCH")
    if not isinstance(configured_owner, str) or not configured_owner.strip():
        raise AlertRoutingError("OWNER_INVALID")
    if not isinstance(configured_runbook, str) or not configured_runbook.startswith(
        "https://"
    ):
        raise AlertRoutingError("RUNBOOK_INVALID")
    return {
        "schema_version": "1.0.0",
        "alert_id": alert_id,
        "deduplication_id": notification_identity(alert_id, target),
        "job_id": job_id,
        "occurrence_id": occurrence_id,
        "state": state,
        "failure_plane": failure_plane,
        "account_id": account_id,
        "region": region,
        "environment": environment,
        "detected_at": detected_at,
        "deployment_identity_id": deployment_identity,
        "owner": configured_owner,
        "notification_target_arn": target,
        "runbook_uri": configured_runbook,
        "operator_safe_reason": _safe_reason(outbox.get("operator_safe_reason")),
    }


def canonical_alert_bytes(alert: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(alert))
