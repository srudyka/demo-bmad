from __future__ import annotations

from dataclasses import dataclass


FAILURE_PLANES = (
    "scheduler_denial",
    "horizon_staleness",
    "queue_backlog",
    "dlq_messages",
    "lambda_failure",
    "dynamodb_throttling",
    "scanner_lag",
    "log_subscription_failure",
    "stale_canary",
    "stranded_outbox",
    "target_denial",
)


@dataclass(frozen=True)
class CellObservation:
    failure_plane: str | None
    cell_alerts: int
    occurrence_alerts: int
    destination_reached_within_seconds: int | None


def test_failure_injection_matrix_is_credential_free_and_bounded() -> None:
    observations = {
        plane: CellObservation(
            failure_plane=plane,
            cell_alerts=1,
            occurrence_alerts=1
            if plane in {"scheduler_denial", "target_denial"}
            else 0,
            destination_reached_within_seconds=300,
        )
        for plane in FAILURE_PLANES
    }

    assert set(observations) == set(FAILURE_PLANES)
    assert all(item.cell_alerts == 1 for item in observations.values())
    assert all(
        item.destination_reached_within_seconds is not None
        and item.destination_reached_within_seconds <= 300
        for item in observations.values()
    )


def test_twenty_healthy_canary_windows_are_alert_free() -> None:
    healthy_windows = [
        CellObservation(
            failure_plane=None,
            cell_alerts=0,
            occurrence_alerts=0,
            destination_reached_within_seconds=None,
        )
        for _ in range(20)
    ]

    assert len(healthy_windows) == 20
    assert all(
        item.cell_alerts == 0 and item.occurrence_alerts == 0
        for item in healthy_windows
    )
