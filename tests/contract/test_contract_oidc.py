from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    evaluate_oidc_case,
    load_json_strict,
)


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_oidc_claim_template_is_immutable_and_exact() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "oidc.json")
    assert catalog["claim_keys"] == [
        "repository_owner_id",
        "repository_id",
        "context",
        "job_workflow_ref",
    ]
    assert catalog["audience"] == "sts.amazonaws.com"
    assert catalog["deployment_environment"] == "production"
    assert catalog["immutable_repository_owner_id"] == "11111111"
    assert catalog["job_workflow_ref"].endswith(
        "@0123456789abcdef0123456789abcdef01234567"
    )


def test_oidc_positive_and_negative_claim_fixtures() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "oidc.json")
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "oidc" / "cases.json"
    )
    for case in fixture["cases"]:
        if case["accepted"]:
            evaluate_oidc_case(case, catalog)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_oidc_case(case, catalog)
