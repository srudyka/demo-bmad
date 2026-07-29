"""Contract and reporting helpers for a trusted, reviewable Terraform plan."""

from __future__ import annotations

import hashlib
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from scripts.deployment_targets import (
    TargetViolation,
    preflight_target,
    validate_iam_binding,
)
from scripts.production_policy import apply_exceptions, evaluate_production_plan
from scripts.check_repository import repository_files, scan_baseline_diff, scan_paths

SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_PLAN_ACTIONS = {"iam:PassRole", "sts:AssumeRole", "terraform:Apply"}


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise TargetViolation(f"PLAN_{name.upper()}_REQUIRED")
    return value


def validate_plan_request(
    request: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    source_commit: str,
    validation_evidence: Mapping[str, Any],
    caller: Mapping[str, Any],
    authority: Mapping[str, Any],
    manifest_bytes: bytes,
) -> None:
    """Fail closed before init/state access when any reviewed binding changes."""
    required = {
        "repository_owner_id",
        "repository_id",
        "source_commit",
        "workflow_sha",
        "workflow_run_id",
        "environment",
        "account_id",
        "region",
        "root",
        "manifest_sha256",
        "plan_role_arn",
        "state_key",
        "cell_contract_sha256",
        "policy_version",
        "provider_lock_sha256",
        "backend_lock_sha256",
        "role_session",
    }
    if set(request) != required or any(key not in request for key in required):
        raise TargetViolation("PLAN_REQUEST_SHAPE")
    if (
        not SHA1.fullmatch(str(request["source_commit"]))
        or request["source_commit"] != source_commit
    ):
        raise TargetViolation("PLAN_SOURCE_COMMIT")
    if not SHA1.fullmatch(str(request["workflow_sha"])):
        raise TargetViolation("PLAN_WORKFLOW_SHA")
    for field in (
        "manifest_sha256",
        "cell_contract_sha256",
        "policy_version",
        "provider_lock_sha256",
        "backend_lock_sha256",
    ):
        if not SHA256.fullmatch(str(request[field])):
            raise TargetViolation("PLAN_CHECKSUM")
    if (
        request["plan_role_arn"] != manifest["plan_role_arn"]
        or request["state_key"] != manifest["state_key"]
    ):
        raise TargetViolation("PLAN_TARGET_BINDING")
    if request["manifest_sha256"] != hashlib.sha256(manifest_bytes).hexdigest():
        raise TargetViolation("PLAN_MANIFEST_DIGEST")
    if request["workflow_sha"] != str(manifest["plan_workflow_ref"]).rsplit("@", 1)[-1]:
        raise TargetViolation("PLAN_WORKFLOW_BINDING")
    if (
        request["repository_owner_id"] != manifest["repository_owner_id"]
        or request["repository_id"] != manifest["repository_id"]
    ):
        raise TargetViolation("PLAN_REPOSITORY_BINDING")
    if (
        request["environment"] != manifest["environment"]
        or request["account_id"] != manifest["account_id"]
        or request["region"] != manifest["region"]
        or request["root"] != manifest["root"]
    ):
        raise TargetViolation("PLAN_SCOPE_BINDING")
    if (
        request["cell_contract_sha256"] != manifest["cell_contract_sha256"]
        or request["policy_version"] != manifest["policy_version"]
    ):
        raise TargetViolation("PLAN_AUTHORITY_BINDING")
    if (
        validation_evidence.get("status") != "passed"
        or validation_evidence.get("credential_free") is not True
        or validation_evidence.get("source_commit") != source_commit
    ):
        raise TargetViolation("PLAN_VALIDATION_EVIDENCE")
    if not request["workflow_run_id"].isdigit() or int(request["workflow_run_id"]) <= 0:
        raise TargetViolation("PLAN_WORKFLOW_RUN")
    preflight_target(
        caller,
        manifest,
        expected_manifest_sha256=request["manifest_sha256"],
        authority=authority,
    )
    validate_iam_binding(
        "plan",
        {
            "role_arn": request["plan_role_arn"],
            "permissions_boundary_arn": manifest["permissions_boundary_arn"],
            "actions": [],
            "state_prefix": request["state_key"],
        },
        manifest,
    )


def manifest_digest(manifest_bytes: bytes) -> str:
    """Use the repository artifact-integrity rule: raw UTF-8 bytes, not semantic JSON."""
    return hashlib.sha256(manifest_bytes).hexdigest()


def validate_lock_integrity(
    provider_lock: Path,
    backend_lock: Path,
    *,
    provider_sha256: str,
    backend_sha256: str,
) -> None:
    for path, expected, code in (
        (provider_lock, provider_sha256, "PLAN_PROVIDER_LOCK"),
        (backend_lock, backend_sha256, "PLAN_BACKEND_LOCK"),
    ):
        if not path.is_file() or not SHA256.fullmatch(expected):
            raise TargetViolation(f"{code}_MISSING")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise TargetViolation(f"{code}_MISMATCH")


def summarize_plan(
    plan: Mapping[str, Any], *, policy_status: str = "passed"
) -> dict[str, Any]:
    """Return only bounded, review-safe plan information; never copy raw values."""
    if policy_status not in {"passed", "failed", "not_run"}:
        raise TargetViolation("PLAN_POLICY_STATUS")
    changes = plan.get("resource_changes", [])
    if not isinstance(changes, list):
        raise TargetViolation("PLAN_RESOURCE_CHANGES")
    counts = {"create": 0, "update": 0, "delete": 0, "replace": 0, "no_op": 0}
    addresses: list[str] = []
    categories = {"iam": 0, "network": 0, "observability": 0, "other": 0}
    lifecycle_handshake = {"create_before_destroy": 0, "prevent_destroy": 0}
    for item in changes:
        if not isinstance(item, Mapping) or not isinstance(item.get("address"), str):
            raise TargetViolation("PLAN_RESOURCE_CHANGE")
        actions = (
            item.get("change", {}).get("actions", [])
            if isinstance(item.get("change"), Mapping)
            else []
        )
        if actions == ["create"]:
            key = "create"
        elif actions == ["update"]:
            key = "update"
        elif actions == ["delete"]:
            key = "delete"
        elif actions == ["delete", "create"] or actions == ["create", "delete"]:
            key = "replace"
        elif actions == []:
            key = "no_op"
        else:
            raise TargetViolation("PLAN_ACTIONS_INVALID")
        counts[key] += 1
        if len(addresses) < 200:
            addresses.append(item["address"])
        address = item["address"].lower()
        category = (
            "iam"
            if "iam" in address or "role" in address or "policy" in address
            else "network"
            if any(
                value in address
                for value in ("vpc", "subnet", "security_group", "route")
            )
            else "observability"
            if any(
                value in address for value in ("cloudwatch", "alarm", "log", "metric")
            )
            else "other"
        )
        categories[category] += 1
        lifecycle = (
            item.get("change", {}).get("after", {})
            if isinstance(item.get("change"), Mapping)
            else {}
        )
        if isinstance(lifecycle, Mapping):
            if lifecycle.get("create_before_destroy") is True:
                lifecycle_handshake["create_before_destroy"] += 1
            if lifecycle.get("prevent_destroy") is True:
                lifecycle_handshake["prevent_destroy"] += 1
    return {
        "counts": counts,
        "addresses": addresses,
        "categories": categories,
        "no_op": sum(counts.values()) == counts["no_op"],
        "policy_status": policy_status,
        "lifecycle_handshake": lifecycle_handshake,
        "cost_notes": [
            "review-required"
            if counts["create"]
            or counts["update"]
            or counts["delete"]
            or counts["replace"]
            else "no-change"
        ],
    }


def validate_plan_policy(plan: Mapping[str, Any]) -> None:
    """Fail closed on actions that can turn a plan into apply authority."""
    changes = plan.get("resource_changes", [])
    if not isinstance(changes, list):
        raise TargetViolation("PLAN_POLICY_INPUT")
    for item in changes:
        if not isinstance(item, Mapping):
            raise TargetViolation("PLAN_POLICY_INPUT")
        change = item.get("change")
        actions = change.get("actions", []) if isinstance(change, Mapping) else []
        if not isinstance(actions, list) or any(
            action not in {"create", "update", "delete"} for action in actions
        ):
            raise TargetViolation("PLAN_POLICY_ACTION")
        address = str(item.get("address", ""))
        if any(
            token in address.lower() for token in ("apply", "assume_role", "passrole")
        ):
            raise TargetViolation("PLAN_POLICY_AUTHORITY")


def verify_plan_json_matches_binary(plan_path: Path, plan_json: Mapping[str, Any]) -> None:
    """Re-render the binary so a substituted sanitized JSON cannot authorize it."""
    try:
        rendered = subprocess.run(
            ("terraform", "show", "-json", str(plan_path)),
            check=True,
            capture_output=True,
            text=True,
        )
        actual = json.loads(rendered.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise TargetViolation("PLAN_JSON_BINARY_RENDER") from error
    expected_bytes = json.dumps(plan_json, sort_keys=True, separators=(",", ":")).encode()
    actual_bytes = json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()
    if expected_bytes != actual_bytes:
        raise TargetViolation("PLAN_JSON_BINARY_MISMATCH")


def build_metadata(
    request: Mapping[str, Any],
    *,
    plan_sha256: str,
    started_at: str,
    completed_at: str,
    terraform_version: str,
) -> dict[str, Any]:
    if not SHA256.fullmatch(plan_sha256):
        raise TargetViolation("PLAN_BINARY_CHECKSUM")
    parsed_times = []
    for value in (started_at, completed_at):
        try:
            parsed_times.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError as error:
            raise TargetViolation("PLAN_TIMESTAMP") from error
    if parsed_times[1] < parsed_times[0]:
        raise TargetViolation("PLAN_TIMESTAMP_ORDER")
    return {
        "schema_version": "1.0.0",
        "source_commit": request["source_commit"],
        "repository_owner_id": request["repository_owner_id"],
        "repository_id": request["repository_id"],
        "workflow_sha": request["workflow_sha"],
        "workflow_run_id": request["workflow_run_id"],
        "manifest_sha256": request["manifest_sha256"],
        "account_id": request["account_id"],
        "region": request["region"],
        "environment": request["environment"],
        "root": request["root"],
        "state_key": request["state_key"],
        "plan_role_arn": request["plan_role_arn"],
        "role_session": request.get("role_session", ""),
        "cell_contract_sha256": request["cell_contract_sha256"],
        "policy_version": request["policy_version"],
        "provider_lock_sha256": request["provider_lock_sha256"],
        "backend_lock_sha256": request["backend_lock_sha256"],
        "plan_sha256": plan_sha256,
        "terraform_version": terraform_version,
        "started_at": started_at,
        "completed_at": completed_at,
        "expires_at": (parsed_times[1] + timedelta(hours=1))
        .isoformat()
        .replace("+00:00", "Z"),
    }


def validate_artifact_reference(reference: Mapping[str, Any]) -> None:
    if set(reference) != {
        "uri",
        "sha256",
        "expires_at",
        "audience",
    } or not SHA256.fullmatch(str(reference["sha256"])):
        raise TargetViolation("PLAN_ARTIFACT_REFERENCE")
    if reference["audience"] != "trusted-reviewer" or not str(
        reference["uri"]
    ).startswith("github-actions://trusted-plan/"):
        raise TargetViolation("PLAN_ARTIFACT_AUDIENCE")
    try:
        expiry = datetime.fromisoformat(
            str(reference["expires_at"]).replace("Z", "+00:00")
        )
    except ValueError as error:
        raise TargetViolation("PLAN_ARTIFACT_EXPIRY") from error
    remaining = expiry - datetime.now(timezone.utc)
    if remaining.total_seconds() <= 0 or remaining.total_seconds() > 86400:
        raise TargetViolation("PLAN_ARTIFACT_EXPIRED")


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Trusted Terraform plan boundary")
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument(
        "--manifest", default=os.environ.get("TARGET_MANIFEST"), required=False
    )
    preflight.add_argument(
        "--source-commit", default=os.environ.get("SOURCE_COMMIT"), required=False
    )
    preflight.add_argument(
        "--manifest-sha256", default=os.environ.get("MANIFEST_SHA256"), required=False
    )
    preflight.add_argument(
        "--plan-role-arn", default=os.environ.get("PLAN_ROLE_ARN"), required=False
    )
    for name in (
        "target-root",
        "region",
        "account-id",
        "repository-owner-id",
        "repository-id",
        "workflow-sha",
        "cell-contract-sha256",
        "policy-version",
        "workflow-run-id",
        "provider-lock-sha256",
        "backend-lock-sha256",
    ):
        preflight.add_argument(
            f"--{name}", default=os.environ.get(name.upper().replace("-", "_"))
        )
    report = sub.add_parser("report")
    report.add_argument("--plan", required=True)
    report.add_argument("--plan-json")
    report.add_argument("--policy", required=True)
    report.add_argument("--output")
    policy = sub.add_parser("policy")
    policy.add_argument("--plan", required=True)
    policy.add_argument("--plan-json", required=True)
    policy.add_argument("--output")
    policy.add_argument("--exceptions")
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            if not all(
                (
                    args.manifest,
                    args.source_commit,
                    args.manifest_sha256,
                    args.plan_role_arn,
                )
            ):
                raise TargetViolation("PLAN_PREFLIGHT_INPUT")
            manifest_path = Path(args.manifest)
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes)
            from scripts.deployment_targets import validate_target_manifest

            validate_target_manifest(manifest)
            if manifest_digest(manifest_bytes) != args.manifest_sha256:
                raise TargetViolation("PLAN_MANIFEST_DIGEST")
            actual_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip()
            if actual_commit != args.source_commit or not SHA1.fullmatch(actual_commit):
                raise TargetViolation("PLAN_SOURCE_COMMIT")
            if not re.fullmatch(
                r"^arn:[a-z0-9-]+:iam::[0-9]{12}:role/.+$", args.plan_role_arn
            ):
                raise TargetViolation("PLAN_ROLE_ARN")
            if any(
                (
                    args.plan_role_arn != manifest["plan_role_arn"],
                    args.target_root != manifest["root"],
                    args.region != manifest["region"],
                    args.account_id != manifest["account_id"],
                    args.repository_owner_id != manifest["repository_owner_id"],
                    args.repository_id != manifest["repository_id"],
                    args.workflow_sha
                    != manifest["plan_workflow_ref"].rsplit("@", 1)[-1],
                    args.cell_contract_sha256 != manifest["cell_contract_sha256"],
                    args.policy_version != manifest["policy_version"],
                    not args.workflow_run_id or int(args.workflow_run_id) <= 0,
                )
            ):
                raise TargetViolation("PLAN_TARGET_BINDING")
            if not all(
                (
                    args.provider_lock_sha256,
                    args.backend_lock_sha256,
                )
            ):
                raise TargetViolation("PLAN_LOCK_INPUT")
            validate_lock_integrity(
                Path(manifest["provider_lock_path"]),
                Path(manifest["backend_lock_path"]),
                provider_sha256=args.provider_lock_sha256,
                backend_sha256=args.backend_lock_sha256,
            )
            import boto3  # type: ignore[import-untyped]

            if (
                boto3.client("sts", region_name=args.region).get_caller_identity()[
                    "Account"
                ]
                != args.account_id
            ):
                raise TargetViolation("PLAN_AWS_ACCOUNT")
            print("TRUSTED_PLAN_PREFLIGHT_OK")
        elif args.command == "policy":
            plan_path = Path(args.plan)
            if not plan_path.is_file():
                raise TargetViolation("PLAN_BINARY_MISSING")
            plan_json = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
            if not isinstance(plan_json, Mapping):
                raise TargetViolation("PLAN_JSON_SHAPE")
            verify_plan_json_matches_binary(plan_path, plan_json)
            manifest_path = Path(
                _required(os.environ.get("TARGET_MANIFEST"), "manifest")
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            decision = evaluate_production_plan(
                plan_json,
                target=manifest,
                source_commit=_required(
                    os.environ.get("SOURCE_COMMIT"), "source_commit"
                ),
                plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                now=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                hygiene_violations=scan_paths(
                    Path(__file__).resolve().parents[1],
                    repository_files(Path(__file__).resolve().parents[1]),
                ) + (scan_baseline_diff(Path(__file__).resolve().parents[1], os.environ["BASELINE_COMMIT"]) if os.environ.get("BASELINE_COMMIT") else []),
            )
            if args.exceptions:
                exceptions_path = Path(args.exceptions)
                exceptions = json.loads(exceptions_path.read_text(encoding="utf-8"))
                if not isinstance(exceptions, list) or any(not isinstance(item, Mapping) for item in exceptions):
                    raise TargetViolation("POLICY_EXCEPTION_SHAPE")
                decision = apply_exceptions(
                    decision,
                    exceptions,
                    now=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    ledger=Path(os.environ["EXCEPTION_LEDGER_PATH"]) if os.environ.get("EXCEPTION_LEDGER_PATH") else None,
                )
            encoded = json.dumps(decision, sort_keys=True, separators=(",", ":"))
            if args.output:
                Path(args.output).write_text(encoded + "\n", encoding="utf-8")
            if decision["status"] != "passed":
                print(f"TRUSTED_PLAN_POLICY_FAILED:{encoded}")
                return 1
            print("TRUSTED_PLAN_POLICY_OK")
        else:
            plan = Path(args.plan)
            if not plan.is_file():
                raise TargetViolation("PLAN_BINARY_MISSING")
            policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
            if policy.get("status") != "passed":
                raise TargetViolation("PLAN_POLICY_FAILED")
            binary_sha256 = hashlib.sha256(plan.read_bytes()).hexdigest()
            if (
                policy.get("policy_id") != "production-readiness"
                or policy.get("policy_version") != "1.0.0"
                or policy.get("plan_sha256") != binary_sha256
                or policy.get("source_commit") != os.environ.get("SOURCE_COMMIT")
                or policy.get("environment") != "production"
            ):
                raise TargetViolation("PLAN_POLICY_BINDING")
            if not args.plan_json:
                raise TargetViolation("PLAN_JSON_REQUIRED")
            summary = (
                summarize_plan(
                    json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
                )
                if args.plan_json
                else summarize_plan({"resource_changes": []})
            )
            manifest_path = Path(
                _required(os.environ.get("TARGET_MANIFEST"), "manifest")
            )
            manifest_bytes = manifest_path.read_bytes()
            manifest = json.loads(manifest_bytes)
            completed_at = datetime.now(timezone.utc)
            started_at = datetime.fromisoformat(
                os.environ.get("PLAN_STARTED_AT", completed_at.isoformat()).replace(
                    "Z", "+00:00"
                )
            )
            metadata_request = {
                "source_commit": _required(
                    os.environ.get("SOURCE_COMMIT"), "source_commit"
                ),
                "repository_owner_id": manifest["repository_owner_id"],
                "repository_id": manifest["repository_id"],
                "workflow_sha": str(manifest["plan_workflow_ref"]).rsplit("@", 1)[-1],
                "workflow_run_id": _required(
                    os.environ.get("WORKFLOW_RUN_ID"), "workflow_run_id"
                ),
                "manifest_sha256": manifest_digest(manifest_bytes),
                "account_id": _required(os.environ.get("ACCOUNT_ID"), "account_id"),
                "region": _required(os.environ.get("AWS_REGION"), "region"),
                "environment": manifest["environment"],
                "root": manifest["root"],
                "state_key": manifest["state_key"],
                "plan_role_arn": manifest["plan_role_arn"],
                "role_session": _required(
                    os.environ.get("AWS_ROLE_SESSION_NAME"), "role_session"
                ),
                "cell_contract_sha256": manifest["cell_contract_sha256"],
                "policy_version": manifest["policy_version"],
                "provider_lock_sha256": _required(
                    os.environ.get("PROVIDER_LOCK_SHA256"), "provider_lock_sha256"
                ),
                "backend_lock_sha256": _required(
                    os.environ.get("BACKEND_LOCK_SHA256"), "backend_lock_sha256"
                ),
            }
            metadata = build_metadata(
                metadata_request,
                plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
                started_at=started_at.isoformat().replace("+00:00", "Z"),
                completed_at=completed_at.isoformat().replace("+00:00", "Z"),
                terraform_version="1.15.8",
            )
            report_data = {
                "metadata": metadata,
                "summary": summary,
                "policy": {
                    "policy_id": policy.get("policy_id"),
                    "policy_version": policy.get("policy_version"),
                    "status": policy.get("status"),
                    "finding_count": len(policy.get("findings", [])),
                    "security_review_required": policy.get("classification", {}).get(
                        "security_review_required"
                    ),
                    "plan_sha256": policy.get("plan_sha256"),
                    "catalog_version": policy.get("catalog_version"),
                    "evaluated_at": policy.get("evaluated_at"),
                    "findings": [
                        {
                            key: item.get(key)
                            for key in ("policy_id", "policy_version", "address", "requirement", "evidence", "severity", "remediation", "exemptible")
                        }
                        for item in policy.get("findings", [])[:200]
                        if isinstance(item, Mapping)
                    ],
                },
            }
            encoded = json.dumps(report_data, sort_keys=True, separators=(",", ":"))
            if args.output:
                Path(args.output).write_text(encoded + "\n", encoding="utf-8")
            print(f"TRUSTED_PLAN_REPORT:{encoded}")
    except (OSError, subprocess.SubprocessError, TargetViolation) as error:
        print(f"TRUSTED_PLAN_FAILED:{error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
