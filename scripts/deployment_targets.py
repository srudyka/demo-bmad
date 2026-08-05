"""Pure validation for immutable trusted deployment targets.

This module is intentionally AWS/network free: callers must validate the target
before Terraform initialization or any protected state access.
"""

from __future__ import annotations

import re
import argparse
import json
import hashlib
from pathlib import Path
from typing import Any, Mapping

import boto3  # type: ignore[import-untyped]


class TargetViolation(ValueError):
    pass


def validate_rotation(
    old_manifest: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
    *,
    overlap_seconds: int,
    new_verified: bool,
) -> None:
    """Require a bounded, verified identity transition before old trust removal."""
    validate_target_manifest(old_manifest)
    validate_target_manifest(new_manifest)
    if not 1 <= overlap_seconds <= 86400:
        raise TargetViolation("ROTATION_OVERLAP_UNBOUNDED")
    if not new_verified:
        raise TargetViolation("ROTATION_NEW_IDENTITY_UNVERIFIED")
    immutable = (
        "repository_owner_id",
        "repository_id",
        "account_id",
        "region",
        "environment",
        "root",
        "state_bucket",
        "state_key",
        "lock_key",
        "provider_lock_path",
        "backend_lock_path",
        "provider_lock_path",
        "backend_lock_path",
    )
    if any(old_manifest[field] != new_manifest[field] for field in immutable):
        raise TargetViolation("ROTATION_SCOPE_CHANGED")
    if (
        old_manifest["plan_oidc_subject"] == new_manifest["plan_oidc_subject"]
        and old_manifest["apply_oidc_subject"] == new_manifest["apply_oidc_subject"]
    ):
        raise TargetViolation("ROTATION_NOOP")


SHA = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
ACCOUNT = re.compile(r"^[0-9]{12}$")
REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-[0-9]+$")
REPO_ID = re.compile(r"^[0-9]+$")
ARN = re.compile(r"^arn:[a-z0-9-]+:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$")


def oidc_subject(target: Mapping[str, Any]) -> str:
    return (
        f"repository_owner_id:{target['repository_owner_id']}"
        f":repository_id:{target['repository_id']}"
        f":environment:{target['environment']}"
        f":job_workflow_ref:{target['workflow_ref']}"
    )


def validate_target_manifest(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "repository_owner_id",
        "repository_id",
        "repository_name",
        "root",
        "environment",
        "account_id",
        "region",
        "plan_role_arn",
        "apply_role_arn",
        "permissions_boundary_arn",
        "state_bucket",
        "state_key",
        "lock_key",
        "provider_lock_path",
        "backend_lock_path",
        "cell_contract_path",
        "cell_contract_sha256",
        "policy_catalog",
        "policy_version",
        "plan_workflow_ref",
        "apply_workflow_ref",
        "oidc_audience",
        "plan_oidc_subject",
        "apply_oidc_subject",
        "state_controls",
        "protected_environment_controls",
        "apply_resource_prefixes",
    }
    if set(manifest) != required:
        raise TargetViolation("TARGET_MANIFEST_SHAPE")
    if (
        manifest["schema_version"] != "1.0.0"
        or not REPO_ID.fullmatch(str(manifest["repository_owner_id"]))
        or not REPO_ID.fullmatch(str(manifest["repository_id"]))
    ):
        raise TargetViolation("TARGET_REPOSITORY_ID")
    for field in ("plan_workflow_ref", "apply_workflow_ref"):
        if not SHA.fullmatch(str(manifest[field]).rsplit("@", 1)[-1]):
            raise TargetViolation("TARGET_WORKFLOW_SHA")
    if not HASH.fullmatch(str(manifest["cell_contract_sha256"])) or not HASH.fullmatch(
        str(manifest["policy_version"])
    ):
        raise TargetViolation("TARGET_CHECKSUM")
    if (
        not ACCOUNT.fullmatch(str(manifest["account_id"]))
        or not manifest["environment"]
        or not REGION.fullmatch(str(manifest["region"]))
    ):
        raise TargetViolation("TARGET_SCOPE")
    if not str(manifest["root"]).startswith("envs/") or ".." in str(manifest["root"]):
        raise TargetViolation("TARGET_ROOT")
    for key in ("plan_role_arn", "apply_role_arn", "permissions_boundary_arn"):
        if not ARN.fullmatch(str(manifest[key])):
            raise TargetViolation("TARGET_ROLE_ARN")
    if manifest["oidc_audience"] != "sts.amazonaws.com" or manifest[
        "plan_oidc_subject"
    ] != oidc_subject({**manifest, "workflow_ref": manifest["plan_workflow_ref"]}):
        raise TargetViolation("TARGET_OIDC_BINDING")
    if (
        manifest["apply_oidc_subject"]
        != oidc_subject({**manifest, "workflow_ref": manifest["apply_workflow_ref"]})
        or manifest["plan_oidc_subject"] == manifest["apply_oidc_subject"]
    ):
        raise TargetViolation("TARGET_OIDC_BINDING")
    if not all(
        isinstance(manifest[key], str) and manifest[key] and "*" not in manifest[key]
        for key in (
            "state_bucket",
            "state_key",
            "lock_key",
            "cell_contract_path",
            "policy_catalog",
        )
    ):
        raise TargetViolation("TARGET_PATH_SCOPE")
    expected_prefix = (
        f"{manifest['environment']}/{manifest['region']}/{manifest['root']}/"
    )
    if not str(manifest["state_key"]).startswith(expected_prefix) or not str(
        manifest["lock_key"]
    ).startswith(expected_prefix):
        raise TargetViolation("TARGET_PATH_ISOLATION")
    if manifest["lock_key"] != f"{manifest['state_key']}.tflock":
        raise TargetViolation("TARGET_LOCK_PATH")
    for field in ("provider_lock_path", "backend_lock_path"):
        if (
            not str(manifest[field]).startswith(str(manifest["root"]) + "/")
            or ".." in str(manifest[field])
            or "*" in str(manifest[field])
        ):
            raise TargetViolation("TARGET_DEPENDENCY_PATH")
    controls = manifest["state_controls"]
    if controls != {
        "encrypted": True,
        "versioned": True,
        "public_blocked": True,
        "native_lockfile": True,
    }:
        raise TargetViolation("TARGET_STATE_CONTROLS")
    if manifest["protected_environment_controls"] != {
        "required_reviewers": True,
        "prevent_self_review": True,
        "restricted_refs": True,
        "concurrency": True,
        "administrator_bypass": False,
    }:
        raise TargetViolation("TARGET_PROTECTED_CONTROLS")
    prefixes = manifest["apply_resource_prefixes"]
    if (
        not isinstance(prefixes, list)
        or not prefixes
        or any(
            not isinstance(prefix, str) or not prefix or "*" in prefix
            for prefix in prefixes
        )
    ):
        raise TargetViolation("TARGET_RESOURCE_NAMESPACE")


def validate_oidc_claims(
    claims: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    validate_target_manifest(manifest)
    if claims.get("aud") != "sts.amazonaws.com" or claims.get("sub") not in {
        manifest["plan_oidc_subject"],
        manifest["apply_oidc_subject"],
    }:
        raise TargetViolation("OIDC_EXACT_TRUST")
    if (
        claims.get("repository_owner_id") != manifest["repository_owner_id"]
        or claims.get("repository_id") != manifest["repository_id"]
    ):
        raise TargetViolation("OIDC_REPOSITORY_ID")

    matching_roles = [
        role
        for role in ("plan", "apply")
        if claims.get("sub") == manifest[f"{role}_oidc_subject"]
    ]
    role_type = claims.get("role_type") or (
        matching_roles[0] if len(matching_roles) == 1 else None
    )
    if (
        role_type not in {"plan", "apply"}
        or claims.get("sub") != manifest[f"{role_type}_oidc_subject"]
    ):
        raise TargetViolation("OIDC_ROLE_BINDING")
    if claims.get("event_name") == "pull_request" or claims.get("ref_type") in {
        "branch",
        "tag",
    }:
        raise TargetViolation("OIDC_UNPROTECTED_CONTEXT")


def preflight_target(
    caller: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    expected_manifest_sha256: str,
    authority: Mapping[str, Any] | None = None,
) -> None:
    validate_target_manifest(manifest)
    if authority is None:
        raise TargetViolation("TARGET_AUTHORITY_REQUIRED")
    if any(
        authority.get(field) != caller.get(field)
        for field in (
            "account_id",
            "region",
            "repository_owner_id",
            "repository_id",
            "environment",
            "workflow_sha",
            "role_arn",
            "state_key",
            "policy_version",
            "cell_contract_sha256",
        )
    ):
        raise TargetViolation("TARGET_AUTHORITY_MISMATCH")
    if caller.get("role_type") not in {"plan", "apply"}:
        raise TargetViolation("TARGET_ROLE_TYPE")
    for field in (
        "account_id",
        "region",
        "repository_owner_id",
        "repository_id",
        "environment",
        "workflow_sha",
        "manifest_sha256",
        "root",
        "role_arn",
        "state_key",
        "policy_version",
        "cell_contract_sha256",
    ):
        expected: Any
        if field == "workflow_sha":
            workflow_field = (
                "plan_workflow_ref"
                if caller.get("role_type") == "plan"
                else "apply_workflow_ref"
            )
            expected = str(manifest[workflow_field]).rsplit("@", 1)[-1]
        elif field == "manifest_sha256":
            expected = expected_manifest_sha256
        elif field == "role_arn":
            role_type = caller.get("role_type")
            if role_type not in {"plan", "apply"}:
                raise TargetViolation("TARGET_ROLE_TYPE")
            expected = manifest[f"{role_type}_role_arn"]
        elif field == "state_key":
            expected = manifest["state_key"]
        elif field == "policy_version":
            expected = manifest["policy_version"]
        elif field == "cell_contract_sha256":
            expected = manifest["cell_contract_sha256"]
        else:
            expected = manifest[field]
        if caller.get(field) != expected:
            raise TargetViolation("TARGET_PREFLIGHT_MISMATCH")
        if authority.get(field) != expected:
            raise TargetViolation("TARGET_AUTHORITY_MISMATCH")


def validate_iam_binding(
    role_type: str, policy: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    """Validate the non-negotiable effective-policy boundary without AWS access."""
    validate_target_manifest(manifest)
    if role_type not in {"plan", "apply"}:
        raise TargetViolation("TARGET_ROLE_TYPE")
    if policy.get("role_arn") != manifest[f"{role_type}_role_arn"]:
        raise TargetViolation("IAM_ROLE_BINDING")
    if policy.get("permissions_boundary_arn") != manifest["permissions_boundary_arn"]:
        raise TargetViolation("IAM_BOUNDARY_BINDING")
    forbidden = {
        "iam:CreateUser",
        "iam:CreateAccessKey",
        "iam:PutRolePolicy",
        "iam:UpdateAssumeRolePolicy",
        "iam:PassRole",
        "sts:AssumeRole",
    }
    if forbidden.intersection(policy.get("actions", [])):
        raise TargetViolation("IAM_FORBIDDEN_ACTION")
    if policy.get("state_prefix") != manifest["state_key"]:
        raise TargetViolation("IAM_STATE_SCOPE")
    resources = policy.get("resource_arns", [])
    if role_type == "apply" and any(
        not isinstance(resource, str)
        or not any(
            resource.startswith(prefix)
            for prefix in manifest["apply_resource_prefixes"]
        )
        for resource in resources
    ):
        raise TargetViolation("IAM_RESOURCE_NAMESPACE")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a trusted deployment target before Terraform init"
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--caller", required=True, type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--authority", required=True, type=Path)
    parser.add_argument("--github-claims", required=True, type=Path)
    parser.add_argument("--cell-contract", required=True, type=Path)
    args = parser.parse_args()
    try:
        expected_digest = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        if expected_digest != args.expected_manifest_sha256:
            raise TargetViolation("TARGET_MANIFEST_DIGEST")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        caller = json.loads(args.caller.read_text(encoding="utf-8"))
        authority = json.loads(args.authority.read_text(encoding="utf-8"))
        claims = json.loads(args.github_claims.read_text(encoding="utf-8"))
        validate_oidc_claims(claims, manifest)
        cell_contract = json.loads(args.cell_contract.read_text(encoding="utf-8"))
        if (
            cell_contract.get("cell_contract_sha256")
            != manifest["cell_contract_sha256"]
        ):
            raise TargetViolation("TARGET_CELL_CONTRACT")
        try:
            sts_account = boto3.client("sts").get_caller_identity()["Account"]
        except Exception as error:  # noqa: BLE001 - bounded preflight failure
            raise TargetViolation("TARGET_AWS_IDENTITY_UNAVAILABLE") from error
        if sts_account != manifest["account_id"]:
            raise TargetViolation("TARGET_AWS_ACCOUNT")
        preflight_target(
            caller,
            manifest,
            expected_manifest_sha256=args.expected_manifest_sha256,
            authority=authority,
        )
        expected_subject = manifest[f"{caller['role_type']}_oidc_subject"]
        if claims.get("sub") != expected_subject:
            raise TargetViolation("TARGET_OIDC_ROLE_MISMATCH")
    except (OSError, json.JSONDecodeError, TargetViolation) as error:
        print(f"TARGET_PREFLIGHT_FAILED:{error}")
        return 1
    print("TARGET_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
