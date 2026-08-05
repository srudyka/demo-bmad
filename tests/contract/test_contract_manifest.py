from __future__ import annotations

import json
from pathlib import Path
from shutil import copytree

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    artifact_digest,
    classify_semantic_change,
    load_json_strict,
    semantic_surface_digest,
    validate_manifest,
    validate_release,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"


def test_manifest_declares_initial_release_and_required_roots() -> None:
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")

    assert manifest["package_version"] == "1.0.0"
    assert manifest["predecessor_release"] is None
    assert manifest["current_major"] == 1
    assert manifest["previous_major"] is None
    assert manifest["initial_release"] is True
    assert manifest["minimum_support_horizon_days"] == 14
    assert manifest["schema_dialect"] == (
        "https://json-schema.org/draft/2020-12/schema"
    )
    assert manifest["canonicalization"]["semantic_json"] == "RFC8785"
    assert manifest["canonicalization"]["artifact_integrity"] == (
        "sha256-raw-utf8-lf-final-newline"
    )
    assert set(manifest["artifact_roots"]) == {
        "migrations",
        "releases",
        "v1/catalogs",
        "v1/fixtures",
        "v1/schemas",
    }
    validate_manifest(CONTRACTS_ROOT, manifest)


def test_manifest_inventory_uses_exact_raw_bytes() -> None:
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")
    for artifact in manifest["artifacts"]:
        path = CONTRACTS_ROOT / artifact["path"]
        assert artifact["sha256"] == artifact_digest(path)


def test_manifest_rejects_path_escape_and_duplicate_inventory() -> None:
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")
    bad = dict(manifest)
    bad["artifacts"] = [
        {"path": "../README.md", "sha256": "0" * 64},
        {"path": "../README.md", "sha256": "0" * 64},
    ]

    with pytest.raises(ContractViolation, match="MANIFEST_PATH_ESCAPE"):
        validate_manifest(CONTRACTS_ROOT, bad)


def test_manifest_rejects_unreferenced_controlled_artifact() -> None:
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")
    bad = dict(manifest)
    bad["artifacts"] = [
        item for item in manifest["artifacts"] if item["path"] != "migrations/v1.0.0.md"
    ]

    with pytest.raises(ContractViolation, match="MANIFEST_UNREFERENCED_ARTIFACT"):
        validate_manifest(CONTRACTS_ROOT, bad)


def test_release_snapshot_is_initial_and_matches_manifest_version() -> None:
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")
    snapshot = load_json_strict(CONTRACTS_ROOT / "releases" / "1.0.0.json")

    assert snapshot["package_version"] == manifest["package_version"]
    assert snapshot["predecessor_release"] is None
    assert snapshot["classification"] == "initial"
    assert snapshot["migration"] == "migrations/v1.0.0.md"
    assert snapshot["semantic_surface_sha256"] == semantic_surface_digest(manifest)
    validate_release(CONTRACTS_ROOT, manifest)


def test_semantic_change_classification_fixtures() -> None:
    fixture = load_json_strict(
        CONTRACTS_ROOT
        / "v1"
        / "fixtures"
        / "compatibility"
        / "semantic-change-classification.json"
    )
    for case in fixture["cases"]:
        actual = classify_semantic_change(case["before"], case["after"])
        assert actual == case["expected"], case["name"]


def test_manifest_file_is_not_in_its_own_inventory() -> None:
    manifest = json.loads((CONTRACTS_ROOT / "manifest.json").read_text("utf-8"))
    assert "manifest.json" not in {item["path"] for item in manifest["artifacts"]}


def test_manifest_rejects_unreferenced_future_major_artifact(tmp_path: Path) -> None:
    copied = tmp_path / "contracts"
    copytree(CONTRACTS_ROOT, copied)
    future_schema = copied / "v2" / "schemas" / "future.schema.json"
    future_schema.parent.mkdir(parents=True)
    future_schema.write_text("{}\n", encoding="utf-8")
    manifest = load_json_strict(copied / "manifest.json")

    with pytest.raises(ContractViolation, match="MANIFEST_UNREFERENCED_ARTIFACT"):
        validate_manifest(copied, manifest)


def test_future_release_cannot_misclassify_a_semantic_change(tmp_path: Path) -> None:
    copied = tmp_path / "contracts"
    copytree(CONTRACTS_ROOT, copied)
    manifest = load_json_strict(copied / "manifest.json")
    manifest.update(
        initial_release=False,
        package_version="1.0.1",
        predecessor_release="1.0.0",
    )
    next(
        item
        for item in manifest["artifacts"]
        if item["path"] == "v1/catalogs/producers.json"
    )["sha256"] = "0" * 64
    (copied / "migrations" / "v1.0.1.md").write_text(
        '<!-- compatibility-release: {"package_version":"1.0.1",'
        '"predecessor_release":"1.0.0","classification":"patch"} -->\n',
        encoding="utf-8",
    )
    (copied / "releases" / "1.0.1.json").write_text(
        json.dumps(
            {
                "classification": "patch",
                "migration": "migrations/v1.0.1.md",
                "package_version": "1.0.1",
                "predecessor_release": "1.0.0",
                "semantic_surface_sha256": semantic_surface_digest(manifest),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractViolation, match="RELEASE_CLASSIFICATION_MISMATCH"):
        validate_release(copied, manifest)
