from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    load_json_strict,
    manual_occurrence_bytes,
    validate_operator_request,
)


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_operator_request_rejects_caller_owned_canonical_identity() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "commands.json")
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "compatibility" / "commands.json"
    )
    for case in fixture["operator_requests"]:
        if case["accepted"]:
            validate_operator_request(case["request"], catalog)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                validate_operator_request(case["request"], catalog)


def test_manual_occurrence_identity_matches_literal_bytes_and_digest() -> None:
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "compatibility" / "commands.json"
    )["canonical"]
    actual = manual_occurrence_bytes(
        fixture["job_id"],
        fixture["original_occurrence_id"],
        fixture["config_version"],
        fixture["command_id"],
    )
    expected = base64.b64decode(fixture["expected_bytes_base64"], validate=True)
    assert actual == expected
    assert not actual.endswith(b"\n")
    assert hashlib.sha256(actual).hexdigest() == fixture["expected_occurrence_id"]
