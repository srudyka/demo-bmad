from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    evaluate_lifecycle_case,
    load_json_strict,
)


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_lifecycle_catalog_freezes_two_phase_enablement() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "lifecycle.json")
    assert catalog["states"] == [
        "RESERVED",
        "PUBLISHED",
        "VALIDATED",
        "MATERIALIZED",
        "ENABLED",
        "REJECTED",
    ]
    assert catalog["timeout_disposition"] == "REJECTED"
    assert catalog["legal_transitions"]["MATERIALIZED"] == [
        "ENABLED",
        "REJECTED",
    ]
    assert set(catalog["acknowledgement_bindings"]) == {
        "job_id",
        "ownership_generation",
        "config_version",
        "schedule_generation",
        "scheduler_delivery_role_arn",
        "schedule_arn",
        "contract_version",
        "horizon_watermark",
    }
    assert catalog["acknowledgement_integrity_bindings"] == [
        "contract_checksum",
        "validation_evidence",
    ]


def test_lifecycle_transition_and_stale_acknowledgement_fixtures() -> None:
    catalog = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "lifecycle.json")
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "lifecycle" / "cases.json"
    )
    for case in fixture["cases"]:
        if case["accepted"]:
            evaluate_lifecycle_case(case, catalog)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_lifecycle_case(case, catalog)


def test_metric_and_alert_dimensions_are_bounded() -> None:
    catalog = load_json_strict(
        CONTRACTS_ROOT / "v1" / "catalogs" / "metrics-alerts.json"
    )
    assert catalog["metric_dimensions"] == ["job_id", "environment", "state"]
    assert "occurrence_id" in catalog["forbidden_dimensions"]
    assert catalog["alarm_contract"]["threshold"] == 1
    assert "deployment_identity_id" in catalog["alert_required_fields"]
