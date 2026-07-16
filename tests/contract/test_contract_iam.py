from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    evaluate_iam_case,
    evaluate_producer_authority,
    load_json_strict,
)


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_role_catalog_is_explicit_and_contains_every_architecture_role() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "iam.json")
    expected = {
        "scheduler-delivery",
        "materializer",
        "normalizer",
        "process-manager",
        "log-ingestor",
        "deadline-scanner",
        "alert-router",
        "command-handler",
        "lifecycle-garbage-collection",
        "operator",
        "break-glass",
        "job-launch",
        "execution",
        "task",
        "plan",
        "apply",
    }
    assert set(catalog["roles"]) == expected
    for name, role in catalog["roles"].items():
        assert role["actions"], name
        assert role["resources"], name
        assert role["trust"], name
        assert "*" not in role["actions"], name
        assert "*" not in role["resources"], name


def test_iam_positive_and_negative_authority_cases() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "iam.json")
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "iam" / "cases.json"
    )
    for case in fixture["cases"]:
        if case["accepted"]:
            evaluate_iam_case(case, catalog)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_iam_case(case, catalog)


def test_producer_identity_comes_from_registered_non_body_metadata() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "producers.json")
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "iam" / "producer-authority.json"
    )
    for case in fixture["cases"]:
        if case["accepted"]:
            evaluate_producer_authority(case, catalog)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_producer_authority(case, catalog)


def test_raw_aws_shapes_keep_authority_separate_from_additive_fields() -> None:
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "iam" / "raw-aws-producer-shapes.json"
    )
    accepted = fixture["ecs"]["accepted"]
    assert accepted["source"] == "aws.ecs"
    assert accepted["resources"] == [accepted["detail"]["taskArn"]]
    assert accepted["detail"]["newAwsManagedField"] == "ignored"
    rejected = fixture["ecs"]["rejected_missing_authority"]
    assert not rejected["resources"]
    assert fixture["scheduler"]["occurrence_time_source"] == (
        "<aws.scheduler.scheduled-time>"
    )


def test_every_integration_edge_has_one_owner_and_version() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "ownership.json")
    names: set[str] = set()
    for edge in catalog["edges"]:
        assert edge["integration"] not in names
        names.add(edge["integration"])
        for required in (
            "terraform_owner",
            "lifecycle_owner",
            "producer",
            "consumer",
            "evidence_type",
            "resource_arn_shape",
            "compatibility_version",
        ):
            assert edge[required], (edge["integration"], required)
