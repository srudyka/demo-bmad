"""Credential-free ECS launch and runtime qualification primitives.

The protected workflow supplies disposable-Cell evidence. This module validates
that evidence and projects only the launch/runtime readiness controls. It never
assumes AWS credentials, calls ECS, or mutates infrastructure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from hashlib import sha256
import hmac
import os
import re
from typing import Any

import rfc8785

from scripts.schedule_qualification import build_qualification_manifest

SHA256 = re.compile(r"^[0-9a-f]{64}$")
TASK_ARN = re.compile(r"^arn:[^:]+:ecs:[^:]+:[0-9]{12}:task/[^/]+/[0-9a-fA-F-]+$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
FORBIDDEN = re.compile(
    r"secret|password|credential|private[_ -]?key|raw[_ -]?config|token|plan",
    re.IGNORECASE,
)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
KNOWN_STOP_CODES = {
    "EssentialContainerExited",
    "ResourceInitializationError",
    "TaskFailedToStart",
    "UserInitiated",
    "SpotInterruption",
    "ServiceSchedulerInitiated",
}


class EcsQualificationError(ValueError):
    """A launch/runtime qualification input failed closed."""


def _canonical(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError) as error:
        raise EcsQualificationError("ECS_CANONICAL_JSON") from error


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _safe(value: Any, code: str, *, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise EcsQualificationError(code)
    if FORBIDDEN.search(value) or CONTROL.search(value):
        raise EcsQualificationError("ECS_SENSITIVE")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise EcsQualificationError("ECS_TIMESTAMP")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EcsQualificationError("ECS_TIMESTAMP") from error
    return value


def _task_arn(value: Any) -> str:
    if not isinstance(value, str) or not TASK_ARN.fullmatch(value):
        raise EcsQualificationError("ECS_TASK_ARN")
    return value


def _arn_parts(value: Any, code: str) -> tuple[str, str, str, str, str]:
    if not isinstance(value, str):
        raise EcsQualificationError(code)
    parts = value.split(":", 5)
    if len(parts) != 6 or parts[0] != "arn" or not all(parts[1:5]):
        raise EcsQualificationError(code)
    return (parts[1], parts[2], parts[3], parts[4], parts[5])


def _tags(value: Any) -> dict[str, str]:
    if isinstance(value, Mapping):
        raw = list(value.items())
    elif isinstance(value, list):
        raw = [
            (item.get("key"), item.get("value"))
            for item in value
            if isinstance(item, Mapping)
        ]
    else:
        raise EcsQualificationError("ECS_TASK_TAGS")
    result: dict[str, str] = {}
    for key, item_value in raw:
        if not isinstance(key, str) or not isinstance(item_value, str):
            raise EcsQualificationError("ECS_TASK_TAGS")
        if key in result:
            raise EcsQualificationError("ECS_TASK_TAGS_DUPLICATE")
        result[key] = item_value
    return result


def build_launch_runtime_manifest(
    *,
    release_version: str,
    compatibility_package: str,
    account_id: str,
    region: str,
    cell_identity: str,
    task_definition_arn: str,
    deployment_identity_id: str,
    injected_fault: str,
    expected_result: str,
    test_configuration: Mapping[str, Any],
    policy_versions: Mapping[str, str],
    evidence: Mapping[str, Any],
    bindings: Mapping[str, str],
) -> dict[str, Any]:
    """Build a sanitized manifest bound to the exact ECS qualification target."""

    _safe(task_definition_arn, "ECS_MANIFEST_BINDING")
    if not task_definition_arn.startswith("arn:"):
        raise EcsQualificationError("ECS_MANIFEST_BINDING")
    if not SHA256.fullmatch(deployment_identity_id):
        raise EcsQualificationError("ECS_MANIFEST_BINDING")
    fault = _safe(injected_fault, "ECS_MANIFEST_FAULT")
    expected = _safe(expected_result, "ECS_MANIFEST_RESULT")
    base = build_qualification_manifest(
        release_version=release_version,
        compatibility_package=compatibility_package,
        account_id=account_id,
        region=region,
        cell_identity=cell_identity,
        test_configuration=test_configuration,
        policy_versions=policy_versions,
        evidence=evidence,
        bindings=bindings,
    )
    base.update(
        {
            "task_definition_arn": task_definition_arn,
            "deployment_identity_id": deployment_identity_id,
            "injected_fault": fault,
            "expected_result": expected,
        }
    )
    body = {key: value for key, value in base.items() if key != "manifest_sha256"}
    base["manifest_sha256"] = _digest(body)
    return base


def classify_run_task_response(response: Mapping[str, Any]) -> dict[str, Any]:
    """Classify an ECS response without treating HTTP 200 as task acceptance."""

    if not isinstance(response, Mapping):
        raise EcsQualificationError("ECS_RESPONSE_SHAPE")
    tasks = response.get("tasks")
    failures = response.get("failures")
    if not isinstance(tasks, list) or not isinstance(failures, list):
        raise EcsQualificationError("ECS_RESPONSE_SHAPE")
    for failure in failures:
        if not isinstance(failure, Mapping):
            raise EcsQualificationError("ECS_RESPONSE_FAILURE")
        _safe(failure.get("reason"), "ECS_RESPONSE_FAILURE")
    if failures and not tasks:
        return {
            "disposition": "FAILED",
            "accepted": False,
            "error_code": "ECS_RUN_TASK_FAILED",
            "failure_count": len(failures),
        }
    if failures and tasks:
        return {
            "disposition": "AMBIGUOUS",
            "accepted": False,
            "error_code": "ECS_RUN_TASK_CONFLICT",
            "failure_count": len(failures),
        }
    if len(tasks) != 1 or not isinstance(tasks[0], Mapping):
        raise EcsQualificationError("ECS_RESPONSE_TASK_COUNT")
    return {
        "disposition": "ACCEPTED",
        "accepted": True,
        "task_arn": _task_arn(tasks[0].get("taskArn")),
    }


def validate_task_evidence(
    event: Mapping[str, Any], expected: Mapping[str, str]
) -> dict[str, Any]:
    """Validate ECS-owned identity and return sanitized task evidence."""

    required = {
        "task_arn",
        "cluster_arn",
        "task_definition_arn",
        "platform_cell",
        "job_id",
        "occurrence_id",
        "config_version",
        "deployment_identity_id",
        "account_id",
        "region",
        "started_by",
    }
    if not required.issubset(event) or not required.issubset(expected):
        raise EcsQualificationError("ECS_TASK_CORRELATION")
    for key in required:
        if event.get(key) != expected.get(key):
            raise EcsQualificationError("ECS_TASK_CORRELATION")
    task_arn = _task_arn(event["task_arn"])
    if event["started_by"] != expected["occurrence_id"]:
        raise EcsQualificationError("ECS_TASK_CORRELATION")
    task_parts = _arn_parts(task_arn, "ECS_TASK_CORRELATION")
    cluster_parts = _arn_parts(event["cluster_arn"], "ECS_TASK_CORRELATION")
    definition_parts = _arn_parts(event["task_definition_arn"], "ECS_TASK_CORRELATION")
    if (
        task_parts[0:4] != (cluster_parts[0], "ecs", cluster_parts[2], cluster_parts[3])
        or cluster_parts[1] != "ecs"
        or definition_parts[1] != "ecs"
        or definition_parts[2:4] != cluster_parts[2:4]
        or cluster_parts[3] != expected["account_id"]
        or cluster_parts[2] != expected["region"]
        or task_parts[4].split("/", 2)[1] != cluster_parts[4].rsplit("/", 1)[-1]
    ):
        raise EcsQualificationError("ECS_TASK_CORRELATION")
    status = event.get("last_status")
    if status not in {"PENDING", "RUNNING", "STOPPED"}:
        raise EcsQualificationError("ECS_TASK_STATUS")
    event_time = _timestamp(event.get("event_time"))
    stop_code = event.get("stop_code")
    stopped_reason = event.get("stopped_reason")
    if stop_code is not None:
        stop_code = _safe(stop_code, "ECS_STOP_CODE")
    if stopped_reason is not None:
        stopped_reason = _safe(stopped_reason, "ECS_STOPPED_REASON")
    containers = event.get("containers")
    if not isinstance(containers, list) or not containers:
        raise EcsQualificationError("ECS_CONTAINERS")
    normalized_containers: list[dict[str, Any]] = []
    for container in containers:
        if not isinstance(container, Mapping):
            raise EcsQualificationError("ECS_CONTAINERS")
        name = _safe(container.get("name"), "ECS_CONTAINERS", max_length=128)
        essential = container.get("essential")
        exit_code = container.get("exit_code")
        reason = container.get("reason")
        if type(essential) is not bool or (
            exit_code is not None and type(exit_code) is not int
        ):
            raise EcsQualificationError("ECS_CONTAINERS")
        normalized = {"name": name, "essential": essential, "exit_code": exit_code}
        if reason is not None:
            normalized["reason"] = _safe(reason, "ECS_CONTAINERS")
        normalized_containers.append(normalized)
    if status == "STOPPED" and stop_code is None:
        raise EcsQualificationError("ECS_STOP_CODE")
    tags = _tags(event.get("tags"))
    expected_tags = {
        "PlatformCell": expected["platform_cell"],
        "JobId": expected["job_id"],
        "OccurrenceId": expected["occurrence_id"],
        "ConfigVersion": expected["config_version"],
        "AttemptNo": "0",
        "DeploymentIdentity": expected["deployment_identity_id"],
    }
    if any(tags.get(key) != value for key, value in expected_tags.items()):
        raise EcsQualificationError("ECS_TASK_CORRELATION")
    return {
        "task_arn": task_arn,
        "cluster_arn": event["cluster_arn"],
        "task_definition_arn": event["task_definition_arn"],
        "started_by": event["started_by"],
        "last_status": status,
        "event_time": event_time,
        "stop_code": stop_code,
        "stopped_reason": stopped_reason,
        "containers": normalized_containers,
        "tags": expected_tags,
    }


def _runtime_error_code(evidence: Mapping[str, Any]) -> str:
    stop_code = evidence.get("stop_code")
    if stop_code == "TaskFailedToStart":
        return "ECS_TASK_FAILED_TO_START"
    if stop_code == "ResourceInitializationError":
        return "ECS_RESOURCE_INITIALIZATION_FAILED"
    containers = evidence["containers"]
    essential = [item for item in containers if item["essential"]]
    if any(item["exit_code"] not in (None, 0) for item in essential):
        return "ECS_ESSENTIAL_EXIT_NONZERO"
    if stop_code == "UserInitiated":
        return "ECS_TASK_EXTERNALLY_STOPPED"
    return "ECS_TASK_STOPPED_BEFORE_COMPLETION"


def _validate_completion_marker(
    marker: Mapping[str, Any], expected: Mapping[str, str], task_arn: str
) -> None:
    required = {
        "marker_id",
        "occurrence_id",
        "task_arn",
        "status",
        "exit_code",
        "observed_at",
    }
    if not required.issubset(marker):
        raise EcsQualificationError("ECS_COMPLETION_MARKER")
    _safe(marker["marker_id"], "ECS_COMPLETION_MARKER")
    if (
        marker["occurrence_id"] != expected["occurrence_id"]
        or marker["task_arn"] != task_arn
        or marker["status"] != "SUCCESS"
        or marker["exit_code"] != 0
    ):
        raise EcsQualificationError("ECS_COMPLETION_MARKER")
    _timestamp(marker["observed_at"])


def classify_task_runtime(
    event: Mapping[str, Any],
    expected: Mapping[str, str],
    *,
    completion_marker: Mapping[str, Any] | None = None,
    runtime_deadline_reached: bool = False,
) -> dict[str, Any]:
    """Reduce one validated task-state observation without declaring completion early."""

    evidence = validate_task_evidence(event, expected)
    if type(runtime_deadline_reached) is not bool:
        raise EcsQualificationError("ECS_RUNTIME_INPUT")
    completion_observed = completion_marker is not None
    if completion_marker is not None:
        if not isinstance(completion_marker, Mapping):
            raise EcsQualificationError("ECS_COMPLETION_MARKER")
        _validate_completion_marker(completion_marker, expected, evidence["task_arn"])
    if runtime_deadline_reached and evidence["last_status"] != "STOPPED":
        return {
            "state": "OVERDUE",
            "completion_pending": True,
            "automatic_stop": False,
            "evidence": evidence,
        }
    if evidence["last_status"] == "PENDING":
        return {
            "state": "EXPECTED",
            "completion_pending": True,
            "automatic_stop": False,
            "evidence": evidence,
        }
    if evidence["last_status"] == "RUNNING":
        return {
            "state": "STARTED",
            "completion_pending": True,
            "automatic_stop": False,
            "evidence": evidence,
        }
    essential = [item for item in evidence["containers"] if item["essential"]]
    all_zero = bool(essential) and all(item["exit_code"] == 0 for item in essential)
    forced_failure = evidence["stop_code"] in {
        "TaskFailedToStart",
        "ResourceInitializationError",
        "UserInitiated",
    }
    if evidence["stop_code"] not in KNOWN_STOP_CODES:
        forced_failure = True
    if all_zero and completion_observed and not forced_failure:
        state = "SUCCEEDED"
    elif all_zero and not forced_failure:
        state = "STARTED"
    else:
        state = "FAILED"
    result: dict[str, Any] = {
        "state": state,
        "completion_pending": state != "SUCCEEDED",
        "automatic_stop": False,
        "evidence": evidence,
    }
    if state == "FAILED":
        result["error_code"] = _runtime_error_code(evidence)
    return result


def reduce_task_observations(
    observations: Sequence[Mapping[str, Any]],
    expected: Mapping[str, str],
) -> dict[str, Any]:
    """Canonicalize and deduplicate task observations before state reduction."""

    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for observation in observations:
        evidence = validate_task_evidence(observation, expected)
        key = (evidence["task_arn"], evidence["last_status"], evidence["event_time"])
        if key in unique and unique[key] != evidence:
            raise EcsQualificationError("ECS_OBSERVATION_CONFLICT")
        unique[key] = evidence
    ordered = sorted(unique.values(), key=lambda item: item["event_time"])
    return {
        "observations": ordered,
        "count": len(ordered),
        "deduplicated": len(observations) - len(ordered),
    }


def qualify_healthy_launch_runtime(
    cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Require twenty unique, exact-once launch/runtime cases with no alerts."""

    if len(cases) != 20:
        raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, Mapping):
            raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
        occurrence_id = case.get("occurrence_id")
        if (
            not isinstance(occurrence_id, str)
            or not occurrence_id
            or occurrence_id in seen
        ):
            raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
        seen.add(occurrence_id)
        _task_arn(case.get("task_arn"))
        if case.get("window_index") != len(seen) - 1:
            raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
        _timestamp(case.get("started_at"))
        _timestamp(case.get("stopped_at"))
        for key in (
            "accepted_task_count",
            "start_evidence",
            "stop_evidence",
            "launch_alerts",
            "runtime_alerts",
            "cell_health_alerts",
        ):
            if type(case.get(key)) is not int:
                raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
        if (
            case.get("accepted_task_count") != 1
            or case.get("start_evidence") != 1
            or case.get("stop_evidence") != 1
            or case.get("runtime_state") != "STARTED"
            or case.get("completion_pending") is not True
            or any(
                case.get(key) != 0
                for key in ("launch_alerts", "runtime_alerts", "cell_health_alerts")
            )
        ):
            raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
    return {"windows": 20, "passed": True, "false_alerts": 0}


def qualify_alert_evidence(alerts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Require bounded, deduplicated, operator-actionable alert evidence."""

    if not isinstance(alerts, Sequence) or isinstance(alerts, (str, bytes)):
        raise EcsQualificationError("ECS_ALERTS")
    seen: set[str] = set()
    for alert in alerts:
        if not isinstance(alert, Mapping):
            raise EcsQualificationError("ECS_ALERTS")
        required = {
            "alert_id",
            "deduplication_id",
            "occurrence_id",
            "task_arn",
            "deployment_identity_id",
            "failure_plane",
            "owner",
            "routing",
            "runbook",
            "signal_at",
            "detected_at",
            "metric_dimensions",
        }
        if not required.issubset(alert):
            raise EcsQualificationError("ECS_ALERTS")
        for key in (
            "alert_id",
            "deduplication_id",
            "occurrence_id",
            "deployment_identity_id",
        ):
            _safe(alert[key], "ECS_ALERTS")
        _task_arn(alert["task_arn"])
        signal = datetime.fromisoformat(
            _timestamp(alert["signal_at"]).replace("Z", "+00:00")
        )
        detected = datetime.fromisoformat(
            _timestamp(alert["detected_at"]).replace("Z", "+00:00")
        )
        if (detected - signal).total_seconds() < 0 or (
            detected - signal
        ).total_seconds() > 300:
            raise EcsQualificationError("ECS_ALERT_LATENCY")
        if alert["deduplication_id"] in seen:
            raise EcsQualificationError("ECS_ALERT_DEDUPLICATION")
        seen.add(alert["deduplication_id"])
        if not all(
            isinstance(alert.get(key), str) and alert[key]
            for key in ("failure_plane", "owner", "routing", "runbook")
        ):
            raise EcsQualificationError("ECS_ALERTS")
        dimensions = alert["metric_dimensions"]
        if not isinstance(dimensions, Mapping) or set(dimensions) - {
            "job_id",
            "environment",
            "state",
        }:
            raise EcsQualificationError("ECS_METRIC_DIMENSIONS")
        if "occurrence_id" in dimensions:
            raise EcsQualificationError("ECS_METRIC_DIMENSIONS")
    return {"alerts": len(alerts), "passed": True, "max_latency_seconds": 300}


def validate_cleanup_evidence(cleanup: Mapping[str, Any]) -> dict[str, Any]:
    """Require disable-first, fault removal, teardown, and explicit retention proof."""

    if not isinstance(cleanup, Mapping):
        raise EcsQualificationError("ECS_CLEANUP")
    if cleanup.get("launch_disabled_first") is not True:
        raise EcsQualificationError("ECS_CLEANUP_ORDER")
    if (
        cleanup.get("faults_removed") is not True
        or cleanup.get("cleanup_verified") is not True
    ):
        raise EcsQualificationError("ECS_CLEANUP")
    resources = cleanup.get("resources")
    retained = cleanup.get("retained_evidence")
    if not isinstance(resources, list) or not isinstance(retained, list):
        raise EcsQualificationError("ECS_CLEANUP")
    if any(not isinstance(item, str) or not item for item in resources + retained):
        raise EcsQualificationError("ECS_CLEANUP")
    if not set(retained).issubset(resources):
        raise EcsQualificationError("ECS_CLEANUP_RETENTION")
    return {
        "passed": True,
        "deleted": len(set(resources) - set(retained)),
        "retained": len(set(retained)),
    }


def validate_qualification_evidence(
    evidence: Mapping[str, Any], configuration: Mapping[str, Any]
) -> None:
    """Require live-cell attestation and every qualification evidence plane."""

    proof = evidence.get("execution_proof")
    if not isinstance(proof, Mapping) or proof.get("mode") != "live-disposable-cell":
        raise EcsQualificationError("ECS_EXECUTION_PROOF")
    if proof.get("observed") is not True or not SHA256.fullmatch(
        str(proof.get("schedule_qualification_sha256", ""))
    ):
        raise EcsQualificationError("ECS_EXECUTION_PROOF")
    proof_signature = proof.get("signature")
    proof_key = os.environ.get("ECS_QUALIFICATION_PROOF_KEY")
    if (
        not proof_key
        or not isinstance(proof_signature, str)
        or not re.fullmatch(r"[0-9a-f]{64}", proof_signature)
    ):
        raise EcsQualificationError("ECS_EXECUTION_PROOF")
    unsigned_proof = {key: value for key, value in proof.items() if key != "signature"}
    expected_signature = hmac.new(
        proof_key.encode("utf-8"), _canonical(unsigned_proof), sha256
    ).hexdigest()
    if not hmac.compare_digest(proof_signature, expected_signature):
        raise EcsQualificationError("ECS_EXECUTION_PROOF")
    for key in (
        "account_id",
        "region",
        "cell_identity",
        "task_definition_arn",
        "deployment_identity_id",
    ):
        if proof.get(key) != configuration.get(key):
            raise EcsQualificationError("ECS_EXECUTION_PROOF")
    if not isinstance(evidence.get("results"), Mapping):
        raise EcsQualificationError("ECS_RESULTS")
    scenarios = evidence.get("scenario_results")
    required_scenarios = {
        "launch-failure",
        "crash-reconciliation",
        "task-start",
        "runtime-evidence",
    }
    if not isinstance(scenarios, Mapping) or any(
        scenarios.get(key) != "passed" for key in required_scenarios
    ):
        raise EcsQualificationError("ECS_SCENARIOS")
    if not isinstance(evidence.get("healthy_cases"), list):
        raise EcsQualificationError("ECS_HEALTHY_WINDOWS")
    qualify_healthy_launch_runtime(evidence["healthy_cases"])
    alerts = evidence.get("alerts")
    if not isinstance(alerts, list):
        raise EcsQualificationError("ECS_ALERTS")
    qualify_alert_evidence(alerts)
    validate_cleanup_evidence(evidence.get("cleanup", {}))


def launch_runtime_projection(
    manifest: Mapping[str, Any],
    results: Mapping[str, str],
    expected_bindings: Mapping[str, str],
) -> dict[str, str]:
    """Project only verified ECS launch/runtime controls into readiness."""

    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != _digest(body):
        raise EcsQualificationError("ECS_MANIFEST_DIGEST")
    if manifest.get("bindings") != dict(expected_bindings):
        raise EcsQualificationError("ECS_BINDING")
    required = (
        "launch-failure",
        "crash-reconciliation",
        "task-start",
        "runtime-evidence",
        "alert-timing",
        "healthy-runs",
    )
    if any(results.get(key) != "passed" for key in required):
        raise EcsQualificationError("ECS_RESULTS")
    return {
        "launch-runtime": "passed",
        "completion-alerts": "blocked",
        "security": "blocked",
        "recovery": "blocked",
    }


def seal_launch_runtime_manifest(
    manifest: Mapping[str, Any], controls: Mapping[str, str]
) -> dict[str, Any]:
    """Include the published controls in the signed manifest body."""

    sealed = {**manifest, "controls": dict(controls)}
    sealed["manifest_sha256"] = _digest(
        {key: value for key, value in sealed.items() if key != "manifest_sha256"}
    )
    return sealed
