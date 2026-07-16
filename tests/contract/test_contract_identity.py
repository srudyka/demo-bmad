from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    canonical_json_bytes,
    config_hash,
    load_json_strict,
    occurrence_bytes,
    occurrence_id,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = REPOSITORY_ROOT / "contracts" / "v1" / "fixtures"


def test_canonical_json_and_config_hash_vectors() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "canonical-json" / "vectors.json")
    for case in fixture["cases"]:
        actual = canonical_json_bytes(case["input"])
        assert actual.hex() == case["expected_utf8_hex"], case["name"]
        if "expected_sha256" in case:
            assert config_hash(case["input"]) == case["expected_sha256"]


def test_canonical_profile_rejects_ambiguous_values() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "canonical-json" / "invalid.json")
    for case in fixture["cases"]:
        with pytest.raises(ContractViolation, match=case["error_code"]):
            canonical_json_bytes(case["input"])


def test_occurrence_identity_exact_byte_vectors() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "identity" / "occurrence-v1.json")
    for case in fixture["valid"]:
        actual_bytes = occurrence_bytes(
            case["job_id"], case["schedule_generation"], case["epoch_minute"]
        )
        assert actual_bytes.hex() == case["expected_utf8_hex"], case["name"]
        assert (
            occurrence_id(
                case["job_id"], case["schedule_generation"], case["epoch_minute"]
            )
            == case["expected_sha256"]
        )


def test_occurrence_identity_rejects_noncanonical_coordinates() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "identity" / "occurrence-v1.json")
    for case in fixture["invalid"]:
        with pytest.raises(ContractViolation, match=case["error_code"]):
            occurrence_bytes(
                case["job_id"], case["schedule_generation"], case["epoch_minute"]
            )


def test_asserted_occurrence_hash_mismatch_is_detected() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "identity" / "occurrence-v1.json")
    case = fixture["mismatched_assertion"]
    actual = occurrence_id(
        case["job_id"], case["schedule_generation"], case["epoch_minute"]
    )
    assert actual != case["asserted_occurrence_id"]
