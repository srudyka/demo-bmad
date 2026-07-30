"""Assemble and validate the protected production apply bundle.

This boundary never creates approval or readiness evidence. It only joins
independently produced evidence to the exact trusted plan and fails closed when
any binding, expiry, or provenance check differs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from scripts.deployment_targets import TargetViolation
from scripts.production_apply import validate_approval, validate_readiness
from scripts.deployment_evidence import validate_deployment_evidence

FILES = (
    "approved.tfplan",
    "trusted-plan.json",
    "trusted-policy.json",
    "trusted-artifact-manifest.json",
    "approval.json",
    "readiness.json",
    "apply-authorization.json",
    "caller.json",
    "authority.json",
    "github-claims.json",
    "cell-contract.json",
    "lock.json",
    "deployment-evidence.json",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    if (
        manifest.get("schema_version") != "1.0.0"
        or manifest.get("audience") != "production-apply"
    ):
        raise TargetViolation("BUNDLE_MANIFEST_SHAPE")
    files = manifest.get("files")
    if not isinstance(files, Mapping) or set(files) != set(FILES):
        raise TargetViolation("BUNDLE_MANIFEST_FILES")
    for name in FILES:
        path = root / name
        if not path.is_file() or _digest(path) != files[name]:
            raise TargetViolation("BUNDLE_MANIFEST_DIGEST")
    if manifest.get("plan_sha256") != _digest(root / "approved.tfplan"):
        raise TargetViolation("BUNDLE_MANIFEST_PLAN")


def assemble_bundle(
    source: Path,
    destination: Path,
    expected: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Copy only a complete, exact-bound bundle and return its manifest."""
    missing = [name for name in FILES if not (source / name).is_file()]
    if missing:
        raise TargetViolation("BUNDLE_MISSING:" + ",".join(missing))
    plan_sha = _digest(source / "approved.tfplan")
    if plan_sha != expected.get("plan_sha256"):
        raise TargetViolation("BUNDLE_PLAN_CHECKSUM")
    policy = json.loads((source / "trusted-policy.json").read_text(encoding="utf-8"))
    if policy.get("status") != "passed" or policy.get("plan_sha256") != plan_sha:
        raise TargetViolation("BUNDLE_POLICY_BINDING")
    approval = json.loads((source / "approval.json").read_text(encoding="utf-8"))
    readiness = json.loads((source / "readiness.json").read_text(encoding="utf-8"))
    deployment_evidence = json.loads(
        (source / "deployment-evidence.json").read_text(encoding="utf-8")
    )
    validate_deployment_evidence(
        deployment_evidence, expected_status="awaiting-approval", expected=expected
    )
    validate_approval(approval, expected, now=now)
    validate_readiness(readiness, expected, now=now)
    if (
        readiness.get("environment") == "production"
        and readiness.get("evidence_source") != "epic4"
    ):
        raise TargetViolation("BUNDLE_PRODUCTION_FIXTURE")
    destination.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        (destination / name).write_bytes((source / name).read_bytes())
    manifest = {
        "schema_version": "1.0.0",
        "audience": "production-apply",
        "plan_sha256": plan_sha,
        "files": {name: _digest(destination / name) for name in FILES},
    }
    (destination / "bundle-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    verify_bundle_manifest(destination, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    assemble_bundle(
        args.source, args.destination, expected, now=datetime.now(timezone.utc)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
