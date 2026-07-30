from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import rfc8785

from scripts.deployment_targets import TargetViolation
from scripts.release_manifest import (
    build_release_manifest,
    classify_release_change,
    validate_immutable_reference,
    validate_release_manifest,
    verify_release_artifacts,
    validate_consumer_compatibility,
)


def _manifest() -> dict:
    return build_release_manifest(
        version="1.1.0",
        source_commit="a" * 40,
        builder_workflow_sha="b" * 40,
        builder_run_id="42",
        artifacts={
            "module": {"kind": "module", "reference": "a" * 40, "sha256": "c" * 64}
        },
        qualification={"status": "passed", "evidence_sha256": "d" * 64},
        compatibility={"supported": [">=1.0.0,<2.0.0"]},
        policy_bundle_sha256="e" * 64,
        migration_class="minor",
        known_limitations=["none"],
        published_at="2026-07-30T12:00:00Z",
        provider_lock_sha256="f" * 64,
        tested_matrix={
            "terraform": "1.15.8",
            "aws_provider": "6.54.0",
            "python": "3.14.6",
            "fargate": "latest",
        },
        component_versions={"module": "1.1.0"},
        schema_ranges={"contract": ">=1.0.0,<2.0.0"},
        qualification_observations=[
            {"name": "credential-free", "observed_at": "2026-07-30T12:00:00Z"}
        ],
        runtime_exceptions=[],
        publisher_oidc_actor="github-actions[bot]",
    )


def test_release_classification_rejects_semver_drift() -> None:
    assert (
        classify_release_change(
            ["docs/release.md"], requested_version="1.0.1", previous_version="1.0.0"
        )
        == "patch"
    )
    assert (
        classify_release_change(
            ["modules/job/main.tf"], requested_version="1.1.0", previous_version="1.0.0"
        )
        == "minor"
    )
    with pytest.raises(TargetViolation, match="RELEASE_CLASS_MISMATCH"):
        classify_release_change(
            ["contracts/v1/schemas/new.schema.json"],
            requested_version="1.1.0",
            previous_version="1.0.0",
        )


def test_release_manifest_is_checksum_and_reference_bound(tmp_path: Path) -> None:
    manifest = _manifest()
    validate_release_manifest(manifest)
    artifact = tmp_path / "module"
    artifact.write_bytes(b"immutable artifact")
    manifest["artifacts"]["module"]["sha256"] = hashlib.sha256(
        artifact.read_bytes()
    ).hexdigest()
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = hashlib.sha256(rfc8785.dumps(manifest)).hexdigest()
    verify_release_artifacts(
        tmp_path,
        {**manifest, "artifacts": {"module": {**manifest["artifacts"]["module"]}}},
    )


def test_mutable_release_references_are_rejected() -> None:
    with pytest.raises(TargetViolation, match="RELEASE_MUTABLE_REFERENCE"):
        validate_immutable_reference("image", "latest")
    with pytest.raises(TargetViolation, match="RELEASE_MUTABLE_REFERENCE"):
        validate_immutable_reference("action", "v4")


def test_consumer_validation_rejects_missing_lock_or_unsupported_component() -> None:
    manifest = _manifest()
    manifest["compatibility"] = {"components": {"module": ">=1.0.0,<2.0.0"}}
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = hashlib.sha256(rfc8785.dumps(manifest)).hexdigest()
    validate_consumer_compatibility(
        manifest, required_components={"module": "1.1.0"}, provider_lock_sha256="f" * 64
    )
    with pytest.raises(TargetViolation, match="RELEASE_PROVIDER_LOCK"):
        validate_consumer_compatibility(
            manifest,
            required_components={"module": "1.1.0"},
            provider_lock_sha256="latest",
        )


@pytest.mark.parametrize(
    ("kind", "reference"),
    [("module", "1.1.0"), ("workflow", "git::https://example.invalid/repo@main")],
)
def test_mutable_git_and_module_references_are_rejected(
    kind: str, reference: str
) -> None:
    with pytest.raises(TargetViolation, match="RELEASE_MUTABLE_REFERENCE"):
        validate_immutable_reference(kind, reference)


def test_release_validation_rejects_unknown_kind_and_path_escape(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    manifest["artifacts"]["module"]["kind"] = "unknown"
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = hashlib.sha256(rfc8785.dumps(manifest)).hexdigest()
    with pytest.raises(TargetViolation, match="RELEASE_ARTIFACT"):
        validate_release_manifest(manifest)

    manifest = _manifest()
    manifest["artifacts"]["module"]["reference"] = "a" * 40
    manifest["artifacts"]["../outside"] = manifest["artifacts"].pop("module")
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = hashlib.sha256(rfc8785.dumps(manifest)).hexdigest()
    with pytest.raises(TargetViolation, match="RELEASE_ARTIFACT_PATH"):
        verify_release_artifacts(tmp_path, manifest)


def test_classification_fails_closed_for_empty_and_unclassified_changes() -> None:
    with pytest.raises(TargetViolation, match="RELEASE_NO_CHANGES"):
        classify_release_change([], requested_version="1.0.1", previous_version="1.0.0")
    with pytest.raises(TargetViolation, match="RELEASE_UNCLASSIFIED_CHANGE"):
        classify_release_change(
            ["unknown/input.bin"], requested_version="1.0.1", previous_version="1.0.0"
        )


def test_consumer_validation_rejects_provider_lock_drift() -> None:
    manifest = _manifest()
    with pytest.raises(TargetViolation, match="RELEASE_PROVIDER_LOCK"):
        validate_consumer_compatibility(
            manifest,
            required_components={"module": "1.1.0"},
            provider_lock_sha256="0" * 64,
        )
