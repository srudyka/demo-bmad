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
                "change": {"actions": ["create"], "after": {"retention_in_days": 30, "tags": {"Environment": "production", "Application": "demo", "Service": "job", "Owner": "platform", "ManagedBy": "Terraform"}, "logs": "enabled", "alarms": "alarm", "notifications": "sns", "acknowledgement": True, "cell_contract": "cell-contract-v1"}},
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
            assert any(case["finding"].lower() in item["policy_id"] for item in decision["findings"])
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
        {"resource_changes": [{"address": "aws_ecr_image.job", "change": {"actions": ["update"], "after": {"image": "repo:latest"}}}]},
        target=production_target(), source_commit="a" * 40, plan_sha256="b" * 64,
        now="2026-07-29T12:00:00Z",
    )
    exception = {
        "policy_id": "production-readiness", "policy_version": "1.0.0",
        "address": "aws_ecr_image.job", "environment": "production",
        "source_commit": "a" * 40, "plan_sha256": "b" * 64,
        "owner": "owner", "justification": "bounded", "approver": "security",
        "compensating_control": "control", "expires_at": "2026-07-30T12:00:00Z",
        "review_at": "2026-07-29T13:00:00Z", "signature": "",
    }
    key = b"fixture-signing-key"
    payload = json.dumps({k: exception[k] for k in sorted(exception) if k != "signature"}, sort_keys=True, separators=(",", ":")).encode()
    exception["signature"] = "hmac-sha256:" + hmac.new(key, payload, hashlib.sha256).hexdigest()
    consumed: set[str] = set()
    validate_exception(exception, decision, now="2026-07-29T12:00:00Z", consumed_exception_ids=consumed, signing_key=key)
    with pytest.raises(TargetViolation, match="POLICY_EXCEPTION_REUSE"):
        validate_exception(exception, decision, now="2026-07-29T12:00:00Z", consumed_exception_ids=consumed, signing_key=key)
