"""Exact, bounded cleanup execution boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Protocol

from .domain import (
    ArtifactClass,
    ArtifactIdentity,
    LifecycleRejected,
    PostCleanupEvidence,
    ReferenceEvidence,
    manifest_checksum,
)


class DeleteAdapter(Protocol):
    """Adapter that deletes one exact, already-authorized artifact."""

    def delete(self, artifact: ArtifactIdentity) -> str:
        """Return ``DELETED`` or idempotent ``ALREADY_ABSENT``."""


class RetirementEvidenceStore(Protocol):
    """Lifecycle-owned reader for protected workflow and notice artifacts."""

    def load_submission(
        self, handoff_sha256: str
    ) -> tuple[bytes, Mapping[str, object]]: ...

    def read_notice_evidence(self, reference: str) -> bytes: ...


class CleanupStore(Protocol):
    """Durable conditional lifecycle evidence store."""

    def claim(self, manifest_id: str, artifact: ArtifactIdentity) -> bool: ...

    def record_outcome(self, outcome: "DeletionOutcome") -> None: ...

    def record_tombstone(self, tombstone: "Tombstone") -> None: ...

    def record_post_cleanup(self, verification: "PostCleanupRecord") -> None: ...

    def record_deletion_intent(self, intent: "DeletionIntent") -> None: ...

    def record_invalidation(self, invalidation: "InvalidationRecord") -> None: ...


class DynamoCleanupStore:
    """Minimal DynamoDB-backed claim/outcome/tombstone store."""

    def __init__(self, client: Any, table_name: str, cell_id: str) -> None:
        self.client = client
        self.table_name = table_name
        self.cell_id = cell_id

    def _key(
        self, manifest_id: str, artifact: ArtifactIdentity
    ) -> dict[str, dict[str, str]]:
        return {
            "pk": {"S": f"LIFECYCLE#{self.cell_id}"},
            "sk": {
                "S": f"MANIFEST#{manifest_id}#{artifact.artifact_class}#{artifact.version}"
            },
        }

    def claim(self, manifest_id: str, artifact: ArtifactIdentity) -> bool:
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item=self._key(manifest_id, artifact) | {"status": {"S": "CLAIMED"}},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except self.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def record_outcome(self, outcome: "DeletionOutcome") -> None:
        self.client.update_item(
            TableName=self.table_name,
            Key=self._key(outcome.manifest_id, outcome.artifact),
            UpdateExpression="SET #status = :status, #reason = :reason",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": {"S": outcome.status},
                ":reason": {"S": outcome.reason or ""},
            },
        )

    def record_tombstone(self, tombstone: "Tombstone") -> None:
        self.client.update_item(
            TableName=self.table_name,
            Key=self._key(tombstone.manifest_id, tombstone.artifact),
            UpdateExpression="SET tombstone_checksum = :checksum, deleted_at = :deleted_at",
            ExpressionAttributeValues={
                ":checksum": {"S": tombstone.manifest_checksum},
                ":deleted_at": {"S": tombstone.deleted_at.isoformat()},
            },
        )

    def record_post_cleanup(self, verification: "PostCleanupRecord") -> None:
        self.client.update_item(
            TableName=self.table_name,
            Key=self._key(verification.manifest_id, verification.artifact),
            UpdateExpression=(
                "SET post_cleanup_status = :status, post_cleanup_reason = :reason, "
                "post_cleanup_checks = :checks"
            ),
            ExpressionAttributeValues={
                ":status": {"S": verification.status},
                ":reason": {"S": verification.reason or ""},
                ":checks": {
                    "M": {
                        name: {"BOOL": passed}
                        for name, passed in verification.checks.items()
                    }
                },
            },
        )

    def record_deletion_intent(self, intent: "DeletionIntent") -> None:
        self.client.update_item(
            TableName=self.table_name,
            Key=self._key(intent.manifest_id, intent.artifact),
            UpdateExpression=(
                "SET deletion_intent_status = :status, "
                "deletion_manifest_checksum = :checksum, deletion_requested_at = :at"
            ),
            ExpressionAttributeValues={
                ":status": {"S": "PENDING"},
                ":checksum": {"S": intent.manifest_checksum},
                ":at": {"S": intent.requested_at.isoformat()},
            },
        )

    def record_invalidation(self, invalidation: "InvalidationRecord") -> None:
        self.client.update_item(
            TableName=self.table_name,
            Key=self._key(invalidation.manifest_id, invalidation.artifact),
            UpdateExpression=(
                "SET invalidation_status = :status, invalidation_reason = :reason, "
                "invalidation_remediation = :remediation"
            ),
            ExpressionAttributeValues={
                ":status": {"S": invalidation.status},
                ":reason": {"S": invalidation.reason},
                ":remediation": {
                    "M": {
                        name: {"BOOL": complete}
                        for name, complete in invalidation.remediation.items()
                    }
                },
            },
        )


@dataclass(frozen=True)
class DeletionOutcome:
    manifest_id: str
    artifact: ArtifactIdentity
    status: str
    reason: str | None = None


@dataclass(frozen=True)
class Tombstone:
    manifest_id: str
    manifest_checksum: str
    artifact: ArtifactIdentity
    actor: str
    deleted_at: datetime
    result: str


@dataclass(frozen=True)
class DeletionIntent:
    manifest_id: str
    manifest_checksum: str
    artifact: ArtifactIdentity
    requested_at: datetime


@dataclass(frozen=True)
class InvalidationEvidence:
    support_status_updated: bool
    communications_updated: bool
    launch_blocked: bool

    @property
    def complete(self) -> bool:
        return (
            type(self.support_status_updated) is bool
            and type(self.communications_updated) is bool
            and type(self.launch_blocked) is bool
            and self.support_status_updated
            and self.communications_updated
            and self.launch_blocked
        )


@dataclass(frozen=True)
class InvalidationRecord:
    manifest_id: str
    artifact: ArtifactIdentity
    status: str
    reason: str
    remediation: Mapping[str, bool]


@dataclass(frozen=True)
class PostCleanupRecord:
    manifest_id: str
    artifact: ArtifactIdentity
    status: str
    checks: Mapping[str, bool]
    reason: str | None = None


def _post_cleanup_record(
    manifest_id: str,
    artifact: ArtifactIdentity,
    verification: PostCleanupEvidence | None,
    *,
    status: str,
    reason: str | None = None,
) -> PostCleanupRecord:
    names = (
        "consumers_verified",
        "delayed_replay_verified",
        "prior_major_replay_verified",
        "rollback_identities_verified",
        "documentation_verified",
        "monitoring_verified",
        "canary_verified",
    )
    return PostCleanupRecord(
        manifest_id,
        artifact,
        status,
        {name: bool(getattr(verification, name, False)) for name in names},
        reason,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise LifecycleRejected("LIFECYCLE_TIMEZONE")
    return value.astimezone(UTC)


def _artifact_from_manifest(manifest: Mapping[str, object]) -> ArtifactIdentity:
    raw = manifest.get("artifact")
    if not isinstance(raw, Mapping):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_ARTIFACT")
    values = {
        key: raw.get(key)
        for key in (
            "artifact_class",
            "resource",
            "version",
            "checksum",
            "cell_id",
            "job_id",
        )
    }
    if not all(
        isinstance(values[key], str)
        for key in ("artifact_class", "resource", "version", "checksum", "cell_id")
    ):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_ARTIFACT")
    return ArtifactIdentity(
        values["artifact_class"],  # type: ignore[arg-type]
        values["resource"],  # type: ignore[arg-type]
        values["version"],  # type: ignore[arg-type]
        values["checksum"],  # type: ignore[arg-type]
        values["cell_id"],  # type: ignore[arg-type]
        values["job_id"] if isinstance(values["job_id"], str) else None,
    )


def validate_manifest_for_execution(
    manifest: Mapping[str, object],
    *,
    now: datetime,
    inventory_digest: str,
    approved: bool,
    dry_run: bool,
) -> ArtifactIdentity:
    """Validate all immutable execution gates before invoking any adapter."""

    required = (
        "manifest_id",
        "lifecycle_principal",
        "owner",
        "approval_reference",
        "approval_result",
        "account_id",
        "region",
        "environment",
        "support_status",
        "reference_proof",
        "expected_effects",
        "preserve",
        "artifact",
    )
    if any(name not in manifest for name in required):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_FIELDS")
    if manifest.get("manifest_checksum") != manifest_checksum(manifest):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_CHECKSUM")
    if manifest.get("schema_version") != "1.0.0":
        raise LifecycleRejected("LIFECYCLE_MANIFEST_SCHEMA")
    if manifest.get("inventory_digest") != inventory_digest:
        raise LifecycleRejected("LIFECYCLE_INVENTORY_CHANGED")
    if not approved:
        raise LifecycleRejected("LIFECYCLE_APPROVAL_REQUIRED")
    if manifest.get("approval_result") != "APPROVED":
        raise LifecycleRejected("LIFECYCLE_APPROVAL_REQUIRED")
    if manifest.get("support_status") != "unsupported-candidate":
        raise LifecycleRejected("LIFECYCLE_SUPPORTED_VERSION")
    expected_effects = manifest.get("expected_effects")
    if not isinstance(expected_effects, list) or not all(
        isinstance(effect, str) and effect for effect in expected_effects
    ):
        raise LifecycleRejected("LIFECYCLE_EXPECTED_EFFECTS")
    proof = manifest.get("reference_proof")
    if not isinstance(proof, Mapping) or proof.get("inventory_complete") is not True:
        raise LifecycleRejected("LIFECYCLE_INVENTORY_INCOMPLETE")
    if dry_run or manifest.get("dry_run") is True:
        raise LifecycleRejected("LIFECYCLE_DRY_RUN")
    expires_at = manifest.get("expires_at")
    if not isinstance(expires_at, str):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_EXPIRY")
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise LifecycleRejected("LIFECYCLE_MANIFEST_EXPIRY") from error
    if _utc(expiry) <= _utc(now):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_EXPIRED")
    if not isinstance(manifest.get("manifest_id"), str) or not manifest["manifest_id"]:
        raise LifecycleRejected("LIFECYCLE_MANIFEST_ID")
    if (
        not isinstance(manifest.get("lifecycle_principal"), str)
        or not manifest["lifecycle_principal"]
    ):
        raise LifecycleRejected("LIFECYCLE_PRINCIPAL")
    return _artifact_from_manifest(manifest)


def _execute_manifest(
    manifest: Mapping[str, object],
    *,
    now: datetime,
    inventory_digest: str,
    approved: bool,
    dry_run: bool,
    revalidate: Callable[[ArtifactIdentity], ReferenceEvidence],
    adapters: Mapping[ArtifactClass, DeleteAdapter],
    store: CleanupStore,
    on_invalidation: Callable[[ArtifactIdentity, str], InvalidationEvidence],
) -> tuple[DeletionOutcome, Tombstone]:
    """Revalidate immediately before one exact destructive operation."""

    artifact = validate_manifest_for_execution(
        manifest,
        now=now,
        inventory_digest=inventory_digest,
        approved=approved,
        dry_run=dry_run,
    )
    if not store.claim(str(manifest["manifest_id"]), artifact):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_ALREADY_CLAIMED")
    live_evidence = revalidate(artifact)
    if not isinstance(live_evidence, ReferenceEvidence):
        raise LifecycleRejected("LIFECYCLE_LATE_REFERENCE_EVIDENCE")
    from .domain import evaluate_candidate

    expected_proof = manifest.get("reference_proof")
    expected_surfaces = (
        expected_proof.get("surface_digests")
        if isinstance(expected_proof, Mapping)
        else None
    )

    def invalidate(reason: str) -> None:
        try:
            remediation = on_invalidation(artifact, reason)
        except Exception as error:
            store.record_invalidation(
                InvalidationRecord(
                    str(manifest["manifest_id"]),
                    artifact,
                    "FAILED",
                    reason,
                    {},
                )
            )
            raise LifecycleRejected("LIFECYCLE_INVALIDATION_HANDLER_FAILED") from error
        checks = {
            name: bool(getattr(remediation, name, False))
            for name in (
                "support_status_updated",
                "communications_updated",
                "launch_blocked",
            )
        }
        complete = (
            isinstance(remediation, InvalidationEvidence) and remediation.complete
        )
        store.record_invalidation(
            InvalidationRecord(
                str(manifest["manifest_id"]),
                artifact,
                "COMPLETED" if complete else "INCOMPLETE",
                reason,
                checks,
            )
        )
        if not complete:
            raise LifecycleRejected("LIFECYCLE_INVALIDATION_INCOMPLETE")

    if not isinstance(expected_surfaces, Mapping) or dict(
        live_evidence.surface_digests
    ) != dict(expected_surfaces):
        reason = "LIFECYCLE_LATE_SURFACE_CHANGE"
        store.record_outcome(
            DeletionOutcome(str(manifest["manifest_id"]), artifact, "BLOCKED", reason)
        )
        invalidate(reason)
        raise LifecycleRejected("LIFECYCLE_LATE_SURFACE_CHANGE")

    eligible = evaluate_candidate(artifact, live_evidence, now=now).eligible
    if not eligible:
        reason = "LIFECYCLE_LATE_REFERENCE"
        store.record_outcome(
            DeletionOutcome(str(manifest["manifest_id"]), artifact, "BLOCKED", reason)
        )
        invalidate(reason)
        raise LifecycleRejected("LIFECYCLE_LATE_REFERENCE")
    adapter = adapters.get(artifact.artifact_class)
    if adapter is None:
        raise LifecycleRejected("LIFECYCLE_ADAPTER_MISSING")
    checksum = manifest["manifest_checksum"]
    if not isinstance(checksum, str):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_CHECKSUM")
    store.record_deletion_intent(
        DeletionIntent(str(manifest["manifest_id"]), checksum, artifact, _utc(now))
    )
    try:
        status = adapter.delete(artifact)
    except Exception as error:
        outcome = DeletionOutcome(
            str(manifest["manifest_id"]), artifact, "FAILED", "LIFECYCLE_DELETE_FAILED"
        )
        store.record_outcome(outcome)
        raise LifecycleRejected("LIFECYCLE_DELETE_FAILED") from error
    if status not in {"DELETED", "ALREADY_ABSENT"}:
        store.record_outcome(
            DeletionOutcome(
                str(manifest["manifest_id"]),
                artifact,
                "FAILED",
                "LIFECYCLE_DELETE_RESULT",
            )
        )
        raise LifecycleRejected("LIFECYCLE_DELETE_RESULT")
    result = DeletionOutcome(str(manifest["manifest_id"]), artifact, status)
    tombstone = Tombstone(
        manifest_id=str(manifest["manifest_id"]),
        manifest_checksum=checksum,
        artifact=artifact,
        actor=str(manifest["lifecycle_principal"]),
        deleted_at=_utc(now),
        result=status,
    )
    try:
        store.record_outcome(result)
        store.record_tombstone(tombstone)
    except Exception as error:
        # The durable pending intent permits exact post-delete reconciliation.
        raise LifecycleRejected("LIFECYCLE_DELETE_RECONCILIATION_REQUIRED") from error
    return result, tombstone


def execute_manifest(
    manifest: Mapping[str, object],
    *,
    now: datetime,
    inventory_digest: str,
    approved: bool,
    dry_run: bool,
    revalidate: Callable[[ArtifactIdentity], ReferenceEvidence],
    adapters: Mapping[ArtifactClass, DeleteAdapter],
    store: CleanupStore,
) -> tuple[DeletionOutcome, Tombstone]:
    """Reject raw-manifest execution.

    Retirement can reach a delete adapter only through
    :func:`execute_retirement_handoff`, which validates its complete immutable
    deprecation, migration, inventory, plan, approval, and withdrawal proof.
    The retained signature makes accidental callers fail closed rather than
    silently acquiring a second destructive execution path.
    """
    del manifest, now, inventory_digest, approved, dry_run, revalidate, adapters, store
    raise LifecycleRejected("LIFECYCLE_RETIREMENT_HANDOFF_REQUIRED")


def execute_retirement_handoff(
    handoff: Mapping[str, object],
    *,
    now: datetime,
    revalidate: Callable[[ArtifactIdentity], ReferenceEvidence],
    post_verify: Callable[[ArtifactIdentity, Tombstone], PostCleanupEvidence],
    on_invalidation: Callable[[ArtifactIdentity, str], InvalidationEvidence],
    adapters: Mapping[ArtifactClass, DeleteAdapter],
    store: CleanupStore,
    evidence_store: "RetirementEvidenceStore",
) -> tuple[DeletionOutcome, Tombstone]:
    """Execute only a Story 3.9-validated retirement handoff.

    The import is local to keep the lifecycle package free of an import cycle:
    the handoff builder already imports lifecycle primitives.
    """
    from scripts.deprecation_contract import (
        validate_retirement_handoff,
        validate_retirement_submission,
    )

    stored_raw_handoff, submission = evidence_store.load_submission(
        str(handoff.get("handoff_sha256", ""))
    )
    validate_retirement_handoff(
        handoff, now=now, notice_evidence_reader=evidence_store.read_notice_evidence
    )
    validate_retirement_submission(
        handoff, raw_handoff=stored_raw_handoff, submission=submission
    )
    manifest = handoff.get("lifecycle_manifest")
    if not isinstance(manifest, Mapping):
        raise LifecycleRejected("LIFECYCLE_HANDOFF_MANIFEST")
    inventory = handoff.get("inventory")
    if not isinstance(inventory, Mapping) or not isinstance(
        inventory.get("inventory_sha256"), str
    ):
        raise LifecycleRejected("LIFECYCLE_HANDOFF_INVENTORY")
    result, tombstone = _execute_manifest(
        manifest,
        now=now,
        inventory_digest=inventory["inventory_sha256"],
        approved=True,
        dry_run=False,
        revalidate=revalidate,
        adapters=adapters,
        store=store,
        on_invalidation=on_invalidation,
    )
    try:
        verification = post_verify(result.artifact, tombstone)
    except Exception as error:
        store.record_post_cleanup(
            _post_cleanup_record(
                result.manifest_id,
                result.artifact,
                None,
                status="BLOCKED",
                reason="LIFECYCLE_POST_CLEANUP_FAILED",
            )
        )
        store.record_outcome(
            DeletionOutcome(
                result.manifest_id,
                result.artifact,
                "POST_DELETE_BLOCKED",
                "LIFECYCLE_POST_CLEANUP_FAILED",
            )
        )
        raise LifecycleRejected("LIFECYCLE_POST_CLEANUP_FAILED") from error
    if not isinstance(verification, PostCleanupEvidence) or not verification.complete:
        store.record_post_cleanup(
            _post_cleanup_record(
                result.manifest_id,
                result.artifact,
                verification if isinstance(verification, PostCleanupEvidence) else None,
                status="BLOCKED",
                reason="LIFECYCLE_POST_CLEANUP_INCOMPLETE",
            )
        )
        store.record_outcome(
            DeletionOutcome(
                result.manifest_id,
                result.artifact,
                "POST_DELETE_BLOCKED",
                "LIFECYCLE_POST_CLEANUP_INCOMPLETE",
            )
        )
        raise LifecycleRejected("LIFECYCLE_POST_CLEANUP_INCOMPLETE")
    store.record_post_cleanup(
        _post_cleanup_record(
            result.manifest_id,
            result.artifact,
            verification,
            status="VERIFIED",
        )
    )
    return result, tombstone


def execute_batch(
    manifests: list[Mapping[str, object]],
    *,
    max_batch_size: int,
    execute_one: Callable[[Mapping[str, object]], tuple[DeletionOutcome, Tombstone]],
) -> list[tuple[DeletionOutcome, Tombstone]]:
    """Stop at the first failure and never exceed the configured batch bound."""

    if max_batch_size < 1 or len(manifests) > max_batch_size:
        raise LifecycleRejected("LIFECYCLE_BATCH_BOUND")
    results: list[tuple[DeletionOutcome, Tombstone]] = []
    for manifest in manifests:
        results.append(execute_one(manifest))
    return results
