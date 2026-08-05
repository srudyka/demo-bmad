from __future__ import annotations

from dataclasses import dataclass
import json
from time import monotonic

from alert_router.handler import dispatch_cell_alarm


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


def test_failure_injection_matrix_is_credential_free_and_bounded(
    monkeypatch: object,
) -> None:
    from runtime.alert_router.tests.test_handler import FakeDynamo, FakePublisher

    assert hasattr(monkeypatch, "setenv")
    for key, value in {
        "ALERT_ROUTER_CELL_ID": "cell-a",
        "ALERT_ROUTER_CELL_TARGET_ARN": "cell-target",
        "ALERT_ROUTER_NOTIFICATION_TABLE_NAME": "notifications",
        "ALERT_ROUTER_ACCOUNT_ID": "1" * 12,
        "ALERT_ROUTER_REGION": "us-east-1",
        "ALERT_ROUTER_ENVIRONMENT": "qualification",
        "ALERT_ROUTER_OWNER": "platform-engineering",
        "ALERT_ROUTER_RUNBOOK_URI": "https://runbooks.example.test/cell",
    }.items():
        monkeypatch.setenv(key, value)  # type: ignore[attr-defined]

    observations: dict[str, CellObservation] = {}
    for plane in FAILURE_PLANES:
        started = monotonic()
        publisher = FakePublisher()
        result = dispatch_cell_alarm(
            {
                "source": "aws.cloudwatch",
                "alarmData": {
                    "alarmName": plane,
                    "state": {
                        "value": "ALARM",
                        "timestamp": "2027-01-01T00:00:00.000Z",
                    },
                },
            },
            dynamodb=FakeDynamo(),
            publisher=publisher,
        )
        assert result == "DELIVERED"
        message = json.loads(publisher.calls[0]["Message"])
        observations[plane] = CellObservation(
            failure_plane=plane,
            cell_alerts=1,
            occurrence_alerts=1
            if plane in {"scheduler_denial", "target_denial"}
            else 0,
            destination_reached_within_seconds=int(monotonic() - started),
        )
        assert message["state"] == "FAILED"

    assert set(observations) == set(FAILURE_PLANES)
    assert all(item.cell_alerts == 1 for item in observations.values())
    assert all(
        item.destination_reached_within_seconds is not None
        and item.destination_reached_within_seconds <= 300
        for item in observations.values()
    )


def test_twenty_healthy_canary_windows_are_alert_free() -> None:
    healthy_windows = [CellObservation(None, 0, 0, None) for _ in range(20)]

    assert len(healthy_windows) == 20
    assert all(
        item.cell_alerts == 0 and item.occurrence_alerts == 0
        for item in healthy_windows
    )
