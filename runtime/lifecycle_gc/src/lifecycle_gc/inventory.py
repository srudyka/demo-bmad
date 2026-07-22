"""Deterministic inventory projection for lifecycle reference proofs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Iterable, Mapping, Protocol

from .domain import ArtifactIdentity, LifecycleRejected, ReferenceEvidence


@dataclass(frozen=True)
class InventoryPage:
    """One page returned by an authoritative Cell inventory source."""

    source: str
    artifacts: tuple[ArtifactIdentity, ...]
    references: Mapping[str, tuple[str, ...]]
    unresolved: Mapping[str, tuple[str, ...]]
    horizons: Mapping[str, datetime | None]
    complete: bool = True


class InventorySource(Protocol):
    """Paginated source adapter owned by the Cell controller."""

    def pages(self) -> Iterable[InventoryPage]:
        """Yield all pages without silently truncating results."""


@dataclass(frozen=True)
class InventorySnapshot:
    digest: str
    evidence: Mapping[str, ReferenceEvidence]
    sources: tuple[str, ...]


@dataclass
class _EvidenceAccumulator:
    artifact: ArtifactIdentity
    references: set[str]
    unresolved: set[str]
    horizons: list[datetime | None]
    complete: bool


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def build_inventory(sources: Iterable[InventorySource]) -> InventorySnapshot:
    """Merge authoritative pages and fail closed on incomplete/contradictory data."""

    pages = [page for source in sources for page in source.pages()]
    pages.sort(key=lambda page: page.source)
    by_artifact: dict[str, _EvidenceAccumulator] = {}
    digest_input: list[dict[str, object]] = []
    for page in pages:
        if not page.source:
            raise LifecycleRejected("LIFECYCLE_INVENTORY_SOURCE")
        for artifact in page.artifacts:
            key = json.dumps(artifact.as_dict(), sort_keys=True, separators=(",", ":"))
            entry = by_artifact.setdefault(
                key, _EvidenceAccumulator(artifact, set(), set(), [], True)
            )
            entry.references.update(page.references.get(key, ()))
            entry.unresolved.update(page.unresolved.get(key, ()))
            entry.horizons.append(page.horizons.get(key))
            entry.complete = entry.complete and page.complete
            digest_input.append({"source": page.source, "artifact": artifact.as_dict()})
    evidence: dict[str, ReferenceEvidence] = {}
    for key, raw in by_artifact.items():
        horizons = [value for value in raw.horizons if value is not None]
        if any(value.tzinfo is None for value in horizons):
            raise LifecycleRejected("LIFECYCLE_HORIZON_TIMEZONE")
        evidence[key] = ReferenceEvidence(
            active_references=tuple(sorted(raw.references)),
            unresolved_references=tuple(sorted(raw.unresolved)),
            horizon_until=max(horizons, default=None),
            inventory_complete=raw.complete,
        )
    return InventorySnapshot(
        digest=sha256(_canonical(digest_input)).hexdigest(),
        evidence=evidence,
        sources=tuple(sorted({page.source for page in pages})),
    )
