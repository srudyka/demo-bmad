from __future__ import annotations

import copy
import hashlib
import json
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.deployment_targets import TargetViolation
from scripts.trusted_plan import (
    build_metadata,
    summarize_plan,
    validate_artifact_reference,
    validate_plan_request,
)
from scripts.production_policy import evaluate_production_plan, validate_exception
from scripts.production_apply import (
    bounded_failure_evidence,
    validate_apply_authorization,
    validate_approval,
    validate_readiness,
    validate_emergency_access,
)
from scripts.production_bundle import FILES, assemble_bundle, verify_bundle_manifest

ROOT = Path(__file__).resolve().parents[1]


def manifest() -> dict:
    return json.loads(
        (ROOT / "contract" / "fixtures" / "target-manifest.json").read_text()
    )


def request(m: dict) -> dict:
    canonical = json.dumps(m, sort_keys=True, separators=(",", ":")).encode()
    return {
        "repository_owner_id": m["repository_owner_id"],
        "repository_id": m["repository_id"],
        "source_commit": "0" * 40,
        "workflow_sha": m["plan_workflow_ref"].rsplit("@", 1)[-1],
        "workflow_run_id": "123",
        "environment": m["environment"],
        "account_id": m["account_id"],
        "region": m["region"],
        "root": m["root"],
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "plan_role_arn": m["plan_role_arn"],
        "state_key": m["state_key"],
        "cell_contract_sha256": m["cell_contract_sha256"],
        "policy_version": m["policy_version"],
        "provider_lock_sha256": "c" * 64,
        "backend_lock_sha256": "d" * 64,
        "role_session": "trusted-plan-123",
    }


def caller(m: dict) -> dict:
    return {
        "account_id": m["account_id"],
        "region": m["region"],
        "repository_owner_id": m["repository_owner_id"],
        "repository_id": m["repository_id"],
        "environment": m["environment"],
        "workflow_sha": m["plan_workflow_ref"].rsplit("@", 1)[-1],
        "manifest_sha256": request(m)["manifest_sha256"],
        "root": m["root"],
        "role_type": "plan",
        "role_arn": m["plan_role_arn"],
        "state_key": m["state_key"],
        "policy_version": m["policy_version"],
        "cell_contract_sha256": m["cell_contract_sha256"],
    }


def test_plan_request_requires_credential_free_validation_and_exact_bindings() -> None:
    m = manifest()
    req = request(m)
    auth = caller(m)
    validate_plan_request(
        req,
        m,
        source_commit="0" * 40,
        validation_evidence={
            "status": "passed",
            "credential_free": True,
            "source_commit": "0" * 40,
        },
        caller=auth,
        authority=auth,
        manifest_bytes=json.dumps(m, sort_keys=True, separators=(",", ":")).encode(),
    )
    evidence = {"status": "passed", "credential_free": False, "source_commit": "0" * 40}
    with pytest.raises(TargetViolation, match="PLAN_VALIDATION_EVIDENCE"):
        validate_plan_request(
            req,
            m,
            source_commit="0" * 40,
            validation_evidence=evidence,
            caller=auth,
            authority=auth,
            manifest_bytes=json.dumps(
                m, sort_keys=True, separators=(",", ":")
            ).encode(),
        )


def test_plan_rejects_changed_commit_or_role() -> None:
    m = manifest()
    req = request(m)
    auth = caller(m)
    for field, value in (
        ("source_commit", "1" * 40),
        ("plan_role_arn", m["apply_role_arn"]),
    ):
        bad = copy.deepcopy(req)
        bad[field] = value
        with pytest.raises(TargetViolation):
            validate_plan_request(
                bad,
                m,
                source_commit="0" * 40,
                validation_evidence={
                    "status": "passed",
                    "credential_free": True,
                    "source_commit": "0" * 40,
                },
                caller=auth,
                authority=auth,
                manifest_bytes=json.dumps(
                    m, sort_keys=True, separators=(",", ":")
                ).encode(),
            )


def test_summary_is_bounded_and_does_not_expose_values() -> None:
    result = summarize_plan(
        {
            "resource_changes": [
                {
                    "address": "aws_s3_bucket.state",
                    "change": {
                        "actions": ["update"],
                        "after": {"secret": "must-not-appear"},
                    },
                },
                {"address": "aws_iam_role.plan", "change": {"actions": []}},
            ]
        }
    )
    assert result["counts"] == {
        "create": 0,
        "update": 1,
        "delete": 0,
        "replace": 0,
        "no_op": 1,
    }
    assert "secret" not in json.dumps(result)


def test_noop_summary_and_metadata_are_still_reviewable() -> None:
    m = manifest()
    req = request(m)
    summary = summarize_plan({"resource_changes": []}, policy_status="passed")
    assert summary["no_op"] is True and summary["policy_status"] == "passed"
    metadata = build_metadata(
        req,
        plan_sha256="e" * 64,
        started_at="2026-07-28T12:00:00Z",
        completed_at="2026-07-28T12:01:00Z",
        terraform_version="1.9.0",
    )
    assert metadata["manifest_sha256"] == req["manifest_sha256"]


def test_artifact_reference_requires_trusted_audience_and_expiry() -> None:
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    validate_artifact_reference(
        {
            "uri": "github-actions://trusted-plan/review/plan",
            "sha256": "f" * 64,
            "expires_at": expiry,
            "audience": "trusted-reviewer",
        }
    )
    with pytest.raises(TargetViolation):
        validate_artifact_reference(
            {
                "uri": "https://attacker/plan",
                "sha256": "f" * 64,
                "expires_at": expiry,
                "audience": "pull-request",
            }
        )


def production_target() -> dict:
    return {
        "environment": "production",
        "account_id": "123456789012",
        "region": "us-east-1",
        "root": "modules/example",
    }


def clean_plan() -> dict:
    return {
        "resource_changes": [
            {
                "address": "aws_cloudwatch_log_group.job",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "retention_in_days": 30,
                        "tags": {
                            "Environment": "production",
                            "Application": "demo",
                            "Service": "job",
                            "Owner": "platform",
                            "ManagedBy": "Terraform",
                        },
                        "logs": "enabled",
                        "alarms": "alarm",
                        "notifications": "sns",
                        "acknowledgement": True,
                        "cell_contract": "cell-contract-v1",
                    },
                },
            }
        ]
    }


def test_production_policy_is_bounded_and_classifies_security_review() -> None:
    decision = evaluate_production_plan(
        clean_plan(),
        target=production_target(),
        source_commit="a" * 40,
        plan_sha256="b" * 64,
        now="2026-07-29T12:00:00Z",
    )
    assert decision["status"] == "passed"
    assert decision["classification"]["security_review_required"] is False
    assert "retention" not in json.dumps(decision)


@pytest.mark.parametrize(
    ("address", "after", "code"),
    [
        ("aws_security_group.job", {"egress": "0.0.0.0/0"}, "UNSAFE_EGRESS"),
        ("aws_iam_role.admin", {}, "PRIVILEGE_ESCALATION"),
        ("aws_ecr_image.job", {"image": "repo:latest"}, "MUTABLE_IMAGE"),
        (
            "aws_secretsmanager_secret_version.job",
            {"password": "hidden"},
            "PLAINTEXT_SECRET",
        ),
    ],
)
def test_production_policy_blocks_sensitive_changes(
    address: str, after: dict, code: str
) -> None:
    decision = evaluate_production_plan(
        {
            "resource_changes": [
                {"address": address, "change": {"actions": ["update"], "after": after}}
            ]
        },
        target=production_target(),
        source_commit="a" * 40,
        plan_sha256="b" * 64,
        now="2026-07-29T12:00:00Z",
    )
    assert decision["status"] == "failed"
    assert any(code.lower() in item["policy_id"] for item in decision["findings"])
    assert "hidden" not in json.dumps(decision)


def test_exception_requires_exact_binding_and_cannot_waive_non_exemptible() -> None:
    decision = evaluate_production_plan(
        {
            "resource_changes": [
                {
                    "address": "aws_iam_role.admin",
                    "change": {"actions": ["update"], "after": {}},
                }
            ]
        },
        target=production_target(),
        source_commit="a" * 40,
        plan_sha256="b" * 64,
        now="2026-07-29T12:00:00Z",
    )
    exception = {
        "policy_id": "production-readiness",
        "policy_version": "1.0.0",
        "address": "aws_iam_role.admin",
        "environment": "production",
        "source_commit": "a" * 40,
        "plan_sha256": "b" * 64,
        "owner": "owner",
        "justification": "bounded",
        "approver": "security",
        "compensating_control": "control",
        "expires_at": "2026-07-30T12:00:00Z",
        "review_at": "2026-07-30T11:00:00Z",
        "signature": "signed:example",
    }
    with pytest.raises(TargetViolation, match="POLICY_EXCEPTION_NON_EXEMPTIBLE"):
        validate_exception(exception, decision, now="2026-07-29T12:00:00Z")


def test_production_policy_fixture_matrix_is_enforced() -> None:
    cases = json.loads(
        (ROOT.parent / "contracts/v1/fixtures/production-policy/cases.json").read_text()
    )["cases"]
    for case in cases:
        decision = evaluate_production_plan(
            case["plan"],
            target=production_target(),
            source_commit="a" * 40,
            plan_sha256="b" * 64,
            now="2026-07-29T12:00:00Z",
        )
        if case["expected"] == "blocking":
            assert decision["status"] == "failed"
            assert any(
                case["finding"].lower() in item["policy_id"]
                for item in decision["findings"]
            )
        else:
            assert decision["status"] == "passed"


def test_malformed_policy_change_fails_closed() -> None:
    with pytest.raises(TargetViolation, match="POLICY_PLAN_CHANGE"):
        evaluate_production_plan(
            {"resource_changes": [{"address": "aws_iam_policy.job", "change": {}}]},
            target=production_target(),
            source_commit="a" * 40,
            plan_sha256="b" * 64,
            now="2026-07-29T12:00:00Z",
        )


def test_exception_signature_is_verified_and_replay_is_rejected() -> None:
    decision = evaluate_production_plan(
        {
            "resource_changes": [
                {
                    "address": "aws_ecr_image.job",
                    "change": {
                        "actions": ["update"],
                        "after": {"image": "repo:latest"},
                    },
                }
            ]
        },
        target=production_target(),
        source_commit="a" * 40,
        plan_sha256="b" * 64,
        now="2026-07-29T12:00:00Z",
    )
    exception = {
        "policy_id": "production-readiness",
        "policy_version": "1.0.0",
        "address": "aws_ecr_image.job",
        "environment": "production",
        "source_commit": "a" * 40,
        "plan_sha256": "b" * 64,
        "owner": "owner",
        "justification": "bounded",
        "approver": "security",
        "compensating_control": "control",
        "expires_at": "2026-07-30T12:00:00Z",
        "review_at": "2026-07-29T13:00:00Z",
        "signature": "",
    }
    key = b"fixture-signing-key"
    payload = json.dumps(
        {k: exception[k] for k in sorted(exception) if k != "signature"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    exception["signature"] = (
        "hmac-sha256:" + hmac.new(key, payload, hashlib.sha256).hexdigest()
    )
    consumed: set[str] = set()
    validate_exception(
        exception,
        decision,
        now="2026-07-29T12:00:00Z",
        consumed_exception_ids=consumed,
        signing_key=key,
    )
    with pytest.raises(TargetViolation, match="POLICY_EXCEPTION_REUSE"):
        validate_exception(
            exception,
            decision,
            now="2026-07-29T12:00:00Z",
            consumed_exception_ids=consumed,
            signing_key=key,
        )


def apply_expected() -> dict:
    return {
        "source_commit": "a" * 40,
        "workflow_sha": "b" * 40,
        "workflow_run_id": "123",
        "manifest_sha256": "c" * 64,
        "account_id": "123456789012",
        "region": "us-east-1",
        "environment": "production",
        "root": "envs/prod",
        "state_key": "production/us-east-1/envs/prod/state",
        "cell_contract_sha256": "d" * 64,
        "policy_version": "e" * 64,
        "plan_sha256": "f" * 64,
        "readiness_sha256": "1" * 64,
        "phase": "phase-two",
        "generation": "generation-1",
        "target_manifest_sha256": "c" * 64,
        "job_id": "demo-job",
        "config_sha256": "2" * 64,
        "schedule_generation": "generation-1",
        "deployment_identity_sha256": "3" * 64,
        "approval_id": "approval-1",
        "apply_role_arn": "arn:aws:iam::123456789012:role/apply",
        "lock_id": "lock-1",
        "caller_role_id": "AROATEST",
    }


def readiness_fixture() -> dict:
    e = apply_expected()
    return {
        "schema_version": "1.0.0",
        "status": "passed",
        "environment": "test",
        "evidence_source": "disposable-fixture",
        "source_commit": e["source_commit"],
        "plan_sha256": e["plan_sha256"],
        "target_manifest_sha256": e["target_manifest_sha256"],
        "job_id": e["job_id"],
        "config_sha256": e["config_sha256"],
        "schedule_generation": e["schedule_generation"],
        "deployment_identity_sha256": e["deployment_identity_sha256"],
        "lifecycle_state": "MATERIALIZED",
        "occurrence_tracking": True,
        "evaluated_at": "2026-07-29T12:00:00Z",
        "expires_at": "2026-07-29T13:00:00Z",
        "evidence_sha256": "2ce49d07f9d55f7645862b233d0a5e5b8acce769f8539ceaa8778b9e734cbafb",
    }


def test_exact_readiness_and_approval_bindings_are_required() -> None:
    expected = apply_expected()
    readiness = readiness_fixture()
    validate_readiness(
        readiness,
        {**expected, "environment": "test"},
        now=datetime.fromisoformat("2026-07-29T12:30:00+00:00"),
    )
    approval = {
        "schema_version": "1.0.0",
        "approval_id": "approval-1",
        "status": "approved",
        **{
            key: expected[key]
            for key in (
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
            )
        },
        "author": "author-user",
        "approvers": [
            {
                "role": "platform",
                "actor": "platform-user",
                "approved_at": "2026-07-29T12:01:00Z",
            },
            {
                "role": "job-owner",
                "actor": "owner-user",
                "approved_at": "2026-07-29T12:02:00Z",
            },
        ],
        "approved_at": "2026-07-29T12:02:00Z",
        "expires_at": "2026-07-29T13:00:00Z",
        "security_required": False,
    }
    validate_approval(
        approval, expected, now=datetime.fromisoformat("2026-07-29T12:30:00+00:00")
    )
    bad = copy.deepcopy(approval)
    bad["plan_sha256"] = "9" * 64
    with pytest.raises(TargetViolation, match="APPROVAL_BINDING"):
        validate_approval(bad, expected)


def test_apply_authorization_binds_binary_plan_and_caller() -> None:
    expected = apply_expected()
    binary = b"approved-plan"
    authorization = {
        "schema_version": "1.0.0",
        "status": "authorized",
        "apply_role_arn": "arn:aws:iam::123456789012:role/apply",
        "caller_account_id": "123456789012",
        "caller_role_arn": "arn:aws:iam::123456789012:role/apply",
        "caller_role_id": "AROATEST",
        **{
            key: expected[key]
            for key in (
                "source_commit",
                "workflow_sha",
                "workflow_run_id",
                "manifest_sha256",
                "state_key",
                "readiness_sha256",
                "approval_id",
            )
        },
        "target_environment": "production",
        "target_root": expected["root"],
        "plan_sha256": hashlib.sha256(binary).hexdigest(),
        "policy_status": "passed",
        "artifact_audience": "trusted-reviewer",
        "artifact_expires_at": "2026-07-29T13:00:00Z",
        "lock_id": "lock-1",
        "authorized_at": "2026-07-29T12:05:00Z",
    }
    authorization_expected = {
        **expected,
        "target_environment": "production",
        "plan_sha256": hashlib.sha256(binary).hexdigest(),
    }
    validate_apply_authorization(
        authorization,
        authorization_expected,
        binary_plan=binary,
        now=datetime.fromisoformat("2026-07-29T12:30:00+00:00"),
    )
    with pytest.raises(TargetViolation, match="APPLY_PLAN_CHECKSUM"):
        validate_apply_authorization(authorization, expected, binary_plan=b"changed")


def test_failure_evidence_is_bounded_and_rejects_bad_plan_identity() -> None:
    evidence = bounded_failure_evidence(
        {
            "schema_version": "1.0.0",
            "status": "failed",
            "run_id": "123",
            "plan_sha256": "a" * 64,
            "state_key": "state",
            "lock_state": "inspect",
            "error_code": "LOCK_CONFLICT",
            "recovery_guidance": "fresh plan",
            "recorded_at": "2026-07-29T12:00:00Z",
        }
    )
    assert "error_output" not in evidence
    with pytest.raises(TargetViolation, match="FAILURE_PLAN_BINDING"):
        bounded_failure_evidence(
            {
                "schema_version": "1.0.0",
                "status": "failed",
                "run_id": "123",
                "plan_sha256": "bad",
                "state_key": "state",
                "lock_state": "inspect",
                "error_code": "LOCK_CONFLICT",
                "recovery_guidance": "fresh plan",
                "recorded_at": "2026-07-29T12:00:00Z",
            }
        )


def test_emergency_access_requires_distinct_current_target_bound_approval() -> None:
    emergency = {
        "schema_version": "1.0.0",
        "status": "approved",
        "actor": "operator",
        "approver": "security",
        "target_manifest_sha256": "a" * 64,
        "operation": "rollback",
        "expires_at": "2026-07-29T13:00:00Z",
        "alert_id": "alert-1",
        "incident_id": "incident-1",
        "review_due_at": "2026-07-29T14:00:00Z",
    }
    validate_emergency_access(
        emergency,
        "a" * 64,
        now=datetime.fromisoformat("2026-07-29T12:00:00+00:00"),
    )
    bad = dict(emergency, approver="operator")
    with pytest.raises(TargetViolation, match="EMERGENCY_SELF_APPROVAL"):
        validate_emergency_access(bad, "a" * 64)


def test_production_apply_workflow_requires_bundle_and_publishes_failure_evidence() -> (
    None
):
    workflow = (
        ROOT.parent / ".github" / "workflows" / "production-apply.yml"
    ).read_text(encoding="utf-8")
    assert "production-approved-bundle-${{ inputs.source_commit }}" in workflow
    assert "bundle_run_id" in workflow
    for filename in (
        "approval.json",
        "readiness.json",
        "apply-authorization.json",
        "caller.json",
        "lock.json",
    ):
        assert filename in workflow
    assert "actions/upload-artifact" in workflow
    assert "TARGET_MANIFEST" in workflow
    assert "get-caller-identity" in workflow


def test_bundle_assembly_fails_closed_when_evidence_is_incomplete(
    tmp_path: Path,
) -> None:
    with pytest.raises(TargetViolation, match="BUNDLE_MISSING"):
        assemble_bundle(
            tmp_path / "source",
            tmp_path / "destination",
            {"plan_sha256": "a" * 64},
        )


def test_bundle_manifest_detects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    for name in FILES:
        (root / name).write_bytes(name.encode())
    manifest = {
        "schema_version": "1.0.0",
        "audience": "production-apply",
        "plan_sha256": hashlib.sha256(
            (root / "approved.tfplan").read_bytes()
        ).hexdigest(),
        "files": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in FILES
        },
    }
    verify_bundle_manifest(root, manifest)
    (root / "approved.tfplan").write_bytes(b"tampered")
    with pytest.raises(TargetViolation, match="BUNDLE_MANIFEST_DIGEST"):
        verify_bundle_manifest(root, manifest)
