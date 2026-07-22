from __future__ import annotations

import pytest

from command_handler.recovery import (
    RecoveryManifest,
    RecoveryPhase,
    RecoveryRejected,
    execute_recovery,
    validate_restore_point,
)


class FakeOperations:
    def __init__(self, fail: str | None = None) -> None:
        self.calls: list[str] = []
        self.fail = fail

    def _call(self, name: str) -> None:
        self.calls.append(name)
        if self.fail == name:
            raise RuntimeError(name)

    def contain(self, manifest: RecoveryManifest) -> None:
        self._call("contain")

    def restore(self, manifest: RecoveryManifest) -> tuple[str, ...]:
        self._call("restore")
        return ("target-a", "target-b")

    def validate(
        self, manifest: RecoveryManifest, target_tables: tuple[str, ...]
    ) -> str:
        self._call("validate")
        return "a" * 64

    def cutover(
        self, manifest: RecoveryManifest, target_tables: tuple[str, ...]
    ) -> None:
        self._call("cutover")

    def replay(self, manifest: RecoveryManifest) -> None:
        self._call("replay")

    def reconcile(self, manifest: RecoveryManifest) -> None:
        self._call("reconcile")

    def verify(self, manifest: RecoveryManifest) -> None:
        self._call("verify")

    def rollback(self, manifest: RecoveryManifest) -> None:
        self._call("rollback")

    def resume(self, manifest: RecoveryManifest) -> None:
        self._call("resume")

    def checkpoint(self, manifest: RecoveryManifest) -> None:
        pass


def _manifest() -> RecoveryManifest:
    return RecoveryManifest(
        recovery_id="0190f2c9-6c00-7000-8000-000000000001",
        recovery_generation="0190f2c9-6c00-7000-8000-000000000001-1",
        cell_id="cell-a",
        account_id="123456789012",
        region="us-test-1",
        actor="operator",
        session_id="session-1",
        approval_reference="APPROVAL-1",
        reason="verified control-plane corruption",
        restore_point="2026-07-22T10:00:00.000Z",
        expected_rpo_seconds=300,
        expected_rto_seconds=1800,
        source_deployment_identity="d" * 64,
        phase_started_at="2026-07-22T10:01:00.000Z",
        source_tables=("source-a", "source-b"),
    )


def test_restore_point_must_be_inside_every_table_pitr_window() -> None:
    assert (
        validate_restore_point(
            "2026-07-22T10:00:00Z",
            earliest="2026-07-22T09:00:00Z",
            latest="2026-07-22T10:05:00Z",
        )
        == "2026-07-22T10:00:00.000Z"
    )
    with pytest.raises(RecoveryRejected, match="RECOVERY_RESTORE_POINT_OUTSIDE_PITR"):
        validate_restore_point(
            "2026-07-22T08:59:00Z",
            earliest="2026-07-22T09:00:00Z",
            latest="2026-07-22T10:05:00Z",
        )


def test_recovery_runs_in_order_and_resumes_only_after_verification() -> None:
    operations = FakeOperations()
    result = execute_recovery(_manifest(), operations, now="2026-07-22T10:02:00Z")
    assert result.phase is RecoveryPhase.RESUMED
    assert result.target_tables == ("target-a", "target-b")
    assert operations.calls == [
        "contain",
        "restore",
        "validate",
        "cutover",
        "replay",
        "reconcile",
        "verify",
        "resume",
    ]


def test_recovery_failure_blocks_and_rolls_back_without_resuming() -> None:
    operations = FakeOperations(fail="validate")
    result = execute_recovery(_manifest(), operations, now="2026-07-22T10:02:00Z")
    assert result.phase is RecoveryPhase.BLOCKED
    assert result.failure_code == "RECOVERY_RUNTIMEERROR"
    assert operations.calls == ["contain", "restore", "validate", "rollback"]
