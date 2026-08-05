"""Fail-closed Cell recovery state machine and operation boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping, Protocol


class RecoveryRejected(ValueError):
    """A stable, operator-safe recovery rejection."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RecoveryPhase(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    CONTAINING = "CONTAINING"
    CONTAINED = "CONTAINED"
    RESTORING = "RESTORING"
    VALIDATING = "VALIDATING"
    CUTOVER_READY = "CUTOVER_READY"
    CUTOVER = "CUTOVER"
    REPLAYING = "REPLAYING"
    VERIFYING = "VERIFYING"
    RESUMED = "RESUMED"
    BLOCKED = "BLOCKED"
    ROLLED_BACK = "ROLLED_BACK"


_NEXT: dict[RecoveryPhase, RecoveryPhase] = {
    RecoveryPhase.REQUESTED: RecoveryPhase.APPROVED,
    RecoveryPhase.APPROVED: RecoveryPhase.CONTAINING,
    RecoveryPhase.CONTAINING: RecoveryPhase.CONTAINED,
    RecoveryPhase.CONTAINED: RecoveryPhase.RESTORING,
    RecoveryPhase.RESTORING: RecoveryPhase.VALIDATING,
    RecoveryPhase.VALIDATING: RecoveryPhase.CUTOVER_READY,
    RecoveryPhase.CUTOVER_READY: RecoveryPhase.CUTOVER,
    RecoveryPhase.CUTOVER: RecoveryPhase.REPLAYING,
    RecoveryPhase.REPLAYING: RecoveryPhase.VERIFYING,
    RecoveryPhase.VERIFYING: RecoveryPhase.RESUMED,
}


@dataclass(frozen=True)
class RecoveryManifest:
    recovery_id: str
    recovery_generation: str
    cell_id: str
    account_id: str
    region: str
    actor: str
    session_id: str
    approval_reference: str
    reason: str
    restore_point: str
    expected_rpo_seconds: int
    expected_rto_seconds: int
    source_deployment_identity: str
    phase: RecoveryPhase = RecoveryPhase.REQUESTED
    source_tables: tuple[str, ...] = ()
    target_tables: tuple[str, ...] = ()
    phase_started_at: str = ""
    failure_code: str | None = None
    validation_digest: str | None = None
    actual_rpo_seconds: int | None = None
    actual_rto_seconds: int | None = None


class RecoveryOperations(Protocol):
    """AWS operation boundary owned by the recovery role."""

    def contain(self, manifest: RecoveryManifest) -> None: ...

    def restore(self, manifest: RecoveryManifest) -> tuple[str, ...]: ...

    def validate(
        self, manifest: RecoveryManifest, target_tables: tuple[str, ...]
    ) -> str: ...

    def cutover(
        self, manifest: RecoveryManifest, target_tables: tuple[str, ...]
    ) -> None: ...

    def replay(self, manifest: RecoveryManifest) -> None: ...

    def reconcile(self, manifest: RecoveryManifest) -> None: ...

    def verify(self, manifest: RecoveryManifest) -> None: ...

    def rollback(self, manifest: RecoveryManifest) -> None: ...

    def resume(self, manifest: RecoveryManifest) -> None: ...

    def checkpoint(self, manifest: RecoveryManifest) -> None: ...


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RecoveryRejected("RECOVERY_RESTORE_POINT_INVALID") from error
    if parsed.tzinfo is None:
        raise RecoveryRejected("RECOVERY_RESTORE_POINT_INVALID")
    return parsed.astimezone(UTC)


def validate_restore_point(
    restore_point: str,
    *,
    earliest: str,
    latest: str,
) -> str:
    point = _parse_timestamp(restore_point)
    if point < _parse_timestamp(earliest) or point > _parse_timestamp(latest):
        raise RecoveryRejected("RECOVERY_RESTORE_POINT_OUTSIDE_PITR")
    return point.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def recovery_command_fields(command: Mapping[str, object]) -> tuple[str, int, int, str]:
    if command.get("command_type") != "RECOVER":
        raise RecoveryRejected("RECOVERY_COMMAND_TYPE")
    restore_point = command.get("restore_point")
    rpo = command.get("expected_rpo_seconds")
    rto = command.get("expected_rto_seconds")
    deployment = command.get("deployment_identity_id")
    if (
        not isinstance(restore_point, str)
        or not isinstance(rpo, int)
        or isinstance(rpo, bool)
        or not isinstance(rto, int)
        or isinstance(rto, bool)
        or not isinstance(deployment, str)
        or not deployment
    ):
        raise RecoveryRejected("RECOVERY_REQUEST_FIELDS")
    if not 1 <= rpo <= 2_592_000 or not 1 <= rto <= 2_592_000:
        raise RecoveryRejected("RECOVERY_OBJECTIVE_BOUNDS")
    return restore_point, rpo, rto, deployment


def advance(manifest: RecoveryManifest, *, now: str) -> RecoveryManifest:
    next_phase = _NEXT.get(manifest.phase)
    if next_phase is None:
        raise RecoveryRejected("RECOVERY_PHASE_NOT_ADVANCEABLE")
    return replace(manifest, phase=next_phase, phase_started_at=now, failure_code=None)


def block(manifest: RecoveryManifest, *, code: str, now: str) -> RecoveryManifest:
    if not code or not code.startswith("RECOVERY_"):
        raise RecoveryRejected("RECOVERY_FAILURE_CODE")
    return replace(
        manifest,
        phase=RecoveryPhase.BLOCKED,
        phase_started_at=now,
        failure_code=code,
    )


def execute_recovery(
    manifest: RecoveryManifest,
    operations: RecoveryOperations,
    *,
    now: str,
) -> RecoveryManifest:
    """Run the ordered recovery phases; any failure blocks and rolls back safely."""

    current = manifest

    def checkpoint(value: RecoveryManifest) -> None:
        callback = getattr(operations, "checkpoint", None)
        if callback is not None:
            callback(value)

    try:
        current = advance(current, now=now)
        checkpoint(current)
        operations.contain(current)
        current = advance(current, now=now)
        checkpoint(current)
        current = advance(current, now=now)
        checkpoint(current)
        targets = operations.restore(current)
        current = replace(advance(current, now=now), target_tables=targets)
        checkpoint(current)
        digest = operations.validate(current, targets)
        current = replace(advance(current, now=now), validation_digest=digest)
        checkpoint(current)
        current = advance(current, now=now)
        checkpoint(current)
        operations.cutover(current, targets)
        current = advance(current, now=now)
        checkpoint(current)
        operations.replay(current)
        operations.reconcile(current)
        current = advance(current, now=now)
        checkpoint(current)
        operations.verify(current)
        current = advance(current, now=now)
        checkpoint(current)
        operations.resume(current)
        current = advance(current, now=now)
        checkpoint(current)
        return current
    except RecoveryRejected as error:
        blocked = block(current, code=error.code, now=now)
        checkpoint(blocked)
        try:
            operations.rollback(blocked)
        except Exception:
            blocked = block(blocked, code="RECOVERY_ROLLBACK_FAILED", now=now)
        checkpoint(blocked)
        return blocked
    except Exception as error:  # noqa: BLE001 - recovery must fail closed
        code = f"RECOVERY_{type(error).__name__.upper()}"
        blocked = block(current, code=code, now=now)
        try:
            operations.rollback(blocked)
        except Exception:
            blocked = block(blocked, code="RECOVERY_ROLLBACK_FAILED", now=now)
        checkpoint(blocked)
        return blocked
