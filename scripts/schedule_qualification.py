"""Credential-free schedule qualification and evidence boundary.

The protected workflow supplies adapters for a disposable Cell. This module
validates the manifest and scenario results before they can be projected into
the Story 4.3 readiness envelope; it never treats caller counters as proof.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

import rfc8785

from tests.contract.support.contracts import (
    expand_schedule,
    occurrence_id,
    schedule_generation,
    validate_schedule_contract,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
REGION = re.compile(r"^[a-z]{2}(?:-[a-z0-9]+)+-[0-9]+$")
TIMESTAMP = "%Y-%m-%dT%H:%M:%S.%fZ"
FORBIDDEN = re.compile(
    r"secret|password|credential|private|token|raw_config|plan", re.I
)


class QualificationError(ValueError):
    """A deterministic qualification input or result failed closed."""


def _canonical(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError) as error:
        raise QualificationError("QUALIFICATION_JSON") from error


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _sanitized_json(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str) or FORBIDDEN.search(key):
                raise QualificationError("QUALIFICATION_SENSITIVE")
            _sanitized_json(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _sanitized_json(child, f"{path}[{index}]")
    elif not isinstance(value, (str, int, float, bool, type(None))):
        raise QualificationError("QUALIFICATION_JSON")
    elif isinstance(value, str) and FORBIDDEN.search(value):
        raise QualificationError("QUALIFICATION_SENSITIVE")


def build_qualification_manifest(
    *,
    release_version: str,
    compatibility_package: str,
    account_id: str,
    region: str,
    cell_identity: str,
    test_configuration: Mapping[str, Any],
    policy_versions: Mapping[str, str],
    evidence: Mapping[str, Any] | None = None,
    evidence_sha256: str | None = None,
    bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build a canonical, sanitized and independently checksum-bound manifest."""

    if not re.fullmatch(r"[0-9]{12}", account_id) or not REGION.fullmatch(region):
        raise QualificationError("QUALIFICATION_BINDING")
    if not release_version or not compatibility_package or not cell_identity:
        raise QualificationError("QUALIFICATION_BINDING")
    _sanitized_json(test_configuration)
    _sanitized_json(policy_versions)
    if not policy_versions or any(
        not isinstance(value, str) or not value for value in policy_versions.values()
    ):
        raise QualificationError("QUALIFICATION_POLICY")
    if evidence is None:
        raise QualificationError("QUALIFICATION_EVIDENCE_REQUIRED")
    _sanitized_json(evidence)
    calculated_evidence = _digest(evidence)
    if evidence_sha256 is not None and evidence_sha256 != calculated_evidence:
        raise QualificationError("QUALIFICATION_DIGEST")
    if bindings is None:
        raise QualificationError("QUALIFICATION_BINDING")
    required_bindings = {
        "repository",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "plan_sha256",
        "deployment_identity_sha256",
        "job_id",
        "config_sha256",
        "schedule_generation",
        "target_manifest_sha256",
    }
    if set(bindings) != required_bindings:
        raise QualificationError("QUALIFICATION_BINDING")
    if not re.fullmatch(r"[0-9a-f]{40}", bindings["source_commit"]):
        raise QualificationError("QUALIFICATION_BINDING")
    for key in required_bindings - {
        "repository",
        "workflow_run_id",
        "job_id",
        "source_commit",
        "workflow_sha",
    }:
        if not SHA256.fullmatch(bindings[key]) and key != "workflow_sha":
            raise QualificationError("QUALIFICATION_BINDING")
    if not re.fullmatch(r"[0-9a-f]{40}", bindings["workflow_sha"]):
        raise QualificationError("QUALIFICATION_BINDING")
    body: dict[str, Any] = {
        "schema_version": "1.0.0",
        "provenance": "disposable-qualification",
        "release_version": release_version,
        "compatibility_package": compatibility_package,
        "account_id": account_id,
        "region": region,
        "cell_identity": cell_identity,
        "test_configuration": dict(test_configuration),
        "policy_versions": dict(policy_versions),
        "evidence_sha256": calculated_evidence,
        "bindings": dict(bindings),
    }
    body["manifest_sha256"] = _digest(body)
    return body


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise QualificationError("QUALIFICATION_TIMESTAMP")
    try:
        parsed = datetime.strptime(value, TIMESTAMP).replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise QualificationError("QUALIFICATION_TIMESTAMP") from error
    return parsed


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def materialize_expectations(
    *,
    job_id: str,
    schedule_generation: str,
    schedule: dict[str, Any],
    window_start: str,
    completion_window_seconds: int = 3600,
) -> tuple[dict[str, Any], ...]:
    """Materialize a non-empty 24-hour expectation horizon independently of delivery."""

    if not re.fullmatch(r"[0-9a-f]{64}", schedule_generation) or not job_id:
        raise QualificationError("QUALIFICATION_BINDING")
    if type(completion_window_seconds) is not int or completion_window_seconds <= 0:
        raise QualificationError("QUALIFICATION_DEADLINE")
    try:
        validate_schedule_contract(schedule)
        if schedule_generation_value(schedule) != schedule_generation:
            raise QualificationError("QUALIFICATION_GENERATION_MISMATCH")
        start = _parse_timestamp(window_start)
        end = start + timedelta(hours=24)
        end_text = _format_timestamp(end)
        times = expand_schedule(schedule, window_start, end_text)
    except QualificationError:
        raise
    except Exception as error:
        raise QualificationError("QUALIFICATION_SCHEDULE") from error
    if not times:
        raise QualificationError("QUALIFICATION_HORIZON")
    return tuple(
        {
            "occurrence_id": occurrence_id(
                job_id,
                schedule_generation,
                str(int(_parse_timestamp(value).timestamp() // 60)),
            ),
            "job_id": job_id,
            "schedule_generation": schedule_generation,
            "scheduled_time": value,
            "completion_deadline": _format_timestamp(
                _parse_timestamp(value) + timedelta(seconds=completion_window_seconds)
            ),
            "lifecycle": "EXPECTED",
            "source": "independent-materializer",
        }
        for value in times
    )


def schedule_generation_value(schedule: dict[str, Any]) -> str:
    try:
        return schedule_generation(schedule)
    except Exception as error:
        raise QualificationError("QUALIFICATION_SCHEDULE") from error


def classify_delivery(
    events: Sequence[Mapping[str, Any]],
    *,
    deadline_reached: bool,
    expected_occurrence: Mapping[str, str] | None = None,
) -> str:
    """Classify authenticated delivery evidence and reject malformed records."""

    if type(deadline_reached) is not bool:
        raise QualificationError("QUALIFICATION_DEADLINE")
    accepted: list[Mapping[str, Any]] = []
    for event in events:
        if not isinstance(event, Mapping):
            raise QualificationError("QUALIFICATION_EVENT")
        if event.get("accepted") is not True:
            continue
        if type(event.get("attempt")) is not int or event["attempt"] < 0:
            raise QualificationError("QUALIFICATION_ATTEMPT")
        for field in ("occurrence_id", "job_id", "schedule_generation", "emitted_at"):
            if not isinstance(event.get(field), str) or not event[field]:
                raise QualificationError("QUALIFICATION_EVENT")
        _parse_timestamp(event["emitted_at"])
        if expected_occurrence and any(
            event.get(key) != expected_occurrence.get(key)
            for key in ("occurrence_id", "job_id", "schedule_generation")
        ):
            raise QualificationError("QUALIFICATION_EVENT_BINDING")
        accepted.append(event)
    attempts = [event["attempt"] for event in accepted]
    if len(accepted) != len(set(attempts)) or len(set(attempts)) > 1:
        return "DUPLICATE"
    if not accepted:
        return "MISSED" if deadline_reached else "EXPECTED"
    return "STARTED"


def qualify_healthy_windows(windows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Require twenty exact-once correlated healthy windows and no alerts."""

    if len(windows) != 20:
        raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
    occurrence_ids: set[str] = set()
    for window in windows:
        if not isinstance(window, Mapping):
            raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
        for key in ("expected", "accepted", "alerts", "cell_health_alerts"):
            if type(window.get(key)) is not int:
                raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
        occurrence_id_value = window.get("occurrence_id")
        if not isinstance(occurrence_id_value, str) or not occurrence_id_value:
            raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
        if occurrence_id_value in occurrence_ids:
            raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
        occurrence_ids.add(occurrence_id_value)
        if any(window.get(key) != 0 for key in ("alerts", "cell_health_alerts")):
            raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
        if window.get("expected") != 1 or window.get("accepted") != 1:
            raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
        if (
            window.get("terminal_state") != "SUCCEEDED"
            or window.get("late") is not False
            or window.get("ambiguous") is not False
        ):
            raise QualificationError("QUALIFICATION_HEALTHY_WINDOWS")
    return {"windows": len(windows), "passed": True, "false_alerts": 0}


def assert_detection_latency(
    observed_seconds: int,
    *,
    threshold_seconds: int = 300,
    state_seconds: int | None = None,
) -> dict[str, int]:
    if type(observed_seconds) is not int or type(threshold_seconds) is not int:
        raise QualificationError("QUALIFICATION_ALERT_LATENCY")
    if state_seconds is not None and type(state_seconds) is not int:
        raise QualificationError("QUALIFICATION_ALERT_LATENCY")
    if (
        observed_seconds < 0
        or threshold_seconds <= 0
        or observed_seconds > threshold_seconds
    ):
        raise QualificationError("QUALIFICATION_ALERT_LATENCY")
    if state_seconds is not None and (
        state_seconds < 0 or state_seconds > observed_seconds
    ):
        raise QualificationError("QUALIFICATION_ALERT_LATENCY")
    return {
        "observed_seconds": observed_seconds,
        "threshold_seconds": threshold_seconds,
    }


def validate_cleanup_inventory(
    resources: Sequence[str], retained: Sequence[str] = ()
) -> dict[str, Any]:
    names = tuple(resources)
    if any(not isinstance(name, str) or not name for name in names):
        raise QualificationError("QUALIFICATION_CLEANUP_INVENTORY")
    if any(not isinstance(name, str) for name in retained):
        raise QualificationError("QUALIFICATION_CLEANUP_INVENTORY")
    retained_set = set(retained)
    if len(set(names)) != len(names) or not retained_set.issubset(names):
        raise QualificationError("QUALIFICATION_CLEANUP_INVENTORY")
    return {
        "deleted": [name for name in names if name not in retained_set],
        "retained": sorted(retained_set),
        "evidence_retention_explicit": bool(retained_set),
    }


def readiness_projection(
    manifest: Mapping[str, Any],
    results: Mapping[str, str],
    expected_bindings: Mapping[str, str],
) -> dict[str, str]:
    """Project only verified schedule controls into the Story 4.3 gate."""

    if manifest.get("manifest_sha256") != _digest(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    ):
        raise QualificationError("QUALIFICATION_MANIFEST_DIGEST")
    if manifest.get("bindings") != dict(expected_bindings):
        raise QualificationError("QUALIFICATION_BINDING")
    required = (
        "schedule-interpretation",
        "expectation-independence",
        "scheduler-delivery",
        "delivery-idempotency",
        "qualification-timing",
        "healthy-windows",
    )
    if any(results.get(control) != "passed" for control in required):
        raise QualificationError("QUALIFICATION_RESULTS")
    controls = {control: "passed" for control in required}
    controls.update(
        {
            control: "blocked"
            for control in (
                "launch-runtime",
                "completion-alerts",
                "security",
                "recovery",
            )
        }
    )
    return controls
