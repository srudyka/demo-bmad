from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.pilot_measurement import (
    PilotMeasurementError,
    _digest,
    measure_pilot,
    validate_measurement_definition,
)
from scripts.run_pilot_measurement import _validate_root

ROOT = Path(__file__).resolve().parents[2]


def _definition() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "calculation_version": "1.0.0",
        "definition_id": "pilot-measurement-v1",
        "owner": "platform-product",
        "generated_at": "2026-08-03T18:00:00.000Z",
        "observation_window": {
            "start": "2026-08-01T00:00:00.000Z",
            "end": "2026-08-03T23:59:59.000Z",
        },
        "bindings": {
            "release_version": "1.0.0",
            "compatibility_package_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "workflow_sha": "c" * 40,
            "workflow_run_id": "run-1",
            "account_id": "111111111111",
            "region": "us-east-1",
            "environment": "qualification",
            "pilot_id": "synthetic-fixture",
        },
        "metrics": [
            {
                "metric_id": "active-setup",
                "owner": "platform-product",
                "unit": "seconds",
                "start_event": "ready_inputs",
                "stop_event": "successful_standard_deployment",
                "inclusion_rules": ["complete_setup_events"],
                "exclusions": ["unrelated_interruption"],
                "evidence_sources": ["workflow"],
                "calculation": "active_setup_seconds",
                "target": {"operator": "lt", "value": 1000, "unit": "seconds"},
                "comparability_dimensions": ["complexity_class", "repository"],
            },
            {
                "metric_id": "elapsed-lead",
                "owner": "platform-product",
                "unit": "seconds",
                "start_event": "ready_inputs",
                "stop_event": "successful_standard_deployment",
                "inclusion_rules": ["complete_setup_events"],
                "exclusions": ["none"],
                "evidence_sources": ["workflow"],
                "calculation": "elapsed_lead_seconds",
                "target": {"operator": "lt", "value": 2000, "unit": "seconds"},
                "comparability_dimensions": ["complexity_class"],
            },
            {
                "metric_id": "findings",
                "owner": "security",
                "unit": "count",
                "start_event": "review_opened",
                "stop_event": "successful_standard_deployment",
                "inclusion_rules": ["all_findings"],
                "exclusions": ["none"],
                "evidence_sources": ["pull_request"],
                "calculation": "finding_disposition_counts",
                "target": {"operator": "eq", "value": 0, "unit": "count"},
                "comparability_dimensions": ["complexity_class"],
            },
            {
                "metric_id": "control-coverage",
                "owner": "platform-product",
                "unit": "ratio",
                "start_event": "readiness_started",
                "stop_event": "successful_standard_deployment",
                "inclusion_rules": ["exact_generation"],
                "exclusions": ["none"],
                "evidence_sources": ["readiness"],
                "calculation": "control_coverage_ratio",
                "target": {"operator": "gte", "value": 1, "unit": "ratio"},
                "comparability_dimensions": ["complexity_class"],
            },
            {
                "metric_id": "occurrences",
                "owner": "platform-operations",
                "unit": "count",
                "start_event": "pilot_window_start",
                "stop_event": "pilot_window_end",
                "inclusion_rules": ["all_occurrences"],
                "exclusions": ["none"],
                "evidence_sources": ["operations"],
                "calculation": "occurrence_outcomes",
                "target": {"operator": "gte", "value": 0, "unit": "count"},
                "comparability_dimensions": ["complexity_class"],
            },
            {
                "metric_id": "alert-latency",
                "owner": "platform-operations",
                "unit": "seconds",
                "start_event": "alert_signal",
                "stop_event": "alert_receipt",
                "inclusion_rules": ["delivered_alerts"],
                "exclusions": ["lost_alerts"],
                "evidence_sources": ["operations"],
                "calculation": "alert_latency_seconds",
                "target": {"operator": "lte", "value": 300, "unit": "seconds"},
                "comparability_dimensions": ["complexity_class"],
            },
            {
                "metric_id": "recovery-rto",
                "owner": "platform-operations",
                "unit": "seconds",
                "start_event": "recovery_started",
                "stop_event": "recovery_verified",
                "inclusion_rules": ["completed_rehearsals"],
                "exclusions": ["none"],
                "evidence_sources": ["readiness"],
                "calculation": "recovery_rto_seconds",
                "target": {"operator": "lte", "value": 3600, "unit": "seconds"},
                "comparability_dimensions": ["complexity_class"],
            },
            {
                "metric_id": "qualitative",
                "owner": "platform-product",
                "unit": "count",
                "start_event": "interview_collected",
                "stop_event": "interview_collected",
                "inclusion_rules": ["attributed_categories"],
                "exclusions": ["personal_data"],
                "evidence_sources": ["survey"],
                "calculation": "qualitative_categories",
                "target": {"operator": "gte", "value": 0, "unit": "count"},
                "comparability_dimensions": ["complexity_class"],
            },
        ],
    }


def _sample(sample_id: str, kind: str, *, complexity: str = "low") -> dict[str, object]:
    source = {
        "source_id": f"source-{sample_id}",
        "kind": "readiness",
        "locator": f"inline://{sample_id}",
        "sha256": "d" * 64,
        "sensitivity": "public-sanitized",
        "redacted": True,
        "provenance": {
            "repository": "org/platform",
            "source_revision": "e" * 40,
            "owner": "platform-owner",
            "job_id": "qualification/platform/canary",
            "workflow_run_id": "run-1",
            "account_id": "111111111111",
            "region": "us-east-1",
            "environment": "qualification",
            "deployment_identity_sha256": "1" * 64,
            "target_manifest_sha256": "2" * 64,
            "config_sha256": "3" * 64,
            "schedule_generation": 1,
            "window_start": "2026-08-01T00:00:00.000Z",
            "window_end": "2026-08-03T00:00:00.000Z",
        },
    }
    return {
        "sample_id": sample_id,
        "sample_kind": kind,
        "repository": "org/platform",
        "source_revision": "e" * 40,
        "job_id": "qualification/platform/canary",
        "owner": "platform-owner",
        "risk_class": "low",
        "complexity_class": complexity,
        "environment": "qualification",
        "account_id": "111111111111",
        "region": "us-east-1",
        "module_version": "1.0.0",
        "workflow_version": "1.0.0",
        "window_start": "2026-08-01T00:00:00.000Z",
        "window_end": "2026-08-03T00:00:00.000Z",
        "approval_record_sha256": "f" * 64,
        "events": [
            {
                "event_id": f"{sample_id}-ready",
                "kind": "ready_inputs",
                "at": "2026-08-02T10:00:00.000Z",
            },
            {
                "event_id": f"{sample_id}-success",
                "kind": "successful_standard_deployment",
                "at": "2026-08-02T10:30:00.000Z",
            },
        ],
        "effort_intervals": [
            {
                "interval_id": f"{sample_id}-active",
                "category": "active_engineering",
                "start": "2026-08-02T10:00:00.000Z",
                "end": "2026-08-02T10:10:00.000Z",
            },
            {
                "interval_id": f"{sample_id}-review",
                "category": "review",
                "start": "2026-08-02T10:10:00.000Z",
                "end": "2026-08-02T10:15:00.000Z",
            },
            {
                "interval_id": f"{sample_id}-approval",
                "category": "approval_wait",
                "start": "2026-08-02T10:15:00.000Z",
                "end": "2026-08-02T10:17:00.000Z",
            },
            {
                "interval_id": f"{sample_id}-deploy",
                "category": "deployment_wait",
                "start": "2026-08-02T10:17:00.000Z",
                "end": "2026-08-02T10:20:00.000Z",
            },
            {
                "interval_id": f"{sample_id}-interrupt",
                "category": "unrelated_interruption",
                "start": "2026-08-02T10:20:00.000Z",
                "end": "2026-08-02T10:21:00.000Z",
            },
        ],
        "review_cycles": 1,
        "failed_checks": 0,
        "manual_interventions": 0,
        "findings": [
            {
                "finding_id": f"finding-{sample_id}",
                "category": "documentation",
                "disposition": "prevented",
            }
        ],
        "controls": [
            {
                "control_id": "immutable-image",
                "generation": "1",
                "result": "passed",
                "readiness_evidence_sha256": "a" * 64,
                "source_ref_id": f"source-{sample_id}",
            }
        ],
        "reliability": {
            "expected": 20,
            "started": 20,
            "successful": 20,
            "failed": 0,
            "overdue": 0,
            "missed": 0,
            "duplicate": 0,
            "ambiguous": 0,
            "false_alerts": 0,
            "lost_alerts": 0,
            "reruns": 0,
            "incidents": 0,
            "alert_detection_seconds": [60, 90],
            "alert_delivery_seconds": [120, 150],
            "recovery_rto_seconds": [900],
        },
        "qualitative": [
            {
                "finding_code": "clear-runbook",
                "role": "on-call",
                "collected_at": "2026-08-02T12:00:00.000Z",
            }
        ],
        "source_refs": [source],
    }


def _pilot_sample(sample: dict[str, object]) -> dict[str, object]:
    sample.update(
        {
            "deployment_identity_sha256": "1" * 64,
            "target_manifest_sha256": "2" * 64,
            "config_sha256": "3" * 64,
            "schedule_generation": 1,
        }
    )
    return sample


def _packages() -> tuple[dict[str, object], dict[str, object]]:
    return {
        "package_version": "1.0.0",
        "samples": [_sample("baseline-1", "baseline")],
    }, {
        "package_version": "1.0.0",
        "samples": [_pilot_sample(_sample("synthetic-fixture/pilot-1", "pilot"))],
    }


def test_definition_and_complete_measurement_are_deterministic() -> None:
    definition = _definition()
    baseline, pilot = _packages()
    first = measure_pilot(definition, baseline, pilot)
    second = measure_pilot(
        copy.deepcopy(definition), copy.deepcopy(baseline), copy.deepcopy(pilot)
    )
    assert first == second
    assert first["status"] == "MEASURED"
    assert first["evidence_sha256"] == _digest(
        {key: value for key, value in first.items() if key != "evidence_sha256"}
    )
    assert first["metrics"][0]["value"] == 600.0


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: value["metrics"].append(copy.deepcopy(value["metrics"][0])),
            "PILOT_DUPLICATE_METRIC",
        ),
        (
            lambda value: value["observation_window"].update(
                end="2026-07-01T00:00:00.000Z"
            ),
            "PILOT_WINDOW_ORDER",
        ),
    ],
)
def test_definition_fails_closed(mutation, code: str) -> None:
    definition = _definition()
    mutation(definition)
    with pytest.raises(PilotMeasurementError, match=code):
        validate_measurement_definition(definition)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: value["pilot"]["samples"][0].update(sample_id="baseline-1"),
            "PILOT_DUPLICATE_SAMPLE",
        ),
        (
            lambda value: value["pilot"]["samples"][0]["effort_intervals"].append(
                copy.deepcopy(value["pilot"]["samples"][0]["effort_intervals"][0])
            ),
            "PILOT_EFFORT_OVERLAP",
        ),
        (
            lambda value: value["pilot"]["samples"][0].update(
                window_start="2026-07-01T00:00:00.000Z"
            ),
            "PILOT_SAMPLE_OUTSIDE_WINDOW",
        ),
        (
            lambda value: value["pilot"]["samples"][0]["source_refs"][0].update(
                redacted=False
            ),
            "PILOT_SOURCE_REDACTION",
        ),
    ],
)
def test_measurement_inputs_fail_closed(mutation, code: str) -> None:
    definition = _definition()
    baseline, pilot = _packages()
    value = {"baseline": baseline, "pilot": pilot}
    mutation(value)
    recoverable = {
        "PILOT_DUPLICATE_SAMPLE",
        "PILOT_EFFORT_OVERLAP",
        "PILOT_SAMPLE_OUTSIDE_WINDOW",
    }
    if code in recoverable:
        result = measure_pilot(definition, value["baseline"], value["pilot"])
        assert result["status"] == "INCOMPLETE"
        assert all(metric["reason"] == code for metric in result["metrics"])
    else:
        with pytest.raises(PilotMeasurementError, match=code):
            measure_pilot(definition, value["baseline"], value["pilot"])


def test_missing_baseline_is_unknown_and_never_estimated() -> None:
    result = measure_pilot(
        _definition(), {"package_version": "1.0.0", "samples": []}, _packages()[1]
    )
    assert result["status"] == "UNKNOWN"
    assert all(metric["status"] == "UNKNOWN" for metric in result["metrics"])
    assert any("Baseline evidence is UNKNOWN" in item for item in result["limitations"])


def test_complexity_mismatch_is_not_comparable() -> None:
    baseline, pilot = _packages()
    pilot["samples"][0]["complexity_class"] = "high"
    result = measure_pilot(_definition(), baseline, pilot)
    assert result["status"] == "NOT_COMPARABLE"
    assert all(metric["status"] == "NOT_COMPARABLE" for metric in result["metrics"])


def test_cli_emits_sealed_result_and_report(tmp_path) -> None:
    definition = _definition()
    baseline, pilot = _packages()
    for name, value in (
        ("definition.json", definition),
        ("baseline.json", baseline),
        ("pilot.json", pilot),
    ):
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "out" / "result.json"
    report = tmp_path / "out" / "report.md"
    output.parent.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_pilot_measurement",
            "--definition",
            str(tmp_path / "definition.json"),
            "--baseline",
            str(tmp_path / "baseline.json"),
            "--pilot",
            str(tmp_path / "pilot.json"),
            "--artifact-root",
            str(tmp_path),
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["evidence_sha256"] == _digest(
        {key: value for key, value in result.items() if key != "evidence_sha256"}
    )
    assert "not a rollout" in report.read_text(encoding="utf-8")


def test_cli_rejects_duplicate_json_keys(tmp_path) -> None:
    baseline, pilot = _packages()
    (tmp_path / "definition.json").write_text(
        '{"schema_version":"1.0.0","schema_version":"1.0.0"}', encoding="utf-8"
    )
    (tmp_path / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
    (tmp_path / "pilot.json").write_text(json.dumps(pilot), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_pilot_measurement",
            "--definition",
            str(tmp_path / "definition.json"),
            "--baseline",
            str(tmp_path / "baseline.json"),
            "--pilot",
            str(tmp_path / "pilot.json"),
            "--artifact-root",
            str(tmp_path),
            "--output",
            str(tmp_path / "result.json"),
            "--report",
            str(tmp_path / "report.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "PILOT_DUPLICATE_JSON_KEY" in completed.stderr


def test_fixture_catalog_lists_all_fail_closed_scenarios() -> None:
    catalog = json.loads(
        (ROOT / "contracts/v1/fixtures/pilot-measurement/cases.json").read_text()
    )
    names = {case["name"] for case in catalog["cases"]}
    assert {
        "complete-comparable",
        "missing-baseline",
        "incomplete-event-window",
        "contradictory-timestamps",
        "duplicate-sample",
        "stale-outside-window",
        "complexity-mismatch",
        "governed-exception",
        "unresolved-control",
        "sensitive-artifact",
        "qualitative-only",
        "deterministic-regeneration",
    } <= names


def test_incomplete_event_and_governed_exception_are_visible() -> None:
    baseline, pilot = _packages()
    pilot["samples"][0]["events"] = [pilot["samples"][0]["events"][0]]
    result = measure_pilot(_definition(), baseline, pilot)
    elapsed = next(
        metric for metric in result["metrics"] if metric["metric_id"] == "elapsed-lead"
    )
    assert elapsed["status"] == "INCOMPLETE"

    baseline, pilot = _packages()
    pilot["samples"][0]["findings"][0]["disposition"] = "exception"
    assert measure_pilot(_definition(), baseline, pilot)["status"] == "MEASURED"


def test_unresolved_control_and_unsafe_artifact_are_rejected(tmp_path) -> None:
    baseline, pilot = _packages()
    pilot["samples"][0]["controls"][0]["result"] = "failed"
    with pytest.raises(PilotMeasurementError, match="PILOT_CONTROL_NOT_PASSED"):
        measure_pilot(_definition(), baseline, pilot)
    unsafe = tmp_path / "plans"
    unsafe.mkdir()
    (unsafe / "plan.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PilotMeasurementError, match="PILOT_FORBIDDEN_ARTIFACT"):
        _validate_root(tmp_path)
