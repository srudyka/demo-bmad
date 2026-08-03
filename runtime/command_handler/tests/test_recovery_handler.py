from __future__ import annotations

import json
from typing import cast

import pytest

from command_handler.recovery_handler import AwsRecoveryOperations


class FakeSsm:
    def __init__(self, value: str) -> None:
        self.value = value
        self.puts: list[dict[str, object]] = []

    def get_parameter(self, **_: object) -> dict[str, object]:
        return {"Parameter": {"Value": self.value}}

    def put_parameter(self, **kwargs: object) -> None:
        self.puts.append(kwargs)


class FakeLambda:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def invoke(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def _operations(
    ssm: FakeSsm | None = None, lambda_client: FakeLambda | None = None
) -> AwsRecoveryOperations:
    return AwsRecoveryOperations(
        {
            "dynamodb": object(),
            "scheduler": object(),
            "lambda": lambda_client or FakeLambda(),
            "ssm": ssm
            or FakeSsm('{"recovery_generation":"prior","tables":["source"]}'),
        }
    )


def test_rollback_fails_closed_when_prior_pointer_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RECOVERY_POINTER_PARAMETER_NAME", "pointer")
    operations = _operations(FakeSsm("{}"))
    manifest = type("Manifest", (), {"source_tables": ("source",)})()
    with pytest.raises(RuntimeError, match="RECOVERY_PRIOR_POINTER_INVALID"):
        operations.rollback(manifest)
    assert operations.ssm.puts == []


def test_replay_and_reconcile_are_bound_to_recovery_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lambda_client = FakeLambda()
    monkeypatch.setenv("RECOVERY_REPLAY_FUNCTIONS", '["replay-fn"]')
    monkeypatch.setenv("RECOVERY_RECONCILIATION_FUNCTIONS", '["reconcile-fn"]')
    operations = _operations(lambda_client=lambda_client)
    manifest = type(
        "Manifest",
        (),
        {
            "recovery_id": "recovery-1",
            "recovery_generation": "generation-1",
            "restore_point": "2026-08-03T14:00:00.000Z",
            "source_deployment_identity": "a" * 64,
        },
    )()
    operations.replay(manifest)
    operations.reconcile(manifest)
    payloads = [
        json.loads(cast(bytes, call["Payload"])) for call in lambda_client.calls
    ]
    assert payloads == [
        {
            "mode": "replay",
            "recovery_id": "recovery-1",
            "recovery_generation": "generation-1",
            "restore_point": "2026-08-03T14:00:00.000Z",
        },
        {
            "mode": "reconciliation",
            "recovery_id": "recovery-1",
            "recovery_generation": "generation-1",
            "deployment_identity": "a" * 64,
        },
    ]
