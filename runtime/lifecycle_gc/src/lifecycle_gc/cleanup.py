"""Exact, bounded cleanup execution boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Protocol

from .domain import (
    ArtifactClass,
    ArtifactIdentity,
    LifecycleRejected,
    ReferenceEvidence,
    manifest_checksum,
)


class DeleteAdapter(Protocol):
    """Adapter that deletes one exact, already-authorized artifact."""

    def delete(self, artifact: ArtifactIdentity) -> str:
        """Return ``DELETED`` or idempotent ``ALREADY_ABSENT``."""


class CleanupStore(Protocol):
    """Durable conditional lifecycle evidence store."""

    def claim(self, manifest_id: str, artifact: ArtifactIdentity) -> bool: ...

    def record_outcome(self, outcome: "DeletionOutcome") -> None: ...

    def record_tombstone(self, tombstone: "Tombstone") -> None: ...


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
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": {"S": outcome.status}},
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


def execute_manifest(
    manifest: Mapping[str, object],
    *,
    now: datetime,
    inventory_digest: str,
    approved: bool,
    dry_run: bool,
    revalidate: Callable[[ArtifactIdentity], "ReferenceEvidence | bool"],
    adapters: Mapping[ArtifactClass, DeleteAdapter],
    store: CleanupStore,
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
    if isinstance(live_evidence, bool):
        eligible = live_evidence
    else:
        from .domain import evaluate_candidate

        eligible = evaluate_candidate(artifact, live_evidence, now=now).eligible
    if not eligible:
        store.record_outcome(
            DeletionOutcome(
                str(manifest["manifest_id"]),
                artifact,
                "BLOCKED",
                "LIFECYCLE_LATE_REFERENCE",
            )
        )
        raise LifecycleRejected("LIFECYCLE_LATE_REFERENCE")
    adapter = adapters.get(artifact.artifact_class)
    if adapter is None:
        raise LifecycleRejected("LIFECYCLE_ADAPTER_MISSING")
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
    checksum = manifest["manifest_checksum"]
    if not isinstance(checksum, str):
        raise LifecycleRejected("LIFECYCLE_MANIFEST_CHECKSUM")
    result = DeletionOutcome(str(manifest["manifest_id"]), artifact, status)
    tombstone = Tombstone(
        manifest_id=str(manifest["manifest_id"]),
        manifest_checksum=checksum,
        artifact=artifact,
        actor=str(manifest["lifecycle_principal"]),
        deleted_at=_utc(now),
        result=status,
    )
    store.record_outcome(result)
    store.record_tombstone(tombstone)
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
