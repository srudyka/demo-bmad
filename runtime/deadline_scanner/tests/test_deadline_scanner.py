from __future__ import annotations

from deadline_scanner import (
    DeadlineCandidate,
    ScannerCheckpoint,
    build_deadline_envelope,
    deadline_bucket,
    deadline_event_id,
    deadline_index_key,
    due_candidates,
)


def test_package_boundary_is_importable() -> None:
    assert "DeadlineCandidate" in __import__("deadline_scanner").__all__


def candidate(**overrides: object) -> DeadlineCandidate:
    values: dict[str, object] = {
        "job_id": "dev/demo/job",
        "config_version": "a" * 64,
        "schedule_generation": "b" * 64,
        "occurrence_id": "c" * 64,
        "scheduled_time": "2026-07-20T10:00:00.000Z",
        "deadline_at": "2026-07-20T10:05:00.000Z",
        "deadline_kind": "START",
        "state": "EXPECTED",
        "deadline_key": "DEADLINE#0#2026-07-20T10:05:00.000Z",
    }
    values["deadline_sort"] = f"{values['deadline_at']}#{values['occurrence_id']}#{values['deadline_kind']}"
    values.update(overrides)
    return DeadlineCandidate(**values)


def test_deadline_key_and_event_identity_are_stable() -> None:
    item = candidate()
    assert deadline_bucket(item.deadline_at) == "2026-07-20T10:05:00.000Z"
    assert deadline_index_key(item.deadline_at, "0") == item.deadline_key
    assert deadline_event_id(item) == deadline_event_id(item)
    envelope = build_deadline_envelope(
        item,
        scanner_watermark="2026-07-20T10:06:00.000Z",
        emitted_at="2026-07-20T10:06:00.000Z",
    )
    assert envelope["event_type"] == "occurrence.deadline-reached.v1"
    assert envelope["producer_id"] == "deadline-scanner"


def test_due_selection_reconciles_only_nonterminal_items_in_bounded_window() -> None:
    values = [
        candidate(),
        candidate(occurrence_id="d" * 64, deadline_at="2026-07-20T09:00:00.000Z"),
        candidate(occurrence_id="e" * 64, state="SUCCEEDED"),
    ]
    result = due_candidates(
        values,
        now="2026-07-20T10:06:00.000Z",
        lookback_seconds=900,
        maximum_lateness_seconds=900,
    )
    assert [item.occurrence_id for item in result] == ["c" * 64]


def test_checkpoint_rejects_regression_and_allows_replay_at_same_watermark() -> None:
    checkpoint = ScannerCheckpoint("2026-07-20T10:06:00.000Z", "page-a")
    assert checkpoint.advance("2026-07-20T10:06:00.000Z", "page-b").position == "page-b"
    try:
        checkpoint.advance("2026-07-20T10:05:00.000Z", "page-z")
    except ValueError as error:
        assert str(error) == "CHECKPOINT_NOT_MONOTONIC"
    else:
        raise AssertionError("checkpoint regression was accepted")
