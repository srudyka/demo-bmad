"""Sanitized, immutable deployment and recovery evidence helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from referencing import Registry, Resource

from scripts.deployment_targets import TargetViolation

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
OUTCOMES = {
    "succeeded",
    "failed",
    "partial",
    "cancelled",
    "runner-lost",
    "lock-conflict",
}
TERMINAL_FIELDS = {
    "apply_actor",
    "started_at",
    "ended_at",
    "state_result",
    "lock_condition",
    "lifecycle_state",
    "workflow_conclusion",
    "errors",
    "output_checksums",
    "resource_identities",
    "verification",
}
SECRET_PATTERN = re.compile(
    r"(?i)(aws_access_key_id|aws_secret_access_key|aws_session_token|password|secret|token|private_key)\s*[=:]"
)
SECRET_KEY_PATTERN = re.compile(
    r"(?i)(password|secret|token|credential|private[_-]?key|access[_-]?key)"
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]+PRIVATE KEY-----|"
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
)


def _timestamp(value: str, code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise TargetViolation(code) from error
    if parsed.tzinfo is None:
        raise TargetViolation(code)
    return parsed.astimezone(timezone.utc)


def _hash(value: Any) -> bool:
    return bool(SHA256.fullmatch(str(value)))


def _screen(value: Any) -> None:
    if isinstance(value, str):
        if SECRET_PATTERN.search(value) or SECRET_VALUE_PATTERN.search(value):
            raise TargetViolation("DEPLOYMENT_SECRET")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if SECRET_KEY_PATTERN.search(str(key)) and not str(key).endswith(
                ("_sha256", "_checksum")
            ):
                raise TargetViolation("DEPLOYMENT_SECRET")
            _screen(child)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for child in value:
            _screen(child)


def _validate_identity(identity: Mapping[str, Any]) -> None:
    if set(identity) != {"schema_version", "deployment_identity_id", "identity"}:
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    if identity["schema_version"] != "1.0.0" or not _hash(
        identity["deployment_identity_id"]
    ):
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    body = identity.get("identity")
    if not isinstance(body, Mapping):
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    required = {
        "account_id",
        "region",
        "environment",
        "source_commit",
        "image_digest",
        "task_definition_arn",
        "module_versions",
        "contract_version",
        "workflow",
        "tool_versions",
        "resolved_platform",
        "artifact_checksums",
    }
    if not required.issubset(body) or not SHA1.fullmatch(str(body["source_commit"])):
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(body["image_digest"])):
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    if set(body) != required:
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    schema_root = Path(__file__).resolve().parents[1] / "contracts" / "v1" / "schemas"
    try:
        resources = []
        selected = None
        for path in schema_root.glob("*.schema.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            resources.append((document["$id"], Resource.from_contents(document)))
            if path.name == "deployment-identity.schema.json":
                selected = document
        if selected is None:
            raise TargetViolation("DEPLOYMENT_IDENTITY_SCHEMA_MISSING")
        errors = sorted(
            Draft202012Validator(
                selected, registry=Registry().with_resources(resources)
            ).iter_errors(identity),
            key=lambda error: list(error.absolute_path),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise TargetViolation("DEPLOYMENT_IDENTITY_SCHEMA_UNAVAILABLE") from error
    if errors:
        raise TargetViolation("DEPLOYMENT_IDENTITY_SCHEMA")


def assemble_deployment_evidence(
    expected: Mapping[str, Any],
    *,
    deployment_identity: Mapping[str, Any],
    changed_addresses: Sequence[str],
) -> dict[str, Any]:
    """Create the sanitized pre-approval projection from exact bindings."""
    required = {
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "manifest_sha256",
        "account_id",
        "region",
        "environment",
        "root",
        "state_key",
        "plan_sha256",
        "policy_sha256",
        "readiness_sha256",
        "provider_lock_sha256",
        "backend_lock_sha256",
        "cell_contract_sha256",
        "config_sha256",
        "schedule_generation",
        "deployment_identity_sha256",
        "phase",
        "expected_plan_impact",
        "cost_note",
    }
    binding_fields = required - {"expected_plan_impact", "cost_note"}
    if not required.issubset(expected) or any(
        expected.get(key) in (None, "") for key in required
    ):
        raise TargetViolation("DEPLOYMENT_REQUIRED")
    if not SHA1.fullmatch(str(expected["source_commit"])) or not SHA1.fullmatch(
        str(expected["workflow_sha"])
    ):
        raise TargetViolation("DEPLOYMENT_BINDING")
    hash_fields = {key for key in required if key.endswith("sha256")}
    if any(not _hash(expected[key]) for key in hash_fields):
        raise TargetViolation("DEPLOYMENT_BINDING")
    if len(changed_addresses) > 200:
        raise TargetViolation("DEPLOYMENT_ADDRESS_LIMIT")
    if any(
        not isinstance(address, str)
        or not address
        or ".." in address
        or len(address) > 200
        for address in changed_addresses
    ):
        raise TargetViolation("DEPLOYMENT_ADDRESS")
    _validate_identity(deployment_identity)
    identity_body = deployment_identity["identity"]
    identity_digest = hashlib.sha256(
        json.dumps(identity_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if expected["deployment_identity_sha256"] != identity_digest:
        raise TargetViolation("DEPLOYMENT_IDENTITY_BINDING")
    if any(
        expected[key] != identity_body[field]
        for key, field in (
            ("source_commit", "source_commit"),
            ("account_id", "account_id"),
            ("region", "region"),
            ("environment", "environment"),
        )
    ):
        raise TargetViolation("DEPLOYMENT_IDENTITY_BINDING")
    _screen(expected)
    record = {
        "schema_version": "1.0.0",
        "status": "awaiting-approval",
        "bindings": {key: expected[key] for key in sorted(binding_fields)},
        "deployment_identity": deployment_identity,
        "deployment_identity_sha256": expected["deployment_identity_sha256"],
        "changed_addresses": list(changed_addresses)[:200],
        "expected_plan_impact": expected["expected_plan_impact"][:240],
        "cost_note": expected["cost_note"][:240],
    }
    if "occurrence_id" in expected or "task_arn" in expected:
        record["references"] = {
            key: expected[key]
            for key in ("occurrence_id", "task_arn")
            if key in expected
        }
    record["evidence_sha256"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return record


def validate_deployment_evidence(
    evidence: Mapping[str, Any],
    *,
    expected_status: str | None = None,
    expected: Mapping[str, Any] | None = None,
) -> None:
    if not isinstance(evidence, Mapping) or evidence.get("schema_version") != "1.0.0":
        raise TargetViolation("DEPLOYMENT_SCHEMA")
    if evidence.get("status") not in {"awaiting-approval", *OUTCOMES}:
        raise TargetViolation("DEPLOYMENT_SCHEMA")
    if expected_status is not None and evidence.get("status") != expected_status:
        raise TargetViolation("DEPLOYMENT_STATUS")
    required = {
        "bindings",
        "deployment_identity",
        "deployment_identity_sha256",
        "changed_addresses",
        "expected_plan_impact",
        "cost_note",
        "evidence_sha256",
    }
    if not required.issubset(evidence):
        raise TargetViolation("DEPLOYMENT_REQUIRED")
    _validate_identity(evidence["deployment_identity"])
    if not _hash(evidence["deployment_identity_sha256"]):
        raise TargetViolation("DEPLOYMENT_BINDING")
    if not isinstance(evidence["bindings"], Mapping):
        raise TargetViolation("DEPLOYMENT_BINDING")
    bindings = evidence["bindings"]
    required_bindings = {
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "manifest_sha256",
        "account_id",
        "region",
        "environment",
        "root",
        "state_key",
        "plan_sha256",
        "policy_sha256",
        "readiness_sha256",
        "provider_lock_sha256",
        "backend_lock_sha256",
        "cell_contract_sha256",
        "config_sha256",
        "schedule_generation",
        "deployment_identity_sha256",
        "phase",
    }
    if set(bindings) != required_bindings:
        raise TargetViolation("DEPLOYMENT_BINDING")
    if (
        not SHA1.fullmatch(str(bindings["source_commit"]))
        or not SHA1.fullmatch(str(bindings["workflow_sha"]))
        or not re.fullmatch(r"[1-9][0-9]*", str(bindings["workflow_run_id"]))
        or not re.fullmatch(r"[0-9]{12}", str(bindings["account_id"]))
        or not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+", str(bindings["region"]))
        or any(
            not _hash(bindings[key])
            for key in required_bindings
            if key.endswith("sha256")
        )
        or not all(
            isinstance(bindings[key], str) and bindings[key]
            for key in (
                "environment",
                "root",
                "state_key",
                "schedule_generation",
                "phase",
            )
        )
    ):
        raise TargetViolation("DEPLOYMENT_BINDING")
    if expected is not None:
        for key in required_bindings:
            if str(bindings[key]) != str(expected.get(key, "")):
                raise TargetViolation("DEPLOYMENT_BINDING")
    identity_body = evidence["deployment_identity"].get("identity")
    if not isinstance(identity_body, Mapping):
        raise TargetViolation("DEPLOYMENT_IDENTITY_SHAPE")
    if (
        evidence["deployment_identity_sha256"]
        != hashlib.sha256(
            json.dumps(identity_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    ):
        raise TargetViolation("DEPLOYMENT_IDENTITY_BINDING")
    if bindings["deployment_identity_sha256"] != evidence["deployment_identity_sha256"]:
        raise TargetViolation("DEPLOYMENT_IDENTITY_BINDING")
    if (
        not isinstance(evidence["changed_addresses"], list)
        or len(evidence["changed_addresses"]) > 200
    ):
        raise TargetViolation("DEPLOYMENT_ADDRESS_LIMIT")
    _screen(evidence)
    if evidence.get("status") != "awaiting-approval":
        if not TERMINAL_FIELDS.issubset(evidence):
            raise TargetViolation("DEPLOYMENT_TERMINAL")
    if not _hash(evidence["evidence_sha256"]):
        raise TargetViolation("DEPLOYMENT_CHECKSUM")
    unsigned = {
        key: value for key, value in evidence.items() if key != "evidence_sha256"
    }
    if (
        hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        != evidence["evidence_sha256"]
    ):
        raise TargetViolation("DEPLOYMENT_CHECKSUM")
    if (
        not isinstance(evidence["expected_plan_impact"], str)
        or not evidence["expected_plan_impact"]
    ):
        raise TargetViolation("DEPLOYMENT_IMPACT")
    if not isinstance(evidence["cost_note"], str) or not evidence["cost_note"]:
        raise TargetViolation("DEPLOYMENT_COST")


def finalize_deployment_evidence(
    pre_approval: Mapping[str, Any],
    *,
    outcome: str,
    apply_actor: str,
    started_at: str,
    ended_at: str,
    state_result: str,
    lock_condition: str,
    lifecycle_state: str,
    errors: Sequence[str],
    output_checksums: Mapping[str, str],
    resource_identities: Mapping[str, str] | None = None,
    verification: Mapping[str, Any] | None = None,
    approvals: Sequence[Mapping[str, Any]] | None = None,
    policy_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        outcome not in OUTCOMES
        or not isinstance(pre_approval, Mapping)
        or pre_approval.get("status") != "awaiting-approval"
    ):
        raise TargetViolation("DEPLOYMENT_OUTCOME")
    original_hash = pre_approval.get("evidence_sha256")
    if not SHA256.fullmatch(str(original_hash)):
        raise TargetViolation("DEPLOYMENT_CHECKSUM")
    unsigned = {
        key: value for key, value in pre_approval.items() if key != "evidence_sha256"
    }
    if (
        hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        != original_hash
    ):
        raise TargetViolation("DEPLOYMENT_CHECKSUM")
    if outcome == "succeeded" and (
        state_result != "succeeded"
        or errors
        or lock_condition not in {"clear", "released"}
        or not resource_identities
        or not verification
        or verification.get("status") != "passed"
    ):
        raise TargetViolation("DEPLOYMENT_OUTCOME")
    if outcome == "succeeded" and (not approvals or policy_result is None):
        raise TargetViolation("DEPLOYMENT_PROVENANCE")
    if outcome != "succeeded" and state_result == "succeeded":
        raise TargetViolation("DEPLOYMENT_OUTCOME")
    if outcome == "lock-conflict" and lock_condition not in {
        "conflict",
        "inspect-required",
    }:
        raise TargetViolation("DEPLOYMENT_OUTCOME")
    if outcome in {"failed", "partial", "cancelled", "runner-lost"} and not errors:
        raise TargetViolation("DEPLOYMENT_ERROR")
    start = _timestamp(started_at, "DEPLOYMENT_TIMESTAMP")
    end = _timestamp(ended_at, "DEPLOYMENT_TIMESTAMP")
    if end < start or not apply_actor or not state_result or not lifecycle_state:
        raise TargetViolation("DEPLOYMENT_RESULT")
    if any(not isinstance(item, str) or len(item) > 240 for item in errors):
        raise TargetViolation("DEPLOYMENT_ERROR")
    if any(
        not isinstance(key, str) or not _hash(value)
        for key, value in output_checksums.items()
    ):
        raise TargetViolation("DEPLOYMENT_OUTPUT")
    result = {
        **dict(pre_approval),
        "status": outcome,
        "apply_actor": apply_actor,
        "started_at": started_at,
        "ended_at": ended_at,
        "state_result": state_result,
        "lock_condition": lock_condition,
        "lifecycle_state": lifecycle_state,
        "errors": list(errors)[:20],
        "output_checksums": dict(output_checksums),
        "resource_identities": dict(resource_identities or {}),
        "verification": dict(
            verification or {"status": "not-run", "launch_enabled": False}
        ),
        "workflow_conclusion": "success" if outcome == "succeeded" else "failure",
    }
    if approvals is not None:
        result["approvals"] = [dict(item) for item in approvals]
    if policy_result is not None:
        result["policy_result"] = dict(policy_result)
    _screen(result)
    result.pop("evidence_sha256", None)
    result["evidence_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


def lookup_deployment_identity(
    evidence: Mapping[str, Any],
    *,
    occurrence_id: str | None = None,
    task_arn: str | None = None,
    index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded identity metadata from a checksum-verified authoritative index."""
    if not occurrence_id and not task_arn:
        raise TargetViolation("DEPLOYMENT_LOOKUP_REFERENCE")
    if index is not None:
        key = occurrence_id or task_arn
        entries = index.get("entries") if isinstance(index, Mapping) else None
        if not isinstance(entries, Mapping) or key not in entries:
            raise TargetViolation("DEPLOYMENT_LOOKUP_REFERENCE")
        indexed = entries[key]
        if not isinstance(indexed, Mapping) or indexed.get(
            "evidence_sha256"
        ) != evidence.get("evidence_sha256"):
            raise TargetViolation("DEPLOYMENT_LOOKUP_INDEX")
    supplied_hash = evidence.get("evidence_sha256")
    if not SHA256.fullmatch(str(supplied_hash)):
        raise TargetViolation("DEPLOYMENT_LOOKUP_CHECKSUM")
    unsigned = {
        key: value for key, value in evidence.items() if key != "evidence_sha256"
    }
    if (
        hashlib.sha256(
            json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        != supplied_hash
    ):
        raise TargetViolation("DEPLOYMENT_LOOKUP_CHECKSUM")
    validate_deployment_evidence(evidence)
    identity = evidence.get("deployment_identity", {})
    if not isinstance(identity, Mapping) or not isinstance(
        identity.get("identity"), Mapping
    ):
        raise TargetViolation("DEPLOYMENT_LOOKUP")
    body = identity["identity"]
    bindings = evidence.get("bindings", {})
    if not isinstance(bindings, Mapping):
        raise TargetViolation("DEPLOYMENT_LOOKUP")
    references = evidence.get("references", {})
    if references and not isinstance(references, Mapping):
        raise TargetViolation("DEPLOYMENT_LOOKUP")
    if occurrence_id and references.get("occurrence_id") != occurrence_id:
        raise TargetViolation("DEPLOYMENT_LOOKUP_REFERENCE")
    if task_arn and references.get("task_arn") != task_arn:
        raise TargetViolation("DEPLOYMENT_LOOKUP_REFERENCE")
    return {
        "deployment_identity_sha256": evidence.get("deployment_identity_sha256"),
        "source_commit": body.get("source_commit"),
        "image_digest": body.get("image_digest"),
        "task_definition_arn": body.get("task_definition_arn"),
        "module_versions": body.get("module_versions"),
        "contract_version": body.get("contract_version"),
        "config_version": body.get("artifact_checksums", {}).get("config_version"),
        "cell_version": body.get("artifact_checksums", {}).get("cell_contract_version"),
        "workflow": body.get("workflow"),
        "target": {
            key: bindings.get(key)
            for key in ("account_id", "region", "environment", "root", "state_key")
        },
        "config_sha256": bindings.get("config_sha256"),
        "schedule_generation": bindings.get("schedule_generation"),
        "status": evidence.get("status"),
        "workflow_conclusion": evidence.get("workflow_conclusion"),
        "deployment_run_id": bindings.get("workflow_run_id"),
        "approvals": evidence.get("approvals", []),
        "policy_result": evidence.get("policy_result"),
    }


def build_deployment_identity_index(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a non-sensitive, duplicate-free lookup index from terminal evidence."""
    entries: dict[str, Any] = {}
    for record in records:
        validate_deployment_evidence(record)
        if record.get("status") == "awaiting-approval":
            raise TargetViolation("DEPLOYMENT_LOOKUP_TERMINAL")
        references = record.get("references", {})
        if not isinstance(references, Mapping):
            raise TargetViolation("DEPLOYMENT_LOOKUP_REFERENCE")
        keys = [references.get("occurrence_id"), references.get("task_arn")]
        for key in filter(None, keys):
            if (
                key in entries
                and entries[key]["evidence_sha256"] != record["evidence_sha256"]
            ):
                raise TargetViolation("DEPLOYMENT_LOOKUP_DUPLICATE")
            entries[str(key)] = {
                "evidence_sha256": record["evidence_sha256"],
                "deployment_identity_sha256": record["deployment_identity_sha256"],
                "deployment_run_id": record["bindings"]["workflow_run_id"],
            }
    return {"schema_version": "1.0.0", "entries": entries}


def validate_recovery_plan(recovery: Mapping[str, Any]) -> None:
    required = {
        "known_good_identity_sha256",
        "disable_launch_first",
        "retire_generation",
        "evidence_action",
        "fresh_plan_required",
        "state_migration",
        "application_compensation_owner",
        "recovery_objective_seconds",
        "verification",
    }
    if "revert the commit" in json.dumps(recovery, sort_keys=True).lower():
        raise TargetViolation("RECOVERY_GENERIC")
    optional = {
        "target_manifest_sha256",
        "current_identity_sha256",
        "current_generation",
        "changed_addresses",
    }
    if set(recovery) - required - optional or any(
        recovery.get(key) in (None, "") for key in required
    ):
        raise TargetViolation("RECOVERY_REQUIRED")
    if not _hash(recovery["known_good_identity_sha256"]):
        raise TargetViolation("RECOVERY_IDENTITY")
    if recovery.get("target_manifest_sha256") is not None and not _hash(
        recovery["target_manifest_sha256"]
    ):
        raise TargetViolation("RECOVERY_TARGET")
    if recovery.get("current_identity_sha256") is not None and not _hash(
        recovery["current_identity_sha256"]
    ):
        raise TargetViolation("RECOVERY_IDENTITY")
    if (
        "target_manifest_sha256" not in recovery
        or "current_identity_sha256" not in recovery
    ):
        raise TargetViolation("RECOVERY_BINDING")
    if "current_generation" not in recovery or "changed_addresses" not in recovery:
        raise TargetViolation("RECOVERY_SCOPE")
    if not isinstance(recovery["changed_addresses"], list) or any(
        not isinstance(item, str) or not item or len(item) > 200
        for item in recovery["changed_addresses"]
    ):
        raise TargetViolation("RECOVERY_SCOPE")
    if (
        recovery["disable_launch_first"] is not True
        or recovery["fresh_plan_required"] is not True
    ):
        raise TargetViolation("RECOVERY_ORDER")
    if recovery["evidence_action"] not in {
        "quarantine-and-drain",
        "preserve-and-reconcile",
    }:
        raise TargetViolation("RECOVERY_EVIDENCE")
    if (
        not isinstance(recovery["recovery_objective_seconds"], int)
        or not 1 <= recovery["recovery_objective_seconds"] <= 604800
    ):
        raise TargetViolation("RECOVERY_OBJECTIVE")
    allowed_checks = {
        "target_identity",
        "lifecycle",
        "schedule",
        "expectation_horizon",
        "task_revision",
        "networking",
        "logs",
        "occurrences",
        "deadlines",
        "alarms",
        "notifications",
        "compensation",
    }
    if (
        not isinstance(recovery["verification"], list)
        or not recovery["verification"]
        or any(item not in allowed_checks for item in recovery["verification"])
    ):
        raise TargetViolation("RECOVERY_VERIFICATION")


def plan_recovery_execution(
    recovery: Mapping[str, Any],
    *,
    known_good: Mapping[str, Any],
    current: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Return the only permitted recovery order; no mutation occurs here."""
    validate_recovery_plan(recovery)
    _validate_identity(known_good)
    _validate_identity(current)
    known_body = known_good["identity"]
    current_body = current["identity"]
    if known_good["deployment_identity_id"] != recovery["known_good_identity_sha256"]:
        raise TargetViolation("RECOVERY_IDENTITY")
    if current["deployment_identity_id"] != recovery["current_identity_sha256"]:
        raise TargetViolation("RECOVERY_IDENTITY")
    for field in ("account_id", "region", "environment"):
        if known_body[field] != current_body[field]:
            raise TargetViolation("RECOVERY_COMPATIBILITY")
    if known_body["source_commit"] == current_body["source_commit"]:
        raise TargetViolation("RECOVERY_NOOP")
    return (
        {"step": 1, "action": "disable-launch", "required": True},
        {
            "step": 2,
            "action": "retire-generation",
            "generation": recovery["current_generation"],
        },
        {"step": 3, "action": recovery["evidence_action"]},
        {"step": 4, "action": "create-fresh-plan", "stale_plan_reuse": False},
        {"step": 5, "action": "normal-target-policy-readiness-approval-lock-controls"},
        {"step": 6, "action": "apply-fresh-approved-plan"},
    )


def validate_verification(
    observed: Mapping[str, Any],
    *,
    required: Sequence[str],
    evidence_refs: Mapping[str, str] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    allowed = {
        "target_identity",
        "lifecycle",
        "schedule",
        "expectation_horizon",
        "task_revision",
        "networking",
        "logs",
        "occurrences",
        "deadlines",
        "alarms",
        "notifications",
        "compensation",
    }
    if not required or any(
        not isinstance(key, str) or not key or key not in allowed for key in required
    ):
        raise TargetViolation("VERIFICATION_REQUIRED")
    if not isinstance(observed, Mapping):
        raise TargetViolation("VERIFICATION_OBSERVED")
    missing = [key for key in required if observed.get(key) is not True]
    timestamp = observed_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    _timestamp(timestamp, "VERIFICATION_TIMESTAMP")
    return {
        "schema_version": "1.0.0",
        "status": "passed" if not missing else "blocked",
        "launch_enabled": not missing,
        "missing": missing,
        "checks": {key: observed.get(key) is True for key in required},
        "observed_at": timestamp,
        "evidence_refs": {
            key: value
            for key, value in (evidence_refs or {}).items()
            if key in required
        },
        "remediation": (
            "Keep launch disabled; execute the reviewed rollback or forward-fix plan."
            if missing
            else ""
        ),
        "decision": "blocked" if missing else "resume-eligible",
    }


def validate_emergency_record(
    record: Mapping[str, Any], *, now: datetime | None = None
) -> None:
    required = {
        "schema_version",
        "status",
        "actor",
        "approver",
        "reason",
        "scope",
        "started_at",
        "expires_at",
        "commands",
        "deployment_identity_sha256",
        "verification",
        "alert_received",
        "review_due_at",
    }
    if (
        set(record) != required
        or record.get("schema_version") != "1.0.0"
        or record.get("status") != "approved"
    ):
        raise TargetViolation("EMERGENCY_SHAPE")
    if (
        record["actor"] == record["approver"]
        or not record["reason"]
        or not record["scope"]
    ):
        raise TargetViolation("EMERGENCY_APPROVAL")
    if not _hash(record["deployment_identity_sha256"]):
        raise TargetViolation("EMERGENCY_IDENTITY")
    if (
        not isinstance(record["commands"], list)
        or not record["commands"]
        or any(
            not isinstance(command, str) or len(command) > 240
            for command in record["commands"]
        )
    ):
        raise TargetViolation("EMERGENCY_COMMANDS")
    start = _timestamp(record["started_at"], "EMERGENCY_TIMESTAMP")
    expiry = _timestamp(record["expires_at"], "EMERGENCY_TIMESTAMP")
    review = _timestamp(record["review_due_at"], "EMERGENCY_TIMESTAMP")
    current = now or datetime.now(timezone.utc)
    if not start < expiry or expiry <= current or review <= current:
        raise TargetViolation("EMERGENCY_EXPIRED")
    if record["alert_received"] is not True or not isinstance(
        record["verification"], Mapping
    ):
        raise TargetViolation("EMERGENCY_VERIFICATION")
    _screen(record)
    required_checks = {"target_identity", "deployment_identity", "review_complete"}
    if any(record["verification"].get(key) is not True for key in required_checks):
        raise TargetViolation("EMERGENCY_VERIFICATION")
    if (
        record["verification"].get("deployment_identity_sha256")
        != record["deployment_identity_sha256"]
    ):
        raise TargetViolation("EMERGENCY_IDENTITY")
