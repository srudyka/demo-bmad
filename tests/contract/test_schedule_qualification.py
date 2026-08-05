from __future__ import annotations

import pytest

from scripts.schedule_qualification import (
    QualificationError,
    assert_detection_latency,
    build_qualification_manifest,
    classify_delivery,
    materialize_expectations,
    readiness_projection,
    schedule_generation_value,
    qualify_healthy_windows,
    validate_cleanup_inventory,
)

SCHEDULE = {
    "activation_end": None,
    "activation_start": "2027-01-01T00:00:00.000Z",
    "evaluator_version": "schedule-evaluator/1.0.0",
    "expression": "rate(1 hour)",
    "flexible_time_window": "OFF",
    "start_anchor": "2027-01-01T00:00:00.000Z",
    "time_zone": "UTC",
    "tzdb_version": "2026b",
}
BINDINGS = {
    "repository": "demo-bmad",
    "source_commit": "a" * 40,
    "workflow_sha": "b" * 40,
    "workflow_run_id": "run-1",
    "plan_sha256": "c" * 64,
    "deployment_identity_sha256": "d" * 64,
    "job_id": "dev/platform/canary",
    "config_sha256": "e" * 64,
    "schedule_generation": schedule_generation_value(SCHEDULE),
    "target_manifest_sha256": "f" * 64,
}
EVIDENCE = {"scenario": "complete", "checks": ["schedule", "delivery"]}


def _manifest() -> dict[str, object]:
    return build_qualification_manifest(
        release_version="1.0.0",
        compatibility_package="1.0.0",
        account_id="111111111111",
        region="us-gov-west-1",
        cell_identity="cell-test",
        test_configuration={"clock": "accelerated", "windows": 20},
        policy_versions={"schedule": "1.0.0"},
        evidence=EVIDENCE,
        bindings=BINDINGS,
    )


def test_manifest_is_canonical_sanitized_and_bound() -> None:
    manifest = _manifest()
    assert manifest["manifest_sha256"]
    assert manifest["evidence_sha256"]
    with pytest.raises(QualificationError, match="QUALIFICATION_SENSITIVE"):
        build_qualification_manifest(
            release_version="1",
            compatibility_package="1",
            account_id="1" * 12,
            region="us-east-1",
            cell_identity="cell",
            test_configuration={"secret": "x"},
            policy_versions={"schedule": "1"},
            evidence=EVIDENCE,
            bindings=BINDINGS,
        )


def test_expectations_are_independent_with_deadlines() -> None:
    result = materialize_expectations(
        job_id=BINDINGS["job_id"],
        schedule_generation=BINDINGS["schedule_generation"],
        schedule=SCHEDULE,
        window_start="2027-01-01T00:00:00.000Z",
    )
    assert len(result) == 24
    assert len({item["occurrence_id"] for item in result}) == 24
    assert result[0]["completion_deadline"] == "2027-01-01T01:00:00.000Z"
    with pytest.raises(QualificationError, match="QUALIFICATION_HORIZON"):
        out_of_range = {**SCHEDULE, "activation_start": "2030-01-01T00:00:00.000Z"}
        materialize_expectations(
            job_id="job",
            schedule_generation=schedule_generation_value(out_of_range),
            schedule=out_of_range,
            window_start="2027-01-01T00:00:00.000Z",
        )


def _event(attempt: int = 0) -> dict[str, object]:
    return {
        "attempt": attempt,
        "accepted": True,
        "occurrence_id": "1" * 64,
        "job_id": BINDINGS["job_id"],
        "schedule_generation": BINDINGS["schedule_generation"],
        "emitted_at": "2027-01-01T00:00:00.000Z",
    }


def test_delivery_is_bound_and_duplicate_safe() -> None:
    expected = {
        "occurrence_id": "1" * 64,
        "job_id": BINDINGS["job_id"],
        "schedule_generation": BINDINGS["schedule_generation"],
    }
    assert (
        classify_delivery(
            [_event()], deadline_reached=True, expected_occurrence=expected
        )
        == "STARTED"
    )
    assert (
        classify_delivery([], deadline_reached=True, expected_occurrence=expected)
        == "MISSED"
    )
    assert (
        classify_delivery(
            [_event(), _event()], deadline_reached=True, expected_occurrence=expected
        )
        == "DUPLICATE"
    )
    malformed = _event()
    del malformed["attempt"]
    with pytest.raises(QualificationError, match="QUALIFICATION_ATTEMPT"):
        classify_delivery(
            [malformed], deadline_reached=True, expected_occurrence=expected
        )


def test_healthy_windows_require_unique_correlated_successes() -> None:
    windows = [
        {
            "occurrence_id": str(index),
            "expected": 1,
            "accepted": 1,
            "alerts": 0,
            "cell_health_alerts": 0,
            "terminal_state": "SUCCEEDED",
            "late": False,
            "ambiguous": False,
        }
        for index in range(20)
    ]
    assert qualify_healthy_windows(windows)["passed"] is True
    with pytest.raises(QualificationError, match="QUALIFICATION_HEALTHY_WINDOWS"):
        qualify_healthy_windows([*windows[:-1], {**windows[-1], "occurrence_id": "0"}])


def test_projection_requires_verified_results_and_bindings() -> None:
    manifest = _manifest()
    results = {
        key: "passed"
        for key in (
            "schedule-interpretation",
            "expectation-independence",
            "scheduler-delivery",
            "delivery-idempotency",
            "qualification-timing",
            "healthy-windows",
        )
    }
    projection = readiness_projection(manifest, results, BINDINGS)
    assert projection["scheduler-delivery"] == "passed"
    assert projection["security"] == "blocked"


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(QualificationError, match="QUALIFICATION_ALERT_LATENCY"):
        assert_detection_latency(True)  # type: ignore[arg-type]
    assert validate_cleanup_inventory(["schedule", "task"], ["task"])["deleted"] == [
        "schedule"
    ]
    with pytest.raises(QualificationError, match="QUALIFICATION_CLEANUP_INVENTORY"):
        validate_cleanup_inventory(["schedule", 1])  # type: ignore[list-item]
