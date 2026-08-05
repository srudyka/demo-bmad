"""Credential-free, deterministic pilot measurement and evidence packaging."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
from datetime import UTC, datetime
import hashlib
import math
import re
from typing import Any

import rfc8785

from scripts.deployment_targets import TargetViolation

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ACCOUNT = re.compile(r"^[0-9]{12}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")
JOB_ID = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$"
)

STATUSES = {
    "MEASURED",
    "UNKNOWN",
    "INCOMPLETE",
    "INCONCLUSIVE",
    "NOT_COMPARABLE",
    "BLOCKED",
}
SAMPLE_KINDS = {"baseline", "pilot"}
EFFORT_CATEGORIES = {
    "active_engineering",
    "review",
    "approval_wait",
    "deployment_wait",
    "unrelated_interruption",
}
METRIC_CALCULATIONS = {
    "active_setup_seconds",
    "review_effort_seconds",
    "approval_wait_seconds",
    "deployment_wait_seconds",
    "unrelated_interruption_seconds",
    "total_active_effort_seconds",
    "active_effort_reduction_ratio",
    "elapsed_lead_seconds",
    "review_cycles",
    "failed_checks",
    "manual_interventions",
    "time_to_success_seconds",
    "finding_disposition_counts",
    "control_coverage_ratio",
    "occurrence_outcomes",
    "alert_latency_seconds",
    "recovery_rto_seconds",
    "qualitative_categories",
}
COMPARABILITY_DIMENSIONS = {
    "complexity_class",
    "repository",
    "risk_class",
    "environment",
    "module_version",
    "workflow_version",
}
SENSITIVE_MARKERS = (
    "secret",
    "password",
    "credential",
    "private_key",
    "raw_payload",
    "terraform.tfstate",
    ".tfplan",
    "access_key",
    "token",
)


class PilotMeasurementError(TargetViolation):
    """Stable, sanitized rejection from the measurement contract."""


def _digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _require_keys(value: Mapping[str, Any], required: set[str], code: str) -> None:
    if set(value) != required:
        raise PilotMeasurementError(code)


def _text(value: Any, code: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise PilotMeasurementError(code)
    if any(ord(character) < 32 for character in value) or "|" in value:
        raise PilotMeasurementError(code)
    if any(marker in value.lower() for marker in SENSITIVE_MARKERS):
        raise PilotMeasurementError("PILOT_SENSITIVE_FIELD")
    return value


def _timestamp(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise PilotMeasurementError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PilotMeasurementError(code) from error
    if parsed.tzinfo is None:
        raise PilotMeasurementError(code)
    return parsed.astimezone(UTC)


def _hash(value: Any, code: str, pattern: re.Pattern[str] = SHA256) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise PilotMeasurementError(code)
    return value


def _positive_int(value: Any, code: str, *, maximum: int = 1_000_000) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= maximum
    ):
        raise PilotMeasurementError(code)
    return value


def _validate_sanitized(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if any(marker in key_text for marker in SENSITIVE_MARKERS):
                raise PilotMeasurementError("PILOT_SENSITIVE_FIELD")
            _validate_sanitized(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str) and any(
        marker in value.lower() for marker in SENSITIVE_MARKERS
    ):
        raise PilotMeasurementError("PILOT_SENSITIVE_FIELD")


def _validate_target(target: Mapping[str, Any]) -> None:
    _require_keys(target, {"operator", "value", "unit"}, "PILOT_TARGET_SHAPE")
    if target["operator"] not in {"lt", "lte", "eq", "gte", "gt"}:
        raise PilotMeasurementError("PILOT_TARGET_OPERATOR")
    if not isinstance(target["value"], (int, float)) or isinstance(
        target["value"], bool
    ):
        raise PilotMeasurementError("PILOT_TARGET_VALUE")
    if not math.isfinite(float(target["value"])):
        raise PilotMeasurementError("PILOT_TARGET_VALUE")
    _text(target["unit"], "PILOT_TARGET_UNIT", maximum=32)


def validate_measurement_definition(definition: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "calculation_version",
        "definition_id",
        "owner",
        "generated_at",
        "observation_window",
        "bindings",
        "metrics",
    }
    _require_keys(definition, required, "PILOT_DEFINITION_SHAPE")
    if definition["schema_version"] != "1.0.0":
        raise PilotMeasurementError("PILOT_SCHEMA_VERSION")
    _text(definition["calculation_version"], "PILOT_CALCULATION_VERSION", maximum=64)
    _text(definition["definition_id"], "PILOT_DEFINITION_ID")
    _text(definition["owner"], "PILOT_OWNER")
    _timestamp(definition["generated_at"], "PILOT_GENERATED_AT")
    window = definition["observation_window"]
    if not isinstance(window, Mapping):
        raise PilotMeasurementError("PILOT_WINDOW_SHAPE")
    _require_keys(window, {"start", "end"}, "PILOT_WINDOW_SHAPE")
    window_start = _timestamp(window["start"], "PILOT_WINDOW_TIME")
    window_end = _timestamp(window["end"], "PILOT_WINDOW_TIME")
    if window_end <= window_start:
        raise PilotMeasurementError("PILOT_WINDOW_ORDER")
    metrics = definition["metrics"]
    if not isinstance(metrics, list) or not metrics:
        raise PilotMeasurementError("PILOT_METRICS_SHAPE")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for metric in metrics:
        if not isinstance(metric, Mapping):
            raise PilotMeasurementError("PILOT_METRIC_SHAPE")
        metric_required = {
            "metric_id",
            "owner",
            "unit",
            "start_event",
            "stop_event",
            "inclusion_rules",
            "exclusions",
            "evidence_sources",
            "calculation",
            "target",
            "comparability_dimensions",
        }
        _require_keys(metric, metric_required, "PILOT_METRIC_SHAPE")
        metric_id = _text(metric["metric_id"], "PILOT_METRIC_ID", maximum=96)
        if metric_id in seen:
            raise PilotMeasurementError("PILOT_DUPLICATE_METRIC")
        seen.add(metric_id)
        for key in ("owner", "unit", "start_event", "stop_event"):
            _text(metric[key], "PILOT_METRIC_FIELD", maximum=96)
        if metric["calculation"] not in METRIC_CALCULATIONS:
            raise PilotMeasurementError("PILOT_METRIC_CALCULATION")
        for key in (
            "inclusion_rules",
            "exclusions",
            "evidence_sources",
            "comparability_dimensions",
        ):
            values = metric[key]
            if (
                not isinstance(values, list)
                or not values
                or any(not isinstance(item, str) or not item for item in values)
            ):
                raise PilotMeasurementError("PILOT_METRIC_RULES")
        if any(
            item not in COMPARABILITY_DIMENSIONS
            for item in metric["comparability_dimensions"]
        ):
            raise PilotMeasurementError("PILOT_COMPARABILITY_DIMENSION")
        _validate_target(metric["target"])
        normalized.append(dict(metric))
    return {"definition_id": definition["definition_id"], "metrics": normalized}


def _validate_bindings(bindings: Mapping[str, Any]) -> None:
    required = {
        "release_version",
        "compatibility_package_sha256",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "account_id",
        "region",
        "environment",
        "pilot_id",
    }
    _require_keys(bindings, required, "PILOT_BINDINGS_SHAPE")
    _text(bindings["release_version"], "PILOT_BINDING")
    _hash(bindings["compatibility_package_sha256"], "PILOT_BINDING")
    _hash(bindings["source_commit"], "PILOT_BINDING", SHA1)
    _hash(bindings["workflow_sha"], "PILOT_BINDING", SHA1)
    _text(bindings["workflow_run_id"], "PILOT_BINDING")
    if not ACCOUNT.fullmatch(str(bindings["account_id"])):
        raise PilotMeasurementError("PILOT_ACCOUNT_FORMAT")
    _text(bindings["region"], "PILOT_BINDING", maximum=64)
    _text(bindings["environment"], "PILOT_BINDING", maximum=64)
    _text(bindings["pilot_id"], "PILOT_PILOT_ID", maximum=96)


def _validate_source_ref(
    source: Mapping[str, Any],
    sample: Mapping[str, Any],
    *,
    pilot_id: str,
    workflow_run_id: str,
) -> None:
    required = {
        "source_id",
        "kind",
        "locator",
        "sha256",
        "sensitivity",
        "redacted",
        "provenance",
    }
    _require_keys(source, required, "PILOT_SOURCE_SHAPE")
    _text(source["source_id"], "PILOT_SOURCE_ID", maximum=96)
    if source["kind"] not in {
        "workflow",
        "pull_request",
        "readiness",
        "deployment",
        "operations",
        "survey",
        "external",
    }:
        raise PilotMeasurementError("PILOT_SOURCE_KIND")
    locator = _text(source["locator"], "PILOT_SOURCE_LOCATOR", maximum=512)
    if locator.startswith("/") or ".." in locator.split("/"):
        raise PilotMeasurementError("PILOT_SOURCE_LOCATOR")
    _hash(source["sha256"], "PILOT_SOURCE_DIGEST")
    if source["sensitivity"] not in {
        "public-sanitized",
        "internal-sanitized",
        "protected-reference",
    }:
        raise PilotMeasurementError("PILOT_SOURCE_SENSITIVITY")
    if source["redacted"] is not True:
        raise PilotMeasurementError("PILOT_SOURCE_REDACTION")
    provenance = source["provenance"]
    if not isinstance(provenance, Mapping):
        raise PilotMeasurementError("PILOT_SOURCE_PROVENANCE")
    provenance_required = {
        "repository",
        "source_revision",
        "owner",
        "job_id",
        "workflow_run_id",
        "account_id",
        "region",
        "environment",
        "window_start",
        "window_end",
    }
    provenance_required.update(
        {
            "deployment_identity_sha256",
            "target_manifest_sha256",
            "config_sha256",
            "schedule_generation",
        }
    )
    _require_keys(
        provenance,
        provenance_required,
        "PILOT_SOURCE_PROVENANCE",
    )
    _text(provenance["repository"], "PILOT_PROVENANCE")
    _hash(provenance["source_revision"], "PILOT_PROVENANCE", SHA1)
    _text(provenance["owner"], "PILOT_PROVENANCE")
    _text(provenance["job_id"], "PILOT_PROVENANCE")
    _text(provenance["workflow_run_id"], "PILOT_PROVENANCE")
    if sample["sample_kind"] == "pilot":
        for key in (
            "deployment_identity_sha256",
            "target_manifest_sha256",
            "config_sha256",
        ):
            _hash(provenance[key], "PILOT_PROVENANCE_DEPLOYMENT")
        _positive_int(provenance["schedule_generation"], "PILOT_PROVENANCE_DEPLOYMENT")
        if any(
            provenance[key] != sample[key]
            for key in (
                "deployment_identity_sha256",
                "target_manifest_sha256",
                "config_sha256",
                "schedule_generation",
            )
        ):
            raise PilotMeasurementError("PILOT_PROVENANCE_DEPLOYMENT")
    if (
        any(
            provenance[key] != sample[key]
            for key in ("job_id", "account_id", "region", "environment")
        )
        or provenance["workflow_run_id"] != workflow_run_id
    ):
        raise PilotMeasurementError("PILOT_PROVENANCE_BINDING")
    start = _timestamp(provenance["window_start"], "PILOT_PROVENANCE_TIME")
    end = _timestamp(provenance["window_end"], "PILOT_PROVENANCE_TIME")
    if end <= start:
        raise PilotMeasurementError("PILOT_PROVENANCE_WINDOW")
    if (
        sample["sample_kind"] == "pilot"
        and source["locator"].startswith("inline://")
        and pilot_id != "synthetic-fixture"
    ):
        raise PilotMeasurementError("PILOT_INLINE_SOURCE")
    if (
        sample["sample_kind"] == "pilot"
        and source["sensitivity"] == "protected-reference"
    ):
        raise PilotMeasurementError("PILOT_PROTECTED_SOURCE")


def _validate_events(
    sample: Mapping[str, Any], window_start: datetime, window_end: datetime
) -> None:
    events = sample["events"]
    if not isinstance(events, list) or not events:
        raise PilotMeasurementError("PILOT_EVENTS_SHAPE")
    seen: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping):
            raise PilotMeasurementError("PILOT_EVENT_SHAPE")
        _require_keys(event, {"event_id", "kind", "at"}, "PILOT_EVENT_SHAPE")
        event_id = _text(event["event_id"], "PILOT_EVENT_ID", maximum=96)
        if event_id in seen:
            raise PilotMeasurementError("PILOT_DUPLICATE_EVENT")
        seen.add(event_id)
        _text(event["kind"], "PILOT_EVENT_KIND", maximum=96)
        event_time = _timestamp(event["at"], "PILOT_EVENT_TIME")
        if not window_start <= event_time <= window_end:
            raise PilotMeasurementError("PILOT_EVENT_OUTSIDE_WINDOW")


def _validate_effort(
    sample: Mapping[str, Any], window_start: datetime, window_end: datetime
) -> None:
    intervals = sample["effort_intervals"]
    if not isinstance(intervals, list):
        raise PilotMeasurementError("PILOT_EFFORT_SHAPE")
    occupied: list[tuple[datetime, datetime]] = []
    for interval in intervals:
        if not isinstance(interval, Mapping):
            raise PilotMeasurementError("PILOT_EFFORT_SHAPE")
        _require_keys(
            interval, {"interval_id", "category", "start", "end"}, "PILOT_EFFORT_SHAPE"
        )
        _text(interval["interval_id"], "PILOT_EFFORT_ID", maximum=96)
        if interval["category"] not in EFFORT_CATEGORIES:
            raise PilotMeasurementError("PILOT_EFFORT_CATEGORY")
        start = _timestamp(interval["start"], "PILOT_EFFORT_TIME")
        end = _timestamp(interval["end"], "PILOT_EFFORT_TIME")
        if start < window_start or end > window_end:
            raise PilotMeasurementError("PILOT_EFFORT_OUTSIDE_WINDOW")
        if end <= start:
            raise PilotMeasurementError("PILOT_EFFORT_ORDER")
        if any(
            start < previous_end and end > previous_start
            for previous_start, previous_end in occupied
        ):
            raise PilotMeasurementError("PILOT_EFFORT_OVERLAP")
        occupied.append((start, end))


def _validate_sample(
    sample: Mapping[str, Any],
    *,
    pilot_id: str,
    expected_kind: str,
    workflow_run_id: str,
) -> None:
    required = {
        "sample_id",
        "sample_kind",
        "repository",
        "source_revision",
        "job_id",
        "owner",
        "risk_class",
        "complexity_class",
        "environment",
        "account_id",
        "region",
        "module_version",
        "workflow_version",
        "window_start",
        "window_end",
        "approval_record_sha256",
        "events",
        "effort_intervals",
        "review_cycles",
        "failed_checks",
        "manual_interventions",
        "findings",
        "controls",
        "reliability",
        "qualitative",
        "source_refs",
    }
    if sample.get("sample_kind") == "pilot":
        required.update(
            {
                "deployment_identity_sha256",
                "target_manifest_sha256",
                "config_sha256",
                "schedule_generation",
            }
        )
    _require_keys(sample, required, "PILOT_SAMPLE_SHAPE")
    _text(sample["sample_id"], "PILOT_SAMPLE_ID", maximum=96)
    if sample["sample_kind"] not in SAMPLE_KINDS:
        raise PilotMeasurementError("PILOT_SAMPLE_KIND")
    if sample["sample_kind"] != expected_kind:
        raise PilotMeasurementError("PILOT_SAMPLE_PACKAGE_MISMATCH")
    _text(sample["repository"], "PILOT_SAMPLE_FIELD")
    _hash(sample["source_revision"], "PILOT_SAMPLE_REVISION", SHA1)
    if not JOB_ID.fullmatch(str(sample["job_id"])):
        raise PilotMeasurementError("PILOT_JOB_ID")
    for key in (
        "owner",
        "risk_class",
        "complexity_class",
        "environment",
        "region",
        "module_version",
        "workflow_version",
    ):
        _text(sample[key], "PILOT_SAMPLE_FIELD")
    if not ACCOUNT.fullmatch(str(sample["account_id"])):
        raise PilotMeasurementError("PILOT_ACCOUNT_FORMAT")
    window_start = _timestamp(sample["window_start"], "PILOT_SAMPLE_TIME")
    window_end = _timestamp(sample["window_end"], "PILOT_SAMPLE_TIME")
    if window_end <= window_start:
        raise PilotMeasurementError("PILOT_SAMPLE_WINDOW")
    _hash(sample["approval_record_sha256"], "PILOT_APPROVAL_DIGEST")
    if sample["sample_kind"] == "pilot":
        for key in (
            "deployment_identity_sha256",
            "target_manifest_sha256",
            "config_sha256",
        ):
            _hash(sample[key], "PILOT_DEPLOYMENT_BINDING")
        _positive_int(sample["schedule_generation"], "PILOT_SCHEDULE_GENERATION")
    for key in ("review_cycles", "failed_checks", "manual_interventions"):
        _positive_int(sample[key], "PILOT_SAMPLE_COUNT")
    _validate_events(sample, window_start, window_end)
    _validate_effort(sample, window_start, window_end)
    for key in ("findings", "controls", "qualitative", "source_refs"):
        if not isinstance(sample[key], list):
            raise PilotMeasurementError("PILOT_SAMPLE_COLLECTION")
    reliability = sample["reliability"]
    if not isinstance(reliability, Mapping):
        raise PilotMeasurementError("PILOT_RELIABILITY_SHAPE")
    _require_keys(
        reliability,
        {
            "expected",
            "started",
            "successful",
            "failed",
            "overdue",
            "missed",
            "duplicate",
            "ambiguous",
            "false_alerts",
            "lost_alerts",
            "reruns",
            "incidents",
            "alert_detection_seconds",
            "alert_delivery_seconds",
            "recovery_rto_seconds",
        },
        "PILOT_RELIABILITY_SHAPE",
    )
    for key in (
        "expected",
        "started",
        "successful",
        "failed",
        "overdue",
        "missed",
        "duplicate",
        "ambiguous",
        "false_alerts",
        "lost_alerts",
        "reruns",
        "incidents",
    ):
        _positive_int(reliability[key], "PILOT_RELIABILITY_COUNT")
    for key in (
        "alert_detection_seconds",
        "alert_delivery_seconds",
        "recovery_rto_seconds",
    ):
        values = reliability[key]
        if not isinstance(values, list) or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or value < 0
            for value in values
        ):
            raise PilotMeasurementError("PILOT_RELIABILITY_LATENCY")
    if sample["sample_kind"] == "pilot" and not sample["controls"]:
        raise PilotMeasurementError("PILOT_CONTROLS_REQUIRED")
    if sample["sample_kind"] == "pilot" and not sample["qualitative"]:
        raise PilotMeasurementError("PILOT_QUALITATIVE_REQUIRED")
    for finding in sample["findings"]:
        if not isinstance(finding, Mapping):
            raise PilotMeasurementError("PILOT_FINDING_SHAPE")
        _require_keys(
            finding, {"finding_id", "category", "disposition"}, "PILOT_FINDING_SHAPE"
        )
        _text(finding["finding_id"], "PILOT_FINDING_ID", maximum=96)
        _text(finding["category"], "PILOT_FINDING_CATEGORY", maximum=96)
        if finding["disposition"] not in {
            "prevented",
            "review-found",
            "exception",
            "reopened",
            "unresolved",
        }:
            raise PilotMeasurementError("PILOT_FINDING_DISPOSITION")
    for control in sample["controls"]:
        if not isinstance(control, Mapping):
            raise PilotMeasurementError("PILOT_CONTROL_SHAPE")
        _require_keys(
            control,
            {
                "control_id",
                "generation",
                "result",
                "readiness_evidence_sha256",
                "source_ref_id",
            },
            "PILOT_CONTROL_SHAPE",
        )
        _text(control["control_id"], "PILOT_CONTROL_ID", maximum=96)
        _text(control["generation"], "PILOT_CONTROL_GENERATION", maximum=96)
        if control["result"] != "passed":
            raise PilotMeasurementError("PILOT_CONTROL_NOT_PASSED")
        _hash(control["readiness_evidence_sha256"], "PILOT_CONTROL_DIGEST")
        _text(control["source_ref_id"], "PILOT_CONTROL_SOURCE", maximum=96)
    for item in sample["qualitative"]:
        if not isinstance(item, Mapping):
            raise PilotMeasurementError("PILOT_QUALITATIVE_SHAPE")
        _require_keys(
            item, {"finding_code", "role", "collected_at"}, "PILOT_QUALITATIVE_SHAPE"
        )
        _text(item["finding_code"], "PILOT_QUALITATIVE_CODE", maximum=96)
        _text(item["role"], "PILOT_QUALITATIVE_ROLE", maximum=96)
        collected_at = _timestamp(item["collected_at"], "PILOT_QUALITATIVE_TIME")
        if not window_start <= collected_at <= window_end:
            raise PilotMeasurementError("PILOT_QUALITATIVE_OUTSIDE_WINDOW")
    source_ids: set[str] = set()
    sources_by_id: dict[str, Mapping[str, Any]] = {}
    for source in sample["source_refs"]:
        if not isinstance(source, Mapping):
            raise PilotMeasurementError("PILOT_SOURCE_SHAPE")
        _validate_source_ref(
            source,
            sample,
            pilot_id=pilot_id,
            workflow_run_id=workflow_run_id,
        )
        provenance = source["provenance"]
        if provenance["source_revision"] != sample["source_revision"]:
            raise PilotMeasurementError("PILOT_PROVENANCE_REVISION")
        if provenance["repository"] != sample["repository"]:
            raise PilotMeasurementError("PILOT_PROVENANCE_REPOSITORY")
        provenance_start = _timestamp(
            provenance["window_start"], "PILOT_PROVENANCE_TIME"
        )
        provenance_end = _timestamp(provenance["window_end"], "PILOT_PROVENANCE_TIME")
        if provenance_start < window_start or provenance_end > window_end:
            raise PilotMeasurementError("PILOT_PROVENANCE_OUTSIDE_WINDOW")
        source_id = str(source["source_id"])
        if source_id in source_ids:
            raise PilotMeasurementError("PILOT_DUPLICATE_SOURCE")
        source_ids.add(source_id)
        sources_by_id[source_id] = source
    for control in sample["controls"]:
        if control["source_ref_id"] not in source_ids:
            raise PilotMeasurementError("PILOT_CONTROL_SOURCE")
        if sample["sample_kind"] == "pilot":
            if control["generation"] != str(sample["schedule_generation"]):
                raise PilotMeasurementError("PILOT_CONTROL_GENERATION")
            if sources_by_id[control["source_ref_id"]]["kind"] != "readiness":
                raise PilotMeasurementError("PILOT_CONTROL_SOURCE_KIND")
    if sample["sample_kind"] == "pilot" and sample["job_id"].split("/")[0] == "fixture":
        if pilot_id != "synthetic-fixture":
            raise PilotMeasurementError("PILOT_FIXTURE_BINDING")


def validate_measurement_inputs(
    definition: Mapping[str, Any],
    baseline: Mapping[str, Any],
    pilot: Mapping[str, Any],
) -> dict[str, Any]:
    definition_summary = validate_measurement_definition(definition)
    if not isinstance(definition.get("bindings"), Mapping):
        raise PilotMeasurementError("PILOT_BINDINGS_REQUIRED")
    _validate_bindings(definition["bindings"])
    for package, code in (
        (baseline, "PILOT_BASELINE_SHAPE"),
        (pilot, "PILOT_PILOT_SHAPE"),
    ):
        _require_keys(package, {"package_version", "samples"}, code)
        if package["package_version"] != "1.0.0" or not isinstance(
            package["samples"], list
        ):
            raise PilotMeasurementError(code)
    sample_ids: set[str] = set()
    measurement_start = _timestamp(
        definition["observation_window"]["start"], "PILOT_WINDOW_TIME"
    )
    measurement_end = _timestamp(
        definition["observation_window"]["end"], "PILOT_WINDOW_TIME"
    )
    for package, expected_kind in (
        (baseline, "baseline"),
        (pilot, "pilot"),
    ):
        for sample in package["samples"]:
            if not isinstance(sample, Mapping):
                raise PilotMeasurementError("PILOT_SAMPLE_SHAPE")
            if sample.get("sample_id") in sample_ids:
                raise PilotMeasurementError("PILOT_DUPLICATE_SAMPLE")
            _validate_sample(
                sample,
                pilot_id=str(definition["bindings"]["pilot_id"]),
                expected_kind=expected_kind,
                workflow_run_id=str(definition["bindings"]["workflow_run_id"]),
            )
            bindings = definition["bindings"]
            for key in ("account_id", "region", "environment"):
                if sample[key] != bindings[key]:
                    raise PilotMeasurementError("PILOT_BINDING_MISMATCH")
            if sample["sample_kind"] == "pilot" and sample["sample_id"].split("/")[
                0
            ] != str(bindings["pilot_id"]):
                raise PilotMeasurementError("PILOT_PILOT_ID_MISMATCH")
            sample_start = _timestamp(sample["window_start"], "PILOT_SAMPLE_TIME")
            sample_end = _timestamp(sample["window_end"], "PILOT_SAMPLE_TIME")
            if sample_start < measurement_start or sample_end > measurement_end:
                raise PilotMeasurementError("PILOT_SAMPLE_OUTSIDE_WINDOW")
            sample_ids.add(str(sample["sample_id"]))
    _validate_sanitized(
        {"definition": definition, "baseline": baseline, "pilot": pilot}
    )
    return definition_summary


def _event_time(
    sample: Mapping[str, Any], kind: str, *, latest: bool = False
) -> datetime | None:
    values = [
        _timestamp(event["at"], "PILOT_EVENT_TIME")
        for event in sample["events"]
        if event["kind"] == kind
    ]
    if not values:
        return None
    return max(values) if latest else min(values)


def _duration(sample: Mapping[str, Any], start_kind: str, stop_kind: str) -> int | None:
    start = _event_time(sample, start_kind)
    stop = _event_time(sample, stop_kind)
    if start is None or stop is None:
        return None
    seconds = int((stop - start).total_seconds())
    if seconds < 0:
        raise PilotMeasurementError("PILOT_EVENT_ORDER")
    return seconds


def _effort_seconds(sample: Mapping[str, Any], category: str) -> int:
    return sum(
        int(
            (
                _timestamp(item["end"], "PILOT_EFFORT_TIME")
                - _timestamp(item["start"], "PILOT_EFFORT_TIME")
            ).total_seconds()
        )
        for item in sample["effort_intervals"]
        if item["category"] == category
    )


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _metric_value(
    metric: Mapping[str, Any], samples: list[Mapping[str, Any]]
) -> tuple[Any, str, list[str], list[str]]:
    calculation = metric["calculation"]
    included = [str(sample["sample_id"]) for sample in samples]
    excluded: list[str] = []
    if not samples:
        return None, "UNKNOWN", [], []
    if calculation == "active_setup_seconds":
        effort_values = [
            _effort_seconds(sample, "active_engineering") for sample in samples
        ]
        return (
            _median([float(value) for value in effort_values]),
            "MEASURED",
            included,
            excluded,
        )
    effort_calculations = {
        "review_effort_seconds": "review",
        "approval_wait_seconds": "approval_wait",
        "deployment_wait_seconds": "deployment_wait",
        "unrelated_interruption_seconds": "unrelated_interruption",
        "total_active_effort_seconds": "active_engineering",
    }
    if calculation in effort_calculations:
        if calculation == "total_active_effort_seconds":
            effort_values = [
                sum(
                    _effort_seconds(sample, category)
                    for category in ("active_engineering", "review")
                )
                for sample in samples
            ]
        else:
            effort_values = [
                _effort_seconds(sample, effort_calculations[calculation])
                for sample in samples
            ]
        return (
            _median([float(value) for value in effort_values]),
            "MEASURED",
            included,
            excluded,
        )
    if calculation == "active_effort_reduction_ratio":
        return None, "INCOMPLETE", [], included
    if calculation in {"elapsed_lead_seconds", "time_to_success_seconds"}:
        values: list[int] = []
        for sample in samples:
            value = _duration(sample, metric["start_event"], metric["stop_event"])
            if value is None:
                excluded.append(str(sample["sample_id"]))
            else:
                values.append(value)
        if not values:
            return None, "INCOMPLETE", [], excluded
        included = [sample_id for sample_id in included if sample_id not in excluded]
        return (
            _median([float(value) for value in values]),
            "MEASURED",
            included,
            excluded,
        )
    if calculation == "review_cycles":
        return (
            _median([float(sample["review_cycles"]) for sample in samples]),
            "MEASURED",
            included,
            excluded,
        )
    if calculation == "failed_checks":
        return (
            sum(int(sample["failed_checks"]) for sample in samples),
            "MEASURED",
            included,
            excluded,
        )
    if calculation == "manual_interventions":
        return (
            sum(int(sample["manual_interventions"]) for sample in samples),
            "MEASURED",
            included,
            excluded,
        )
    if calculation == "finding_disposition_counts":
        counts = {
            key: 0
            for key in {
                "prevented",
                "review-found",
                "exception",
                "reopened",
                "unresolved",
            }
        }
        for sample in samples:
            for finding in sample["findings"]:
                counts[finding["disposition"]] += 1
        return counts, "MEASURED", included, excluded
    if calculation == "control_coverage_ratio":
        total = sum(len(sample["controls"]) for sample in samples)
        passed = sum(
            sum(control["result"] == "passed" for control in sample["controls"])
            for sample in samples
        )
        if total == 0:
            return None, "UNKNOWN", [], included
        return passed / total, "MEASURED", included, excluded
    reliability_keys = {
        "occurrence_outcomes": (
            "expected",
            "started",
            "successful",
            "failed",
            "overdue",
            "missed",
            "duplicate",
            "ambiguous",
            "false_alerts",
            "lost_alerts",
            "reruns",
            "incidents",
        ),
        "alert_latency_seconds": ("alert_detection_seconds", "alert_delivery_seconds"),
        "recovery_rto_seconds": ("recovery_rto_seconds",),
    }
    if calculation in reliability_keys:
        result: dict[str, Any] = {}
        for key in reliability_keys[calculation]:
            values = (
                [value for sample in samples for value in sample["reliability"][key]]
                if key.endswith("seconds")
                else [sum(sample["reliability"][key] for sample in samples)]
            )
            result[key] = (
                _median([float(value) for value in values]) if values else None
            )
        if all(value is None for value in result.values()):
            return None, "INCOMPLETE", [], included
        return result, "MEASURED", included, excluded
    if calculation == "qualitative_categories":
        categories: dict[str, int] = {}
        for sample in samples:
            for item in sample["qualitative"]:
                categories[item["finding_code"]] = (
                    categories.get(item["finding_code"], 0) + 1
                )
        return (
            categories,
            "MEASURED" if categories else "UNKNOWN",
            included if categories else [],
            excluded,
        )
    raise PilotMeasurementError("PILOT_METRIC_CALCULATION")


def _compare(value: Any, target: Mapping[str, Any]) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "NOT_EVALUATED"
    expected = float(target["value"])
    actual = float(value)
    operator = target["operator"]
    passed = {
        "lt": actual < expected,
        "lte": actual <= expected,
        "eq": actual == expected,
        "gte": actual >= expected,
        "gt": actual > expected,
    }[operator]
    return "TARGET_MET" if passed else "TARGET_MISSED"


def _comparable(
    metric: Mapping[str, Any],
    baseline_samples: list[Mapping[str, Any]],
    pilot_samples: list[Mapping[str, Any]],
) -> bool:
    dimensions = metric["comparability_dimensions"]
    baseline_population = {
        tuple(str(sample[dimension]) for dimension in dimensions)
        for sample in baseline_samples
    }
    pilot_population = {
        tuple(str(sample[dimension]) for dimension in dimensions)
        for sample in pilot_samples
    }
    if baseline_population != pilot_population:
        return False
    return all(
        sum(
            tuple(str(sample[dimension]) for dimension in dimensions) == population
            for sample in baseline_samples
        )
        == sum(
            tuple(str(sample[dimension]) for dimension in dimensions) == population
            for sample in pilot_samples
        )
        for population in baseline_population
    )


def measure_pilot(
    definition: Mapping[str, Any],
    baseline: Mapping[str, Any],
    pilot: Mapping[str, Any],
) -> dict[str, Any]:
    definition = copy.deepcopy(definition)
    baseline = copy.deepcopy(baseline)
    pilot = copy.deepcopy(pilot)
    for package in (baseline, pilot):
        for sample in package["samples"]:
            for key in (
                "events",
                "effort_intervals",
                "findings",
                "controls",
                "qualitative",
                "source_refs",
            ):
                sample[key] = sorted(
                    sample[key],
                    key=lambda item: str(
                        item.get(
                            "event_id",
                            item.get(
                                "interval_id",
                                item.get(
                                    "finding_id",
                                    item.get(
                                        "control_id",
                                        item.get(
                                            "finding_code", item.get("source_id", "")
                                        ),
                                    ),
                                ),
                            ),
                        )
                    ),
                )
    try:
        summary = validate_measurement_inputs(definition, baseline, pilot)
    except PilotMeasurementError as error:
        recoverable = {
            "PILOT_DUPLICATE_SAMPLE",
            "PILOT_DUPLICATE_SOURCE",
            "PILOT_DUPLICATE_EVENT",
            "PILOT_EFFORT_OVERLAP",
            "PILOT_EFFORT_OUTSIDE_WINDOW",
            "PILOT_EVENT_OUTSIDE_WINDOW",
            "PILOT_SAMPLE_OUTSIDE_WINDOW",
            "PILOT_PROVENANCE_OUTSIDE_WINDOW",
            "PILOT_EVENT_ORDER",
        }
        if str(error) not in recoverable:
            raise
        validate_measurement_definition(definition)
        rejected_result: dict[str, Any] = {
            "schema_version": "1.0.0",
            "calculation_version": definition["calculation_version"],
            "status": "INCOMPLETE",
            "bindings": dict(definition["bindings"]),
            "definition_id": definition["definition_id"],
            "definition_sha256": _digest(definition),
            "baseline_package_sha256": _digest(baseline),
            "pilot_package_sha256": _digest(pilot),
            "source_reference_manifest": [],
            "baseline_sample_ids": [],
            "pilot_sample_ids": [],
            "metrics": [
                {
                    "metric_id": metric["metric_id"],
                    "calculation": metric["calculation"],
                    "unit": metric["unit"],
                    "status": "INCOMPLETE",
                    "value": None,
                    "baseline_value": None,
                    "comparison": "INCOMPLETE",
                    "sample_size": 0,
                    "included_sample_ids": [],
                    "excluded_sample_ids": [],
                    "reason": str(error),
                }
                for metric in validate_measurement_definition(definition)["metrics"]
            ],
            "limitations": [f"Evidence package requires review: {error}"],
            "generated_at": definition["generated_at"],
        }
        rejected_result["evidence_sha256"] = _digest(rejected_result)
        return rejected_result
    baseline_samples = sorted(
        baseline["samples"], key=lambda sample: sample["sample_id"]
    )
    pilot_samples = sorted(pilot["samples"], key=lambda sample: sample["sample_id"])
    results: list[dict[str, Any]] = []
    for metric in summary["metrics"]:
        if metric["calculation"] == "active_effort_reduction_ratio" and pilot_samples:
            pilot_efforts = [
                _effort_seconds(sample, "active_engineering")
                for sample in pilot_samples
            ]
            value: Any
            status: str
            included: list[str]
            excluded: list[str]
            value, status, included, excluded = (
                _median([float(item) for item in pilot_efforts]),
                "MEASURED",
                [str(sample["sample_id"]) for sample in pilot_samples],
                [],
            )
        else:
            value, status, included, excluded = _metric_value(metric, pilot_samples)
        baseline_value: Any = None
        comparison = "NOT_EVALUATED"
        if baseline_samples and pilot_samples:
            if not _comparable(metric, baseline_samples, pilot_samples):
                status = "NOT_COMPARABLE"
                comparison = "NOT_COMPARABLE"
            else:
                if metric["calculation"] == "active_effort_reduction_ratio":
                    baseline_value = _median(
                        [
                            float(_effort_seconds(sample, "active_engineering"))
                            for sample in baseline_samples
                        ]
                    )
                    baseline_status = "MEASURED"
                else:
                    baseline_value, baseline_status, _, _ = _metric_value(
                        metric, baseline_samples
                    )
                if status == "MEASURED" and baseline_status == "MEASURED":
                    if metric["calculation"] == "active_effort_reduction_ratio":
                        baseline_efforts = [
                            _effort_seconds(sample, "active_engineering")
                            for sample in baseline_samples
                        ]
                        baseline_value = _median(
                            [float(item) for item in baseline_efforts]
                        )
                        value = (
                            (baseline_value - value) / baseline_value
                            if baseline_value
                            else None
                        )
                        comparison = _compare(value, metric["target"])
                    else:
                        comparison = _compare(value, metric["target"])
                elif baseline_status != "MEASURED":
                    status = baseline_status
                    comparison = baseline_status
        elif not baseline_samples:
            status = "UNKNOWN"
            comparison = "UNKNOWN_BASELINE"
        elif not pilot_samples:
            status = "UNKNOWN"
        results.append(
            {
                "metric_id": metric["metric_id"],
                "calculation": metric["calculation"],
                "unit": metric["unit"],
                "status": status,
                "value": value,
                "baseline_value": baseline_value,
                "comparison": comparison,
                "sample_size": len(included),
                "included_sample_ids": included,
                "excluded_sample_ids": excluded,
                "reason": ""
                if status == "MEASURED"
                else comparison.lower().replace("_", " "),
            }
        )
    overall = (
        "MEASURED"
        if results and all(item["status"] == "MEASURED" for item in results)
        else "INCOMPLETE"
    )
    if any(item["status"] == "NOT_COMPARABLE" for item in results):
        overall = "NOT_COMPARABLE"
    elif any(item["status"] == "UNKNOWN" for item in results):
        overall = "UNKNOWN"
    if not baseline_samples or not pilot_samples:
        overall = "UNKNOWN"
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "calculation_version": definition["calculation_version"],
        "status": overall,
        "bindings": dict(definition["bindings"]),
        "definition_id": definition["definition_id"],
        "definition_sha256": _digest(definition),
        "baseline_package_sha256": _digest(baseline),
        "pilot_package_sha256": _digest(pilot),
        "source_reference_manifest": sorted(
            [
                {"source_id": source["source_id"], "sha256": source["sha256"]}
                for package in (baseline, pilot)
                for sample in package["samples"]
                for source in sample["source_refs"]
            ],
            key=lambda item: item["source_id"],
        ),
        "baseline_sample_ids": [sample["sample_id"] for sample in baseline_samples],
        "pilot_sample_ids": [sample["sample_id"] for sample in pilot_samples],
        "metrics": results,
        "limitations": [],
        "generated_at": definition["generated_at"],
    }
    if not baseline_samples:
        result["limitations"].append(
            "Baseline evidence is UNKNOWN; no estimate was substituted."
        )
    if not pilot_samples:
        result["limitations"].append("No pilot evidence was supplied.")
    result["evidence_sha256"] = _digest(result)
    return result


def reviewer_report(result: Mapping[str, Any]) -> str:
    def markdown(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = [
        "# Pilot Measurement Report",
        "",
        f"- Status: `{result['status']}`",
        f"- Pilot: `{result['bindings']['pilot_id']}`",
        f"- Generated at: `{result['generated_at']}`",
        "",
        "| Metric | Status | Value | Baseline | Comparison |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for metric in result["metrics"]:
        lines.append(
            f"| {markdown(metric['metric_id'])} | {markdown(metric['status'])} | {markdown(metric['value'])} | {markdown(metric['baseline_value'])} | {markdown(metric['comparison'])} |"
        )
    if result["limitations"]:
        lines.extend(
            ["", "## Limitations", "", *[f"- {item}" for item in result["limitations"]]]
        )
    lines.extend(
        [
            "",
            "This report measures evidence only; it is not a rollout or acceptance decision.",
            "",
        ]
    )
    return "\n".join(lines)
