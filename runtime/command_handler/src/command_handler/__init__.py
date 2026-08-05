"""Typed package boundary for authorized operator commands."""

from .domain import (
    Authorization,
    CallerContext,
    CommandRejected,
    OccurrenceBinding,
    authorize_operator_request,
    manual_identity_bytes,
    manual_occurrence_id,
)

__all__ = (
    "Authorization",
    "CallerContext",
    "CommandRejected",
    "OccurrenceBinding",
    "authorize_operator_request",
    "manual_identity_bytes",
    "manual_occurrence_id",
)
