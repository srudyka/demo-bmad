from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    expand_schedule,
    load_json_strict,
    schedule_generation,
    validate_schedule_contract,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"
FIXTURE = CONTRACTS_ROOT / "v1" / "fixtures" / "schedules" / "cases.json"


def test_schedule_catalog_freezes_grammar_and_tzdb() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "schedules.json")
    assert catalog["contract"] == "schedule/v1"
    assert catalog["tzdata_package_version"] == "2026.2"
    assert catalog["iana_release"] == "2026b"
    assert catalog["flexible_time_window"] == "OFF"


def test_schedule_generation_exact_vectors() -> None:
    fixture = load_json_strict(FIXTURE)
    for case in fixture["valid"]:
        validate_schedule_contract(case["schedule"])
        assert schedule_generation(case["schedule"]) == case["expected_generation"]


def test_schedule_occurrence_vectors() -> None:
    fixture = load_json_strict(FIXTURE)
    for case in fixture["valid"]:
        actual = expand_schedule(
            case["schedule"], case["window_start"], case["window_end"]
        )
        assert actual == tuple(case["expected_occurrences"]), case["name"]


def test_invalid_schedule_contracts_fail_deterministically() -> None:
    fixture = load_json_strict(FIXTURE)
    for case in fixture["invalid"]:
        with pytest.raises(ContractViolation, match=case["error_code"]):
            validate_schedule_contract(case["schedule"])


def test_asserted_schedule_generation_mismatch_is_visible() -> None:
    fixture = load_json_strict(FIXTURE)
    case = fixture["valid"][0]
    assert schedule_generation(case["schedule"]) != "f" * 64
