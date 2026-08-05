from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, cast

import pytest
import rfc8785

from lifecycle_gc.cleanup import (
    InvalidationEvidence,
    execute_manifest,
    execute_retirement_handoff,
)
from lifecycle_gc.domain import (
    ArtifactIdentity,
    LifecycleRejected,
    PostCleanupEvidence,
    ReferenceEvidence,
    manifest_checksum,
)
from scripts.deployment_targets import TargetViolation
from scripts.deprecation_contract import (
    build_retirement_handoff,
    parse_retirement_handoff_bytes,
    validate_deprecation_record,
    validate_retirement_handoff,
)
from scripts.migration_contract import build_migration_manifest
from scripts.release_manifest import build_release_manifest


NOW = datetime(2026, 7, 30, 12, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
NOTICE_GITHUB = b'{"channel":"github-release","version":"0.1.0"}\n'
NOTICE_INTERNAL = b'{"channel":"internal","version":"0.1.0"}\n'
NOTICE_ACK = b'{"actor":"platform-owner","version":"0.1.0"}\n'
NOTICE_GITHUB_REF = "contracts/retirement-evidence/github-release-0.1.0.json"
NOTICE_INTERNAL_REF = "contracts/retirement-evidence/internal-notice-0.1.0.json"
NOTICE_ACK_REF = "contracts/retirement-evidence/ack-platform-owner-0.1.0.json"
NOTICE_EVIDENCE = {
    NOTICE_GITHUB_REF: NOTICE_GITHUB,
    NOTICE_INTERNAL_REF: NOTICE_INTERNAL,
    NOTICE_ACK_REF: NOTICE_ACK,
}


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _deprecation(
    *, emergency: bool = False, source: str = "0.1.0"
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": "1.0.0",
        "version": source,
        "replacement_version": "2.0.0",
        "warning_behavior": "warn-only",
        "affected_consumers": ["dev/orders/reconcile"],
        "migration_guide": "docs/runbooks/platform-version-migration.md",
        "support_status": "security-emergency" if emergency else "deprecated-supported",
        "earliest_removal_major": 1,
        "owner": "platform",
        "review_at": "2026-08-30T12:00:00Z",
        "notice": {
            "github_release": "release-2.0.0",
            "internal_channel": "engineering-platform",
            "deadline": "2026-08-29T12:00:00Z",
            "support_contact": "platform-oncall",
            "rollback_guidance": "docs/runbooks/platform-version-migration.md#rollback",
        },
        "notice_tracking": {
            "publication": {
                "source_commit": COMMIT_A,
                "github_release_artifact": NOTICE_GITHUB_REF,
                "github_release_sha256": hashlib.sha256(NOTICE_GITHUB).hexdigest(),
                "internal_notice_artifact": NOTICE_INTERNAL_REF,
                "internal_notice_sha256": hashlib.sha256(NOTICE_INTERNAL).hexdigest(),
                "published_at": "2026-07-29T12:00:00Z",
            },
            "acknowledgements": [
                {
                    "actor": "platform-owner",
                    "acknowledged_at": "2026-07-29T13:00:00Z",
                    "evidence_artifact": NOTICE_ACK_REF,
                    "evidence_sha256": hashlib.sha256(NOTICE_ACK).hexdigest(),
                }
            ],
            "unresolved_exceptions": [],
        },
    }
    if emergency:
        record["emergency_exception"] = {
            "risk": "remote-code-execution",
            "compensating_control": "launch-disabled",
            "migration_path": "docs/runbooks/platform-version-migration.md",
            "approvers": ["security", "release-manager"],
            "ends_at": "2026-08-01T12:00:00Z",
        }
    return record


def _release(version: str, checksum: str, commit: str) -> dict[str, Any]:
    return build_release_manifest(
        version=version,
        source_commit=commit,
        builder_workflow_sha=COMMIT_B,
        builder_run_id="12",
        artifacts={
            "runtime": {
                "kind": "runtime",
                "reference": COMMIT_A,
                "sha256": checksum,
                "identity": _artifact(version).as_dict(),
            }
        },
        qualification={"status": "passed", "evidence_sha256": SHA_C},
        compatibility={"retained": True},
        policy_bundle_sha256=SHA_C,
        provider_lock_sha256=SHA_C,
        migration_class="major",
        known_limitations=[],
        published_at="2026-07-29T12:00:00Z",
        tested_matrix={"python": "3.14.6"},
        component_versions={"cell": "2.0.0"},
        schema_ranges={"cell": ">=1.0.0,<3.0.0"},
        publisher_oidc_actor="github-actions",
    )


def _artifact(version: str = "0.1.0") -> ArtifactIdentity:
    return ArtifactIdentity(
        "runtime", "dev-cell-process-manager", version, SHA_A, "dev-cell"
    )


def _sources(
    *, owner: str = "platform", state: str = "retired", complete: bool = True
) -> dict[str, dict[str, Any]]:
    observed = "2026-07-30T11:00:00Z"
    return {
        name: {
            "query_id": f"retirement-{name}-20260730",
            "queried_at": observed,
            "complete": complete,
            "result_count": 1,
            "records": [
                {
                    "identity": f"{name}-record",
                    "owner": owner,
                    "last_observed_at": observed,
                    "state": state,
                }
            ],
        }
        for name in (
            "cells",
            "jobs",
            "repositories",
            "config",
            "schedule_generations",
            "workflows",
            "runtimes",
            "queues_dlqs",
            "occurrences_task_attempts",
            "aliases_pointers",
            "rollback_identities",
            "documentation_support",
        )
    }


def _inventory(
    source_release: Mapping[str, Any], artifact: ArtifactIdentity, **changes: Any
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "1.0.0",
        "source_release_sha256": source_release["manifest_sha256"],
        "artifact": artifact.as_dict(),
        "sources": _sources(),
        "active_references": [],
        "unresolved_references": [],
        "horizons": {
            name: "2026-07-30T12:00:00Z"
            for name in (
                "support",
                "replay",
                "retention",
                "investigation",
                "recovery",
                "rollback",
            )
        },
        "surface_digests": {
            name: SHA_C
            for name in ("aliases", "cell_contract_ranges", "workflow_manifests")
        },
        "observed_at": "2026-07-30T11:00:00Z",
    }
    value.update(changes)
    value["inventory_sha256"] = _digest(value)
    return value


def _migration(
    source: Mapping[str, Any], target: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = build_migration_manifest(
        migration_id="migration-2",
        source_release=source["version"],
        target_release=target["version"],
        source_release_sha256=source["manifest_sha256"],
        target_release_sha256=target["manifest_sha256"],
        phase="cutover",
        horizons={
            name: 1
            for name in (
                "queue",
                "replay",
                "runtime",
                "retention",
                "investigation",
                "recovery",
                "rollback",
            )
        },
        consumers=[
            {
                "consumer_id": "dev/orders/reconcile",
                "current_identity": "release-1",
                "target_version": target["version"],
                "validation": "ready",
                "required_change": "adopt release-2",
                "owner": "platform",
                "due_at": "2026-07-29T12:00:00Z",
                "rollback_identity": "release-1",
            }
        ],
        inventory={
            "consumers": ["dev/orders/reconcile"],
            "active_generations": ["generation-2"],
            "retired_generations": ["generation-1"],
            "config_versions": ["config-2"],
            "occurrences": ["none"],
            "task_attempts": ["none"],
            "queues_dlqs": ["none"],
            "state_addresses": ["none"],
            "policies": ["none"],
            "operator_procedures": ["runbook"],
            "rollback_horizons": ["one-day"],
        },
        component_ranges={"cell": ">=1.0.0,<3.0.0"},
        required_components={"cell": "2.0.0"},
        launch_disabled=True,
        owner="platform",
        actor="github-actions",
        created_at="2026-07-29T12:00:00Z",
    )
    plan = {
        "plan_sha256": SHA_C,
        "policy_sha256": SHA_B,
        "approval_id": "migration-approval",
        "target_manifest_sha256": target["manifest_sha256"],
        "environment": "production",
        "expires_at": "2026-07-30T12:30:00Z",
        "migration_id": "migration-2",
        "source_commit": source["source_commit"],
    }
    phase_evidence = {
        "migration_id": "migration-2",
        "phase": "cutover",
        "operation_id": "op-2",
        "status": "verified",
        "checkpoint_id": "checkpoint-2",
        "resumed": False,
        "source_count": 0,
        "target_count": 0,
        "source_checksum": SHA_A,
        "target_checksum": SHA_A,
        "observed_at": "2026-07-30T11:00:00Z",
        "verified_at": "2026-07-30T11:30:00Z",
        "source_release_sha256": source["manifest_sha256"],
        "target_release_sha256": target["manifest_sha256"],
        "source_schema_sha256": SHA_A,
        "target_schema_sha256": SHA_A,
        "access_pattern_sha256": SHA_A,
        "reducer_invariants_passed": True,
        "launch_disabled": True,
        "empty_scope_justification": "no retained records",
    }
    acknowledgement = {
        "migration_id": "migration-2",
        "target_release": target["version"],
        "target_release_sha256": target["manifest_sha256"],
        "horizon_watermark": manifest["compatibility_horizon"],
        "acknowledged_at": "2026-07-30T11:45:00Z",
        "issued_at": "2026-07-30T11:40:00Z",
        "expires_at": "2026-07-30T12:30:00Z",
        "actor": "github-actions",
        "plan_sha256": SHA_C,
    }
    completion: dict[str, Any] = {
        "schema_version": "1.0.0",
        "manifest": manifest,
        "phase_evidence": phase_evidence,
        "acknowledgement": acknowledgement,
        "plan": plan,
    }
    completion["completion_sha256"] = _digest(completion)
    return completion, plan


def _evidence(
    *,
    source_version: str = "0.1.0",
    emergency: bool = False,
    inventory_changes: Mapping[str, Any] | None = None,
    policy_expires_at: str = "2026-07-30T12:30:00Z",
    withdrawal_surfaces: list[str] | None = None,
    earliest_removal_major: int = 1,
) -> dict[str, Any]:
    source, target, artifact = (
        _release(source_version, SHA_A, COMMIT_A),
        _release("2.0.0", SHA_B, COMMIT_B),
        _artifact(source_version),
    )
    inventory = _inventory(source, artifact, **dict(inventory_changes or {}))
    completion, plan = _migration(source, target)
    policy: dict[str, Any] = {
        "schema_version": "1.0.0",
        "status": "passed",
        "plan_sha256": plan["plan_sha256"],
        "policy_sha256": plan["policy_sha256"],
        "source_commit": source["source_commit"],
        "evaluated_at": "2026-07-30T11:50:00Z",
        "expires_at": policy_expires_at,
    }
    policy["decision_sha256"] = _digest(policy)
    withdrawal: dict[str, Any] = {
        "schema_version": "1.0.0",
        "source_commit": source["source_commit"],
        "workflow_sha": COMMIT_A,
        "plan_sha256": plan["plan_sha256"],
        "status": "withdrawn",
        "surfaces": withdrawal_surfaces
        or sorted(
            {
                "aliases",
                "cell_contract_ranges",
                "workflow_manifests",
                "documentation",
                "support_metadata",
            }
        ),
        "observed_at": "2026-07-30T11:55:00Z",
        "expires_at": policy_expires_at,
    }
    withdrawal["withdrawal_sha256"] = _digest(withdrawal)
    approval: dict[str, Any] = {
        "schema_version": "1.0.0",
        "approval_id": "retirement-approval",
        "status": "approved",
        "source_commit": source["source_commit"],
        "workflow_sha": COMMIT_B,
        "plan_sha256": plan["plan_sha256"],
        "policy_sha256": plan["policy_sha256"],
        "inventory_sha256": inventory["inventory_sha256"],
        "migration_sha256": completion["completion_sha256"],
        "approvers": [
            {
                "role": "platform",
                "actor": "platform-reviewer",
                "approved_at": "2026-07-30T11:58:00Z",
            },
            {
                "role": "job-owner",
                "actor": "job-reviewer",
                "approved_at": "2026-07-30T11:59:00Z",
            },
        ],
        "approved_at": "2026-07-30T11:59:00Z",
        "expires_at": policy_expires_at,
    }
    approval["approval_sha256"] = _digest(approval)
    return {
        "deprecation": {
            **_deprecation(emergency=emergency, source=source_version),
            "earliest_removal_major": earliest_removal_major,
        },
        "source_release": source,
        "target_release": target,
        "artifact": artifact,
        "inventory": inventory,
        "migration_completion": completion,
        "policy_decision": policy,
        "protected_approval": approval,
        "advertisement_withdrawal": withdrawal,
    }


def _handoff(**kwargs: Any) -> dict[str, object]:
    evidence = _evidence(**kwargs)
    return build_retirement_handoff(
        **evidence,
        manifest_id="retire-runtime-0.1.0",
        account_id="123456789012",
        region="us-east-1",
        environment="dev",
        now=NOW,
        notice_evidence_reader=NOTICE_EVIDENCE.__getitem__,
    )


def _post_cleanup(_: ArtifactIdentity, __: object) -> PostCleanupEvidence:
    return PostCleanupEvidence(True, True, True, True, True, True, True)


def _handoff_bytes(handoff: Mapping[str, object]) -> bytes:
    return json.dumps(handoff, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _submission(handoff: Mapping[str, object]) -> dict[str, object]:
    raw = _handoff_bytes(handoff)
    approval = cast(Mapping[str, object], handoff["protected_approval"])
    return {
        "handoff_sha256": handoff["handoff_sha256"],
        "handoff_file_sha256": hashlib.sha256(raw).hexdigest(),
        "repository_id": "1234",
        "run_id": "5678",
        "environment": "production-retirement-approval",
        "approval_sha256": approval["approval_sha256"],
        "source_commit": COMMIT_B,
        "workflow_sha": COMMIT_B,
        "status": "validated",
    }


def _invalidation(_: ArtifactIdentity, __: str) -> InvalidationEvidence:
    return InvalidationEvidence(True, True, True)


class EvidenceStore:
    def __init__(
        self,
        handoff: Mapping[str, object],
        submission: Mapping[str, object] | None = None,
    ) -> None:
        self.raw_handoff = _handoff_bytes(handoff)
        self.submission = dict(submission or _submission(handoff))

    def load_submission(self, _: str) -> tuple[bytes, Mapping[str, object]]:
        return self.raw_handoff, self.submission

    def read_notice_evidence(self, reference: str) -> bytes:
        return NOTICE_EVIDENCE[reference]


def test_deprecation_is_additive_and_notice_is_sanitized() -> None:
    validate_deprecation_record(
        _deprecation(), now=NOW, notice_evidence_reader=NOTICE_EVIDENCE.__getitem__
    )
    invalid = _deprecation()
    invalid["notice"] = {
        **cast(Mapping[str, Any], invalid["notice"]),
        "github_release": "AWS_ACCESS_KEY_ID=not-a-real",
    }
    with pytest.raises(TargetViolation, match="DEPRECATION_SENSITIVE_NOTICE"):
        validate_deprecation_record(invalid, now=NOW)
    invalid = _deprecation()
    tracking = cast(dict[str, object], invalid["notice_tracking"])
    tracking["unresolved_exceptions"] = [{"exception_id": "exception-1"}]
    with pytest.raises(TargetViolation, match="DEPRECATION_NOTICE_TRACKING"):
        validate_deprecation_record(invalid, now=NOW)


def test_strict_retirement_handoff_parser_rejects_duplicate_keys() -> None:
    with pytest.raises(TargetViolation, match="RETIREMENT_HANDOFF_JSON"):
        parse_retirement_handoff_bytes(
            b'{"schema_version":"1.0.0","schema_version":"1.0.0"}'
        )


def test_security_emergency_requires_independent_expiring_approvers() -> None:
    emergency = _deprecation(emergency=True)
    validate_deprecation_record(
        emergency, now=NOW, notice_evidence_reader=NOTICE_EVIDENCE.__getitem__
    )
    exception = cast(dict[str, object], emergency["emergency_exception"])
    exception["approvers"] = ["security", "security"]
    with pytest.raises(TargetViolation, match="DEPRECATION_EMERGENCY"):
        validate_deprecation_record(
            emergency, now=NOW, notice_evidence_reader=NOTICE_EVIDENCE.__getitem__
        )


def _fixture_handoff_kwargs(mutation: Mapping[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if "active_references" in mutation:
        kwargs["inventory_changes"] = {
            "active_references": mutation["active_references"]
        }
    if "source_owner" in mutation:
        kwargs["inventory_changes"] = {
            "sources": _sources(owner=mutation["source_owner"])
        }
    if "horizon_at" in mutation:
        kwargs["inventory_changes"] = {
            "horizons": {
                name: mutation["horizon_at"]
                for name in (
                    "support",
                    "replay",
                    "retention",
                    "investigation",
                    "recovery",
                    "rollback",
                )
            }
        }
    for key in ("policy_expires_at", "withdrawal_surfaces", "emergency"):
        if key in mutation:
            kwargs[key] = mutation[key]
    return kwargs


_RETIREMENT_FIXTURES = json.loads(
    (
        Path(__file__).resolve().parents[2]
        / "contracts/v1/fixtures/deprecation/cases.json"
    ).read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize(
    "case", _RETIREMENT_FIXTURES, ids=lambda case: str(case["name"])
)
def test_deprecation_fixture_cases_execute(case: Mapping[str, Any]) -> None:
    mutation = cast(Mapping[str, Any], case["mutation"])
    expected_error = case["expected_error"]
    execution = mutation.get("execution")
    if execution not in {
        "late_reference",
        "post_cleanup_incomplete",
        "post_cleanup_failure",
    }:
        if expected_error is not None:
            with pytest.raises(
                (TargetViolation, LifecycleRejected), match=str(expected_error)
            ):
                _handoff(**_fixture_handoff_kwargs(mutation))
            return
        validate_retirement_handoff(
            _handoff(**_fixture_handoff_kwargs(mutation)),
            now=NOW,
            notice_evidence_reader=NOTICE_EVIDENCE.__getitem__,
        )
        return

    handoff = _handoff(**_fixture_handoff_kwargs(mutation))

    class Store:
        def claim(self, *_: object) -> bool:
            return True

        def record_outcome(self, _: object) -> None:
            pass

        def record_tombstone(self, _: object) -> None:
            pass

        def record_post_cleanup(self, _: object) -> None:
            pass

        def record_deletion_intent(self, _: object) -> None:
            pass

        def record_invalidation(self, _: object) -> None:
            pass

    def clean_revalidation(_: ArtifactIdentity) -> ReferenceEvidence:
        return ReferenceEvidence(
            surface_digests=(
                ("aliases", SHA_C),
                ("cell_contract_ranges", SHA_C),
                ("workflow_manifests", SHA_C),
            ),
        )

    def late_revalidation(_: ArtifactIdentity) -> ReferenceEvidence:
        return ReferenceEvidence(
            active_references=("late-dlq",),
            surface_digests=(
                ("aliases", SHA_C),
                ("cell_contract_ranges", SHA_C),
                ("workflow_manifests", SHA_C),
            ),
        )

    def incomplete_post_cleanup(_: ArtifactIdentity, __: object) -> PostCleanupEvidence:
        return PostCleanupEvidence(True, True, False, True, True, True, True)

    def failed_post_cleanup(_: ArtifactIdentity, __: object) -> PostCleanupEvidence:
        raise RuntimeError("failed")

    post_verify = _post_cleanup
    revalidate = clean_revalidation
    if execution == "late_reference":
        revalidate = late_revalidation
    elif execution == "post_cleanup_incomplete":
        post_verify = incomplete_post_cleanup
    elif execution == "post_cleanup_failure":
        post_verify = failed_post_cleanup

    class Adapter:
        def delete(self, _: ArtifactIdentity) -> str:
            return "DELETED"

    with pytest.raises(LifecycleRejected, match=str(expected_error)):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=revalidate,
            post_verify=post_verify,
            on_invalidation=_invalidation,
            adapters={"runtime": Adapter()},
            store=Store(),
            evidence_store=EvidenceStore(handoff),
        )


def test_complete_handoff_binds_every_proof_and_reaches_only_handoff_executor() -> None:
    handoff = _handoff()
    validate_retirement_handoff(
        handoff, now=NOW, notice_evidence_reader=NOTICE_EVIDENCE.__getitem__
    )
    lifecycle = cast(Mapping[str, Any], handoff["lifecycle_manifest"])
    with pytest.raises(
        LifecycleRejected, match="LIFECYCLE_RETIREMENT_HANDOFF_REQUIRED"
    ):
        execute_manifest(
            lifecycle,
            now=NOW,
            inventory_digest=str(
                cast(Mapping[str, object], handoff["inventory"])["inventory_sha256"]
            ),
            approved=True,
            dry_run=False,
            revalidate=lambda _artifact: ReferenceEvidence(),
            adapters={},
            store=cast(Any, object()),
        )

    class Adapter:
        def __init__(self) -> None:
            self.deleted: list[ArtifactIdentity] = []

        def delete(self, artifact: ArtifactIdentity) -> str:
            self.deleted.append(artifact)
            return "DELETED"

    class Store:
        def claim(self, *_: object) -> bool:
            return True

        def record_outcome(self, _: object) -> None:
            pass

        def record_tombstone(self, _: object) -> None:
            pass

        def record_post_cleanup(self, _: object) -> None:
            pass

        def record_deletion_intent(self, _: object) -> None:
            pass

        def record_invalidation(self, _: object) -> None:
            pass

    adapter = Adapter()
    outcome, _ = execute_retirement_handoff(
        handoff,
        now=NOW,
        revalidate=lambda _artifact: ReferenceEvidence(
            surface_digests=(
                ("aliases", SHA_C),
                ("cell_contract_ranges", SHA_C),
                ("workflow_manifests", SHA_C),
            )
        ),
        post_verify=_post_cleanup,
        on_invalidation=_invalidation,
        adapters={"runtime": adapter},
        store=Store(),
        evidence_store=EvidenceStore(handoff),
    )
    assert outcome.status == "DELETED"
    assert adapter.deleted == [_artifact()]


def test_submission_and_post_cleanup_failures_are_durable_and_fail_closed() -> None:
    handoff = _handoff()

    class Adapter:
        def delete(self, _: ArtifactIdentity) -> str:
            return "DELETED"

    class Store:
        def __init__(self) -> None:
            self.outcomes: list[object] = []
            self.verifications: list[object] = []

        def claim(self, *_: object) -> bool:
            return True

        def record_outcome(self, outcome: object) -> None:
            self.outcomes.append(outcome)

        def record_tombstone(self, _: object) -> None:
            pass

        def record_post_cleanup(self, verification: object) -> None:
            self.verifications.append(verification)

        def record_deletion_intent(self, _: object) -> None:
            pass

        def record_invalidation(self, _: object) -> None:
            pass

    submission = _submission(handoff)
    submission["handoff_file_sha256"] = SHA_A
    with pytest.raises(TargetViolation, match="RETIREMENT_SUBMISSION"):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=lambda _artifact: ReferenceEvidence(
                surface_digests=(
                    ("aliases", SHA_C),
                    ("cell_contract_ranges", SHA_C),
                    ("workflow_manifests", SHA_C),
                )
            ),
            post_verify=_post_cleanup,
            on_invalidation=_invalidation,
            adapters={"runtime": Adapter()},
            store=Store(),
            evidence_store=EvidenceStore(handoff, submission),
        )

    store = Store()
    with pytest.raises(LifecycleRejected, match="LIFECYCLE_POST_CLEANUP_FAILED"):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=lambda _artifact: ReferenceEvidence(
                surface_digests=(
                    ("aliases", SHA_C),
                    ("cell_contract_ranges", SHA_C),
                    ("workflow_manifests", SHA_C),
                )
            ),
            post_verify=lambda *_: (_ for _ in ()).throw(RuntimeError("failed")),
            on_invalidation=_invalidation,
            adapters={"runtime": Adapter()},
            store=store,
            evidence_store=EvidenceStore(handoff),
        )
    assert getattr(store.verifications[-1], "status") == "BLOCKED"
    assert getattr(store.outcomes[-1], "status") == "POST_DELETE_BLOCKED"


def test_execution_uses_the_protected_store_and_requires_completed_invalidation() -> (
    None
):
    handoff = _handoff()

    class Store:
        def __init__(self) -> None:
            self.intents: list[object] = []
            self.invalidations: list[object] = []

        def claim(self, *_: object) -> bool:
            return True

        def record_outcome(self, _: object) -> None:
            pass

        def record_tombstone(self, _: object) -> None:
            pass

        def record_post_cleanup(self, _: object) -> None:
            pass

        def record_deletion_intent(self, intent: object) -> None:
            self.intents.append(intent)

        def record_invalidation(self, invalidation: object) -> None:
            self.invalidations.append(invalidation)

    store = Store()
    with pytest.raises(LifecycleRejected, match="LIFECYCLE_INVALIDATION_INCOMPLETE"):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=lambda _: ReferenceEvidence(
                active_references=("late-reference",),
                surface_digests=(
                    ("aliases", SHA_C),
                    ("cell_contract_ranges", SHA_C),
                    ("workflow_manifests", SHA_C),
                ),
            ),
            post_verify=_post_cleanup,
            on_invalidation=lambda *_: InvalidationEvidence(True, False, True),
            adapters={},
            store=store,
            evidence_store=EvidenceStore(handoff),
        )
    assert getattr(store.invalidations[-1], "status") == "INCOMPLETE"
    assert store.intents == []

    altered = _handoff(source_version="0.2.0")
    with pytest.raises(TargetViolation, match="RETIREMENT_SUBMISSION"):
        execute_retirement_handoff(
            altered,
            now=NOW,
            revalidate=lambda _: ReferenceEvidence(),
            post_verify=_post_cleanup,
            on_invalidation=_invalidation,
            adapters={},
            store=store,
            evidence_store=EvidenceStore(handoff),
        )


def test_external_delete_with_audit_write_failure_requires_reconciliation() -> None:
    handoff = _handoff()

    class Adapter:
        def delete(self, _: ArtifactIdentity) -> str:
            return "DELETED"

    class Store:
        def __init__(self) -> None:
            self.intents: list[object] = []

        def claim(self, *_: object) -> bool:
            return True

        def record_outcome(self, _: object) -> None:
            raise RuntimeError("dynamodb unavailable")

        def record_tombstone(self, _: object) -> None:
            pass

        def record_post_cleanup(self, _: object) -> None:
            pass

        def record_deletion_intent(self, intent: object) -> None:
            self.intents.append(intent)

        def record_invalidation(self, _: object) -> None:
            pass

    store = Store()
    with pytest.raises(
        LifecycleRejected, match="LIFECYCLE_DELETE_RECONCILIATION_REQUIRED"
    ):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=lambda _: ReferenceEvidence(
                surface_digests=(
                    ("aliases", SHA_C),
                    ("cell_contract_ranges", SHA_C),
                    ("workflow_manifests", SHA_C),
                )
            ),
            post_verify=_post_cleanup,
            on_invalidation=_invalidation,
            adapters={"runtime": Adapter()},
            store=store,
            evidence_store=EvidenceStore(handoff),
        )
    assert len(store.intents) == 1


def test_tampered_evidence_and_post_cleanup_late_reference_are_rejected() -> None:
    handoff = _handoff(emergency=True)
    tampered = deepcopy(handoff)
    cast(dict[str, Any], tampered["migration_completion"])["manifest"]["phase"] = (
        "rollback"
    )
    tampered["handoff_sha256"] = _digest(
        {key: value for key, value in tampered.items() if key != "handoff_sha256"}
    )
    with pytest.raises(TargetViolation, match="RETIREMENT_MIGRATION"):
        validate_retirement_handoff(
            tampered, now=NOW, notice_evidence_reader=NOTICE_EVIDENCE.__getitem__
        )

    mismatched = deepcopy(handoff)
    lifecycle = cast(dict[str, Any], mismatched["lifecycle_manifest"])
    lifecycle["artifact"] = _artifact("2.0.0").as_dict()
    lifecycle["manifest_checksum"] = manifest_checksum(lifecycle)
    mismatched["handoff_sha256"] = _digest(
        {key: value for key, value in mismatched.items() if key != "handoff_sha256"}
    )
    with pytest.raises(TargetViolation, match="RETIREMENT_LIFECYCLE_BINDING"):
        validate_retirement_handoff(
            mismatched, now=NOW, notice_evidence_reader=NOTICE_EVIDENCE.__getitem__
        )

    class Store:
        def claim(self, *_: object) -> bool:
            return True

        def record_outcome(self, _: object) -> None:
            pass

        def record_tombstone(self, _: object) -> None:
            pass

        def record_post_cleanup(self, _: object) -> None:
            pass

        def record_deletion_intent(self, _: object) -> None:
            pass

        def record_invalidation(self, _: object) -> None:
            pass

    with pytest.raises(LifecycleRejected, match="LIFECYCLE_LATE_REFERENCE"):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=lambda _artifact: ReferenceEvidence(
                active_references=("late-dlq",),
                surface_digests=(
                    ("aliases", SHA_C),
                    ("cell_contract_ranges", SHA_C),
                    ("workflow_manifests", SHA_C),
                ),
            ),
            post_verify=_post_cleanup,
            on_invalidation=_invalidation,
            adapters={},
            store=Store(),
            evidence_store=EvidenceStore(handoff),
        )

    with pytest.raises(LifecycleRejected, match="LIFECYCLE_LATE_REFERENCE_EVIDENCE"):
        execute_retirement_handoff(
            handoff,
            now=NOW,
            revalidate=lambda _artifact: cast(ReferenceEvidence, True),
            post_verify=_post_cleanup,
            on_invalidation=_invalidation,
            adapters={},
            store=Store(),
            evidence_store=EvidenceStore(handoff),
        )


def test_retirement_workflow_uses_locked_dependencies_and_publishes_full_handoff() -> (
    None
):
    workflow = (
        Path(__file__).resolve().parents[2]
        / ".github/workflows/retire-platform-version.yml"
    ).read_text(encoding="utf-8")
    assert "astral-sh/setup-uv@" in workflow
    assert "uv sync --locked" in workflow
    assert 'PYTHONPATH="runtime/lifecycle_gc/src"' in workflow
    assert "parse_retirement_handoff_bytes(raw_handoff)" in workflow
    assert (
        'Path("validated-retirement-handoff.json").write_bytes(raw_handoff)' in workflow
    )
    assert "validated-retirement-submission.json" in workflow
