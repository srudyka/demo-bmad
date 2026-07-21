"""Typed package boundary for alert routing."""

from typing import Any

from .domain import (
    AlertRoutingError,
    build_occurrence_alert,
    notification_identity,
    occurrence_alert_identity,
)

__all__ = (
    "AlertRoutingError",
    "build_occurrence_alert",
    "notification_identity",
    "occurrence_alert_identity",
    "dispatch_outbox_item",
    "lambda_handler",
    "reconciliation_handler",
)


def __getattr__(name: str) -> Any:  # pragma: no cover - import-boundary compatibility
    if name in {"dispatch_outbox_item", "lambda_handler", "reconciliation_handler"}:
        from . import handler

        return getattr(handler, name)
    raise AttributeError(name)
