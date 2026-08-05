"""Credential-free recovery rehearsal evidence contracts.

This module validates sanitized recovery evidence and derives readiness results
from observations. It does not call AWS, apply Terraform, enable launches, or
trust caller-supplied counters or result strings.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import copy
import hashlib
import re
from typing import Any

import rfc8785

from scripts.deployment_targets import TargetViolation
from scripts.deployment_evidence import validate_recovery_inventory

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ACCOUNT = re.compile(r"^[0-9]{12}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")

RECOVERY_CONTROL_IDS = (
    "rollback-containment",
    "rollback-plan",
    "generation-activation",
    "application-compensation",
    "cell-containment",
    "fresh-resource-restore",
    "single-generation-cutover",
    "durable-replay",
    "task-reconciliation",
    "service-verification",
    "rpo-rto-objectives",
    "failed-recovery-backout",
    "recovery-evidence",
)

REQUIRED_BINDINGS = (
    "release_version",
    "compatibility_package_sha256",
    "source_commit",
    "workflow_sha",
    "workflow_run_id",
    "account_id",
    "region",
    "environment",
    "cell_identity",
    "deployment_identity_sha256",
    "target_manifest_sha256",
    "known_good_identity_sha256",
)

PHASE_ORDER = (
    "contain",
    "inventory",
    "restore-fresh-resources",
    "validate-structure",
    "cutover",
    "replay",
    "reconcile",
    "verify",
)

FORBIDDEN = (
    "secret",
    "password",
    "credential",
    "private_key",
    "raw_payload",
    "terraform.tfstate",
    ".tfplan",
)
RETAINED_ARTIFACTS = {"sanitized-recovery-evidence", "recovery-audit"}


class RecoveryQualificationError(TargetViolation):
    """Stable, sanitized recovery qualification rejection."""


def _digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _require_text(value: Any, code: str, *, maximum: int = 256) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise RecoveryQualificationError(code)
    if any(marker in value.lower() for marker in FORBIDDEN):
        raise RecoveryQualificationError("RECOVERY_SENSITIVE_FIELD")


def _require_hash(value: Any, code: str, pattern: re.Pattern[str] = SHA256) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise RecoveryQualificationError(code)


def _require_timestamp(value: Any, code: str) -> None:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise RecoveryQualificationError(code)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as error:
        raise RecoveryQualificationError(code) from error


def _validate_bindings(
    bindings: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    if set(bindings) != set(REQUIRED_BINDINGS):
        raise RecoveryQualificationError("RECOVERY_BINDINGS_SHAPE")
    for key in REQUIRED_BINDINGS:
        value = bindings[key]
        _require_text(value, "RECOVERY_BINDING_MISSING")
        if key in {"source_commit", "workflow_sha"}:
            _require_hash(value, "RECOVERY_BINDING_FORMAT", SHA1)
        elif key.endswith("_sha256"):
            _require_hash(value, "RECOVERY_BINDING_FORMAT")
        elif key == "account_id" and not ACCOUNT.fullmatch(value):
            raise RecoveryQualificationError("RECOVERY_ACCOUNT_FORMAT")
        if key not in expected or value != expected[key]:
            raise RecoveryQualificationError("RECOVERY_BINDING_MISMATCH")


def _validate_sanitized(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if any(marker in key_text for marker in FORBIDDEN):
                raise RecoveryQualificationError("RECOVERY_SENSITIVE_FIELD")
            _validate_sanitized(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_sanitized(child, f"{path}[{index}]")
    elif path == "mode":
        return
    elif isinstance(value, str) and any(
        marker in value.lower() for marker in FORBIDDEN
    ):
        raise RecoveryQualificationError("RECOVERY_SENSITIVE_FIELD")


def _unsigned_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = copy.deepcopy(dict(evidence))
    unsigned.pop("evidence_sha256", None)
    controls = unsigned.get("controls")
    if isinstance(controls, list):
        for control in controls:
            if isinstance(control, dict):
                control["evidence_sha256"] = "0" * 64
    return unsigned


def _validate_observations(observations: Mapping[str, Any]) -> None:
    tasks = observations.get("tasks")
    occurrences = observations.get("occurrences")
    alerts = observations.get("alerts")
    resources = observations.get("resources")
    inventory = observations.get("inventory")
    if (
        not isinstance(tasks, list)
        or not isinstance(occurrences, list)
        or not isinstance(alerts, list)
        or not tasks
        or not occurrences
        or not alerts
        or not isinstance(inventory, Mapping)
    ):
        raise RecoveryQualificationError("RECOVERY_OBSERVATIONS_SHAPE")
    if not isinstance(resources, Mapping):
        raise RecoveryQualificationError("RECOVERY_RESOURCES_SHAPE")
    try:
        validate_recovery_inventory(inventory)
    except TargetViolation as error:
        raise RecoveryQualificationError("RECOVERY_INVENTORY_INVALID") from error

    task_ids: set[str] = set()
    task_by_occurrence: dict[str, str] = {}
    for task in tasks:
        if not isinstance(task, Mapping) or not isinstance(task.get("task_arn"), str):
            raise RecoveryQualificationError("RECOVERY_TASK_SHAPE")
        if not SHA256.fullmatch(str(task.get("deployment_identity", ""))):
            raise RecoveryQualificationError("RECOVERY_DEPLOYMENT_IDENTITY")
        task_id = task["task_arn"]
        if task_id in task_ids:
            raise RecoveryQualificationError("RECOVERY_DUPLICATE_TASK")
        task_ids.add(task_id)
        state = task.get("state")
        if state not in {"ACCEPTED", "RUNNING", "STOPPED", "UNKNOWN"}:
            raise RecoveryQualificationError("RECOVERY_TASK_STATE")
        occurrence_id = task.get("occurrence_id")
        if not isinstance(occurrence_id, str) or not occurrence_id:
            raise RecoveryQualificationError("RECOVERY_TASK_CORRELATION")
        if (
            occurrence_id in task_by_occurrence
            and task_by_occurrence[occurrence_id] != task_id
        ):
            raise RecoveryQualificationError("RECOVERY_TASK_CORRELATION")
        task_by_occurrence[occurrence_id] = task_id

    occurrence_ids: set[str] = set()
    for occurrence in occurrences:
        if not isinstance(occurrence, Mapping):
            raise RecoveryQualificationError("RECOVERY_OCCURRENCE_SHAPE")
        occurrence_id = occurrence.get("occurrence_id")
        if (
            not isinstance(occurrence_id, str)
            or not occurrence_id
            or occurrence_id in occurrence_ids
        ):
            raise RecoveryQualificationError("RECOVERY_OCCURRENCE_ID")
        occurrence_ids.add(occurrence_id)
        if occurrence.get("state") not in {
            "SUCCEEDED",
            "FAILED",
            "MISSED",
            "OVERDUE",
            "AMBIGUOUS",
        }:
            raise RecoveryQualificationError("RECOVERY_OCCURRENCE_STATE")
        task_id = occurrence.get("task_arn")
        if task_id is not None and task_by_occurrence.get(occurrence_id) != task_id:
            raise RecoveryQualificationError("RECOVERY_TASK_CORRELATION")
        if not SHA256.fullmatch(str(occurrence.get("deployment_identity", ""))):
            raise RecoveryQualificationError("RECOVERY_DEPLOYMENT_IDENTITY")
        if (
            task_by_occurrence.get(occurrence_id)
            and next(
                task["state"]
                for task in tasks
                if task["task_arn"] == task_by_occurrence[occurrence_id]
            )
            == "UNKNOWN"
            and occurrence["state"] != "AMBIGUOUS"
        ):
            raise RecoveryQualificationError("RECOVERY_UNKNOWN_TASK_NOT_AMBIGUOUS")
        if occurrence["state"] == "AMBIGUOUS" and occurrence.get(
            "operator_decision"
        ) not in {
            "drain",
            "quarantine",
            "preserve",
            "compensate",
        }:
            raise RecoveryQualificationError("RECOVERY_AMBIGUOUS_DECISION")

    alert_ids: set[str] = set()
    for alert in alerts:
        if not isinstance(alert, Mapping) or not isinstance(alert.get("alert_id"), str):
            raise RecoveryQualificationError("RECOVERY_ALERT_SHAPE")
        if alert["alert_id"] in alert_ids:
            raise RecoveryQualificationError("RECOVERY_ALERT_DEDUP")
        alert_ids.add(alert["alert_id"])
        if alert.get("occurrence_id") not in occurrence_ids:
            raise RecoveryQualificationError("RECOVERY_ALERT_CORRELATION")
        if alert.get("disposition") not in {"delivered", "reconciled"}:
            raise RecoveryQualificationError("RECOVERY_ALERT_DISPOSITION")

    if (
        resources.get("fresh_targets") is not True
        or resources.get("encrypted") is not True
    ):
        raise RecoveryQualificationError("RECOVERY_FRESH_ENCRYPTED_REQUIRED")
    required_checks = {
        "schema",
        "indexes",
        "streams",
        "ttl",
        "pitr",
        "encryption",
        "tags",
        "policies",
        "compatibility",
    }
    if set(resources.get("structural_checks", ())) != required_checks:
        raise RecoveryQualificationError("RECOVERY_STRUCTURAL_CHECKS")
    if resources.get("cutover") not in {
        "ordered-single-generation",
        "atomic-single-generation",
    }:
        raise RecoveryQualificationError("RECOVERY_SPLIT_BRAIN")


def validate_recovery_evidence(
    evidence: Mapping[str, Any],
    expected_bindings: Mapping[str, Any],
    *,
    now: str,
) -> dict[str, Any]:
    required = {
        "schema_version",
        "scenario_id",
        "mode",
        "incident_id",
        "bindings",
        "source_generation",
        "known_good_generation",
        "restore_point",
        "evaluated_at",
        "expected_rpo_seconds",
        "expected_rto_seconds",
        "launch_enabled",
        "phase_order",
        "observations",
        "controls",
        "cleanup",
        "evidence_sha256",
    }
    if set(evidence) != required or evidence.get("schema_version") != "1.0.0":
        raise RecoveryQualificationError("RECOVERY_EVIDENCE_SHAPE")
    _validate_bindings(evidence["bindings"], expected_bindings)
    _require_text(evidence["scenario_id"], "RECOVERY_SCENARIO")
    _require_text(evidence["incident_id"], "RECOVERY_INCIDENT")
    _require_text(evidence["source_generation"], "RECOVERY_GENERATION")
    _require_text(evidence["known_good_generation"], "RECOVERY_GENERATION")
    if evidence["source_generation"] == evidence["known_good_generation"]:
        raise RecoveryQualificationError("RECOVERY_NOOP")
    if evidence["mode"] not in {"credential-free-fixture", "protected-disposable-cell"}:
        raise RecoveryQualificationError("RECOVERY_MODE")
    _require_timestamp(evidence["restore_point"], "RECOVERY_RESTORE_POINT")
    _require_timestamp(evidence["evaluated_at"], "RECOVERY_EVALUATED_AT")
    _require_timestamp(now, "RECOVERY_NOW")
    for key in ("expected_rpo_seconds", "expected_rto_seconds"):
        if (
            not isinstance(evidence[key], int)
            or isinstance(evidence[key], bool)
            or not 1 <= evidence[key] <= 2_592_000
        ):
            raise RecoveryQualificationError("RECOVERY_OBJECTIVE")
    if evidence["launch_enabled"] is not False:
        raise RecoveryQualificationError("RECOVERY_LAUNCH_NOT_FENCED")
    if tuple(evidence["phase_order"]) != PHASE_ORDER:
        raise RecoveryQualificationError("RECOVERY_PHASE_ORDER")

    controls = evidence["controls"]
    if (
        not isinstance(controls, list)
        or len(controls) != len(RECOVERY_CONTROL_IDS)
        or {item.get("control_id") for item in controls if isinstance(item, Mapping)}
        != set(RECOVERY_CONTROL_IDS)
    ):
        raise RecoveryQualificationError("RECOVERY_CONTROL_SET")
    for control in controls:
        if not isinstance(control, Mapping) or control.get("result") != "passed":
            raise RecoveryQualificationError("RECOVERY_CONTROL_BLOCKED")
        control_evidence = control.get("evidence")
        if (
            not isinstance(control_evidence, Mapping)
            or control_evidence.get("status") != "passed"
            or control_evidence.get("observed") is not True
        ):
            raise RecoveryQualificationError("RECOVERY_CONTROL_EVIDENCE")
        _require_hash(control.get("evidence_sha256"), "RECOVERY_CONTROL_DIGEST")
        if control["evidence_sha256"] != _digest(control_evidence):
            raise RecoveryQualificationError("RECOVERY_CONTROL_DIGEST_MISMATCH")

    _validate_observations(evidence["observations"])
    cleanup = evidence["cleanup"]
    if (
        not isinstance(cleanup, Mapping)
        or cleanup.get("mode") != "disable-first"
        or cleanup.get("forbidden_artifacts") != []
    ):
        raise RecoveryQualificationError("RECOVERY_CLEANUP_FAILED")
    if not isinstance(cleanup.get("deleted"), list) or not isinstance(
        cleanup.get("retained"), list
    ):
        raise RecoveryQualificationError("RECOVERY_CLEANUP_SHAPE")
    if set(cleanup["retained"]) - RETAINED_ARTIFACTS:
        raise RecoveryQualificationError("RECOVERY_RETAINED_ARTIFACT")
    _validate_sanitized(evidence)
    _require_hash(evidence["evidence_sha256"], "RECOVERY_EVIDENCE_DIGEST")
    if evidence["evidence_sha256"] != _digest(_unsigned_evidence(evidence)):
        raise RecoveryQualificationError("RECOVERY_EVIDENCE_DIGEST_MISMATCH")
    return {
        "status": "passed",
        "bindings": dict(evidence["bindings"]),
        "control_ids": list(RECOVERY_CONTROL_IDS),
    }


def recovery_readiness_projection(
    summary: Mapping[str, Any], bindings: Mapping[str, Any]
) -> dict[str, Any]:
    if summary.get("status") != "passed":
        raise RecoveryQualificationError("RECOVERY_NOT_PASSED")
    return {
        "category": "recovery",
        "controls": {control: "passed" for control in RECOVERY_CONTROL_IDS},
        "bindings_sha256": _digest(dict(bindings)),
        "evidence_source": "disposable-fixture",
    }
