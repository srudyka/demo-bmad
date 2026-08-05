"""Credential-free production readiness evidence evaluation.

This module evaluates a versioned evidence envelope and returns bounded,
sanitized findings. It does not create approval/readiness evidence, assume AWS
credentials, or mutate infrastructure. The existing Story 3.5 decision
validator remains the apply-facing authorization boundary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from scripts.deployment_targets import TargetViolation

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")

REQUIRED_CATEGORIES = (
    "schedule-expectations",
    "launch-runtime",
    "completion-alerts",
    "security",
    "recovery",
    "operations",
    "target-compatibility",
    "policy-plan",
    "toolchain-hygiene",
)
REQUIRED_CONTROL_IDS = (
    "formatting",
    "terraform-validation",
    "module-examples",
    "contracts-runtime",
    "provider-locks",
    "security-scans",
    "iam-analysis",
    "policy-results",
    "plan-impact",
    "immutable-image",
    "cell-compatibility",
    "target-verification",
    "address-migration",
    "ownership-tags",
    "networking-secrets-state",
    "logs-alarms-notifications",
    "completion-lifecycle",
    "runbook-operations",
    "rollback-compensation",
)
FORBIDDEN_TOKENS = (
    "secret",
    "password",
    "credential",
    "private_key",
    "raw_config",
    "terraform_state",
    "tfplan",
)
REQUIRED_BINDINGS = (
    "repository",
    "source_commit",
    "workflow_sha",
    "workflow_run_id",
    "plan_sha256",
    "deployment_identity_sha256",
    "account_id",
    "region",
    "environment",
    "job_id",
    "config_sha256",
    "schedule_generation",
    "cell_contract_sha256",
    "cell_version",
    "policy_id",
    "policy_version",
    "target_manifest_sha256",
    "terraform_root",
    "state_key",
    "provider_lock_path",
    "backend_lock_path",
)


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise TargetViolation("READINESS_EVIDENCE_TIMESTAMP")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError as error:
        raise TargetViolation("READINESS_EVIDENCE_TIMESTAMP") from error


def _require_digest(value: Any, code: str) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise TargetViolation(code)


def _contains_forbidden(value: Any, path: str = "") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            # Artifact identifiers and control names are opaque, non-secret labels.
            if not path.startswith("artifact_manifest") and any(
                token in key_text for token in FORBIDDEN_TOKENS
            ):
                return f"{path}.{key}" if path else str(key)
            found = _contains_forbidden(child, f"{path}.{key}" if path else str(key))
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _contains_forbidden(child, f"{path}[{index}]")
            if found:
                return found
    elif isinstance(value, str):
        lower = value.lower()
        if any(
            token in lower
            for token in (
                "-----begin",
                "aws_secret_access_key",
                "secret-value",
                "password=",
            )
        ):
            return path or "value"
    return None


def _binding_projection(envelope: Mapping[str, Any]) -> dict[str, Any]:
    bindings = envelope.get("bindings")
    if not isinstance(bindings, Mapping):
        raise TargetViolation("READINESS_BINDINGS_SHAPE")
    return {key: bindings.get(key) for key in REQUIRED_BINDINGS}


def _validate_bindings(
    bindings: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    if set(bindings) != set(REQUIRED_BINDINGS):
        raise TargetViolation("READINESS_BINDINGS_SHAPE")
    for key in REQUIRED_BINDINGS:
        value = bindings[key]
        if value in (None, "") or not isinstance(value, str):
            raise TargetViolation("READINESS_BINDING_MISSING:" + key)
        if key == "source_commit" and not SHA1.fullmatch(value):
            raise TargetViolation("READINESS_BINDING_FORMAT:source_commit")
        if key.endswith("_sha256") and not SHA256.fullmatch(value):
            raise TargetViolation("READINESS_BINDING_FORMAT:" + key)
        if key == "workflow_sha" and not SHA1.fullmatch(value):
            raise TargetViolation("READINESS_BINDING_FORMAT:workflow_sha")
        expected_key = "root" if key == "terraform_root" and "root" in expected else key
        if expected_key not in expected:
            raise TargetViolation("READINESS_EXPECTED_BINDING_MISSING:" + key)
        if str(value) != str(expected[expected_key]):
            raise TargetViolation("READINESS_BINDING_MISMATCH:" + key)


def _validate_item(
    item: Mapping[str, Any],
    expected_bindings: Mapping[str, Any],
    artifact_manifest: Mapping[str, Any],
) -> None:
    required = {
        "category",
        "producer",
        "tool_version",
        "evaluated_at",
        "result",
        "artifact_sha256",
        "sensitivity",
        "reference",
        "bindings_sha256",
        "control_id",
        "claims",
    }
    if set(item) != required or any(item[key] in (None, "") for key in required):
        raise TargetViolation("READINESS_ITEM_SHAPE")
    if item["category"] not in REQUIRED_CATEGORIES:
        raise TargetViolation("READINESS_CATEGORY_UNKNOWN")
    if item["result"] not in {"passed", "failed", "exception", "limitation"}:
        raise TargetViolation("READINESS_ITEM_RESULT")
    if item["sensitivity"] not in {"public", "internal", "restricted"}:
        raise TargetViolation("READINESS_ITEM_SENSITIVITY")
    _timestamp(item["evaluated_at"])
    _require_digest(item["artifact_sha256"], "READINESS_ARTIFACT_CHECKSUM")
    _require_digest(item["bindings_sha256"], "READINESS_ITEM_BINDING_CHECKSUM")
    if item["bindings_sha256"] != _sha256(expected_bindings):
        raise TargetViolation("READINESS_ITEM_BINDING_CHECKSUM")
    if item["control_id"] not in REQUIRED_CONTROL_IDS:
        raise TargetViolation("READINESS_CONTROL_UNKNOWN")
    if not isinstance(item["claims"], Mapping) or not item["claims"]:
        raise TargetViolation("READINESS_CLAIMS_MISSING")
    if (
        not isinstance(item["reference"], str)
        or item["reference"] not in artifact_manifest
    ):
        raise TargetViolation("READINESS_REFERENCE_UNSAFE")
    artifact = artifact_manifest[item["reference"]]
    if (
        not isinstance(artifact, Mapping)
        or artifact.get("sha256") != item["artifact_sha256"]
    ):
        raise TargetViolation("READINESS_ARTIFACT_BINDING")
    if artifact.get("access") not in {"protected", "restricted"}:
        raise TargetViolation("READINESS_ARTIFACT_ACCESS")


def validate_evidence_envelope(
    envelope: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate exact-generation evidence and return a sanitized decision summary."""
    required = {
        "schema_version",
        "status",
        "evidence_source",
        "bindings",
        "items",
        "attestations",
        "findings",
        "exceptions",
        "artifact_manifest",
        "approvals",
        "reviewer_summary",
        "evaluated_at",
        "expires_at",
        "evidence_sha256",
    }
    if set(envelope) != required:
        raise TargetViolation("READINESS_ENVELOPE_SHAPE")
    if envelope["schema_version"] != "1.0.0":
        raise TargetViolation("READINESS_SCHEMA_VERSION")
    if envelope["status"] not in {"passed", "blocked", "exception", "limitation"}:
        raise TargetViolation("READINESS_STATUS")
    if envelope["evidence_source"] not in {"epic4", "disposable-fixture"}:
        raise TargetViolation("READINESS_PROVENANCE")
    bindings = _binding_projection(envelope)
    _validate_bindings(bindings, expected)
    from scripts.production_policy import load_policy_catalog

    catalog = load_policy_catalog()
    catalog_path = (
        Path(__file__).resolve().parents[1]
        / "contracts/v1/catalogs/production-policy.json"
    )
    catalog_digest = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    if bindings["policy_id"] != catalog["policy_id"] or bindings[
        "policy_version"
    ] not in {
        catalog["policy_version"],
        catalog_digest,
    }:
        raise TargetViolation("READINESS_POLICY_UNKNOWN")
    if (
        expected.get("environment") == "production"
        and envelope["evidence_source"] != "epic4"
    ):
        raise TargetViolation("READINESS_PRODUCTION_FIXTURE")
    forbidden = _contains_forbidden(envelope)
    if forbidden:
        raise TargetViolation("READINESS_SENSITIVE_FIELD:" + forbidden)
    evaluated = _timestamp(envelope["evaluated_at"])
    expires = _timestamp(envelope["expires_at"])
    current = now or datetime.now(timezone.utc)
    if (
        evaluated > current
        or current - evaluated > timedelta(days=1)
        or expires <= evaluated
        or expires <= current
    ):
        raise TargetViolation("READINESS_EXPIRED")
    items = envelope["items"]
    if not isinstance(items, list) or not items:
        raise TargetViolation("READINESS_ITEMS_MISSING")
    seen: set[str] = set()
    seen_controls: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise TargetViolation("READINESS_ITEM_SHAPE")
        _validate_item(item, bindings, envelope["artifact_manifest"])
        item_time = _timestamp(item["evaluated_at"])
        if item_time > evaluated or item_time > current:
            raise TargetViolation("READINESS_ITEM_FRESHNESS")
        category = str(item["category"])
        seen.add(category)
        seen_controls.add(str(item["control_id"]))
    missing = sorted(set(REQUIRED_CATEGORIES) - seen)
    if missing:
        raise TargetViolation("READINESS_CATEGORY_MISSING:" + ",".join(missing))
    missing_controls = sorted(set(REQUIRED_CONTROL_IDS) - seen_controls)
    if missing_controls:
        raise TargetViolation("READINESS_CONTROL_MISSING:" + ",".join(missing_controls))
    if not isinstance(envelope["attestations"], list) or not envelope["attestations"]:
        raise TargetViolation("READINESS_ATTESTATIONS_MISSING")
    for attestation in envelope["attestations"]:
        if not isinstance(attestation, Mapping) or not {
            "role",
            "actor",
            "deployment_identity_sha256",
            "attested_at",
            "result",
        }.issubset(attestation):
            raise TargetViolation("READINESS_ATTESTATION_SHAPE")
        if (
            attestation["deployment_identity_sha256"]
            != bindings["deployment_identity_sha256"]
        ):
            raise TargetViolation("READINESS_ATTESTATION_BINDING")
        attested_at = _timestamp(attestation["attested_at"])
        if attested_at > evaluated or attested_at > current:
            raise TargetViolation("READINESS_ATTESTATION_FRESHNESS")
        if attestation["result"] != "passed":
            raise TargetViolation("READINESS_ATTESTATION_FAILED")
    if not isinstance(envelope["findings"], list):
        raise TargetViolation("READINESS_FINDINGS_SHAPE")
    for finding in envelope["findings"]:
        if not isinstance(finding, Mapping) or set(finding) != {
            "code",
            "remediation",
            "owner",
            "resolution_point",
            "blocking",
        }:
            raise TargetViolation("READINESS_FINDING_SHAPE")
        if any(
            not isinstance(finding[key], str) or not finding[key]
            for key in ("code", "remediation", "owner", "resolution_point")
        ) or not isinstance(finding["blocking"], bool):
            raise TargetViolation("READINESS_FINDING_SHAPE")
        if finding["blocking"] is not True and envelope["status"] == "blocked":
            raise TargetViolation("READINESS_FINDING_DISPOSITION")
    if envelope["status"] != "passed" and not envelope["findings"]:
        raise TargetViolation("READINESS_FINDING_REQUIRED")
    if envelope["status"] == "exception" and not envelope["exceptions"]:
        raise TargetViolation("READINESS_EXCEPTION_REQUIRED")
    if envelope["status"] == "passed" and envelope["exceptions"]:
        raise TargetViolation("READINESS_EXCEPTION_UNEXPECTED")
    required_approvals = {"platform", "job-owner"}
    if expected.get("security_required") is True:
        required_approvals.add("security")
    if not isinstance(envelope["approvals"], list):
        raise TargetViolation("READINESS_APPROVALS_SHAPE")
    seen_roles: set[str] = set()
    for approval in envelope["approvals"]:
        approval_fields = {
            "role",
            "actor",
            "source_commit",
            "workflow_sha",
            "workflow_run_id",
            "deployment_identity_sha256",
            "approved_at",
            "expires_at",
            "status",
        }
        if not isinstance(approval, Mapping) or set(approval) != approval_fields:
            raise TargetViolation("READINESS_APPROVAL_SHAPE")
        if approval["role"] in seen_roles or approval["role"] not in {
            "platform",
            "job-owner",
            "security",
        }:
            raise TargetViolation("READINESS_APPROVAL_ROLE")
        seen_roles.add(approval["role"])
        if (
            approval["actor"] in {"", "unknown", "placeholder", "todo"}
            or approval["actor"] == "system"
        ):
            raise TargetViolation("READINESS_APPROVAL_ACTOR")
        if (
            approval["source_commit"] != bindings["source_commit"]
            or approval["workflow_sha"] != bindings["workflow_sha"]
            or approval["workflow_run_id"] != bindings["workflow_run_id"]
            or approval["deployment_identity_sha256"]
            != bindings["deployment_identity_sha256"]
            or approval["status"] != "approved"
        ):
            raise TargetViolation("READINESS_APPROVAL_BINDING")
        approved_at = _timestamp(approval["approved_at"])
        approval_expires = _timestamp(approval["expires_at"])
        if (
            approved_at > evaluated
            or approval_expires <= current
            or approval_expires <= approved_at
        ):
            raise TargetViolation("READINESS_APPROVAL_FRESHNESS")
    if not required_approvals.issubset(seen_roles):
        raise TargetViolation("READINESS_APPROVAL_MISSING")
    summary = envelope["reviewer_summary"]
    if not isinstance(summary, Mapping) or set(summary) != {
        "status",
        "reviewer_roles",
        "evidence_links",
        "generated_at",
        "access_control",
    }:
        raise TargetViolation("READINESS_SUMMARY_SHAPE")
    if (
        summary["status"] != envelope["status"]
        or not isinstance(summary["reviewer_roles"], list)
        or not isinstance(summary["evidence_links"], list)
        or summary["access_control"] not in {"protected", "restricted"}
    ):
        raise TargetViolation("READINESS_SUMMARY_BINDING")
    summary_time = _timestamp(summary["generated_at"])
    if summary_time > evaluated or summary_time > current:
        raise TargetViolation("READINESS_SUMMARY_FRESHNESS")
    if any(
        link not in envelope["artifact_manifest"] for link in summary["evidence_links"]
    ):
        raise TargetViolation("READINESS_SUMMARY_LINK")
    for exception in envelope["exceptions"]:
        fields = {
            "policy_id",
            "policy_version",
            "resource",
            "environment",
            "source_commit",
            "plan_sha256",
            "owner",
            "justification",
            "approver",
            "compensating_control",
            "expires_at",
            "review_at",
            "signature",
        }
        if not isinstance(exception, Mapping) or set(exception) != fields:
            raise TargetViolation("READINESS_EXCEPTION_SHAPE")
        if (
            exception["source_commit"] != bindings["source_commit"]
            or exception["plan_sha256"] != bindings["plan_sha256"]
            or _timestamp(exception["expires_at"]) <= current
            or _timestamp(exception["review_at"]) <= current
        ):
            raise TargetViolation("READINESS_EXCEPTION_BINDING")
    body = {key: envelope[key] for key in sorted(required) if key != "evidence_sha256"}
    if envelope["evidence_sha256"] != _sha256(body):
        raise TargetViolation("READINESS_EVIDENCE_CHECKSUM")
    if envelope["status"] == "passed" and envelope["findings"]:
        raise TargetViolation("READINESS_PASSED_WITH_FINDINGS")
    if envelope["status"] == "passed" and any(
        item["result"] != "passed" for item in items
    ):
        raise TargetViolation("READINESS_PASSED_WITH_FAILED_ITEM")
    return {
        "schema_version": envelope["schema_version"],
        "status": envelope["status"],
        "evidence_source": envelope["evidence_source"],
        "evidence_sha256": envelope["evidence_sha256"],
        "evaluated_at": envelope["evaluated_at"],
        "expires_at": envelope["expires_at"],
        "categories": sorted(seen),
        "blocking_findings": sum(
            1 for finding in envelope["findings"] if finding.get("blocking") is True
        ),
    }


def seal_evidence_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return a checksum-sealed copy without inventing evidence or findings."""
    if "evidence_sha256" in envelope and envelope["evidence_sha256"] not in (None, ""):
        raise TargetViolation("READINESS_ALREADY_SEALED")
    required = {
        "schema_version",
        "status",
        "evidence_source",
        "bindings",
        "items",
        "attestations",
        "findings",
        "exceptions",
        "artifact_manifest",
        "approvals",
        "reviewer_summary",
        "evaluated_at",
        "expires_at",
    }
    if set(envelope) != required or envelope.get("schema_version") != "1.0.0":
        raise TargetViolation("READINESS_ENVELOPE_SHAPE")
    body = dict(envelope)
    body["evidence_sha256"] = _sha256(envelope)
    return body


def invalidate_if_bindings_changed(
    envelope: Mapping[str, Any], current_bindings: Mapping[str, Any]
) -> bool:
    """Return whether a previously evaluated envelope is stale for new inputs."""
    return _binding_projection(envelope) != {
        key: current_bindings.get(key) for key in REQUIRED_BINDINGS
    } or (
        "evidence_sha256" in current_bindings
        and envelope.get("evidence_sha256") != current_bindings.get("evidence_sha256")
    )
