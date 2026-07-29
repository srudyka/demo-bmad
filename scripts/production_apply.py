"""Credential-free validation boundary for exact production plan approval/apply."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from scripts.deployment_targets import (
    TargetViolation,
    preflight_target,
    validate_oidc_claims,
    validate_target_manifest,
)
from scripts.production_policy import evaluate_production_plan, load_policy_catalog
from scripts.trusted_plan import verify_plan_json_matches_binary

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _utc(value: Any, code: str) -> datetime:
    if not isinstance(value, str):
        raise TargetViolation(code)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TargetViolation(code) from error
    if result.tzinfo is None:
        raise TargetViolation(code)
    return result.astimezone(timezone.utc)


def _required(record: Mapping[str, Any], fields: set[str], code: str) -> None:
    if set(record) != fields or any(record[field] in (None, "") for field in fields):
        raise TargetViolation(code)


def validate_readiness(
    readiness: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    now: datetime | None = None,
    allow_fixture: bool = False,
) -> None:
    """Require a readiness decision bound to the exact plan and lifecycle identity."""
    required = {
        "schema_version",
        "status",
        "environment",
        "evidence_source",
        "source_commit",
        "plan_sha256",
        "target_manifest_sha256",
        "job_id",
        "config_sha256",
        "schedule_generation",
        "deployment_identity_sha256",
        "lifecycle_state",
        "occurrence_tracking",
        "evaluated_at",
        "expires_at",
        "evidence_sha256",
    }
    _required(readiness, required, "READINESS_SHAPE")
    if readiness["schema_version"] != "1.0.0" or readiness["status"] != "passed":
        raise TargetViolation("READINESS_NOT_PASSED")
    if (
        expected.get("environment") == "production"
        and readiness["evidence_source"] != "epic4"
    ):
        raise TargetViolation("READINESS_PROVENANCE")
    if readiness["evidence_source"] not in {"epic4", "disposable-fixture"} or (
        readiness["environment"] == "production"
        and readiness["evidence_source"] != "epic4"
    ):
        raise TargetViolation("READINESS_PROVENANCE")
    if readiness["environment"] == "production" and allow_fixture:
        raise TargetViolation("READINESS_FIXTURE_PRODUCTION")
    if (
        readiness["environment"] == "production"
        and readiness.get("source") == "fixture"
    ):
        raise TargetViolation("READINESS_FIXTURE_PRODUCTION")
    for key, pattern in (
        ("source_commit", SHA1),
        ("plan_sha256", SHA256),
        ("target_manifest_sha256", SHA256),
        ("config_sha256", SHA256),
        ("deployment_identity_sha256", SHA256),
        ("evidence_sha256", SHA256),
    ):
        if not pattern.fullmatch(str(readiness[key])):
            raise TargetViolation("READINESS_BINDING")
    for key in (
        "source_commit",
        "plan_sha256",
        "target_manifest_sha256",
        "job_id",
        "config_sha256",
        "schedule_generation",
        "deployment_identity_sha256",
    ):
        if str(readiness[key]) != str(expected.get(key, "")):
            raise TargetViolation("READINESS_BINDING")
    evidence_body = {
        key: readiness[key] for key in sorted(required) if key != "evidence_sha256"
    }
    expected_evidence = hashlib.sha256(
        json.dumps(evidence_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if readiness["evidence_sha256"] != expected_evidence:
        raise TargetViolation("READINESS_EVIDENCE_CHECKSUM")
    if (
        readiness["environment"] != expected.get("environment")
        or readiness["lifecycle_state"] != "MATERIALIZED"
        or readiness["occurrence_tracking"] is not True
    ):
        raise TargetViolation("READINESS_LIFECYCLE")
    evaluated = _utc(readiness["evaluated_at"], "READINESS_TIMESTAMP")
    expires = _utc(readiness["expires_at"], "READINESS_TIMESTAMP")
    current = now or datetime.now(timezone.utc)
    if expires <= evaluated or expires <= current:
        raise TargetViolation("READINESS_TIMESTAMP")


def validate_approval(
    approval: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    required = {
        "schema_version",
        "approval_id",
        "status",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "manifest_sha256",
        "account_id",
        "region",
        "environment",
        "root",
        "state_key",
        "cell_contract_sha256",
        "policy_version",
        "plan_sha256",
        "readiness_sha256",
        "phase",
        "generation",
        "author",
        "approvers",
        "approved_at",
        "expires_at",
        "security_required",
    }
    _required(approval, required, "APPROVAL_SHAPE")
    if approval["schema_version"] != "1.0.0" or approval["status"] != "approved":
        raise TargetViolation("APPROVAL_NOT_GRANTED")
    if not SHA1.fullmatch(str(approval["source_commit"])) or not SHA1.fullmatch(
        str(approval["workflow_sha"])
    ):
        raise TargetViolation("APPROVAL_BINDING")
    for key in (
        "manifest_sha256",
        "cell_contract_sha256",
        "policy_version",
        "plan_sha256",
        "readiness_sha256",
    ):
        if not SHA256.fullmatch(str(approval[key])):
            raise TargetViolation("APPROVAL_BINDING")
    for key in (
        "source_commit",
        "workflow_sha",
        "manifest_sha256",
        "account_id",
        "region",
        "environment",
        "root",
        "state_key",
        "cell_contract_sha256",
        "policy_version",
        "plan_sha256",
        "phase",
        "generation",
    ):
        if str(approval[key]) != str(expected.get(key, "")):
            raise TargetViolation("APPROVAL_BINDING")
    if str(approval["workflow_run_id"]) != str(expected.get("workflow_run_id", "")):
        raise TargetViolation("APPROVAL_RUN_BINDING")
    approvers = approval["approvers"]
    if not isinstance(approvers, list) or len(
        {str(item.get("role")) for item in approvers if isinstance(item, Mapping)}
    ) != len(approvers):
        raise TargetViolation("APPROVAL_REVIEWERS")
    required_roles = {"platform", "job-owner"} | (
        {"security"} if expected.get("security_required") is True else set()
    )
    if approval["security_required"] != (expected.get("security_required") is True):
        raise TargetViolation("APPROVAL_POLICY_BINDING")
    actual_roles = {
        str(item.get("role"))
        for item in approvers
        if isinstance(item, Mapping) and item.get("actor") and item.get("approved_at")
    }
    if not required_roles.issubset(actual_roles):
        raise TargetViolation("APPROVAL_REVIEWERS")
    actors = [str(item.get("actor")) for item in approvers if isinstance(item, Mapping)]
    if len(actors) != len(set(actors)) or any(
        not item.get("actor") or not item.get("approved_at")
        for item in approvers
        if isinstance(item, Mapping)
    ):
        raise TargetViolation("APPROVAL_REVIEWERS")
    author = approval.get("author") or expected.get("author")
    if not author or any(actor == str(author) for actor in actors):
        raise TargetViolation("APPROVAL_SELF_REVIEW")
    approved = _utc(approval["approved_at"], "APPROVAL_TIMESTAMP")
    expires = _utc(approval["expires_at"], "APPROVAL_TIMESTAMP")
    if expires <= approved or expires <= (now or datetime.now(timezone.utc)):
        raise TargetViolation("APPROVAL_TIMESTAMP")


def validate_apply_authorization(
    authorization: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    binary_plan: bytes,
    now: datetime | None = None,
) -> None:
    required = {
        "schema_version",
        "status",
        "apply_role_arn",
        "caller_account_id",
        "caller_role_arn",
        "caller_role_id",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "manifest_sha256",
        "target_environment",
        "target_root",
        "state_key",
        "plan_sha256",
        "policy_status",
        "readiness_sha256",
        "approval_id",
        "artifact_audience",
        "artifact_expires_at",
        "lock_id",
        "authorized_at",
    }
    _required(authorization, required, "APPLY_AUTH_SHAPE")
    if (
        authorization["schema_version"] != "1.0.0"
        or authorization["status"] != "authorized"
    ):
        raise TargetViolation("APPLY_NOT_AUTHORIZED")
    if authorization["plan_sha256"] != hashlib.sha256(binary_plan).hexdigest():
        raise TargetViolation("APPLY_PLAN_CHECKSUM")
    if (
        authorization["policy_status"] != "passed"
        or authorization["artifact_audience"] != "trusted-reviewer"
    ):
        raise TargetViolation("APPLY_POLICY_OR_ARTIFACT")
    expected_keys = {"target_environment": "environment", "target_root": "root"}
    for key in (
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "manifest_sha256",
        "target_environment",
        "target_root",
        "state_key",
        "readiness_sha256",
        "approval_id",
    ):
        if str(authorization[key]) != str(
            expected.get(expected_keys.get(key, key), "")
        ):
            raise TargetViolation("APPLY_BINDING")
    if _utc(authorization["artifact_expires_at"], "APPLY_TIMESTAMP") <= _utc(
        authorization["authorized_at"], "APPLY_TIMESTAMP"
    ) or _utc(authorization["artifact_expires_at"], "APPLY_TIMESTAMP") <= (
        now or datetime.now(timezone.utc)
    ):
        raise TargetViolation("APPLY_ARTIFACT_EXPIRED")
    if (
        authorization.get("caller_account_id") != expected.get("account_id")
        or authorization.get("apply_role_arn") != expected.get("apply_role_arn")
        or not re.fullmatch(r"[A-Za-z0-9._:/=-]{1,256}", str(authorization["lock_id"]))
        or authorization["caller_role_arn"] != authorization["apply_role_arn"]
        or authorization.get("lock_id") != expected.get("lock_id")
        or authorization.get("caller_role_id") != expected.get("caller_role_id")
    ):
        raise TargetViolation("APPLY_CALLER")


def bounded_failure_evidence(failure: Mapping[str, Any]) -> dict[str, Any]:
    """Retain only bounded operational evidence; never copy Terraform output wholesale."""
    allowed = (
        "schema_version",
        "status",
        "run_id",
        "plan_sha256",
        "state_key",
        "lock_state",
        "error_code",
        "recovery_guidance",
        "recorded_at",
    )
    required = {
        "schema_version",
        "status",
        "run_id",
        "plan_sha256",
        "state_key",
        "lock_state",
        "error_code",
        "recovery_guidance",
        "recorded_at",
    }
    if set(failure) != required or any(
        failure.get(key) in (None, "") for key in required
    ):
        raise TargetViolation("FAILURE_EVIDENCE_SHAPE")
    result = {key: str(failure[key])[:240] for key in allowed}
    if "plan_sha256" in result and not SHA256.fullmatch(result["plan_sha256"]):
        raise TargetViolation("FAILURE_PLAN_BINDING")
    if "recorded_at" in result:
        _utc(result["recorded_at"], "FAILURE_TIMESTAMP")
    return result


def validate_emergency_access(
    emergency: Mapping[str, Any],
    expected_manifest_sha256: str,
    *,
    now: datetime | None = None,
) -> None:
    required = {
        "schema_version",
        "status",
        "actor",
        "approver",
        "target_manifest_sha256",
        "operation",
        "expires_at",
        "alert_id",
        "incident_id",
        "review_due_at",
    }
    if set(emergency) != required or any(not emergency.get(key) for key in required):
        raise TargetViolation("EMERGENCY_SHAPE")
    if emergency["schema_version"] != "1.0.0" or emergency["status"] != "approved":
        raise TargetViolation("EMERGENCY_STATUS")
    if emergency["actor"] == emergency["approver"]:
        raise TargetViolation("EMERGENCY_SELF_APPROVAL")
    if emergency["operation"] not in {"disable", "rollback", "forward-fix"}:
        raise TargetViolation("EMERGENCY_OPERATION")
    if emergency["target_manifest_sha256"] != expected_manifest_sha256:
        raise TargetViolation("EMERGENCY_TARGET")
    current = now or datetime.now(timezone.utc)
    if _utc(emergency["expires_at"], "EMERGENCY_TIMESTAMP") <= current:
        raise TargetViolation("EMERGENCY_EXPIRED")
    if _utc(emergency["review_due_at"], "EMERGENCY_TIMESTAMP") <= current:
        raise TargetViolation("EMERGENCY_REVIEW_OVERDUE")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--caller", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--github-claims", type=Path, required=True)
    parser.add_argument("--cell-contract", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--plan-json", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--bundle-manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_target_manifest(manifest)
    if manifest.get("environment") != "production":
        raise TargetViolation("APPLY_ENVIRONMENT")
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    classification = policy.get("classification")
    if not isinstance(classification, Mapping):
        raise TargetViolation("POLICY_RESULT_SHAPE")
    plan_sha256 = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    manifest_sha256 = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    if manifest_sha256 != os.environ["MANIFEST_SHA256"]:
        raise TargetViolation("TARGET_MANIFEST_DIGEST")
    expected = {
        **manifest,
        "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        "workflow_sha": os.environ["WORKFLOW_SHA"],
        "manifest_sha256": os.environ["MANIFEST_SHA256"],
        "target_manifest_sha256": manifest_sha256,
        "plan_sha256": plan_sha256,
        "readiness_sha256": os.environ["READINESS_SHA256"],
        "approval_id": os.environ["APPROVAL_ID"],
        "phase": os.environ["PHASE"],
        "generation": os.environ["GENERATION"],
        "job_id": os.environ["JOB_ID"],
        "config_sha256": os.environ["CONFIG_SHA256"],
        "schedule_generation": os.environ["SCHEDULE_GENERATION"],
        "deployment_identity_sha256": os.environ["DEPLOYMENT_IDENTITY_SHA256"],
        "lock_id": os.environ["LOCK_ID"],
        "caller_role_id": os.environ["CALLER_ROLE_ID"],
        "apply_role_arn": manifest["apply_role_arn"],
        "target_environment": manifest["environment"],
        "target_root": manifest["root"],
        "security_required": classification.get("security_review_required") is True,
    }
    if (
        os.environ.get("TARGET_ROOT") != manifest["root"]
        or os.environ.get("AWS_REGION") != manifest["region"]
    ):
        raise TargetViolation("TARGET_INPUT_MISMATCH")
    caller = json.loads(args.caller.read_text(encoding="utf-8"))
    authority = json.loads(args.authority.read_text(encoding="utf-8"))
    claims = json.loads(args.github_claims.read_text(encoding="utf-8"))
    cell = json.loads(args.cell_contract.read_text(encoding="utf-8"))
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    plan_json = json.loads(args.plan_json.read_text(encoding="utf-8"))
    bundle_manifest = json.loads(args.bundle_manifest.read_text(encoding="utf-8"))
    from scripts.production_bundle import verify_bundle_manifest

    verify_bundle_manifest(args.bundle_manifest.parent, bundle_manifest)
    verify_plan_json_matches_binary(args.plan, plan_json)
    validate_oidc_claims(claims, manifest)
    if claims.get("role_type") != "apply":
        raise TargetViolation("OIDC_APPLY_ROLE_REQUIRED")
    preflight_target(
        caller,
        manifest,
        expected_manifest_sha256=expected["manifest_sha256"],
        authority=authority,
    )
    if cell.get("cell_contract_sha256") != manifest["cell_contract_sha256"]:
        raise TargetViolation("TARGET_CELL_CONTRACT")
    if (
        lock.get("lock_id") != expected["lock_id"]
        or lock.get("state_key") != manifest["state_key"]
        or lock.get("owner") != expected["caller_role_id"]
    ):
        raise TargetViolation("APPLY_LOCK_OWNER")
    load_policy_catalog()
    policy_digest = hashlib.sha256(
        (
            Path(__file__).resolve().parents[1]
            / "contracts/v1/catalogs/production-policy.json"
        ).read_bytes()
    ).hexdigest()
    if expected["policy_version"] != policy_digest:
        raise TargetViolation("POLICY_VERSION_BINDING")
    if not isinstance(plan_json, Mapping):
        raise TargetViolation("POLICY_RESULT_BINDING")
    recomputed_policy = evaluate_production_plan(
        plan_json,
        target=manifest,
        source_commit=expected["source_commit"],
        plan_sha256=expected["plan_sha256"],
        now=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    if (
        policy.get("status") != "passed"
        or policy.get("source_commit") != expected["source_commit"]
        or policy.get("plan_sha256") != expected["plan_sha256"]
        or policy.get("classification") != recomputed_policy["classification"]
        or not isinstance(policy.get("findings"), list)
    ):
        raise TargetViolation("POLICY_RESULT_BINDING")
    validate_approval(json.loads(args.approval.read_text(encoding="utf-8")), expected)
    validate_readiness(json.loads(args.readiness.read_text(encoding="utf-8")), expected)
    validate_apply_authorization(
        json.loads(args.authorization.read_text(encoding="utf-8")),
        expected,
        binary_plan=args.plan.read_bytes(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
