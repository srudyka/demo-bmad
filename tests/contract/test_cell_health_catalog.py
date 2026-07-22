from __future__ import annotations

from pathlib import Path

from tests.contract.support.contracts import load_json_strict


CATALOG = Path(__file__).parents[2] / "contracts/v1/catalogs/metrics-alerts.json"


def test_cell_health_catalog_has_bounded_dimensions_and_freshness_policy() -> None:
    health = load_json_strict(CATALOG)["cell_health"]
    assert "CanaryProcessedHeartbeat" == health["heartbeat_metric"]
    assert health["freshness_alarm"] == {
        "evaluation_periods": 5,
        "missing_data": "breaching",
        "period_seconds": 60,
        "threshold": 1,
    }
    assert set(health["forbidden_dimensions"]) >= {
        "occurrence_id",
        "task_arn",
        "error_text",
        "target_arn",
    }
    assert "job_id" in health["bounded_dimensions"]
    assert health["runbook_uri_required"] is True
    definitions = health["alarm_definitions"]
    assert len(definitions) >= 29
    for definition in definitions.values():
        assert definition["threshold"] >= 1
        assert definition["evaluation_periods"] >= 1
        assert definition["period_seconds"] >= 60
        assert definition["missing_data"] in {"breaching", "notBreaching"}
        assert definition["severity"] in {"critical", "high", "medium"}
        assert definition["owner_required"] is True
