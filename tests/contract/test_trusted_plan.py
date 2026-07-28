from __future__ import annotations

import copy
import hashlib
import json
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
