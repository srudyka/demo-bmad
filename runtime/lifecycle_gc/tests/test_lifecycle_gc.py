from datetime import UTC, datetime

from lifecycle_gc import ArtifactIdentity, ReferenceEvidence, evaluate_candidate


def test_lifecycle_package_exposes_fail_closed_candidate_evaluation() -> None:
    candidate = ArtifactIdentity("config", "config/1", "1", "a" * 64, "cell")
    decision = evaluate_candidate(
        candidate,
        ReferenceEvidence(active_references=("occurrence/1",)),
        now=datetime(2026, 7, 22, tzinfo=UTC),
    )
    assert decision.reason == "LIFECYCLE_REFERENCED"
    assert not decision.eligible
