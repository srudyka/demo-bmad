"""Pure, fail-closed qualification checks for completion, deadlines, and alerts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import re
from typing import Any

from scripts.ecs_qualification import _digest, _safe, _task_arn, _timestamp
from scripts.ecs_qualification import validate_cleanup_evidence

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class QualificationError(ValueError):
    """A completion/deadline qualification input failed closed."""


def _require_string(value: Any, code: str, *, maximum: int = 256) -> str:
    try:
        return _safe(value, code, max_length=maximum)
    except ValueError as error:
        raise QualificationError(code) from error


def _parse(value: Any, code: str) -> datetime:
    try:
        _timestamp(value)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise QualificationError(code) from error


def validate_completion_evidence(
    event: Mapping[str, Any], expected: Mapping[str, str]
) -> dict[str, Any]:
    """Validate completion evidence against authenticated task/log context."""

    required = {
        "job_id",
        "job_name",
        "occurrence_id",
        "config_version",
        "schedule_generation",
        "task_arn",
        "deployment_identity_id",
        "log_group",
        "log_stream",
        "attempt_no",
        "start_time",
        "completion_time",
        "status",
        "exit_code",
        "success_marker",
        "source_context",
    }
    expected_required = required - {
        "start_time",
        "completion_time",
        "status",
        "exit_code",
        "success_marker",
        "source_context",
    }
    if not required.issubset(event) or not expected_required.issubset(expected):
        raise QualificationError("COMPLETION_CORRELATION")
    for key in expected_required:
        if event.get(key) != expected.get(key):
            raise QualificationError("COMPLETION_CORRELATION")
    if event.get("attempt_no") != "0":
        raise QualificationError("COMPLETION_ATTEMPT")
    task_arn = event.get("task_arn")
    try:
        _task_arn(task_arn)
    except ValueError as error:
        raise QualificationError("COMPLETION_TASK") from error
    if not SHA256.fullmatch(str(event.get("occurrence_id"))) or not SHA256.fullmatch(
        str(event.get("config_version"))
    ):
        raise QualificationError("COMPLETION_CORRELATION")
    source = event.get("source_context")
    if not isinstance(source, Mapping):
        raise QualificationError("COMPLETION_SOURCE")
    for key in ("account_id", "region", "log_group", "log_stream"):
        if source.get(key) != expected.get(key) and source.get(key) != event.get(key):
            raise QualificationError("COMPLETION_SOURCE")
    start = _parse(event.get("start_time"), "COMPLETION_TIMESTAMP")
    completed = _parse(event.get("completion_time"), "COMPLETION_TIMESTAMP")
    if completed < start:
        raise QualificationError("COMPLETION_TIMESTAMP")
    if event.get("status") != "SUCCESS" or event.get("exit_code") != 0:
        raise QualificationError("COMPLETION_RESULT")
    marker = _require_string(event.get("success_marker"), "COMPLETION_MARKER")
    if marker != "JOB_COMPLETED_SUCCESSFULLY":
        raise QualificationError("COMPLETION_MARKER")
    return {
        "job_id": str(event["job_id"]),
        "job_name": str(event["job_name"]),
        "occurrence_id": str(event["occurrence_id"]),
        "config_version": str(event["config_version"]),
        "schedule_generation": str(event["schedule_generation"]),
        "task_arn": str(task_arn),
        "deployment_identity_id": str(event["deployment_identity_id"]),
        "start_time": str(event["start_time"]),
        "completion_time": str(event["completion_time"]),
        "exit_code": 0,
        "success_marker": marker,
        "log_group": str(event["log_group"]),
        "log_stream": str(event["log_stream"]),
    }


def classify_completion(
    evidence: Mapping[str, Any],
    *,
    ecs_zero_exit: bool,
    deadline_at: str | None = None,
) -> dict[str, Any]:
    """Classify completion only after marker and ECS evidence are both present."""

    if not isinstance(ecs_zero_exit, bool):
        raise QualificationError("COMPLETION_RUNTIME_INPUT")
    if not ecs_zero_exit:
        return {"state": "AMBIGUOUS", "completion_pending": True}
    if deadline_at is not None and _parse(
        evidence.get("completion_time"), "COMPLETION_TIMESTAMP"
    ) > _parse(deadline_at, "DEADLINE_TIMESTAMP"):
        return {"state": "OVERDUE", "completion_pending": False}
    return {"state": "SUCCEEDED", "completion_pending": False}


def reduce_completion_facts(facts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deduplicate immutable completion facts and reject same-ID conflicts."""

    unique: dict[str, Mapping[str, Any]] = {}
    allowed_kinds = {"STARTED", "SUCCESS", "FAILURE", "CONFLICT"}
    for fact in facts:
        if not isinstance(fact, Mapping) or not SHA256.fullmatch(
            str(fact.get("fact_id", ""))
        ):
            raise QualificationError("COMPLETION_FACT")
        digest = fact.get("digest")
        if not SHA256.fullmatch(str(digest or "")):
            raise QualificationError("COMPLETION_FACT")
        if fact.get("kind") not in allowed_kinds:
            raise QualificationError("COMPLETION_KIND")
        if not SHA256.fullmatch(str(fact.get("occurrence_id", ""))):
            raise QualificationError("COMPLETION_FACT")
        if not isinstance(fact.get("task_arn"), str):
            raise QualificationError("COMPLETION_FACT")
        if fact.get("kind") == "SUCCESS" and fact.get("ecs_zero_exit") is not True:
            raise QualificationError("COMPLETION_RUNTIME_INPUT")
        previous = unique.get(str(fact["fact_id"]))
        if previous is not None and previous.get("digest") != digest:
            return {"state": "AMBIGUOUS", "facts": len(unique)}
        unique[str(fact["fact_id"])] = fact
    kinds = {str(item.get("kind")) for item in unique.values()}
    if "CONFLICT" in kinds or {"SUCCESS", "FAILURE"}.issubset(kinds):
        state = "AMBIGUOUS"
    elif "FAILURE" in kinds:
        state = "FAILED"
    elif "SUCCESS" in kinds:
        state = "SUCCEEDED"
    else:
        state = "STARTED"
    return {"state": state, "facts": len(unique)}


def classify_deadline(
    current_state: str,
    *,
    started: bool,
    completion_time: str | None,
    deadline_at: str,
) -> dict[str, Any]:
    """Classify a deadline without cancellation or late-state erasure."""

    if current_state not in {"EXPECTED", "STARTED"}:
        raise QualificationError("DEADLINE_STATE")
    if not isinstance(started, bool):
        raise QualificationError("DEADLINE_INPUT")
    deadline = _parse(deadline_at, "DEADLINE_TIMESTAMP")
    if completion_time is not None:
        completed = _parse(completion_time, "COMPLETION_TIMESTAMP")
        if completed <= deadline:
            return {"state": "SUCCEEDED", "late": False, "automatic_stop": False}
        return {"state": "OVERDUE", "late": True, "automatic_stop": False}
    return {
        "state": "OVERDUE" if started else "MISSED",
        "late": False,
        "automatic_stop": False,
    }


def qualify_partial_batch(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Model ReportBatchItemFailures without acknowledging poison records."""

    if isinstance(records, (str, bytes)):
        raise QualificationError("BATCH")
    seen: set[str] = set()
    failed: list[str] = []
    accepted = 0
    for record in records:
        if not isinstance(record, Mapping):
            raise QualificationError("BATCH")
        message_id = _require_string(record.get("message_id"), "BATCH_MESSAGE")
        if message_id in seen:
            raise QualificationError("BATCH_DUPLICATE")
        seen.add(message_id)
        disposition = record.get("disposition")
        if disposition == "accepted":
            accepted += 1
        elif disposition in {"retry", "quarantine"}:
            failed.append(message_id)
        else:
            raise QualificationError("BATCH_DISPOSITION")
    return {"accepted": accepted, "failed_message_ids": failed}


def qualify_alert_delivery(alerts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Require unique, operator-actionable alert receipts within five minutes."""

    if not alerts:
        raise QualificationError("ALERT_REQUIRED")
    seen: set[str] = set()
    for alert in alerts:
        if not isinstance(alert, Mapping):
            raise QualificationError("ALERT")
        required = {
            "alert_id",
            "deduplication_id",
            "job_id",
            "occurrence_id",
            "state",
            "failure_plane",
            "detected_at",
            "delivered_at",
            "owner",
            "route",
            "runbook_uri",
            "deployment_identity_id",
            "schema_version",
            "account_id",
            "region",
            "environment",
            "notification_target_arn",
            "operator_safe_reason",
        }
        if not required.issubset(alert):
            raise QualificationError("ALERT")
        dedup = str(alert["deduplication_id"])
        if dedup in seen:
            raise QualificationError("ALERT_DEDUPLICATION")
        seen.add(dedup)
        if alert["alert_id"] != dedup or not SHA256.fullmatch(dedup):
            raise QualificationError("ALERT_IDENTITY")
        if alert["schema_version"] != "1.0.0":
            raise QualificationError("ALERT_SCHEMA")
        if alert["state"] not in {"FAILED", "OVERDUE", "MISSED", "AMBIGUOUS"}:
            raise QualificationError("ALERT_SCHEMA")
        if alert["failure_plane"] not in {
            "SCHEDULE",
            "INGRESS",
            "LAUNCH",
            "TASK",
            "COMPLETION",
            "DEADLINE",
            "ALERT_DELIVERY",
            "CELL",
        }:
            raise QualificationError("ALERT_SCHEMA")
        if not re.fullmatch(r"[0-9]{12}", str(alert["account_id"])):
            raise QualificationError("ALERT_SCHEMA")
        if not re.fullmatch(
            r"[a-z]{2}(?:-gov|-iso)?-[a-z]+-[0-9]", str(alert["region"])
        ):
            raise QualificationError("ALERT_SCHEMA")
        if not isinstance(alert["environment"], str) or not alert["environment"]:
            raise QualificationError("ALERT_SCHEMA")
        if not isinstance(alert["notification_target_arn"], str) or not alert[
            "notification_target_arn"
        ].startswith("arn:"):
            raise QualificationError("ALERT_SCHEMA")
        _require_string(alert["operator_safe_reason"], "ALERT_METADATA", maximum=2048)
        if not SHA256.fullmatch(str(alert["occurrence_id"])) or not SHA256.fullmatch(
            str(alert["deployment_identity_id"])
        ):
            raise QualificationError("ALERT_IDENTITY")
        detected = _parse(alert["detected_at"], "ALERT_TIMESTAMP")
        delivered = _parse(alert["delivered_at"], "ALERT_TIMESTAMP")
        if delivered < detected or (delivered - detected).total_seconds() > 300:
            raise QualificationError("ALERT_LATENCY")
        for field in ("owner", "route", "runbook_uri"):
            _require_string(alert[field], "ALERT_METADATA")
        if not str(alert["runbook_uri"]).startswith("https://"):
            raise QualificationError("ALERT_METADATA")
    return {"alerts": len(alerts), "passed": True, "max_latency_seconds": 300}


def qualify_deadline_scanner(scanner: Mapping[str, Any]) -> dict[str, Any]:
    """Require bounded, restart-safe scanner observations."""

    required = {
        "watermark_before",
        "watermark_after",
        "bounded_lookback_seconds",
        "deadline_bucket_pages",
        "base_table_verified",
        "throttle_retried",
        "restart_replayed_overlap",
        "sustained_lag_seconds",
    }
    if not isinstance(scanner, Mapping) or not required.issubset(scanner):
        raise QualificationError("DEADLINE_SCANNER")
    for key in ("watermark_before", "watermark_after"):
        _parse(scanner[key], "DEADLINE_SCANNER_TIMESTAMP")
    if (
        type(scanner["bounded_lookback_seconds"]) is not int
        or scanner["bounded_lookback_seconds"] <= 0
        or type(scanner["deadline_bucket_pages"]) is not int
        or scanner["deadline_bucket_pages"] < 1
        or type(scanner["sustained_lag_seconds"]) is not int
        or scanner["sustained_lag_seconds"] < 0
        or scanner["sustained_lag_seconds"] > 300
        or scanner["base_table_verified"] is not True
        or scanner["throttle_retried"] is not True
        or scanner["restart_replayed_overlap"] is not True
    ):
        raise QualificationError("DEADLINE_SCANNER")
    return {"passed": True}


def qualify_alert_pipeline(pipeline: Mapping[str, Any]) -> dict[str, Any]:
    """Require durable outbox, notification, retry, and Cell-health observations."""

    required_true = {
        "state_outbox_atomic",
        "duplicate_obligations_suppressed",
        "router_retry_observed",
        "notification_ledger_conflict_reconciled",
        "replay_idempotent",
        "cell_alarm_healthy",
        "disposition_history_complete",
    }
    if not isinstance(pipeline, Mapping) or any(
        pipeline.get(key) is not True for key in required_true
    ):
        raise QualificationError("ALERT_PIPELINE")
    if (
        type(pipeline.get("max_delivery_age_seconds")) is not int
        or pipeline["max_delivery_age_seconds"] > 300
        or type(pipeline.get("consecutive_failure_threshold")) is not int
        or pipeline["consecutive_failure_threshold"] < 1
    ):
        raise QualificationError("ALERT_PIPELINE")
    return {"passed": True}


def qualify_healthy_completions(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Require twenty unique exact-once completion windows with no alerts."""

    if len(cases) != 20:
        raise QualificationError("HEALTHY_COMPLETIONS")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            raise QualificationError("HEALTHY_COMPLETIONS")
        occurrence = str(case.get("occurrence_id", ""))
        if not SHA256.fullmatch(occurrence) or occurrence in seen:
            raise QualificationError("HEALTHY_COMPLETIONS")
        seen.add(occurrence)
        try:
            _task_arn(case.get("task_arn"))
        except ValueError as error:
            raise QualificationError("HEALTHY_COMPLETIONS") from error
        if (
            case.get("window_index") != index
            or case.get("terminal_state") != "SUCCEEDED"
        ):
            raise QualificationError("HEALTHY_COMPLETIONS")
        for key in (
            "accepted_task_count",
            "zero_exit_count",
            "marker_count",
            "failure_alerts",
            "cell_health_alerts",
        ):
            if type(case.get(key)) is not int:
                raise QualificationError("HEALTHY_COMPLETIONS")
        for key in (
            "accepted_task_arns",
            "zero_exit_task_arns",
            "success_marker_ids",
            "failure_alert_ids",
            "cell_health_alert_ids",
        ):
            if not isinstance(case.get(key), list):
                raise QualificationError("HEALTHY_COMPLETIONS")
        if (
            len(case["accepted_task_arns"]) != 1
            or len(case["zero_exit_task_arns"]) != 1
            or len(case["success_marker_ids"]) != 1
            or len(case["failure_alert_ids"]) != 0
            or len(case["cell_health_alert_ids"]) != 0
            or case["accepted_task_arns"][0] != case["task_arn"]
            or case["zero_exit_task_arns"][0] != case["task_arn"]
        ):
            raise QualificationError("HEALTHY_COMPLETIONS")
        if not all(
            isinstance(marker, str)
            and re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{2}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                marker,
            )
            for marker in case["success_marker_ids"]
        ):
            raise QualificationError("HEALTHY_COMPLETIONS")
        if (
            case["accepted_task_count"] != 1
            or case["zero_exit_count"] != 1
            or case["marker_count"] != 1
            or case["failure_alerts"] != 0
            or case["cell_health_alerts"] != 0
        ):
            raise QualificationError("HEALTHY_COMPLETIONS")
    return {"windows": 20, "passed": True, "false_alerts": 0}


def completion_deadline_projection(
    manifest: Mapping[str, Any],
    results: Mapping[str, str],
    expected_bindings: Mapping[str, Any],
) -> dict[str, str]:
    """Project only Story 4.6 controls after validating sealed evidence."""

    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != _digest(body):
        raise QualificationError("MANIFEST_DIGEST")
    if manifest.get("bindings") != dict(expected_bindings):
        raise QualificationError("MANIFEST_BINDINGS")
    required = {
        "completion-correlation",
        "deadline-processing",
        "missed-overdue",
        "durable-alerting",
        "alert-pipeline",
        "alert-timing",
        "healthy-completions",
    }
    if set(results) != required or any(
        results.get(key) != "passed" for key in required
    ):
        raise QualificationError("QUALIFICATION_RESULTS")
    return {
        "launch-runtime": "blocked",
        "completion-correlation": "passed",
        "deadline-processing": "passed",
        "missed-overdue": "passed",
        "durable-alerting": "passed",
        "alert-pipeline": "passed",
        "alert-timing": "passed",
        "healthy-completions": "passed",
        "security": "blocked",
        "recovery": "blocked",
    }


def validate_completion_qualification_evidence(
    evidence: Mapping[str, Any], configuration: Mapping[str, Any]
) -> dict[str, str]:
    """Validate every completion/deadline/alert evidence plane before projection."""

    completions = evidence.get("completion_cases")
    if not isinstance(completions, list) or not completions:
        raise QualificationError("COMPLETION_CASES")
    required_case_ids = {
        "success",
        "marker-without-zero-exit",
        "zero-exit-without-marker",
        "wrong-occurrence",
        "unknown-occurrence",
        "cross-generation",
        "malformed-timestamp",
        "duplicate-replay",
        "conflicting-completion",
    }
    case_ids = {
        case.get("case_id") for case in completions if isinstance(case, Mapping)
    }
    if case_ids != required_case_ids:
        raise QualificationError("COMPLETION_CASE_MATRIX")
    for case in completions:
        if not isinstance(case, Mapping):
            raise QualificationError("COMPLETION_CASES")
        case_id = case.get("case_id")
        if case_id == "success":
            event = case.get("event")
            expected = configuration.get("expected_completion")
            facts = case.get("facts")
            if not isinstance(expected, Mapping) or not isinstance(event, Mapping):
                raise QualificationError("COMPLETION_CASES")
            valid = validate_completion_evidence(event, expected)
            classified = classify_completion(
                valid,
                ecs_zero_exit=case.get("ecs_zero_exit") is True,
                deadline_at=case.get("deadline_at"),
            )
            if classified["state"] != "SUCCEEDED":
                raise QualificationError("COMPLETION_CASE_RESULT")
            if (
                not isinstance(facts, list)
                or reduce_completion_facts(facts)["state"] != "SUCCEEDED"
            ):
                raise QualificationError("COMPLETION_FACTS")
        else:
            if case.get("disposition") not in {
                "REJECTED",
                "QUARANTINED",
            } or not _require_string(case.get("error_code"), "COMPLETION_CASES"):
                raise QualificationError("COMPLETION_CASES")
    deadlines = evidence.get("deadline_cases")
    if not isinstance(deadlines, list) or not deadlines:
        raise QualificationError("DEADLINE_CASES")
    for case in deadlines:
        if not isinstance(case, Mapping):
            raise QualificationError("DEADLINE_CASES")
        deadline_at = case.get("deadline_at")
        if not isinstance(deadline_at, str):
            raise QualificationError("DEADLINE_CASES")
        classify_deadline(
            str(case.get("current_state")),
            started=case.get("started") is True,
            completion_time=case.get("completion_time"),
            deadline_at=deadline_at,
        )
    batch = evidence.get("partial_batch")
    if not isinstance(batch, list) or not batch:
        raise QualificationError("BATCH")
    qualify_partial_batch(batch)
    alerts = evidence.get("alerts")
    if not isinstance(alerts, list):
        raise QualificationError("ALERT")
    qualify_alert_delivery(alerts)
    qualify_alert_pipeline(evidence.get("alert_pipeline", {}))
    qualify_deadline_scanner(evidence.get("deadline_scanner", {}))
    healthy = evidence.get("healthy_cases")
    if not isinstance(healthy, list):
        raise QualificationError("HEALTHY_COMPLETIONS")
    qualify_healthy_completions(healthy)
    cleanup = evidence.get("cleanup", {})
    validate_cleanup_evidence(cleanup)
    if not isinstance(cleanup, Mapping):
        raise QualificationError("CLEANUP")
    deleted = cleanup.get("deleted_resources")
    forbidden = cleanup.get("forbidden_artifacts")
    resources = cleanup.get("resources")
    retained = cleanup.get("retained_evidence")
    if (
        not isinstance(deleted, list)
        or not isinstance(forbidden, list)
        or forbidden
        or not isinstance(resources, list)
        or not isinstance(retained, list)
        or set(deleted) != set(resources) - set(retained)
    ):
        raise QualificationError("CLEANUP_INVENTORY")
    return {
        key: "passed"
        for key in (
            "completion-correlation",
            "deadline-processing",
            "missed-overdue",
            "durable-alerting",
            "alert-pipeline",
            "alert-timing",
            "healthy-completions",
        )
    }
