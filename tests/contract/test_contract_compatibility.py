from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    evaluate_compatibility_case,
    load_json_strict,
)


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_compatibility_catalog_declares_complete_initial_release_matrix() -> None:
    catalog = load_json_strict(
        CONTRACTS_ROOT / "v1" / "catalogs" / "compatibility.json"
    )
    assert catalog["range_semantics"] == "semantic-version SimpleSpec"
    assert catalog["current_major"] == 1
    assert catalog["previous_major"] is None
    assert catalog["initial_release"] is True
    assert catalog["minimum_support_horizon_days"] == 14
    assert catalog["migration_reference"] == "migrations/v1.0.0.md"
    assert {
        "cell",
        "ecs-scheduled-job-module",
        "ecs-scheduled-job-platform-module",
        "config",
        "evidence",
        "evidence-normalizer",
        "occurrence-materializer",
        "process-manager",
        "log-ingestor",
        "deadline-scanner",
        "alert-router",
        "command-handler",
        "workflow",
        "terraform",
        "aws-provider",
        "python",
    } == set(catalog["component_ranges"])


def test_semver_range_and_migration_cases_return_stable_codes() -> None:
    catalog = load_json_strict(
        CONTRACTS_ROOT / "v1" / "catalogs" / "compatibility.json"
    )
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "compatibility" / "cases.json"
    )
    for case in fixture["cases"]:
        if case["accepted"]:
            evaluate_compatibility_case(case, catalog)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_compatibility_case(case, catalog)
            assert case["error_code"] in catalog["rejection_codes"]
