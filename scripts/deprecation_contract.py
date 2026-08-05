"""Fail-closed deprecation, retirement evidence, and lifecycle handoff rules."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence, cast

import rfc8785
from semantic_version import Version  # type: ignore[import-untyped]

from lifecycle_gc.cleanup import validate_manifest_for_execution
from lifecycle_gc.domain import (
    ArtifactClass,
    ArtifactIdentity,
    ReferenceEvidence,
    build_retirement_manifest,
    manifest_checksum,
)
from scripts.deployment_evidence import _screen
from scripts.deployment_targets import TargetViolation
from scripts.migration_contract import (
    validate_cutover,
    validate_migration_manifest,
    validate_phase_evidence,
    validate_plan_binding,
)
from scripts.release_manifest import validate_release_manifest

_SHA256 = frozenset("0123456789abcdef")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_NOTICE_FIELDS = {
    "github_release",
    "internal_channel",
    "deadline",
    "support_contact",
    "rollback_guidance",
}
_NOTICE_PUBLICATION_FIELDS = {
    "source_commit",
    "github_release_artifact",
    "github_release_sha256",
    "internal_notice_artifact",
    "internal_notice_sha256",
    "published_at",
}
_NOTICE_ACKNOWLEDGEMENT_FIELDS = {
    "actor",
    "acknowledged_at",
    "evidence_artifact",
    "evidence_sha256",
}
_NOTICE_EXCEPTION_FIELDS = {
    "exception_id",
    "owner",
    "status",
    "recorded_at",
    "evidence_artifact",
    "evidence_sha256",
}
_DEPRECATION_FIELDS = {
    "schema_version",
    "version",
    "replacement_version",
    "warning_behavior",
    "affected_consumers",
    "migration_guide",
    "support_status",
    "earliest_removal_major",
    "owner",
    "review_at",
    "notice",
    "notice_tracking",
}
_EMERGENCY_FIELDS = {
    "risk",
    "compensating_control",
    "migration_path",
    "approvers",
    "ends_at",
}
_INVENTORY_SOURCES = frozenset(
    {
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
    }
)
_ADVERTISING_SURFACES = frozenset(
    {
        "aliases",
        "cell_contract_ranges",
        "workflow_manifests",
        "documentation",
        "support_metadata",
    }
)
_CATALOG_PATH = (
    Path(__file__).resolve().parents[1] / "contracts/v1/catalogs/deprecation.json"
)
_PACKAGE_PATH = Path(__file__).resolve().parents[1] / "contracts/releases/1.0.0.json"
_MAX_EVIDENCE_AGE = timedelta(hours=1)
_REQUIRED_SURFACE_DIGESTS = frozenset(
    {"aliases", "cell_contract_ranges", "workflow_manifests"}
)


class RetirementEvidenceStore(Protocol):
    """Read-only authority boundary for protected retirement evidence.

    Implementations are owned by the lifecycle principal and must retrieve only
    the protected-workflow artifact and immutable committed notice evidence.
    """

    def load_submission(
        self, handoff_sha256: str
    ) -> tuple[bytes, Mapping[str, object]]: ...

    def read_notice_evidence(self, reference: str) -> bytes: ...


def _load_catalog() -> Mapping[str, object]:
    try:
        catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(
            (_CATALOG_PATH.parents[2] / "manifest.json").read_text(encoding="utf-8")
        )
        expected = next(
            item["sha256"]
            for item in manifest["artifacts"]
            if item["path"] == "v1/catalogs/deprecation.json"
        )
    except (OSError, KeyError, StopIteration, TypeError, json.JSONDecodeError) as error:
        raise TargetViolation("DEPRECATION_CATALOG") from error
    if (
        not isinstance(catalog, Mapping)
        or hashlib.sha256(_CATALOG_PATH.read_bytes()).hexdigest() != expected
        or catalog.get("schema_version") != "1.0.0"
        or catalog.get("catalog_id") != "deprecation"
        or catalog.get("warning_behavior") != "warn-only"
        or catalog.get("lifecycle_principal") != "lifecycle-garbage-collection"
    ):
        raise TargetViolation("DEPRECATION_CATALOG")
    return catalog


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _sha(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _SHA256 for character in value)
    ):
        raise TargetViolation(code)
    return value


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TargetViolation(code)
    return value


def _timestamp(value: object, code: str) -> datetime:
    if not isinstance(value, str):
        raise TargetViolation(code)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TargetViolation(code) from error
    if result.tzinfo is None:
        raise TargetViolation(code)
    return result.astimezone(UTC)


def _migration_retirement_cutoff(manifest: Mapping[str, object]) -> datetime:
    horizon = manifest.get("compatibility_horizon")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
        raise TargetViolation("RETIREMENT_HORIZON_BINDING")
    return _timestamp(
        manifest.get("created_at"), "RETIREMENT_HORIZON_BINDING"
    ) + timedelta(days=horizon)


def _fresh(value: object, *, now: datetime, code: str) -> datetime:
    timestamp = _timestamp(value, code)
    current = now.astimezone(UTC)
    if timestamp > current or current - timestamp > _MAX_EVIDENCE_AGE:
        raise TargetViolation(code)
    return timestamp


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TargetViolation("RETIREMENT_HANDOFF_JSON")
        result[key] = value
    return result


def _reject_non_finite(_: str) -> None:
    raise TargetViolation("RETIREMENT_HANDOFF_JSON")


def parse_retirement_handoff_bytes(raw: bytes) -> Mapping[str, object]:
    """Parse a submitted handoff with the Compatibility Package's strict JSON rules."""

    if len(raw) > 262_144 or raw.startswith(b"\xef\xbb\xbf"):
        raise TargetViolation("RETIREMENT_HANDOFF_JSON")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TargetViolation("RETIREMENT_HANDOFF_JSON") from error
    if not isinstance(value, Mapping):
        raise TargetViolation("RETIREMENT_HANDOFF_JSON")
    return value


def _secret_safe(value: object) -> bool:
    try:
        _screen(value)
    except TargetViolation:
        return False
    if isinstance(value, Mapping):
        return all(
            not any(
                token in str(key).lower() for token in ("secret", "password", "token")
            )
            and _secret_safe(child)
            for key, child in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return all(_secret_safe(child) for child in value)
    return True


def _package_support() -> tuple[int, int | None]:
    try:
        package = json.loads(_PACKAGE_PATH.read_text(encoding="utf-8"))
        current = package["manifest_surface"]["current_major"]
        previous = package["manifest_surface"]["previous_major"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise TargetViolation("RETIREMENT_SUPPORT_POLICY") from error
    if isinstance(current, bool) or not isinstance(current, int) or current < 0:
        raise TargetViolation("RETIREMENT_SUPPORT_POLICY")
    if previous is not None and (
        isinstance(previous, bool) or not isinstance(previous, int) or previous < 0
    ):
        raise TargetViolation("RETIREMENT_SUPPORT_POLICY")
    return current, previous


def _notice_reference(value: object) -> str:
    reference = _text(value, "DEPRECATION_NOTICE_EVIDENCE")
    if (
        not reference.startswith("contracts/retirement-evidence/")
        or ".." in reference.split("/")
        or reference.endswith("/")
    ):
        raise TargetViolation("DEPRECATION_NOTICE_EVIDENCE")
    return reference


def _verify_notice_evidence(
    record: Mapping[str, object],
    *,
    reader: Callable[[str], bytes] | None,
) -> None:
    if reader is None:
        raise TargetViolation("DEPRECATION_NOTICE_EVIDENCE")
    tracking = record["notice_tracking"]
    assert isinstance(tracking, Mapping)
    publication = tracking["publication"]
    assert isinstance(publication, Mapping)
    entries: list[tuple[Mapping[str, object], str, object]] = [
        (publication, "github_release_artifact", publication["github_release_sha256"]),
        (
            publication,
            "internal_notice_artifact",
            publication["internal_notice_sha256"],
        ),
    ]
    for acknowledgement in tracking["acknowledgements"]:
        assert isinstance(acknowledgement, Mapping)
        entries.append(
            (acknowledgement, "evidence_artifact", acknowledgement["evidence_sha256"])
        )
    for exception in tracking["unresolved_exceptions"]:
        assert isinstance(exception, Mapping)
        entries.append((exception, "evidence_artifact", exception["evidence_sha256"]))
    for source, reference_field, expected in entries:
        reference = _notice_reference(source.get(reference_field))
        expected_digest = _sha(expected, "DEPRECATION_NOTICE_EVIDENCE")
        try:
            content = reader(reference)
        except Exception as error:
            raise TargetViolation("DEPRECATION_NOTICE_EVIDENCE") from error
        if (
            not isinstance(content, bytes)
            or hashlib.sha256(content).hexdigest() != expected_digest
        ):
            raise TargetViolation("DEPRECATION_NOTICE_EVIDENCE")


def validate_deprecation_record(
    record: Mapping[str, object],
    *,
    now: datetime,
    notice_evidence_reader: Callable[[str], bytes] | None = None,
) -> None:
    """Validate additive notices and time-bounded security exceptions."""
    catalog = _load_catalog()
    expected = set(_DEPRECATION_FIELDS)
    emergency = record.get("support_status") == "security-emergency"
    if emergency:
        expected.add("emergency_exception")
    if set(record) != expected or record.get("schema_version") != "1.0.0":
        raise TargetViolation("DEPRECATION_SHAPE")
    for name in ("version", "replacement_version", "migration_guide", "owner"):
        _text(record.get(name), "DEPRECATION_VALUE")
    if record["version"] == record["replacement_version"]:
        raise TargetViolation("DEPRECATION_REPLACEMENT")
    if record.get("warning_behavior") != catalog.get("warning_behavior"):
        raise TargetViolation("DEPRECATION_BEHAVIOR")
    statuses = catalog.get("supported_statuses")
    if not isinstance(statuses, list) or record.get("support_status") not in statuses:
        raise TargetViolation("DEPRECATION_SUPPORT_STATUS")
    removal_major = record.get("earliest_removal_major")
    if (
        isinstance(removal_major, bool)
        or not isinstance(removal_major, int)
        or removal_major < 1
    ):
        raise TargetViolation("DEPRECATION_REMOVAL_MAJOR")
    consumers = record.get("affected_consumers")
    if (
        not isinstance(consumers, list)
        or not consumers
        or any(not isinstance(item, str) or not item.strip() for item in consumers)
    ):
        raise TargetViolation("DEPRECATION_CONSUMERS")
    review_at = _timestamp(record.get("review_at"), "DEPRECATION_REVIEW")
    notice = record.get("notice")
    if (
        not isinstance(notice, Mapping)
        or set(notice) != _NOTICE_FIELDS
        or not _secret_safe(notice)
    ):
        raise TargetViolation("DEPRECATION_SENSITIVE_NOTICE")
    if any(
        not _text(notice.get(name), "DEPRECATION_NOTICE") for name in _NOTICE_FIELDS
    ):
        raise TargetViolation("DEPRECATION_NOTICE")
    if _timestamp(notice["deadline"], "DEPRECATION_NOTICE") >= review_at:
        raise TargetViolation("DEPRECATION_NOTICE_DEADLINE")
    tracking = record.get("notice_tracking")
    if not isinstance(tracking, Mapping) or set(tracking) != {
        "publication",
        "acknowledgements",
        "unresolved_exceptions",
    }:
        raise TargetViolation("DEPRECATION_NOTICE_TRACKING")
    publication = tracking.get("publication")
    if (
        not isinstance(publication, Mapping)
        or set(publication) != _NOTICE_PUBLICATION_FIELDS
        or not _SHA1.fullmatch(str(publication.get("source_commit")))
    ):
        raise TargetViolation("DEPRECATION_NOTICE_TRACKING")
    for field in (
        "github_release_artifact",
        "internal_notice_artifact",
        "github_release_sha256",
        "internal_notice_sha256",
    ):
        if field.endswith("_sha256"):
            _sha(publication.get(field), "DEPRECATION_NOTICE_TRACKING")
        else:
            _notice_reference(publication.get(field))
    _timestamp(publication.get("published_at"), "DEPRECATION_NOTICE_TRACKING")
    acknowledgements = tracking.get("acknowledgements")
    if not isinstance(acknowledgements, list):
        raise TargetViolation("DEPRECATION_NOTICE_TRACKING")
    for acknowledgement in acknowledgements:
        if (
            not isinstance(acknowledgement, Mapping)
            or set(acknowledgement) != _NOTICE_ACKNOWLEDGEMENT_FIELDS
        ):
            raise TargetViolation("DEPRECATION_NOTICE_TRACKING")
        _text(acknowledgement.get("actor"), "DEPRECATION_NOTICE_TRACKING")
        _timestamp(
            acknowledgement.get("acknowledged_at"), "DEPRECATION_NOTICE_TRACKING"
        )
        _notice_reference(acknowledgement.get("evidence_artifact"))
        _sha(acknowledgement.get("evidence_sha256"), "DEPRECATION_NOTICE_TRACKING")
    exceptions = tracking.get("unresolved_exceptions")
    if not isinstance(exceptions, list):
        raise TargetViolation("DEPRECATION_NOTICE_TRACKING")
    for exception in exceptions:
        if (
            not isinstance(exception, Mapping)
            or set(exception) != _NOTICE_EXCEPTION_FIELDS
            or exception.get("status") != "open"
        ):
            raise TargetViolation("DEPRECATION_NOTICE_TRACKING")
        _text(exception.get("exception_id"), "DEPRECATION_NOTICE_TRACKING")
        _text(exception.get("owner"), "DEPRECATION_NOTICE_TRACKING")
        _timestamp(exception.get("recorded_at"), "DEPRECATION_NOTICE_TRACKING")
        _notice_reference(exception.get("evidence_artifact"))
        _sha(exception.get("evidence_sha256"), "DEPRECATION_NOTICE_TRACKING")
    _verify_notice_evidence(record, reader=notice_evidence_reader)
    if emergency:
        exception = record.get("emergency_exception")
        if not isinstance(exception, Mapping) or set(exception) != _EMERGENCY_FIELDS:
            raise TargetViolation("DEPRECATION_EMERGENCY")
        if any(
            not _text(exception.get(name), "DEPRECATION_EMERGENCY")
            for name in ("risk", "compensating_control", "migration_path")
        ):
            raise TargetViolation("DEPRECATION_EMERGENCY")
        approvers = exception.get("approvers")
        if (
            not isinstance(approvers, list)
            or len(approvers) < 2
            or any(not isinstance(item, str) or not item.strip() for item in approvers)
            or len(set(approvers)) != len(approvers)
            or str(record["owner"]) in approvers
            or _timestamp(exception.get("ends_at"), "DEPRECATION_EMERGENCY")
            <= now.astimezone(UTC)
        ):
            raise TargetViolation("DEPRECATION_EMERGENCY")


def validate_retirement_inventory(
    inventory: Mapping[str, object], *, now: datetime
) -> ReferenceEvidence:
    """Verify complete, fresh, immutable retirement inventory rather than caller claims."""
    required = {
        "schema_version",
        "source_release_sha256",
        "artifact",
        "sources",
        "active_references",
        "unresolved_references",
        "horizons",
        "surface_digests",
        "observed_at",
        "inventory_sha256",
    }
    if set(inventory) != required or inventory.get("schema_version") != "1.0.0":
        raise TargetViolation("RETIREMENT_INVENTORY_SHAPE")
    unsigned = {
        key: value for key, value in inventory.items() if key != "inventory_sha256"
    }
    if inventory.get("inventory_sha256") != _digest(unsigned):
        raise TargetViolation("RETIREMENT_INVENTORY_CHECKSUM")
    _sha(inventory.get("source_release_sha256"), "RETIREMENT_INVENTORY_RELEASE")
    artifact = inventory.get("artifact")
    if not isinstance(artifact, Mapping):
        raise TargetViolation("RETIREMENT_INVENTORY_ARTIFACT")
    try:
        ArtifactIdentity(
            cast(ArtifactClass, str(artifact.get("artifact_class"))),
            str(artifact.get("resource")),
            str(artifact.get("version")),
            str(artifact.get("checksum")),
            str(artifact.get("cell_id")),
            str(artifact["job_id"]) if artifact.get("job_id") is not None else None,
        )
    except Exception as error:
        raise TargetViolation("RETIREMENT_INVENTORY_ARTIFACT") from error
    sources = inventory.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != _INVENTORY_SOURCES:
        raise TargetViolation("RETIREMENT_INVENTORY_SOURCES")
    for source, collection in sources.items():
        if not isinstance(collection, Mapping) or set(collection) != {
            "query_id",
            "queried_at",
            "complete",
            "result_count",
            "records",
        }:
            raise TargetViolation("RETIREMENT_INVENTORY_SOURCES")
        records = collection.get("records")
        if (
            not isinstance(collection.get("query_id"), str)
            or not collection["query_id"]
            or collection.get("complete") is not True
            or isinstance(collection.get("result_count"), bool)
            or not isinstance(collection.get("result_count"), int)
            or not isinstance(records, list)
            or collection["result_count"] != len(records)
        ):
            raise TargetViolation("RETIREMENT_INVENTORY_INCOMPLETE")
        _fresh(
            collection.get("queried_at"), now=now, code="RETIREMENT_INVENTORY_FRESHNESS"
        )
        for record in records:
            if not isinstance(record, Mapping) or set(record) != {
                "identity",
                "owner",
                "last_observed_at",
                "state",
            }:
                raise TargetViolation("RETIREMENT_INVENTORY_SOURCES")
            identity, owner, state = (
                record.get("identity"),
                record.get("owner"),
                record.get("state"),
            )
            if (
                not isinstance(identity, str)
                or not identity
                or "*" in identity
                or identity.lower() in {"latest", "current"}
            ):
                raise TargetViolation("RETIREMENT_INVENTORY_IDENTITY")
            if (
                not isinstance(owner, str)
                or not owner.strip()
                or owner.lower() in {"unknown", "unowned"}
            ):
                raise TargetViolation("RETIREMENT_INVENTORY_OWNER")
            if state not in {"active", "retired", "none"}:
                raise TargetViolation("RETIREMENT_INVENTORY_SOURCES")
            if state == "active":
                raise TargetViolation("RETIREMENT_INVENTORY_ACTIVE_REFERENCE")
            _fresh(
                record.get("last_observed_at"),
                now=now,
                code="RETIREMENT_INVENTORY_FRESHNESS",
            )
    active = inventory.get("active_references")
    unresolved = inventory.get("unresolved_references")
    if (
        not isinstance(active, list)
        or not isinstance(unresolved, list)
        or any(not isinstance(item, str) or not item for item in [*active, *unresolved])
    ):
        raise TargetViolation("RETIREMENT_INVENTORY_REFERENCES")
    horizons = inventory.get("horizons")
    if not isinstance(horizons, Mapping) or set(horizons) != {
        "support",
        "replay",
        "retention",
        "investigation",
        "recovery",
        "rollback",
    }:
        raise TargetViolation("RETIREMENT_HORIZON_EVIDENCE")
    maximum = max(
        _timestamp(value, "RETIREMENT_HORIZON_EVIDENCE") for value in horizons.values()
    )
    _fresh(inventory.get("observed_at"), now=now, code="RETIREMENT_INVENTORY_FRESHNESS")
    surface_digests = inventory.get("surface_digests")
    if (
        not isinstance(surface_digests, Mapping)
        or set(surface_digests) != _REQUIRED_SURFACE_DIGESTS
        or any(
            not isinstance(value, str) or not _sha(value, "RETIREMENT_SURFACE_PROOF")
            for value in surface_digests.values()
        )
    ):
        raise TargetViolation("RETIREMENT_SURFACE_PROOF")
    return ReferenceEvidence(
        active_references=tuple(sorted(set(active))),
        unresolved_references=tuple(sorted(set(unresolved))),
        horizon_until=maximum,
        inventory_complete=True,
        surface_digests=tuple(sorted(surface_digests.items())),
    )


def _validate_release_binding(
    source_release: Mapping[str, object],
    target_release: Mapping[str, object],
    artifact: ArtifactIdentity,
    inventory: Mapping[str, object],
    deprecation: Mapping[str, object],
) -> tuple[bool, bool]:
    try:
        validate_release_manifest(source_release)
        validate_release_manifest(target_release)
        source_version = Version(str(source_release["version"]))
        target_version = Version(str(target_release["version"]))
    except (TargetViolation, ValueError, KeyError, TypeError) as error:
        raise TargetViolation("RETIREMENT_RELEASE_BINDING") from error
    if (
        source_version >= target_version
        or str(deprecation["version"]) != str(source_release["version"])
        or str(deprecation["replacement_version"]) != str(target_release["version"])
        or inventory.get("source_release_sha256")
        != source_release.get("manifest_sha256")
        or artifact.version != str(source_release["version"])
    ):
        raise TargetViolation("RETIREMENT_RELEASE_BINDING")
    artifacts = source_release.get("artifacts")
    if not isinstance(artifacts, Mapping) or not any(
        isinstance(item, Mapping)
        and item.get("kind") == artifact.artifact_class
        and item.get("sha256") == artifact.checksum
        and item.get("identity") == artifact.as_dict()
        for item in artifacts.values()
    ):
        raise TargetViolation("RETIREMENT_ARTIFACT_RELEASE_BINDING")
    current, previous = _package_support()
    return (
        source_version.major == current,
        previous is not None and source_version.major == previous,
    )


def validate_migration_completion(
    completion: Mapping[str, object],
    *,
    now: datetime,
    source_release: Mapping[str, object],
    target_release: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    required = {
        "schema_version",
        "manifest",
        "phase_evidence",
        "acknowledgement",
        "plan",
        "completion_sha256",
    }
    if set(completion) != required or completion.get("schema_version") != "1.0.0":
        raise TargetViolation("RETIREMENT_MIGRATION_COMPLETION")
    unsigned = {
        key: value for key, value in completion.items() if key != "completion_sha256"
    }
    if completion.get("completion_sha256") != _digest(unsigned):
        raise TargetViolation("RETIREMENT_MIGRATION_CHECKSUM")
    manifest = completion.get("manifest")
    phase_evidence = completion.get("phase_evidence")
    acknowledgement = completion.get("acknowledgement")
    plan = completion.get("plan")
    if not all(
        isinstance(item, Mapping)
        for item in (manifest, phase_evidence, acknowledgement, plan)
    ):
        raise TargetViolation("RETIREMENT_MIGRATION_COMPLETION")
    manifest = cast(Mapping[str, Any], manifest)
    phase_evidence = cast(Mapping[str, Any], phase_evidence)
    acknowledgement = cast(Mapping[str, Any], acknowledgement)
    plan = cast(Mapping[str, Any], plan)
    try:
        validate_migration_manifest(manifest)
        if manifest.get("phase") != "cutover":
            raise TargetViolation("MIGRATION_PHASE")
        validate_phase_evidence(manifest, phase_evidence, now=now)
        validate_cutover(manifest, acknowledgement, now=now)
        validate_plan_binding(plan, manifest, now=now)
    except TargetViolation as error:
        raise TargetViolation("RETIREMENT_MIGRATION_COMPLETION") from error
    if (
        manifest.get("source_release_sha256") != source_release.get("manifest_sha256")
        or manifest.get("target_release_sha256")
        != target_release.get("manifest_sha256")
        or acknowledgement.get("plan_sha256") != plan.get("plan_sha256")
    ):
        raise TargetViolation("RETIREMENT_MIGRATION_BINDING")
    return plan, manifest


def validate_policy_decision(
    policy: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    source_release: Mapping[str, object],
    now: datetime,
) -> None:
    required = {
        "schema_version",
        "status",
        "plan_sha256",
        "policy_sha256",
        "source_commit",
        "evaluated_at",
        "expires_at",
        "decision_sha256",
    }
    if (
        set(policy) != required
        or policy.get("schema_version") != "1.0.0"
        or policy.get("status") != "passed"
    ):
        raise TargetViolation("RETIREMENT_POLICY_DECISION")
    unsigned = {key: value for key, value in policy.items() if key != "decision_sha256"}
    if policy.get("decision_sha256") != _digest(unsigned):
        raise TargetViolation("RETIREMENT_POLICY_CHECKSUM")
    for field in ("plan_sha256", "policy_sha256"):
        _sha(policy.get(field), "RETIREMENT_POLICY_DECISION")
    if (
        policy.get("plan_sha256") != plan.get("plan_sha256")
        or policy.get("policy_sha256") != plan.get("policy_sha256")
        or policy.get("source_commit") != source_release.get("source_commit")
    ):
        raise TargetViolation("RETIREMENT_POLICY_BINDING")
    source_commit = policy.get("source_commit")
    if not isinstance(source_commit, str) or not _SHA1.fullmatch(source_commit):
        raise TargetViolation("RETIREMENT_POLICY_BINDING")
    evaluated, expires = (
        _timestamp(policy.get("evaluated_at"), "RETIREMENT_POLICY_FRESHNESS"),
        _timestamp(policy.get("expires_at"), "RETIREMENT_POLICY_FRESHNESS"),
    )
    if (
        _fresh(policy.get("evaluated_at"), now=now, code="RETIREMENT_POLICY_FRESHNESS")
        < _timestamp(plan.get("expires_at"), "RETIREMENT_POLICY_FRESHNESS")
        - _MAX_EVIDENCE_AGE
        or evaluated > now.astimezone(UTC)
        or expires <= now.astimezone(UTC)
        or expires <= evaluated
    ):
        raise TargetViolation("RETIREMENT_POLICY_FRESHNESS")


def validate_protected_approval(
    approval: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    policy: Mapping[str, object],
    inventory: Mapping[str, object],
    migration: Mapping[str, object],
    owner: str,
    now: datetime,
) -> None:
    required = {
        "schema_version",
        "approval_id",
        "status",
        "source_commit",
        "workflow_sha",
        "plan_sha256",
        "policy_sha256",
        "inventory_sha256",
        "migration_sha256",
        "approvers",
        "approved_at",
        "expires_at",
        "approval_sha256",
    }
    if (
        set(approval) != required
        or approval.get("schema_version") != "1.0.0"
        or approval.get("status") != "approved"
    ):
        raise TargetViolation("RETIREMENT_APPROVAL")
    unsigned = {
        key: value for key, value in approval.items() if key != "approval_sha256"
    }
    if approval.get("approval_sha256") != _digest(unsigned):
        raise TargetViolation("RETIREMENT_APPROVAL_CHECKSUM")
    if (
        not isinstance(approval.get("approval_id"), str)
        or not approval["approval_id"]
        or not isinstance(approval.get("workflow_sha"), str)
        or not _SHA1.fullmatch(str(approval["workflow_sha"]))
    ):
        raise TargetViolation("RETIREMENT_APPROVAL")
    bindings = {
        "plan_sha256": plan.get("plan_sha256"),
        "policy_sha256": policy.get("policy_sha256"),
        "inventory_sha256": inventory.get("inventory_sha256"),
        "migration_sha256": migration.get("completion_sha256"),
        "source_commit": policy.get("source_commit"),
    }
    if any(approval.get(key) != value for key, value in bindings.items()):
        raise TargetViolation("RETIREMENT_APPROVAL_BINDING")
    approvers = approval.get("approvers")
    if not isinstance(approvers, list) or len(approvers) < 2:
        raise TargetViolation("RETIREMENT_APPROVERS")
    roles: set[str] = set()
    actors: set[str] = set()
    for item in approvers:
        if not isinstance(item, Mapping) or set(item) != {
            "role",
            "actor",
            "approved_at",
        }:
            raise TargetViolation("RETIREMENT_APPROVERS")
        role, actor = item.get("role"), item.get("actor")
        if (
            not isinstance(role, str)
            or not role
            or not isinstance(actor, str)
            or not actor
            or actor == owner
            or role in roles
            or actor in actors
        ):
            raise TargetViolation("RETIREMENT_APPROVERS")
        approver_at = _fresh(
            item.get("approved_at"), now=now, code="RETIREMENT_APPROVERS"
        )
        if approver_at > _timestamp(
            approval.get("approved_at"), "RETIREMENT_APPROVAL_FRESHNESS"
        ):
            raise TargetViolation("RETIREMENT_APPROVERS")
        roles.add(role)
        actors.add(actor)
    if not {"platform", "job-owner"}.issubset(roles):
        raise TargetViolation("RETIREMENT_APPROVERS")
    approved, expires = (
        _timestamp(approval.get("approved_at"), "RETIREMENT_APPROVAL_FRESHNESS"),
        _timestamp(approval.get("expires_at"), "RETIREMENT_APPROVAL_FRESHNESS"),
    )
    if (
        _fresh(
            approval.get("approved_at"), now=now, code="RETIREMENT_APPROVAL_FRESHNESS"
        )
        < _timestamp(policy.get("evaluated_at"), "RETIREMENT_APPROVAL_FRESHNESS")
        or approved > now.astimezone(UTC)
        or expires <= now.astimezone(UTC)
        or expires <= approved
    ):
        raise TargetViolation("RETIREMENT_APPROVAL_FRESHNESS")


def validate_advertisement_withdrawal(
    withdrawal: Mapping[str, object],
    *,
    plan: Mapping[str, object],
    policy: Mapping[str, object],
    now: datetime,
) -> None:
    required = {
        "schema_version",
        "source_commit",
        "workflow_sha",
        "plan_sha256",
        "status",
        "surfaces",
        "observed_at",
        "expires_at",
        "withdrawal_sha256",
    }
    if (
        set(withdrawal) != required
        or withdrawal.get("schema_version") != "1.0.0"
        or withdrawal.get("status") != "withdrawn"
    ):
        raise TargetViolation("RETIREMENT_WITHDRAWAL")
    unsigned = {
        key: value for key, value in withdrawal.items() if key != "withdrawal_sha256"
    }
    if withdrawal.get("withdrawal_sha256") != _digest(unsigned):
        raise TargetViolation("RETIREMENT_WITHDRAWAL_CHECKSUM")
    if (
        withdrawal.get("plan_sha256") != plan.get("plan_sha256")
        or withdrawal.get("source_commit") != policy.get("source_commit")
        or not isinstance(withdrawal.get("workflow_sha"), str)
        or not _SHA1.fullmatch(str(withdrawal["workflow_sha"]))
    ):
        raise TargetViolation("RETIREMENT_WITHDRAWAL_BINDING")
    surfaces = withdrawal.get("surfaces")
    if not isinstance(surfaces, list) or set(surfaces) != _ADVERTISING_SURFACES:
        raise TargetViolation("RETIREMENT_WITHDRAWAL_SURFACES")
    observed, expires = (
        _timestamp(withdrawal.get("observed_at"), "RETIREMENT_WITHDRAWAL_FRESHNESS"),
        _timestamp(withdrawal.get("expires_at"), "RETIREMENT_WITHDRAWAL_FRESHNESS"),
    )
    if (
        _fresh(
            withdrawal.get("observed_at"),
            now=now,
            code="RETIREMENT_WITHDRAWAL_FRESHNESS",
        )
        < _timestamp(policy.get("evaluated_at"), "RETIREMENT_WITHDRAWAL_FRESHNESS")
        or observed > now.astimezone(UTC)
        or expires <= now.astimezone(UTC)
        or expires <= observed
    ):
        raise TargetViolation("RETIREMENT_WITHDRAWAL_FRESHNESS")


def build_retirement_handoff(
    *,
    deprecation: Mapping[str, object],
    source_release: Mapping[str, object],
    target_release: Mapping[str, object],
    artifact: ArtifactIdentity,
    inventory: Mapping[str, object],
    migration_completion: Mapping[str, object],
    policy_decision: Mapping[str, object],
    protected_approval: Mapping[str, object],
    advertisement_withdrawal: Mapping[str, object],
    manifest_id: str,
    account_id: str,
    region: str,
    environment: str,
    now: datetime,
    notice_evidence_reader: Callable[[str], bytes],
) -> dict[str, object]:
    """Build the sole, non-destructive lifecycle handoff from immutable evidence."""
    validate_deprecation_record(
        deprecation, now=now, notice_evidence_reader=notice_evidence_reader
    )
    evidence = validate_retirement_inventory(inventory, now=now)
    inventory_artifact = inventory["artifact"]
    assert isinstance(inventory_artifact, Mapping)
    if artifact.as_dict() != dict(inventory_artifact):
        raise TargetViolation("RETIREMENT_INVENTORY_ARTIFACT")
    current, previous = _validate_release_binding(
        source_release, target_release, artifact, inventory, deprecation
    )
    removal_major = deprecation.get("earliest_removal_major")
    if not isinstance(removal_major, int) or isinstance(removal_major, bool):
        raise TargetViolation("RETIREMENT_REMOVAL_MAJOR")
    if _package_support()[0] < removal_major:
        raise TargetViolation("RETIREMENT_REMOVAL_MAJOR")
    evidence = ReferenceEvidence(
        evidence.active_references,
        evidence.unresolved_references,
        evidence.horizon_until,
        current,
        previous,
        True,
        evidence.surface_digests,
    )
    plan, migration_manifest = validate_migration_completion(
        migration_completion,
        now=now,
        source_release=source_release,
        target_release=target_release,
    )
    if (
        evidence.horizon_until is None
        or evidence.horizon_until < _migration_retirement_cutoff(migration_manifest)
    ):
        raise TargetViolation("RETIREMENT_HORIZON_BINDING")
    publication = deprecation["notice_tracking"]
    assert isinstance(publication, Mapping)
    publication = publication["publication"]
    assert isinstance(publication, Mapping)
    if publication.get("source_commit") != source_release.get("source_commit"):
        raise TargetViolation("RETIREMENT_NOTICE_BINDING")
    validate_policy_decision(
        policy_decision, plan=plan, source_release=source_release, now=now
    )
    validate_advertisement_withdrawal(
        advertisement_withdrawal, plan=plan, policy=policy_decision, now=now
    )
    validate_protected_approval(
        protected_approval,
        plan=plan,
        policy=policy_decision,
        inventory=inventory,
        migration=migration_completion,
        owner=str(deprecation["owner"]),
        now=now,
    )
    evidence_binding = _digest(
        {
            "deprecation": dict(deprecation),
            "source_release": dict(source_release),
            "target_release": dict(target_release),
            "inventory": dict(inventory),
            "migration_completion": dict(migration_completion),
            "policy_decision": dict(policy_decision),
            "protected_approval": dict(protected_approval),
            "advertisement_withdrawal": dict(advertisement_withdrawal),
            "artifact": artifact.as_dict(),
        }
    )
    lifecycle_manifest = build_retirement_manifest(
        artifact,
        evidence,
        manifest_id=manifest_id,
        owner=str(deprecation["owner"]),
        lifecycle_principal="lifecycle-garbage-collection",
        approval_reference=str(protected_approval["approval_id"]),
        inventory_digest=str(inventory["inventory_sha256"]),
        inventory_at=_timestamp(
            inventory["observed_at"], "RETIREMENT_INVENTORY_FRESHNESS"
        ),
        expires_at=_timestamp(
            policy_decision["expires_at"], "RETIREMENT_POLICY_FRESHNESS"
        ),
        now=now,
        account_id=account_id,
        region=region,
        environment=environment,
        expected_effects=(
            "withdraw retired-version advertising through a protected fresh plan",
            "delegate one exact artifact to lifecycle-garbage-collection",
        ),
        dry_run=False,
        retirement_evidence_sha256=evidence_binding,
    )
    handoff: dict[str, object] = {
        "schema_version": "1.0.0",
        "deprecation": dict(deprecation),
        "source_release": dict(source_release),
        "target_release": dict(target_release),
        "inventory": dict(inventory),
        "migration_completion": dict(migration_completion),
        "policy_decision": dict(policy_decision),
        "protected_approval": dict(protected_approval),
        "advertisement_withdrawal": dict(advertisement_withdrawal),
        "lifecycle_manifest": lifecycle_manifest,
    }
    handoff["handoff_sha256"] = _digest(handoff)
    return handoff


def validate_retirement_handoff(
    handoff: Mapping[str, object],
    *,
    now: datetime,
    notice_evidence_reader: Callable[[str], bytes],
) -> None:
    """Recheck every immutable cross-binding before lifecycle cleanup can execute."""
    required = {
        "schema_version",
        "deprecation",
        "source_release",
        "target_release",
        "inventory",
        "migration_completion",
        "policy_decision",
        "protected_approval",
        "advertisement_withdrawal",
        "lifecycle_manifest",
        "handoff_sha256",
    }
    if set(handoff) != required or handoff.get("schema_version") != "1.0.0":
        raise TargetViolation("RETIREMENT_HANDOFF_SHAPE")
    unsigned = {key: value for key, value in handoff.items() if key != "handoff_sha256"}
    if handoff.get("handoff_sha256") != _digest(unsigned):
        raise TargetViolation("RETIREMENT_HANDOFF_CHECKSUM")
    values = {
        key: handoff.get(key)
        for key in required - {"schema_version", "handoff_sha256", "lifecycle_manifest"}
    }
    if not all(isinstance(value, Mapping) for value in values.values()):
        raise TargetViolation("RETIREMENT_HANDOFF_SHAPE")
    deprecation, source, target, inventory = (
        values["deprecation"],
        values["source_release"],
        values["target_release"],
        values["inventory"],
    )
    migration, policy, approval, withdrawal = (
        values["migration_completion"],
        values["policy_decision"],
        values["protected_approval"],
        values["advertisement_withdrawal"],
    )
    assert all(
        isinstance(value, Mapping)
        for value in (
            deprecation,
            source,
            target,
            inventory,
            migration,
            policy,
            approval,
            withdrawal,
        )
    )
    deprecation = cast(Mapping[str, object], deprecation)
    source = cast(Mapping[str, object], source)
    target = cast(Mapping[str, object], target)
    inventory = cast(Mapping[str, object], inventory)
    migration = cast(Mapping[str, object], migration)
    policy = cast(Mapping[str, object], policy)
    approval = cast(Mapping[str, object], approval)
    withdrawal = cast(Mapping[str, object], withdrawal)
    validate_deprecation_record(
        deprecation, now=now, notice_evidence_reader=notice_evidence_reader
    )
    evidence = validate_retirement_inventory(inventory, now=now)
    raw_artifact = inventory["artifact"]
    assert isinstance(raw_artifact, Mapping)
    artifact = ArtifactIdentity(
        cast(ArtifactClass, str(raw_artifact["artifact_class"])),
        str(raw_artifact["resource"]),
        str(raw_artifact["version"]),
        str(raw_artifact["checksum"]),
        str(raw_artifact["cell_id"]),
        str(raw_artifact["job_id"]) if raw_artifact.get("job_id") is not None else None,
    )
    current, previous = _validate_release_binding(
        source, target, artifact, inventory, deprecation
    )
    removal_major = deprecation.get("earliest_removal_major")
    if not isinstance(removal_major, int) or isinstance(removal_major, bool):
        raise TargetViolation("RETIREMENT_REMOVAL_MAJOR")
    if _package_support()[0] < removal_major:
        raise TargetViolation("RETIREMENT_REMOVAL_MAJOR")
    plan, migration_manifest = validate_migration_completion(
        migration, now=now, source_release=source, target_release=target
    )
    if (
        evidence.horizon_until is None
        or evidence.horizon_until < _migration_retirement_cutoff(migration_manifest)
    ):
        raise TargetViolation("RETIREMENT_HORIZON_BINDING")
    publication = deprecation["notice_tracking"]
    assert isinstance(publication, Mapping)
    publication = publication["publication"]
    assert isinstance(publication, Mapping)
    if publication.get("source_commit") != source.get("source_commit"):
        raise TargetViolation("RETIREMENT_NOTICE_BINDING")
    validate_policy_decision(policy, plan=plan, source_release=source, now=now)
    validate_advertisement_withdrawal(withdrawal, plan=plan, policy=policy, now=now)
    validate_protected_approval(
        approval,
        plan=plan,
        policy=policy,
        inventory=inventory,
        migration=migration,
        owner=str(deprecation["owner"]),
        now=now,
    )
    lifecycle = handoff.get("lifecycle_manifest")
    if (
        not isinstance(lifecycle, Mapping)
        or lifecycle.get("lifecycle_principal") != "lifecycle-garbage-collection"
    ):
        raise TargetViolation("RETIREMENT_LIFECYCLE_PRINCIPAL")
    binding = _digest(
        {
            "deprecation": dict(deprecation),
            "source_release": dict(source),
            "target_release": dict(target),
            "inventory": dict(inventory),
            "migration_completion": dict(migration),
            "policy_decision": dict(policy),
            "protected_approval": dict(approval),
            "advertisement_withdrawal": dict(withdrawal),
            "artifact": artifact.as_dict(),
        }
    )
    if (
        lifecycle.get("retirement_evidence_sha256") != binding
        or lifecycle.get("approval_reference") != approval.get("approval_id")
        or lifecycle.get("inventory_digest") != inventory.get("inventory_sha256")
        or lifecycle.get("manifest_checksum") != manifest_checksum(lifecycle)
    ):
        raise TargetViolation("RETIREMENT_LIFECYCLE_BINDING")
    try:
        lifecycle_artifact = validate_manifest_for_execution(
            lifecycle,
            now=now,
            inventory_digest=str(inventory["inventory_sha256"]),
            approved=True,
            dry_run=False,
        )
    except Exception as error:
        raise TargetViolation("RETIREMENT_LIFECYCLE_INVALID") from error
    if lifecycle_artifact != artifact:
        raise TargetViolation("RETIREMENT_LIFECYCLE_BINDING")
    proof = lifecycle.get("reference_proof")
    if (
        not isinstance(proof, Mapping)
        or proof.get("current") is not current
        or proof.get("previous_supported_major") is not previous
        or tuple(proof.get("active_references", ())) != evidence.active_references
        or tuple(proof.get("unresolved_references", ()))
        != evidence.unresolved_references
        or proof.get("surface_digests") != dict(evidence.surface_digests)
    ):
        raise TargetViolation("RETIREMENT_LIFECYCLE_BINDING")


def validate_retirement_submission(
    handoff: Mapping[str, object],
    *,
    raw_handoff: bytes,
    submission: Mapping[str, object],
) -> None:
    """Bind lifecycle input to the exact protected-workflow submission bytes."""

    required = {
        "handoff_sha256",
        "handoff_file_sha256",
        "repository_id",
        "run_id",
        "environment",
        "approval_sha256",
        "source_commit",
        "workflow_sha",
        "status",
    }
    if (
        set(submission) != required
        or submission.get("status") != "validated"
        or submission.get("environment") != "production-retirement-approval"
        or not isinstance(submission.get("repository_id"), str)
        or not str(submission.get("repository_id")).isdigit()
        or not isinstance(submission.get("run_id"), str)
        or not str(submission.get("run_id")).isdigit()
    ):
        raise TargetViolation("RETIREMENT_SUBMISSION")
    parsed = parse_retirement_handoff_bytes(raw_handoff)
    if dict(parsed) != dict(handoff):
        raise TargetViolation("RETIREMENT_SUBMISSION")
    protected_approval = handoff.get("protected_approval")
    if not isinstance(protected_approval, Mapping):
        raise TargetViolation("RETIREMENT_SUBMISSION")
    if (
        submission.get("handoff_sha256") != handoff.get("handoff_sha256")
        or submission.get("handoff_file_sha256")
        != hashlib.sha256(raw_handoff).hexdigest()
        or submission.get("approval_sha256")
        != protected_approval.get("approval_sha256")
        or not _SHA1.fullmatch(str(submission.get("source_commit")))
        or not _SHA1.fullmatch(str(submission.get("workflow_sha")))
    ):
        raise TargetViolation("RETIREMENT_SUBMISSION")
