"""Typed package boundary for completion-log ingestion."""

from .ingestor import (
    CloudWatchLogBatch,
    CompletionBinding,
    LogIngestionError,
    build_completion_envelopes,
    decode_subscription_record,
)

__all__ = (
    "CloudWatchLogBatch",
    "CompletionBinding",
    "LogIngestionError",
    "build_completion_envelopes",
    "decode_subscription_record",
)
