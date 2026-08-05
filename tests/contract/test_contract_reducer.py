from __future__ import annotations

from itertools import permutations
from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    load_json_strict,
    reduce_occurrence_state,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"
CATALOG = CONTRACTS_ROOT / "v1" / "catalogs" / "reducer.json"
FIXTURE = CONTRACTS_ROOT / "v1" / "fixtures" / "reducer" / "cases.json"


def test_reducer_catalog_declares_all_canonical_states() -> None:
    catalog = load_json_strict(CATALOG)
    assert catalog["states"] == [
        "EXPECTED",
        "STARTED",
        "SUCCEEDED",
        "FAILED",
        "OVERDUE",
        "MISSED",
        "AMBIGUOUS",
    ]
    assert catalog["deadline_clock"] == "fact_time"
    assert catalog["maximum_fixture_events"] == 6


def test_every_bounded_evidence_permutation_converges() -> None:
    catalog = load_json_strict(CATALOG)
    fixture = load_json_strict(FIXTURE)
    for case in fixture["cases"]:
        accepted_count = sum(event.get("accepted", True) for event in case["evidence"])
        assert accepted_count <= catalog["maximum_fixture_events"], case["name"]
        for ordering in permutations(case["evidence"]):
            actual = reduce_occurrence_state(list(ordering), catalog)
            assert actual == case["expected_state"], case["name"]


def test_oversized_evidence_set_is_rejected_not_sampled() -> None:
    catalog = load_json_strict(CATALOG)
    evidence = [
        {
            "accepted": True,
            "digest": str(index).zfill(64),
            "kind": "EXPECTED",
            "producer_event_id": str(index),
            "producer_id": "materializer",
        }
        for index in range(7)
    ]
    with pytest.raises(ContractViolation, match="REDUCER_FIXTURE_TOO_LARGE"):
        reduce_occurrence_state(evidence, catalog)


def test_correlation_catalog_owns_deduplication_and_ledger_keys() -> None:
    catalog = load_json_strict(
        CONTRACTS_ROOT / "v1" / "catalogs" / "keys-and-correlation.json"
    )
    assert catalog["deduplication_key"] == ["producer_id", "producer_event_id"]
    assert catalog["attempt_no"] == 0
    assert catalog["metrics_forbidden_dimensions"] == ["occurrence_id"]
