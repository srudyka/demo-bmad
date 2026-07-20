"""Typed package boundary for evidence normalization."""

from .normalizer import (
    MaterializerRegistration,
    EcsRegistration,
    NormalizationResult,
    SchedulerRegistration,
    TransientTransportError,
    normalize_scheduler_record,
    normalize_materializer_record,
    normalize_ecs_event,
    process_scheduler_batch,
    process_materializer_batch,
    process_ecs_batch,
    scheduler_producer_event_id,
)

__all__ = (
    "MaterializerRegistration",
    "EcsRegistration",
    "NormalizationResult",
    "SchedulerRegistration",
    "TransientTransportError",
    "normalize_scheduler_record",
    "normalize_materializer_record",
    "normalize_ecs_event",
    "process_scheduler_batch",
    "process_materializer_batch",
    "process_ecs_batch",
    "scheduler_producer_event_id",
)
