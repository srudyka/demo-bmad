"""Credential-free pilot launch checklist and decision evaluator.

This module validates sanitized, exact-scope records.  It never calls AWS,
changes Terraform, or treats a fixture/approval as proof that a pilot ran.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import rfc8785
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]


SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ACCOUNT = re.compile(r"^[0-9]{12}$")
PLACEHOLDERS = {"", "unknown", "pending", "placeholder", "todo", "tbd", "unset"}
LAUNCH_STATES = {
    "BLOCKED",
    "READY_FOR_REVIEW",
    "APPROVED_TO_START",
    "IN_PROGRESS",
    "PAUSED",
    "EVIDENCE_PENDING",
}
DECISIONS = {"ACCEPTED", "REMEDIATE_AND_REPEAT", "REJECTED"}
MEASUREMENT_STATUSES = {
    "MEASURED",
    "UNKNOWN",
    "INCOMPLETE",
    "INCONCLUSIVE",
    "NOT_COMPARABLE",
    "BLOCKED",
}
BEHAVIORAL_CLASSES = {
    "release",
    "contract",
    "policy",
    "module",
    "workflow",
    "action",
    "provider",
    "iam",
    "trust",
    "secrets",
    "state",
    "networking",
    "job",
    "config",
    "schedule",
    "generation",
    "completion",
    "alerting",
    "observability",
    "recovery",
    "rollback",
    "threshold",
    "exclusion",
    "observation-method",
}


class PilotLaunchError(ValueError):
    """Raised when a launch or decision record violates a boundary."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}{(': ' + detail) if detail else ''}")
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require(value: Any, code: str, *, text: bool = False) -> None:
    if value is None or (text and (not isinstance(value, str) or not value.strip())):
        raise PilotLaunchError(code)


def _text(value: Any, code: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\n" in value:
        raise PilotLaunchError(code)
    return value


def _non_placeholder(value: Any, code: str) -> str:
    result = _text(value, code)
    if result.casefold() in PLACEHOLDERS:
        raise PilotLaunchError(code + "_PLACEHOLDER")
    return result


def _hash(value: Any, code: str, pattern: re.Pattern[str] = SHA256) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise PilotLaunchError(code)
    return value


def _timestamp(value: Any, code: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PilotLaunchError(code)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise PilotLaunchError(code) from error
    if parsed.tzinfo != UTC:
        raise PilotLaunchError(code)
    return parsed


def _exact_keys(value: Mapping[str, Any], required: set[str], code: str) -> None:
    if set(value) != required:
        raise PilotLaunchError(code)


def _bindings(bindings: Mapping[str, Any]) -> dict[str, Any]:
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
        "target_manifest_sha256",
        "module_version",
        "workflow_version",
        "observation_window",
    }
    if set(bindings) != required:
        raise PilotLaunchError("PILOT_LAUNCH_BINDINGS")
    _non_placeholder(bindings["release_version"], "PILOT_LAUNCH_RELEASE")
    _hash(bindings["compatibility_package_sha256"], "PILOT_LAUNCH_PACKAGE")
    _hash(bindings["source_commit"], "PILOT_LAUNCH_COMMIT", SHA1)
    _hash(bindings["workflow_sha"], "PILOT_LAUNCH_WORKFLOW", SHA1)
    _non_placeholder(bindings["workflow_run_id"], "PILOT_LAUNCH_RUN")
    if not ACCOUNT.fullmatch(str(bindings["account_id"])):
        raise PilotLaunchError("PILOT_LAUNCH_ACCOUNT")
    for key in (
        "region",
        "environment",
        "pilot_id",
        "module_version",
        "workflow_version",
    ):
        _non_placeholder(bindings[key], "PILOT_LAUNCH_BINDING")
    _hash(bindings["target_manifest_sha256"], "PILOT_LAUNCH_TARGET")
    window = bindings["observation_window"]
    if not isinstance(window, Mapping) or set(window) != {"start", "end"}:
        raise PilotLaunchError("PILOT_LAUNCH_WINDOW")
    start = _timestamp(window["start"], "PILOT_LAUNCH_WINDOW")
    end = _timestamp(window["end"], "PILOT_LAUNCH_WINDOW")
    if end <= start:
        raise PilotLaunchError("PILOT_LAUNCH_WINDOW")
    return dict(bindings)


def _job(job: Mapping[str, Any]) -> None:
    required = {
        "job_id",
        "repository",
        "application_owner",
        "operational_owner",
        "risk_class",
        "environment",
        "account_id",
        "region",
        "dependencies",
        "side_effects",
    }
    if set(job) != required:
        raise PilotLaunchError("PILOT_JOB_SHAPE")
    for key in required - {"dependencies", "side_effects"}:
        _non_placeholder(job[key], "PILOT_JOB_FIELD")
    if not isinstance(job["dependencies"], list) or not isinstance(
        job["side_effects"], list
    ):
        raise PilotLaunchError("PILOT_JOB_COLLECTION")


def _evidence(item: Mapping[str, Any], bindings: Mapping[str, Any]) -> None:
    required = {
        "evidence_id",
        "kind",
        "sha256",
        "source_revision",
        "status",
        "sensitivity",
        "redacted",
        "binding",
    }
    if set(item) != required:
        raise PilotLaunchError("PILOT_EVIDENCE_SHAPE")
    _non_placeholder(item["evidence_id"], "PILOT_EVIDENCE_ID")
    _hash(item["sha256"], "PILOT_EVIDENCE_DIGEST")
    _hash(item["source_revision"], "PILOT_EVIDENCE_REVISION", SHA1)
    if item["status"] not in {"verified", "pending", "failed", "synthetic"}:
        raise PilotLaunchError("PILOT_EVIDENCE_STATUS")
    if (
        item["sensitivity"]
        not in {"public-sanitized", "internal-sanitized", "protected-reference"}
        or item["redacted"] is not True
    ):
        raise PilotLaunchError("PILOT_EVIDENCE_SAFETY")
    binding = item["binding"]
    if not isinstance(binding, Mapping) or set(binding) != {
        "source_commit",
        "workflow_run_id",
        "account_id",
        "region",
        "environment",
        "pilot_id",
        "job_id",
    }:
        raise PilotLaunchError("PILOT_EVIDENCE_BINDING")
    for key in ("source_commit",):
        _hash(binding[key], "PILOT_EVIDENCE_BINDING", SHA1)
    for key in ("workflow_run_id", "region", "environment", "pilot_id", "job_id"):
        _non_placeholder(binding[key], "PILOT_EVIDENCE_BINDING")
    if not ACCOUNT.fullmatch(str(binding["account_id"])):
        raise PilotLaunchError("PILOT_EVIDENCE_BINDING")
    for key in (
        "source_commit",
        "workflow_run_id",
        "account_id",
        "region",
        "environment",
        "pilot_id",
    ):
        if str(binding[key]) != str(bindings[key]):
            raise PilotLaunchError("PILOT_EVIDENCE_SCOPE")


def _field(field: Mapping[str, Any]) -> None:
    required = {
        "field_id",
        "owner",
        "evidence_type",
        "due_at",
        "status",
        "blocking",
        "source_refs",
    }
    if set(field) != required:
        raise PilotLaunchError("PILOT_FIELD_SHAPE")
    for key in ("field_id", "owner", "evidence_type"):
        _non_placeholder(field[key], "PILOT_FIELD")
    _timestamp(field["due_at"], "PILOT_FIELD_DUE")
    if (
        field["status"]
        not in {
            "complete",
            "missing",
            "failed",
            "unknown",
            "inconclusive",
            "not-applicable",
        }
        or not isinstance(field["blocking"], bool)
        or not isinstance(field["source_refs"], list)
    ):
        raise PilotLaunchError("PILOT_FIELD_STATUS")


def _approval(
    approval: Mapping[str, Any],
    bindings: Mapping[str, Any],
    *,
    initiator: str | None = None,
    now: datetime | None = None,
) -> None:
    required = {
        "role",
        "actor",
        "approved_at",
        "expires_at",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "deployment_identity_sha256",
        "status",
    }
    if set(approval) != required:
        raise PilotLaunchError("PILOT_APPROVAL_SHAPE")
    for key in ("role", "actor", "workflow_run_id"):
        _non_placeholder(approval[key], "PILOT_APPROVAL")
    if approval["status"] != "approved" or (
        initiator and approval["actor"] == initiator
    ):
        raise PilotLaunchError("PILOT_APPROVAL_SELF_OR_STATUS")
    _timestamp(approval["approved_at"], "PILOT_APPROVAL_TIME")
    expires = _timestamp(approval["expires_at"], "PILOT_APPROVAL_TIME")
    if expires <= _timestamp(approval["approved_at"], "PILOT_APPROVAL_TIME"):
        raise PilotLaunchError("PILOT_APPROVAL_EXPIRY")
    if now is not None and expires <= now.astimezone(UTC):
        raise PilotLaunchError("PILOT_APPROVAL_EXPIRED")
    _hash(approval["source_commit"], "PILOT_APPROVAL_BINDING", SHA1)
    _hash(approval["workflow_sha"], "PILOT_APPROVAL_BINDING", SHA1)
    _hash(approval["deployment_identity_sha256"], "PILOT_APPROVAL_IDENTITY")
    for key in ("source_commit", "workflow_sha", "workflow_run_id"):
        if str(approval[key]) != str(bindings[key]):
            raise PilotLaunchError("PILOT_APPROVAL_SCOPE")


def validate_launch_checklist(
    checklist: Mapping[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Validate a checklist and return normalized, non-sensitive metadata."""
    if not isinstance(checklist, Mapping):
        raise PilotLaunchError("PILOT_LAUNCH_SHAPE")
    required = {
        "schema_version",
        "checklist_id",
        "status",
        "bindings",
        "jobs",
        "fields",
        "controls",
        "observation_contract",
        "qualifying_change_catalog",
        "evidence_manifest",
        "approval_matrix",
        "rollback_criteria",
        "initiator",
        "history",
        "deployment_identity_sha256",
        "preflight_evidence_sha256",
        "operations",
        "rollout_policy",
    }
    _exact_keys(checklist, required, "PILOT_LAUNCH_SHAPE")
    if (
        checklist["schema_version"] != "1.0.0"
        or checklist["status"] not in LAUNCH_STATES
    ):
        raise PilotLaunchError("PILOT_LAUNCH_STATUS")
    bindings = _bindings(checklist["bindings"])
    _non_placeholder(checklist["checklist_id"], "PILOT_LAUNCH_ID")
    initiator = _non_placeholder(checklist["initiator"], "PILOT_LAUNCH_INITIATOR")
    jobs = checklist["jobs"]
    if not isinstance(jobs, list) or len(jobs) > 2:
        raise PilotLaunchError("PILOT_JOB_COUNT")
    for job in jobs:
        if not isinstance(job, Mapping):
            raise PilotLaunchError("PILOT_JOB_SHAPE")
        _job(job)
    fields = checklist["fields"]
    if not isinstance(fields, list) or not fields:
        raise PilotLaunchError("PILOT_FIELDS")
    for field in fields:
        if not isinstance(field, Mapping):
            raise PilotLaunchError("PILOT_FIELD_SHAPE")
        _field(field)
    controls = checklist["controls"]
    if not isinstance(controls, list) or not controls:
        raise PilotLaunchError("PILOT_CONTROLS")
    control_ids: set[str] = set()
    for control in controls:
        if not isinstance(control, Mapping) or set(control) != {
            "control_id",
            "status",
            "blocking",
            "evidence_ids",
            "invalidates",
        }:
            raise PilotLaunchError("PILOT_CONTROL_SHAPE")
        control_id = _non_placeholder(control["control_id"], "PILOT_CONTROL_ID")
        if control_id in control_ids:
            raise PilotLaunchError("PILOT_DUPLICATE_CONTROL")
        control_ids.add(control_id)
        if (
            control["status"]
            not in {
                "passed",
                "missing",
                "failed",
                "unknown",
                "inconclusive",
                "not-applicable",
            }
            or not isinstance(control["blocking"], bool)
            or not isinstance(control["evidence_ids"], list)
            or not isinstance(control["invalidates"], list)
        ):
            raise PilotLaunchError("PILOT_CONTROL_STATUS")
    observation = checklist["observation_contract"]
    observation_required = {
        "version",
        "minimum_duration_seconds",
        "minimum_occurrences",
        "schedule_frequencies",
        "healthy_windows",
        "controlled_failures",
        "alert_latency_target_seconds",
        "false_alert_limit",
        "lost_alert_limit",
        "setup_time_method",
        "review_categories",
        "recovery_rehearsal_required",
        "stop_conditions",
    }
    if not isinstance(observation, Mapping) or set(observation) != observation_required:
        raise PilotLaunchError("PILOT_OBSERVATION_SHAPE")
    _non_placeholder(observation["version"], "PILOT_OBSERVATION_VERSION")
    for key in (
        "minimum_duration_seconds",
        "minimum_occurrences",
        "alert_latency_target_seconds",
        "false_alert_limit",
        "lost_alert_limit",
    ):
        if (
            not isinstance(observation[key], int)
            or isinstance(observation[key], bool)
            or observation[key] < 0
        ):
            raise PilotLaunchError("PILOT_OBSERVATION_VALUE")
    for key in (
        "schedule_frequencies",
        "healthy_windows",
        "controlled_failures",
        "review_categories",
        "stop_conditions",
    ):
        if not isinstance(observation[key], list) or not observation[key]:
            raise PilotLaunchError("PILOT_OBSERVATION_COLLECTION")
    if (
        not isinstance(observation["setup_time_method"], str)
        or not observation["setup_time_method"]
        or not isinstance(observation["recovery_rehearsal_required"], bool)
    ):
        raise PilotLaunchError("PILOT_OBSERVATION_METHOD")
    if (
        observation["minimum_duration_seconds"] <= 0
        or observation["minimum_occurrences"] <= 0
    ):
        raise PilotLaunchError("PILOT_OBSERVATION_THRESHOLD")
    catalog = checklist["qualifying_change_catalog"]
    if (
        not isinstance(catalog, Mapping)
        or set(catalog) != {"version", "changes"}
        or not isinstance(catalog["changes"], list)
        or not catalog["changes"]
    ):
        raise PilotLaunchError("PILOT_CATALOG_SHAPE")
    for change in catalog["changes"]:
        if not isinstance(change, Mapping) or set(change) != {
            "change_id",
            "class",
            "behavioral",
            "invalidates",
            "security_approval_required",
        }:
            raise PilotLaunchError("PILOT_CATALOG_SHAPE")
        _non_placeholder(change["change_id"], "PILOT_CATALOG_ID")
        if (
            change["class"] not in BEHAVIORAL_CLASSES | {"editorial"}
            or not isinstance(change["behavioral"], bool)
            or not isinstance(change["invalidates"], list)
            or not isinstance(change["security_approval_required"], bool)
        ):
            raise PilotLaunchError("PILOT_CATALOG_VALUE")
    evidence = checklist["evidence_manifest"]
    if not isinstance(evidence, list):
        raise PilotLaunchError("PILOT_EVIDENCE_MANIFEST")
    seen_evidence: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping):
            raise PilotLaunchError("PILOT_EVIDENCE_SHAPE")
        _evidence(item, bindings)
        if item["evidence_id"] in seen_evidence:
            raise PilotLaunchError("PILOT_DUPLICATE_EVIDENCE")
        seen_evidence.add(item["evidence_id"])
    job_ids = {job["job_id"] for job in jobs}
    if job_ids and any(item["binding"]["job_id"] not in job_ids for item in evidence):
        raise PilotLaunchError("PILOT_EVIDENCE_JOB_SCOPE")
    for field in fields:
        if any(ref not in seen_evidence for ref in field["source_refs"]):
            raise PilotLaunchError("PILOT_FIELD_EVIDENCE_REFERENCE")
    for control in controls:
        if control["status"] == "passed" and any(
            ref not in seen_evidence for ref in control["evidence_ids"]
        ):
            raise PilotLaunchError("PILOT_CONTROL_EVIDENCE_REFERENCE")
        if control["status"] == "passed" and not control["evidence_ids"]:
            raise PilotLaunchError("PILOT_CONTROL_EVIDENCE_REQUIRED")
        if control["status"] == "passed":
            evidence_by_id = {item["evidence_id"]: item for item in evidence}
            if any(
                evidence_by_id[ref]["status"] != "verified"
                for ref in control["evidence_ids"]
            ):
                raise PilotLaunchError("PILOT_CONTROL_EVIDENCE_UNVERIFIED")
    approval_matrix = checklist["approval_matrix"]
    if not isinstance(approval_matrix, Mapping) or set(approval_matrix) != {
        "required_roles",
        "security_trigger_classes",
        "self_review_prevention",
        "protected_environment_verified",
        "branch_protection_verified",
        "emergency_bypass_policy",
    }:
        raise PilotLaunchError("PILOT_APPROVAL_MATRIX")
    if (
        not isinstance(approval_matrix["required_roles"], list)
        or not approval_matrix["required_roles"]
        or not isinstance(approval_matrix["security_trigger_classes"], list)
        or not isinstance(approval_matrix["self_review_prevention"], bool)
        or not isinstance(approval_matrix["protected_environment_verified"], bool)
        or not isinstance(approval_matrix["branch_protection_verified"], bool)
        or not isinstance(approval_matrix["emergency_bypass_policy"], str)
    ):
        raise PilotLaunchError("PILOT_APPROVAL_MATRIX")
    if not approval_matrix["self_review_prevention"]:
        raise PilotLaunchError("PILOT_SELF_REVIEW_POLICY")
    _hash(checklist["preflight_evidence_sha256"], "PILOT_PREFLIGHT_EVIDENCE")
    identities = checklist["deployment_identity_sha256"]
    if (
        not isinstance(identities, list)
        or not identities
        or len(identities) > 2
        or any(not SHA256.fullmatch(str(item)) for item in identities)
        or len(set(identities)) != len(identities)
    ):
        raise PilotLaunchError("PILOT_DEPLOYMENT_IDENTITIES")
    operations = checklist["operations"]
    if (
        not isinstance(operations, Mapping)
        or set(operations)
        != {
            "notification_target",
            "escalation_policy",
            "notification_verified",
            "escalation_verified",
        }
        or not isinstance(operations["notification_target"], str)
        or not operations["notification_target"].strip()
        or not isinstance(operations["escalation_policy"], str)
        or not operations["escalation_policy"].strip()
        or operations["notification_verified"] is not True
        or operations["escalation_verified"] is not True
    ):
        raise PilotLaunchError("PILOT_OPERATIONAL_GATES")
    rollout = checklist["rollout_policy"]
    if (
        not isinstance(rollout, Mapping)
        or set(rollout)
        != {
            "support_owner",
            "supported_versions",
            "deprecation_communication",
            "exception_policy",
            "rollback_pause_criteria",
            "rollout_scope",
        }
        or not isinstance(rollout["supported_versions"], list)
        or not rollout["supported_versions"]
        or any(
            not isinstance(item, str) or not item.strip()
            for item in rollout["supported_versions"]
        )
        or any(
            not isinstance(rollout[key], str) or not rollout[key].strip()
            for key in set(rollout) - {"supported_versions"}
        )
    ):
        raise PilotLaunchError("PILOT_ROLLOUT_POLICY")
    rollback = checklist["rollback_criteria"]
    rollback_required = {
        "disable_launch_first",
        "known_good_identity_sha256",
        "compensation_owner",
        "rto_seconds",
        "stop_actions",
        "verification_steps",
    }
    if (
        not isinstance(rollback, Mapping)
        or set(rollback) != rollback_required
        or rollback["disable_launch_first"] is not True
    ):
        raise PilotLaunchError("PILOT_ROLLBACK")
    _hash(rollback["known_good_identity_sha256"], "PILOT_ROLLBACK_IDENTITY")
    _non_placeholder(rollback["compensation_owner"], "PILOT_ROLLBACK_OWNER")
    if (
        not isinstance(rollback["rto_seconds"], int)
        or rollback["rto_seconds"] <= 0
        or not all(
            isinstance(rollback[key], list) and rollback[key]
            for key in ("stop_actions", "verification_steps")
        )
    ):
        raise PilotLaunchError("PILOT_ROLLBACK")
    history = checklist["history"]
    if not isinstance(history, list) or not history:
        raise PilotLaunchError("PILOT_HISTORY")
    for event in history:
        if not isinstance(event, Mapping) or set(event) != {
            "event_id",
            "status",
            "at",
            "actor",
            "reason",
            "record_sha256",
        }:
            raise PilotLaunchError("PILOT_HISTORY")
        _non_placeholder(event["event_id"], "PILOT_HISTORY")
        if event["status"] not in LAUNCH_STATES:
            raise PilotLaunchError("PILOT_HISTORY")
        _timestamp(event["at"], "PILOT_HISTORY")
        _non_placeholder(event["actor"], "PILOT_HISTORY")
        if (
            not isinstance(event["reason"], str)
            or not event["reason"]
            or "\n" in event["reason"]
        ):
            raise PilotLaunchError("PILOT_HISTORY")
        _hash(event["record_sha256"], "PILOT_HISTORY")
    if now is not None and now.tzinfo is None:
        raise PilotLaunchError("PILOT_CLOCK")
    return {
        "checklist_id": checklist["checklist_id"],
        "status": checklist["status"],
        "bindings": bindings,
        "jobs": [dict(item) for item in jobs],
        "controls": [dict(item) for item in controls],
        "evidence_ids": sorted(seen_evidence),
        "initiator": initiator,
        "deployment_identity_sha256": list(identities),
        "preflight_evidence_sha256": checklist["preflight_evidence_sha256"],
        "operations": dict(operations),
        "rollout_policy": dict(rollout),
    }


def validate_measurement_result(
    result: Mapping[str, Any], bindings: Mapping[str, Any]
) -> None:
    if not isinstance(result, Mapping) or result.get("schema_version") != "1.0.0":
        raise PilotLaunchError("PILOT_MEASUREMENT_SCHEMA")
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts/v1/schemas/pilot-measurement-result.schema.json"
    )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(result),
            key=lambda error: list(error.path),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PilotLaunchError("PILOT_MEASUREMENT_SCHEMA") from error
    if errors:
        raise PilotLaunchError("PILOT_MEASUREMENT_SCHEMA")
    if result.get("status") not in MEASUREMENT_STATUSES:
        raise PilotLaunchError("PILOT_MEASUREMENT_STATUS")
    result_bindings = result.get("bindings")
    if not isinstance(result_bindings, Mapping):
        raise PilotLaunchError("PILOT_MEASUREMENT_BINDING")
    for key in (
        "release_version",
        "compatibility_package_sha256",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "account_id",
        "region",
        "environment",
        "pilot_id",
    ):
        if str(result_bindings.get(key)) != str(
            bindings[key] if key in bindings else ""
        ):
            raise PilotLaunchError("PILOT_MEASUREMENT_SCOPE")
    if result.get("status") == "MEASURED":
        metrics = result.get("metrics")
        if (
            not isinstance(metrics, list)
            or not metrics
            or any(
                item.get("status") != "MEASURED"
                for item in metrics
                if isinstance(item, Mapping)
            )
        ):
            raise PilotLaunchError("PILOT_MEASUREMENT_INCOMPLETE")
    if result.get("evidence_sha256") != _measurement_digest(
        {key: value for key, value in result.items() if key != "evidence_sha256"}
    ):
        raise PilotLaunchError("PILOT_MEASUREMENT_DIGEST")


def classify_change(change_class: str, *, catalog: Mapping[str, Any]) -> dict[str, Any]:
    if change_class not in BEHAVIORAL_CLASSES | {"editorial"}:
        raise PilotLaunchError("PILOT_CHANGE_CLASS")
    matches = [
        item
        for item in catalog.get("changes", [])
        if isinstance(item, Mapping) and item.get("class") == change_class
    ]
    if len(matches) != 1:
        raise PilotLaunchError("PILOT_CHANGE_CATALOG")
    item = matches[0]
    return {
        "change_class": change_class,
        "behavioral": bool(item["behavioral"]),
        "invalidates": list(item["invalidates"]),
        "security_approval_required": bool(item["security_approval_required"]),
    }


def invalidate_launch(
    checklist: Mapping[str, Any],
    change_class: str,
    *,
    current_bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a change and return the exact scopes that must be repeated."""
    validate_launch_checklist(checklist)
    classification = classify_change(
        change_class, catalog=checklist["qualifying_change_catalog"]
    )
    bindings_changed = current_bindings is not None and dict(current_bindings) != dict(
        checklist["bindings"]
    )
    invalidated = sorted(set(classification["invalidates"]))
    if bindings_changed:
        invalidated = sorted(set((*invalidated, "approval", "qualification")))
    return {
        "status": "BLOCKED"
        if classification["behavioral"] or bindings_changed
        else checklist["status"],
        "change_class": change_class,
        "behavioral": classification["behavioral"],
        "invalidated_scopes": invalidated,
        "security_approval_required": classification["security_approval_required"],
    }


def evaluate_launch_checklist(
    checklist: Mapping[str, Any],
    *,
    measurement: Mapping[str, Any] | None = None,
    approvals: Sequence[Mapping[str, Any]] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return a deterministic checklist evaluation; failures become blockers."""
    normalized = validate_launch_checklist(checklist, now=now)
    bindings = normalized["bindings"]
    blockers: list[dict[str, str]] = []
    if checklist["status"] == "PAUSED":
        blockers.append(
            {"code": "PAUSED_REQUIRES_DISPOSITION", "owner": "Operational Owner"}
        )
    if bindings["pilot_id"] == "synthetic-fixture":
        blockers.append(
            {"code": "SYNTHETIC_MEASUREMENT_ONLY", "owner": "Evidence Owner"}
        )
    if not normalized["jobs"]:
        blockers.append({"code": "JOBS_UNASSIGNED", "owner": "Platform Product Owner"})
    for job in normalized["jobs"]:
        if any(
            str(job[key]).casefold() in PLACEHOLDERS
            for key in (
                "job_id",
                "repository",
                "application_owner",
                "operational_owner",
                "risk_class",
                "environment",
                "account_id",
                "region",
            )
        ):
            blockers.append(
                {"code": "JOB_ASSIGNMENT_INCOMPLETE", "owner": "Platform Product Owner"}
            )
        if (
            str(job["account_id"]) != str(bindings["account_id"])
            or job["region"] != bindings["region"]
            or job["environment"] != bindings["environment"]
        ):
            blockers.append(
                {"code": "JOB_TARGET_MISMATCH", "owner": "Platform Engineering"}
            )
    for field in checklist["fields"]:
        if field["blocking"] and field["status"] != "complete":
            blockers.append(
                {
                    "code": f"FIELD_{field['field_id']}_INCOMPLETE",
                    "owner": field["owner"],
                }
            )
    for control in checklist["controls"]:
        if control["blocking"] and control["status"] != "passed":
            blockers.append(
                {
                    "code": f"CONTROL_{control['control_id']}_{control['status'].upper()}",
                    "owner": "Control Owner",
                }
            )
    matrix = checklist["approval_matrix"]
    if not matrix["protected_environment_verified"]:
        blockers.append(
            {
                "code": "PROTECTED_ENVIRONMENT_UNVERIFIED",
                "owner": "Platform Engineering",
            }
        )
    if not matrix["branch_protection_verified"]:
        blockers.append(
            {"code": "BRANCH_PROTECTION_UNVERIFIED", "owner": "Platform Engineering"}
        )
    if not approvals:
        blockers.append({"code": "APPROVALS_MISSING", "owner": "Required Reviewers"})
    seen_roles: set[str] = set()
    for approval in approvals:
        try:
            _approval(
                approval,
                bindings,
                initiator=normalized["initiator"],
                now=now or datetime.now(UTC),
            )
        except PilotLaunchError as error:
            blockers.append({"code": error.code, "owner": "Required Reviewers"})
            continue
        if approval["role"] in seen_roles:
            blockers.append(
                {"code": "DUPLICATE_APPROVAL_ROLE", "owner": "Required Reviewers"}
            )
        seen_roles.add(approval["role"])
    actors = [
        approval.get("actor") for approval in approvals if isinstance(approval, Mapping)
    ]
    if len(actors) != len(set(actors)):
        blockers.append(
            {"code": "DUPLICATE_APPROVAL_ACTOR", "owner": "Required Reviewers"}
        )
    for approval in approvals:
        if (
            isinstance(approval, Mapping)
            and approval.get("deployment_identity_sha256")
            not in normalized["deployment_identity_sha256"]
        ):
            blockers.append(
                {
                    "code": "DEPLOYMENT_IDENTITY_MISMATCH",
                    "owner": "Platform Engineering",
                }
            )
    required_roles = set(matrix["required_roles"])
    if any(
        item.get("security_approval_required") and item.get("behavioral")
        for item in checklist["qualifying_change_catalog"]["changes"]
    ):
        required_roles.add("security")
    missing_roles = required_roles - seen_roles
    blockers.extend(
        {"code": f"APPROVAL_{role}_MISSING", "owner": role}
        for role in sorted(missing_roles)
    )
    if measurement is not None:
        try:
            validate_measurement_result(measurement, bindings)
        except PilotLaunchError as error:
            blockers.append({"code": error.code, "owner": "Evidence Owner"})
        if measurement.get("bindings", {}).get("pilot_id") == "synthetic-fixture":
            blockers.append(
                {"code": "SYNTHETIC_MEASUREMENT_ONLY", "owner": "Evidence Owner"}
            )
    launch_status = "BLOCKED" if blockers else "APPROVED_TO_START"
    if checklist["status"] == "PAUSED":
        launch_status = "PAUSED"
    return {
        "schema_version": "1.0.0",
        "status": launch_status,
        "checklist_id": normalized["checklist_id"],
        "bindings": bindings,
        "blockers": sorted(blockers, key=lambda item: (item["code"], item["owner"])),
        "job_ids": sorted(job["job_id"] for job in normalized["jobs"]),
        "evidence_ids": normalized["evidence_ids"],
        "synthetic_only": all(
            item.get("status") == "synthetic" for item in checklist["evidence_manifest"]
        )
        if checklist["evidence_manifest"]
        else True,
        "execution_proven": False,
        "decision_authorized": False,
    }


def _measurement_digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def build_launch_authorization(
    checklist: Mapping[str, Any],
    approvals: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the pre-pilot authorization; measurement is intentionally absent."""
    normalized = validate_launch_checklist(checklist, now=now)
    evaluation = evaluate_launch_checklist(checklist, approvals=approvals, now=now)
    record = {
        "schema_version": "1.0.0",
        "status": evaluation["status"],
        "checklist_id": normalized["checklist_id"],
        "bindings": normalized["bindings"],
        "job_ids": evaluation["job_ids"],
        "deployment_identity_sha256": normalized["deployment_identity_sha256"],
        "observation_window": normalized["bindings"]["observation_window"],
        "rollback_plan_sha256": digest(checklist["rollback_criteria"]),
        "approvals": [
            {
                key: approval[key]
                for key in (
                    "role",
                    "actor",
                    "approved_at",
                    "expires_at",
                    "source_commit",
                    "workflow_sha",
                    "workflow_run_id",
                    "deployment_identity_sha256",
                    "status",
                )
            }
            for approval in sorted(
                approvals,
                key=lambda item: (str(item.get("role")), str(item.get("actor"))),
            )
        ],
        "preflight_evidence_sha256": normalized["preflight_evidence_sha256"],
        "execution_proven": False,
    }
    record["evidence_sha256"] = digest(record)
    return record


def validate_launch_authorization(record: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "status",
        "checklist_id",
        "bindings",
        "job_ids",
        "deployment_identity_sha256",
        "observation_window",
        "rollback_plan_sha256",
        "approvals",
        "preflight_evidence_sha256",
        "execution_proven",
        "evidence_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != required:
        raise PilotLaunchError("PILOT_AUTHORIZATION_SCHEMA")
    if record["schema_version"] != "1.0.0" or record["status"] not in {
        "BLOCKED",
        "APPROVED_TO_START",
        "PAUSED",
    }:
        raise PilotLaunchError("PILOT_AUTHORIZATION_STATUS")
    _bindings(record["bindings"])
    if not isinstance(record["job_ids"], list):
        raise PilotLaunchError("PILOT_AUTHORIZATION_JOBS")
    if not isinstance(record["approvals"], list):
        raise PilotLaunchError("PILOT_AUTHORIZATION_APPROVALS")
    _hash(record["rollback_plan_sha256"], "PILOT_AUTHORIZATION_ROLLBACK")
    _hash(record["preflight_evidence_sha256"], "PILOT_AUTHORIZATION_PREFLIGHT")
    if (
        record["execution_proven"] is not False
        or _hash(record["evidence_sha256"], "PILOT_AUTHORIZATION_DIGEST")
        != record["evidence_sha256"]
    ):
        raise PilotLaunchError("PILOT_AUTHORIZATION_STATUS")
    if (
        digest(
            {key: value for key, value in record.items() if key != "evidence_sha256"}
        )
        != record["evidence_sha256"]
    ):
        raise PilotLaunchError("PILOT_AUTHORIZATION_DIGEST")


def build_decision_record(
    checklist: Mapping[str, Any],
    measurement: Mapping[str, Any] | None,
    *,
    decision: str,
    approvals: Sequence[Mapping[str, Any]],
    rationale: str,
    owners: Sequence[str],
    due_actions: Sequence[str],
    scope: str,
    effective_date: str,
    now: str,
    evidence_ids: Sequence[str],
) -> dict[str, Any]:
    """Build a final decision only after exact checklist and measurement checks."""
    normalized = validate_launch_checklist(checklist)
    if (
        decision not in DECISIONS
        or not rationale
        or "\n" in rationale
        or not owners
        or not due_actions
        or not scope
    ):
        raise PilotLaunchError("PILOT_DECISION_FIELDS")
    if measurement is None:
        raise PilotLaunchError("PILOT_DECISION_MEASUREMENT")
    if decision == "ACCEPTED" and measurement.get("status") != "MEASURED":
        raise PilotLaunchError("PILOT_DECISION_MEASUREMENT_STATUS")
    validate_measurement_result(measurement, normalized["bindings"])
    if measurement.get("bindings", {}).get("pilot_id") == "synthetic-fixture":
        raise PilotLaunchError("PILOT_DECISION_SYNTHETIC_EVIDENCE")
    evaluation = evaluate_launch_checklist(
        checklist, measurement=measurement, approvals=approvals
    )
    if decision == "ACCEPTED" and evaluation["status"] != "APPROVED_TO_START":
        raise PilotLaunchError("PILOT_DECISION_LAUNCH_BLOCKED")
    for approval in approvals:
        _approval(approval, normalized["bindings"], initiator=normalized["initiator"])
    _timestamp(effective_date, "PILOT_DECISION_DATE")
    _timestamp(now, "PILOT_DECISION_DATE")
    if not all(
        isinstance(item, str) and item and "\n" not in item
        for item in (*owners, *due_actions, *evidence_ids)
    ):
        raise PilotLaunchError("PILOT_DECISION_FIELDS")
    manifest_ids = {item["evidence_id"] for item in checklist["evidence_manifest"]}
    if not evidence_ids or not set(evidence_ids) <= manifest_ids:
        raise PilotLaunchError("PILOT_DECISION_EVIDENCE_REFERENCE")
    record = {
        "schema_version": "1.0.0",
        "record_type": "pilot-decision-record",
        "decision": decision,
        "launch_status": evaluation["status"],
        "bindings": normalized["bindings"],
        "checklist_id": normalized["checklist_id"],
        "measurement_status": measurement["status"],
        "measurement_evidence_sha256": measurement.get("evidence_sha256", ""),
        "evidence_ids": sorted(set(evidence_ids)),
        "rationale": rationale,
        "owners": sorted(set(owners)),
        "due_actions": list(due_actions),
        "scope": scope,
        "effective_date": effective_date,
        "decided_at": now,
        "execution_proven": False,
        "approval_roles": sorted(str(item["role"]) for item in approvals),
        "rollout_policy": {
            **normalized["rollout_policy"],
            "new_jobs_use_standard_module": decision == "ACCEPTED",
            "materially_changed_jobs_migrate": decision == "ACCEPTED",
            "exceptions_governed": True,
            "metrics_continue_from_baseline": decision == "ACCEPTED",
        },
    }
    record["evidence_sha256"] = digest(record)
    return record


def validate_decision_record(record: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "record_type",
        "decision",
        "launch_status",
        "bindings",
        "checklist_id",
        "measurement_status",
        "measurement_evidence_sha256",
        "evidence_ids",
        "rationale",
        "owners",
        "due_actions",
        "scope",
        "effective_date",
        "decided_at",
        "execution_proven",
        "approval_roles",
        "rollout_policy",
        "evidence_sha256",
    }
    if (
        not isinstance(record, Mapping)
        or set(record) != required
        or record["schema_version"] != "1.0.0"
        or record["record_type"] != "pilot-decision-record"
        or record["decision"] not in DECISIONS
    ):
        raise PilotLaunchError("PILOT_DECISION_SCHEMA")
    _bindings(record["bindings"])
    if (
        record["launch_status"] not in LAUNCH_STATES
        or record["measurement_status"] not in MEASUREMENT_STATUSES
        or record["execution_proven"] is not False
    ):
        raise PilotLaunchError("PILOT_DECISION_STATUS")
    _hash(record["measurement_evidence_sha256"], "PILOT_DECISION_MEASUREMENT_DIGEST")
    _hash(record["evidence_sha256"], "PILOT_DECISION_DIGEST")
    if (
        digest(
            {key: value for key, value in record.items() if key != "evidence_sha256"}
        )
        != record["evidence_sha256"]
    ):
        raise PilotLaunchError("PILOT_DECISION_DIGEST")


def reviewer_report(result: Mapping[str, Any]) -> str:
    lines = [
        "# Pilot launch review",
        "",
        f"- Status: `{result['status']}`",
        f"- Checklist: `{result.get('checklist_id', '')}`",
        f"- Execution proven: `{result.get('execution_proven', False)}`",
        "",
        "## Blockers",
    ]
    blockers = result.get("blockers", [])
    if blockers:
        lines.extend(f"- `{item['code']}` — {item['owner']}" for item in blockers)
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "This credential-free evaluation does not call AWS, authorize production, or prove that a pilot executed.",
        ]
    )
    return "\n".join(lines) + "\n"
