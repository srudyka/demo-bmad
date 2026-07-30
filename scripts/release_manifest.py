"""Credential-free immutable release classification and manifest validation."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import rfc8785
from semantic_version import SimpleSpec, Version  # type: ignore[import-untyped]

from scripts.deployment_targets import TargetViolation

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IMMUTABLE_SHA = re.compile(r"^[0-9a-f]{40}$")
IMMUTABLE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def classify_release_change(
    changed_paths: Sequence[str],
    *,
    requested_version: str,
    previous_version: str,
) -> str:
    """Classify source changes and reject a requested SemVer class mismatch."""
    try:
        requested = Version(requested_version)
        previous = Version(previous_version)
    except ValueError as error:
        raise TargetViolation("RELEASE_VERSION") from error
    if requested <= previous:
        raise TargetViolation("RELEASE_VERSION_ORDER")
    if not changed_paths:
        raise TargetViolation("RELEASE_NO_CHANGES")
    breaking = any(
        path.endswith(".schema.json")
        or path.startswith(".github/workflows/")
        or path.endswith(".tf")
        and not path.startswith("modules/")
        or "/fixtures/" in path
        for path in changed_paths
    )
    compatible = any(
        path.startswith("modules/")
        or path.startswith("runtime/")
        or path.startswith("contracts/")
        for path in changed_paths
    )
    documentation_only = all(
        path.endswith((".md", ".rst", ".txt")) or path.startswith("tests/")
        for path in changed_paths
    )
    if breaking:
        expected = "major"
    elif compatible:
        expected = "minor"
    elif documentation_only:
        expected = "patch"
    else:
        raise TargetViolation("RELEASE_UNCLASSIFIED_CHANGE")
    actual = (
        "major"
        if requested.major != previous.major
        else "minor"
        if requested.minor != previous.minor
        else "patch"
    )
    if actual != expected:
        raise TargetViolation("RELEASE_CLASS_MISMATCH")
    return actual


def validate_immutable_reference(kind: str, reference: str) -> None:
    if not isinstance(reference, str) or not reference:
        raise TargetViolation("RELEASE_REFERENCE")
    if kind not in {
        "action",
        "workflow",
        "module",
        "source",
        "image",
        "contract",
        "runtime",
    }:
        raise TargetViolation("RELEASE_ARTIFACT")
    if kind in {
        "action",
        "workflow",
        "source",
        "contract",
        "runtime",
    } and not IMMUTABLE_SHA.fullmatch(reference):
        raise TargetViolation("RELEASE_MUTABLE_REFERENCE")
    if kind == "module" and not IMMUTABLE_SHA.fullmatch(reference):
        raise TargetViolation("RELEASE_MUTABLE_REFERENCE")
    if kind == "image" and not IMMUTABLE_DIGEST.fullmatch(reference):
        raise TargetViolation("RELEASE_MUTABLE_REFERENCE")


def _validate_artifact_identity(identity: object) -> None:
    if not isinstance(identity, Mapping) or set(identity) not in (
        {"artifact_class", "resource", "version", "checksum", "cell_id"},
        {"artifact_class", "resource", "version", "checksum", "cell_id", "job_id"},
    ):
        raise TargetViolation("RELEASE_ARTIFACT")
    if any(
        not isinstance(identity.get(field), str) or not identity[field]
        for field in ("artifact_class", "resource", "version", "checksum", "cell_id")
    ) or not SHA256.fullmatch(str(identity["checksum"])):
        raise TargetViolation("RELEASE_ARTIFACT")
    if "job_id" in identity and (
        not isinstance(identity["job_id"], str) or not identity["job_id"]
    ):
        raise TargetViolation("RELEASE_ARTIFACT")


def build_release_manifest(
    *,
    version: str,
    source_commit: str,
    builder_workflow_sha: str,
    builder_run_id: str,
    artifacts: Mapping[str, Mapping[str, Any]],
    qualification: Mapping[str, Any],
    compatibility: Mapping[str, Any],
    policy_bundle_sha256: str,
    migration_class: str,
    known_limitations: Sequence[str],
    published_at: str,
    provider_lock_sha256: str = "",
    tested_matrix: Mapping[str, str] | None = None,
    component_versions: Mapping[str, str] | None = None,
    schema_ranges: Mapping[str, str] | None = None,
    qualification_observations: Sequence[Mapping[str, str]] | None = None,
    runtime_exceptions: Sequence[str] | None = None,
    publisher_oidc_actor: str = "",
) -> dict[str, Any]:
    if not SEMVER.fullmatch(version):
        raise TargetViolation("RELEASE_VERSION")
    if not SHA1.fullmatch(source_commit) or not SHA1.fullmatch(builder_workflow_sha):
        raise TargetViolation("RELEASE_PROVENANCE")
    if not re.fullmatch(r"[1-9][0-9]*", str(builder_run_id)):
        raise TargetViolation("RELEASE_PROVENANCE")
    if not SHA256.fullmatch(policy_bundle_sha256):
        raise TargetViolation("RELEASE_POLICY")
    if not SHA256.fullmatch(provider_lock_sha256) or not publisher_oidc_actor:
        raise TargetViolation("RELEASE_PROVENANCE")
    if migration_class not in {"none", "patch", "minor", "major"}:
        raise TargetViolation("RELEASE_MIGRATION")
    if not artifacts or qualification.get("status") != "passed":
        raise TargetViolation("RELEASE_QUALIFICATION")
    if not isinstance(
        qualification.get("evidence_sha256"), str
    ) or not SHA256.fullmatch(qualification["evidence_sha256"]):
        raise TargetViolation("RELEASE_QUALIFICATION")
    normalized: dict[str, Any] = {}
    for name, artifact in sorted(artifacts.items()):
        if set(artifact) not in (
            {"kind", "reference", "sha256"},
            {"kind", "reference", "sha256", "identity"},
        ):
            raise TargetViolation("RELEASE_ARTIFACT")
        validate_immutable_reference(str(artifact["kind"]), str(artifact["reference"]))
        if not SHA256.fullmatch(str(artifact["sha256"])):
            raise TargetViolation("RELEASE_ARTIFACT")
        if "identity" in artifact:
            _validate_artifact_identity(artifact["identity"])
        normalized[name] = dict(artifact)
    try:
        datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise TargetViolation("RELEASE_TIMESTAMP") from error
    manifest = {
        "schema_version": "1.0.0",
        "version": version,
        "source_commit": source_commit,
        "builder": {
            "workflow_sha": builder_workflow_sha,
            "run_id": str(builder_run_id),
        },
        "artifacts": normalized,
        "qualification": dict(qualification),
        "compatibility": dict(compatibility),
        "policy_bundle_sha256": policy_bundle_sha256,
        "provider_lock_sha256": provider_lock_sha256,
        "migration_class": migration_class,
        "known_limitations": list(known_limitations),
        "tested_matrix": dict(tested_matrix or {}),
        "component_versions": dict(component_versions or {}),
        "schema_ranges": dict(schema_ranges or {}),
        "qualification_observations": [
            dict(item) for item in (qualification_observations or [])
        ],
        "runtime_exceptions": list(runtime_exceptions or []),
        "publisher": {"oidc_actor": publisher_oidc_actor},
        "published_at": published_at,
    }
    manifest["manifest_sha256"] = _digest(manifest)
    return manifest


def validate_release_manifest(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "version",
        "source_commit",
        "builder",
        "artifacts",
        "qualification",
        "compatibility",
        "policy_bundle_sha256",
        "provider_lock_sha256",
        "migration_class",
        "known_limitations",
        "tested_matrix",
        "component_versions",
        "schema_ranges",
        "qualification_observations",
        "runtime_exceptions",
        "publisher",
        "published_at",
        "manifest_sha256",
    }
    if set(manifest) != required or manifest.get("schema_version") != "1.0.0":
        raise TargetViolation("RELEASE_SHAPE")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if manifest["manifest_sha256"] != _digest(unsigned):
        raise TargetViolation("RELEASE_CHECKSUM")
    if not isinstance(manifest["artifacts"], Mapping):
        raise TargetViolation("RELEASE_ARTIFACT")
    if not SEMVER.fullmatch(str(manifest.get("version"))) or not SHA1.fullmatch(
        str(manifest.get("source_commit"))
    ):
        raise TargetViolation("RELEASE_PROVENANCE")
    builder = manifest.get("builder")
    if not isinstance(builder, Mapping) or set(builder) != {"workflow_sha", "run_id"}:
        raise TargetViolation("RELEASE_PROVENANCE")
    if not SHA1.fullmatch(str(builder["workflow_sha"])) or not re.fullmatch(
        r"[1-9][0-9]*", str(builder["run_id"])
    ):
        raise TargetViolation("RELEASE_PROVENANCE")
    if (
        not isinstance(manifest.get("qualification"), Mapping)
        or manifest["qualification"].get("status") != "passed"
        or not SHA256.fullmatch(str(manifest["qualification"].get("evidence_sha256")))
    ):
        raise TargetViolation("RELEASE_QUALIFICATION")
    if not SHA256.fullmatch(
        str(manifest.get("policy_bundle_sha256"))
    ) or not SHA256.fullmatch(str(manifest.get("provider_lock_sha256"))):
        raise TargetViolation("RELEASE_POLICY")
    if manifest.get("migration_class") not in {"none", "patch", "minor", "major"}:
        raise TargetViolation("RELEASE_MIGRATION")
    if not isinstance(manifest.get("known_limitations"), list) or not all(
        isinstance(item, str) and len(item) <= 240
        for item in manifest["known_limitations"]
    ):
        raise TargetViolation("RELEASE_LIMITATIONS")
    if not all(
        isinstance(manifest.get(key), Mapping) and manifest[key]
        for key in ("tested_matrix", "component_versions", "schema_ranges")
    ):
        raise TargetViolation("RELEASE_COMPATIBILITY")
    if not isinstance(
        manifest.get("qualification_observations"), list
    ) or not isinstance(manifest.get("runtime_exceptions"), list):
        raise TargetViolation("RELEASE_QUALIFICATION")
    publisher = manifest.get("publisher")
    if (
        not isinstance(publisher, Mapping)
        or not isinstance(publisher.get("oidc_actor"), str)
        or not publisher["oidc_actor"]
    ):
        raise TargetViolation("RELEASE_PROVENANCE")
    try:
        datetime.fromisoformat(str(manifest["published_at"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise TargetViolation("RELEASE_TIMESTAMP") from error
    for name, artifact in manifest["artifacts"].items():
        if not isinstance(name, str) or not isinstance(artifact, Mapping):
            raise TargetViolation("RELEASE_ARTIFACT")
        validate_immutable_reference(
            str(artifact.get("kind")), str(artifact.get("reference"))
        )
        if not SHA256.fullmatch(str(artifact.get("sha256"))):
            raise TargetViolation("RELEASE_ARTIFACT")
        if "identity" in artifact:
            _validate_artifact_identity(artifact["identity"])


def verify_release_artifacts(root: Path, manifest: Mapping[str, Any]) -> None:
    """Verify published file bytes against the immutable release manifest."""
    validate_release_manifest(manifest)
    artifacts = manifest["artifacts"]
    for name, artifact in artifacts.items():
        path = (root / name).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as error:
            raise TargetViolation("RELEASE_ARTIFACT_PATH") from error
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]
        ):
            raise TargetViolation("RELEASE_ARTIFACT_CHECKSUM")


def validate_consumer_compatibility(
    manifest: Mapping[str, Any],
    *,
    required_components: Mapping[str, str],
    provider_lock_sha256: str,
) -> None:
    """Fail closed when a consumer cannot reproduce the release contract."""
    validate_release_manifest(manifest)
    if provider_lock_sha256 != manifest.get("provider_lock_sha256"):
        raise TargetViolation("RELEASE_PROVIDER_LOCK")
    compatibility = manifest.get("compatibility")
    if not isinstance(compatibility, Mapping):
        raise TargetViolation("RELEASE_COMPATIBILITY")
    ranges = compatibility.get("components", {})
    if not isinstance(ranges, Mapping):
        raise TargetViolation("RELEASE_COMPATIBILITY")
    for component, version in required_components.items():
        try:
            if not isinstance(version, str):
                raise ValueError
            resolved = Version(version)
            spec = SimpleSpec(str(ranges[component]))
            if not spec.match(resolved):
                raise TargetViolation("RELEASE_INCOMPATIBLE")
        except KeyError, ValueError:
            raise TargetViolation("RELEASE_INCOMPATIBLE") from None
