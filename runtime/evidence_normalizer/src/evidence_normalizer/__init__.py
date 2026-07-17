"""Typed package boundary for evidence normalization."""

from .normalizer import (
    MaterializerRegistration,
    NormalizationResult,
    SchedulerRegistration,
    TransientTransportError,
    normalize_scheduler_record,
    normalize_materializer_record,
    process_scheduler_batch,
    process_materializer_batch,
    scheduler_producer_event_id,
)

__all__ = (
    "MaterializerRegistration",
    "NormalizationResult",
    "SchedulerRegistration",
    "TransientTransportError",
    "normalize_scheduler_record",
    "normalize_materializer_record",
    "process_scheduler_batch",
    "process_materializer_batch",
    "scheduler_producer_event_id",
)
