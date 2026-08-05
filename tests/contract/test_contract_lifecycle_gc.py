from pathlib import Path
from datetime import UTC, datetime, timedelta

from lifecycle_gc import ArtifactIdentity, ReferenceEvidence, evaluate_candidate
from tests.contract.support.contracts import load_json_strict


ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 7, 22, 12, tzinfo=UTC)


def test_lifecycle_reference_fixture_covers_fail_closed_cases() -> None:
    fixture = load_json_strict(
        ROOT / "contracts" / "v1" / "fixtures" / "lifecycle" / "retirement-cases.json"
    )
    artifact = ArtifactIdentity("config", "config/1", "1", "a" * 64, "cell")
    for case in fixture["cases"]:
        evidence = ReferenceEvidence(
            active_references=tuple(case.get("active_references", [])),
            unresolved_references=tuple(case.get("unknown_references", [])),
            current=case["current"],
            previous_supported_major=case["previous_supported_major"],
            inventory_complete=case.get("inventory_complete", True),
            horizon_until=(
                NOW - timedelta(minutes=1)
                if case.get("horizon_expired", False)
                else NOW + timedelta(hours=1)
                if case.get("horizon_active", False)
                else None
            ),
        )
        decision = evaluate_candidate(artifact, evidence, now=NOW)
        if case["accepted"]:
            assert decision.eligible, case["name"]
        else:
            assert decision.reason == case["error_code"], case["name"]
