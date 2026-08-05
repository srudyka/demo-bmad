from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.deployment_targets import (
    TargetViolation,
    oidc_subject,
    preflight_target,
    validate_iam_binding,
    validate_oidc_claims,
    validate_target_manifest,
    validate_rotation,
)


ROOT = Path(__file__).resolve().parents[1]


def target() -> dict:
    return json.loads(
        (ROOT / "contract" / "fixtures" / "target-manifest.json").read_text()
    )


def test_manifest_and_exact_oidc_binding() -> None:
    manifest = target()
    validate_target_manifest(manifest)
    assert (
        oidc_subject({**manifest, "workflow_ref": manifest["plan_workflow_ref"]})
        == manifest["plan_oidc_subject"]
    )
    validate_oidc_claims(
        {
            "aud": "sts.amazonaws.com",
            "sub": manifest["plan_oidc_subject"],
            "repository_owner_id": "42424242",
            "repository_id": "42424243",
        },
        manifest,
    )


@pytest.mark.parametrize(
    "field",
    [
        "account_id",
        "region",
        "root",
        "state_key",
        "apply_role_arn",
        "workflow_ref",
        "cell_contract_sha256",
    ],
)
def test_manifest_rejects_substitution(field: str) -> None:
    manifest = target()
    manifest[field] = "*" if field in {"root", "state_key"} else "wrong"
    with pytest.raises(TargetViolation):
        validate_target_manifest(manifest)


def test_oidc_rejects_branch_pr_and_wrong_audience() -> None:
    manifest = target()
    for claims in (
        {"aud": "wrong", "sub": manifest["plan_oidc_subject"]},
        {
            "aud": "sts.amazonaws.com",
            "sub": "repo:x:ref:refs/heads/main",
            "event_name": "pull_request",
        },
    ):
        with pytest.raises(TargetViolation):
            validate_oidc_claims(claims, manifest)


def test_preflight_fails_before_init_on_any_binding_mismatch() -> None:
    manifest = target()
    caller = {
        "account_id": "123456789012",
        "region": "us-east-1",
        "repository_owner_id": "42424242",
        "repository_id": "42424243",
        "environment": "production",
        "workflow_sha": "0123456789abcdef0123456789abcdef01234567",
        "manifest_sha256": "manifest",
        "root": "envs/production",
        "role_type": "plan",
        "role_arn": manifest["plan_role_arn"],
        "state_key": manifest["state_key"],
        "policy_version": manifest["policy_version"],
        "cell_contract_sha256": manifest["cell_contract_sha256"],
    }
    preflight_target(
        caller, manifest, expected_manifest_sha256="manifest", authority=caller
    )
    bad = copy.deepcopy(caller)
    bad["region"] = "eu-west-1"
    with pytest.raises(TargetViolation, match="TARGET_AUTHORITY_MISMATCH"):
        preflight_target(
            bad, manifest, expected_manifest_sha256="manifest", authority=caller
        )


def test_preflight_rejects_tampered_manifest_checksum_and_role_type() -> None:
    manifest = target()
    caller = {"manifest_sha256": "tampered", "role_type": "plan"}
    with pytest.raises(TargetViolation, match="TARGET_PREFLIGHT_MISMATCH"):
        preflight_target(
            caller, manifest, expected_manifest_sha256="reviewed", authority=caller
        )
    with pytest.raises(TargetViolation, match="TARGET_ROLE_TYPE"):
        preflight_target(
            {"manifest_sha256": "reviewed", "role_type": "admin"},
            manifest,
            expected_manifest_sha256="reviewed",
            authority=caller,
        )


def test_iam_binding_rejects_forbidden_actions_and_cross_target_state() -> None:
    manifest = target()
    valid = {
        "role_arn": manifest["plan_role_arn"],
        "permissions_boundary_arn": manifest["permissions_boundary_arn"],
        "actions": [],
        "state_prefix": manifest["state_key"],
    }
    validate_iam_binding("plan", valid, manifest)
    for bad in (
        {**valid, "actions": ["iam:CreateAccessKey"]},
        {**valid, "state_prefix": "other/root"},
    ):
        with pytest.raises(TargetViolation):
            validate_iam_binding("plan", bad, manifest)


def test_rotation_requires_bounded_verified_overlap() -> None:
    old = target()
    new = copy.deepcopy(old)
    new["plan_workflow_ref"] = new["plan_workflow_ref"].replace(
        "0123456789abcdef0123456789abcdef01234567",
        "1123456789abcdef0123456789abcdef01234567",
    )
    new["apply_workflow_ref"] = new["apply_workflow_ref"].replace(
        "0123456789abcdef0123456789abcdef01234567",
        "1123456789abcdef0123456789abcdef01234567",
    )
    new["plan_oidc_subject"] = oidc_subject(
        {**new, "workflow_ref": new["plan_workflow_ref"]}
    )
    new["apply_oidc_subject"] = oidc_subject(
        {**new, "workflow_ref": new["apply_workflow_ref"]}
    )
    validate_rotation(old, new, overlap_seconds=3600, new_verified=True)
    with pytest.raises(TargetViolation, match="ROTATION_OVERLAP_UNBOUNDED"):
        validate_rotation(old, new, overlap_seconds=86401, new_verified=True)
    with pytest.raises(TargetViolation, match="ROTATION_NEW_IDENTITY_UNVERIFIED"):
        validate_rotation(old, new, overlap_seconds=3600, new_verified=False)
