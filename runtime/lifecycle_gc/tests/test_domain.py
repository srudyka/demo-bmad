from datetime import UTC, datetime, timedelta

import pytest

from lifecycle_gc.domain import (
    ArtifactIdentity,
    LifecycleRejected,
    PostCleanupEvidence,
    ReferenceEvidence,
    build_retirement_manifest,
    evaluate_candidate,
    manifest_checksum,
)
from lifecycle_gc.cleanup import execute_manifest


NOW = datetime(2026, 7, 22, 12, tzinfo=UTC)


class Store:
    def __init__(self) -> None:
        self.claimed = False
        self.outcomes: list[object] = []
        self.tombstones: list[object] = []

    def claim(self, _manifest_id: str, _artifact: ArtifactIdentity) -> bool:
        if self.claimed:
            return False
        self.claimed = True
        return True

    def record_outcome(self, outcome: object) -> None:
        self.outcomes.append(outcome)

    def record_tombstone(self, tombstone: object) -> None:
        self.tombstones.append(tombstone)

    def record_post_cleanup(self, _: object) -> None:
        pass

    def record_deletion_intent(self, _: object) -> None:
        pass

    def record_invalidation(self, _: object) -> None:
        pass


def artifact() -> ArtifactIdentity:
    return ArtifactIdentity(
        "config", "jobs/dev/job/config/1.json", "1", "a" * 64, "dev-cell", "dev/job"
    )


def test_unknown_inventory_and_references_fail_closed() -> None:
    result = evaluate_candidate(
        artifact(),
        ReferenceEvidence(unresolved_references=("queue:unknown",)),
        now=NOW,
    )
    assert not result.eligible
    assert result.reason == "LIFECYCLE_REFERENCE_UNKNOWN"
    incomplete = evaluate_candidate(
        artifact(), ReferenceEvidence(inventory_complete=False), now=NOW
    )
    assert incomplete.reason == "LIFECYCLE_INVENTORY_INCOMPLETE"


@pytest.mark.parametrize(
    ("evidence", "reason"),
    [
        (ReferenceEvidence(current=True), "LIFECYCLE_CURRENT_VERSION"),
        (
            ReferenceEvidence(previous_supported_major=True),
            "LIFECYCLE_SUPPORTED_VERSION",
        ),
        (
            ReferenceEvidence(active_references=("occurrence:1",)),
            "LIFECYCLE_REFERENCED",
        ),
        (
            ReferenceEvidence(horizon_until=NOW + timedelta(hours=1)),
            "LIFECYCLE_HORIZON_ACTIVE",
        ),
    ],
)
def test_protected_versions_are_not_eligible(
    evidence: ReferenceEvidence, reason: str
) -> None:
    result = evaluate_candidate(artifact(), evidence, now=NOW)
    assert not result.eligible
    assert result.reason == reason


def test_eligible_manifest_is_exact_and_checksum_bound() -> None:
    manifest = build_retirement_manifest(
        artifact(),
        ReferenceEvidence(
            surface_digests=(
                ("aliases", "c" * 64),
                ("cell_contract_ranges", "c" * 64),
                ("workflow_manifests", "c" * 64),
            )
        ),
        manifest_id="manifest-1",
        owner="platform",
        lifecycle_principal="dev-cell-lifecycle",
        approval_reference="change-1",
        inventory_digest="b" * 64,
        inventory_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        now=NOW,
        account_id="123456789012",
        region="test-region",
        environment="dev",
        retirement_evidence_sha256="c" * 64,
    )
    assert manifest["artifact"] == artifact().as_dict()
    assert manifest["manifest_checksum"] == manifest_checksum(manifest)
    assert manifest["dry_run"] is True


def test_wildcards_and_mutable_versions_are_rejected() -> None:
    with pytest.raises(LifecycleRejected, match="LIFECYCLE_ARTIFACT_RESOURCE"):
        ArtifactIdentity("runtime", "lambda-function:*", "1", "a" * 64, "cell")
    with pytest.raises(LifecycleRejected, match="LIFECYCLE_ARTIFACT_VERSION"):
        ArtifactIdentity("runtime", "function", "latest", "a" * 64, "cell")
    assert ArtifactIdentity("config", "object", "s3-version-id", "a" * 64, "cell")


def test_post_cleanup_evidence_requires_exact_boolean_checks() -> None:
    with pytest.raises(LifecycleRejected, match="LIFECYCLE_POST_CLEANUP_EVIDENCE"):
        PostCleanupEvidence(True, True, 1, True, True, True, True)  # type: ignore[arg-type]


def test_raw_manifest_execution_is_rejected() -> None:
    manifest = build_retirement_manifest(
        artifact(),
        ReferenceEvidence(
            surface_digests=(
                ("aliases", "c" * 64),
                ("cell_contract_ranges", "c" * 64),
                ("workflow_manifests", "c" * 64),
            )
        ),
        manifest_id="manifest-2",
        owner="platform",
        lifecycle_principal="dev-cell-lifecycle",
        approval_reference="change-2",
        inventory_digest="b" * 64,
        inventory_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        now=NOW,
        account_id="123456789012",
        region="test-region",
        environment="dev",
        dry_run=False,
        retirement_evidence_sha256="c" * 64,
    )

    with pytest.raises(
        LifecycleRejected, match="LIFECYCLE_RETIREMENT_HANDOFF_REQUIRED"
    ):
        execute_manifest(
            manifest,
            now=NOW,
            inventory_digest="b" * 64,
            approved=True,
            dry_run=False,
            revalidate=lambda _value: ReferenceEvidence(),
            adapters={},
            store=Store(),
        )


def test_raw_manifest_cannot_bypass_a_late_reference_recheck() -> None:
    manifest = build_retirement_manifest(
        artifact(),
        ReferenceEvidence(
            surface_digests=(
                ("aliases", "c" * 64),
                ("cell_contract_ranges", "c" * 64),
                ("workflow_manifests", "c" * 64),
            )
        ),
        manifest_id="manifest-3",
        owner="platform",
        lifecycle_principal="dev-cell-lifecycle",
        approval_reference="change-3",
        inventory_digest="b" * 64,
        inventory_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        now=NOW,
        account_id="123456789012",
        region="test-region",
        environment="dev",
        dry_run=False,
        retirement_evidence_sha256="c" * 64,
    )
    with pytest.raises(
        LifecycleRejected, match="LIFECYCLE_RETIREMENT_HANDOFF_REQUIRED"
    ):
        execute_manifest(
            manifest,
            now=NOW,
            inventory_digest="b" * 64,
            approved=True,
            dry_run=False,
            revalidate=lambda _: ReferenceEvidence(),
            adapters={},
            store=Store(),
        )
