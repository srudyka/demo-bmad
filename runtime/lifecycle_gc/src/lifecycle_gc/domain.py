"""Pure lifecycle inventory, proof, and manifest rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, Mapping

ArtifactClass = Literal[
    "config",
    "task-definition",
    "schema",
    "runtime",
    "contract",
    "deployment",
]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ARTIFACT_CLASSES: frozenset[str] = frozenset(
    {"config", "task-definition", "schema", "runtime", "contract", "deployment"}
)


class LifecycleRejected(ValueError):
    """A secret-safe, deterministic lifecycle rejection."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ArtifactIdentity:
    artifact_class: ArtifactClass
    resource: str
    version: str
    checksum: str
    cell_id: str
    job_id: str | None = None

    def __post_init__(self) -> None:
        if self.artifact_class not in _ARTIFACT_CLASSES:
            raise LifecycleRejected("LIFECYCLE_ARTIFACT_CLASS")
        if not self.resource or "*" in self.resource:
            raise LifecycleRejected("LIFECYCLE_ARTIFACT_RESOURCE")
        if not _VERSION.fullmatch(self.version) or self.version.lower() in {
            "latest",
            "current",
        }:
            raise LifecycleRejected("LIFECYCLE_ARTIFACT_VERSION")
        if not _SHA256.fullmatch(self.checksum):
            raise LifecycleRejected("LIFECYCLE_ARTIFACT_CHECKSUM")
        if not self.cell_id or "*" in self.cell_id:
            raise LifecycleRejected("LIFECYCLE_CELL_ID")
        if self.job_id is not None and (not self.job_id or "*" in self.job_id):
            raise LifecycleRejected("LIFECYCLE_JOB_ID")

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "artifact_class": self.artifact_class,
            "resource": self.resource,
            "version": self.version,
            "checksum": self.checksum,
            "cell_id": self.cell_id,
        }
        if self.job_id is not None:
            result["job_id"] = self.job_id
        return result


@dataclass(frozen=True)
class ReferenceEvidence:
    active_references: tuple[str, ...] = ()
    unresolved_references: tuple[str, ...] = ()
    horizon_until: datetime | None = None
    current: bool = False
    previous_supported_major: bool = False
    inventory_complete: bool = True
    surface_digests: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.horizon_until is not None and self.horizon_until.tzinfo is None:
            raise LifecycleRejected("LIFECYCLE_HORIZON_TIMEZONE")
        if len({name for name, _ in self.surface_digests}) != len(self.surface_digests):
            raise LifecycleRejected("LIFECYCLE_SURFACE_PROOF")
        if any(
            not name or not _SHA256.fullmatch(digest)
            for name, digest in self.surface_digests
        ):
            raise LifecycleRejected("LIFECYCLE_SURFACE_PROOF")


@dataclass(frozen=True)
class PostCleanupEvidence:
    consumers_verified: bool
    delayed_replay_verified: bool
    prior_major_replay_verified: bool
    rollback_identities_verified: bool
    documentation_verified: bool
    monitoring_verified: bool
    canary_verified: bool

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self.consumers_verified,
                self.delayed_replay_verified,
                self.prior_major_replay_verified,
                self.rollback_identities_verified,
                self.documentation_verified,
                self.monitoring_verified,
                self.canary_verified,
            )
        ):
            raise LifecycleRejected("LIFECYCLE_POST_CLEANUP_EVIDENCE")

    @property
    def complete(self) -> bool:
        return all(
            (
                self.consumers_verified,
                self.delayed_replay_verified,
                self.prior_major_replay_verified,
                self.rollback_identities_verified,
                self.documentation_verified,
                self.monitoring_verified,
                self.canary_verified,
            )
        )


@dataclass(frozen=True)
class CleanupDecision:
    eligible: bool
    reason: str
    maximum_horizon: datetime | None
    reference_count: int


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise LifecycleRejected("LIFECYCLE_TIMEZONE")
    return value.astimezone(UTC)


def evaluate_candidate(
    artifact: ArtifactIdentity,
    evidence: ReferenceEvidence,
    *,
    now: datetime,
) -> CleanupDecision:
    """Prove eligibility; missing evidence always blocks cleanup."""

    current = _utc(now)
    if not evidence.inventory_complete:
        return CleanupDecision(False, "LIFECYCLE_INVENTORY_INCOMPLETE", None, 0)
    if evidence.unresolved_references:
        return CleanupDecision(
            False,
            "LIFECYCLE_REFERENCE_UNKNOWN",
            evidence.horizon_until,
            len(evidence.unresolved_references),
        )
    references = tuple(sorted(set(evidence.active_references)))
    if references:
        return CleanupDecision(
            False, "LIFECYCLE_REFERENCED", evidence.horizon_until, len(references)
        )
    if evidence.current:
        return CleanupDecision(False, "LIFECYCLE_CURRENT_VERSION", None, 0)
    if evidence.previous_supported_major:
        return CleanupDecision(False, "LIFECYCLE_SUPPORTED_VERSION", None, 0)
    if evidence.horizon_until is not None and _utc(evidence.horizon_until) > current:
        return CleanupDecision(
            False, "LIFECYCLE_HORIZON_ACTIVE", _utc(evidence.horizon_until), 0
        )
    return CleanupDecision(True, "LIFECYCLE_ELIGIBLE", evidence.horizon_until, 0)


def _canonical(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def manifest_checksum(manifest: Mapping[str, object]) -> str:
    """Hash manifest content excluding its self-checksum."""

    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_checksum"
    }
    return sha256(_canonical(unsigned)).hexdigest()


def build_retirement_manifest(
    artifact: ArtifactIdentity,
    evidence: ReferenceEvidence,
    *,
    manifest_id: str,
    owner: str,
    lifecycle_principal: str,
    approval_reference: str,
    inventory_digest: str,
    inventory_at: datetime,
    expires_at: datetime,
    now: datetime,
    account_id: str,
    region: str,
    environment: str,
    support_status: str = "unsupported-candidate",
    expected_effects: tuple[str, ...] = (),
    approval_result: str = "APPROVED",
    dry_run: bool = True,
    retirement_evidence_sha256: str = "",
) -> dict[str, object]:
    """Build a checksum-bound exact retirement manifest after eligibility proof."""

    decision = evaluate_candidate(artifact, evidence, now=now)
    if not decision.eligible:
        raise LifecycleRejected(decision.reason)
    for value, code in (
        (manifest_id, "LIFECYCLE_MANIFEST_ID"),
        (owner, "LIFECYCLE_OWNER"),
        (lifecycle_principal, "LIFECYCLE_PRINCIPAL"),
        (approval_reference, "LIFECYCLE_APPROVAL"),
    ):
        if not value or "*" in value:
            raise LifecycleRejected(code)
    if not _SHA256.fullmatch(inventory_digest):
        raise LifecycleRejected("LIFECYCLE_INVENTORY_DIGEST")
    for value, code in (
        (account_id, "LIFECYCLE_ACCOUNT_ID"),
        (region, "LIFECYCLE_REGION"),
        (environment, "LIFECYCLE_ENVIRONMENT"),
    ):
        if not value or "*" in value:
            raise LifecycleRejected(code)
    if support_status != "unsupported-candidate" or approval_result != "APPROVED":
        raise LifecycleRejected("LIFECYCLE_SUPPORT_OR_APPROVAL")
    if not _SHA256.fullmatch(retirement_evidence_sha256):
        raise LifecycleRejected("LIFECYCLE_RETIREMENT_EVIDENCE")
    if set(name for name, _ in evidence.surface_digests) != {
        "aliases",
        "cell_contract_ranges",
        "workflow_manifests",
    }:
        raise LifecycleRejected("LIFECYCLE_SURFACE_PROOF")
    created = _utc(inventory_at)
    expiry = _utc(expires_at)
    current = _utc(now)
    if expiry <= current or created > current:
        raise LifecycleRejected("LIFECYCLE_MANIFEST_WINDOW")
    body: dict[str, object] = {
        "schema_version": "1.0.0",
        "manifest_id": manifest_id,
        "artifact": artifact.as_dict(),
        "owner": owner,
        "lifecycle_principal": lifecycle_principal,
        "approval_reference": approval_reference,
        "approval_result": approval_result,
        "account_id": account_id,
        "region": region,
        "environment": environment,
        "support_status": support_status,
        "expected_effects": list(expected_effects),
        "inventory_digest": inventory_digest,
        "inventory_at": created.isoformat().replace("+00:00", "Z"),
        "expires_at": expiry.isoformat().replace("+00:00", "Z"),
        "maximum_horizon": (
            decision.maximum_horizon.isoformat().replace("+00:00", "Z")
            if decision.maximum_horizon is not None
            else None
        ),
        "reference_count": decision.reference_count,
        "reference_proof": {
            "active_references": list(sorted(evidence.active_references)),
            "unresolved_references": list(sorted(evidence.unresolved_references)),
            "inventory_complete": evidence.inventory_complete,
            "current": evidence.current,
            "previous_supported_major": evidence.previous_supported_major,
            "surface_digests": dict(sorted(evidence.surface_digests)),
        },
        "dry_run": dry_run,
        "rollback_limitation": "deleted identities are not reusable",
        "preserve": ["audit", "recovery", "tombstone"],
    }
    body["retirement_evidence_sha256"] = retirement_evidence_sha256
    body["manifest_checksum"] = manifest_checksum(body)
    return body
