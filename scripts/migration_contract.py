"""Fail-closed expand/migrate/contract validation for platform migrations."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import rfc8785
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from semantic_version import SimpleSpec, Version  # type: ignore[import-untyped]

from scripts.deployment_targets import TargetViolation

SHA256 = "0123456789abcdef"
REQUIRED_HORIZONS = (
    "queue",
    "replay",
    "runtime",
    "retention",
    "investigation",
    "recovery",
    "rollback",
)
PHASES = ("expand", "migrate", "cutover", "rollback")
PHASE_ORDER = {"expand": 0, "migrate": 1, "cutover": 2, "rollback": 3}
INVENTORY_KEYS = (
    "consumers",
    "active_generations",
    "retired_generations",
    "config_versions",
    "occurrences",
    "task_attempts",
    "queues_dlqs",
    "state_addresses",
    "policies",
    "operator_procedures",
    "rollback_horizons",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _sha(value: Any, code: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in SHA256 for char in value)
    ):
        raise TargetViolation(code)


def _text(value: Any, code: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TargetViolation(code)


def _timestamp(value: Any, code: str = "MIGRATION_TIMESTAMP") -> None:
    if not isinstance(value, str):
        raise TargetViolation(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TargetViolation(code) from error
    if parsed.tzinfo is None:
        raise TargetViolation(code)


def _schema_validate(value: Mapping[str, Any], filename: str, code: str) -> None:
    """Validate the normative local schema before semantic checks."""
    path = (
        Path(__file__).resolve().parents[1] / "contracts" / "v1" / "schemas" / filename
    )
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda e: list(e.absolute_path),
        )
    except (OSError, json.JSONDecodeError, TypeError) as error:
        raise TargetViolation("MIGRATION_SCHEMA_UNAVAILABLE") from error
    if errors:
        raise TargetViolation(code)


def calculate_compatibility_horizon(horizons: Mapping[str, Any]) -> int:
    """Return the maximum obligation and reject incomplete horizon evidence."""
    if set(horizons) != set(REQUIRED_HORIZONS):
        raise TargetViolation("MIGRATION_HORIZON_UNKNOWN")
    values: list[int] = []
    for name in REQUIRED_HORIZONS:
        value = horizons[name]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise TargetViolation("MIGRATION_HORIZON_INVALID")
        values.append(value)
    return max(values)


def validate_consumer_inventory(inventory: Sequence[Mapping[str, Any]]) -> None:
    """Require one independently attributable readiness row per consumer."""
    if not inventory:
        raise TargetViolation("MIGRATION_INVENTORY_EMPTY")
    seen: set[str] = set()
    required = {
        "consumer_id",
        "current_identity",
        "target_version",
        "validation",
        "required_change",
        "owner",
        "due_at",
        "rollback_identity",
    }
    for consumer in inventory:
        if not isinstance(consumer, Mapping) or set(consumer) != required:
            raise TargetViolation("MIGRATION_INVENTORY_SHAPE")
        consumer_id = consumer["consumer_id"]
        _text(consumer_id, "MIGRATION_CONSUMER_ID")
        if consumer_id in seen:
            raise TargetViolation("MIGRATION_CONSUMER_DUPLICATE")
        seen.add(consumer_id)
        for key in (
            "current_identity",
            "target_version",
            "required_change",
            "owner",
            "rollback_identity",
        ):
            _text(consumer[key], "MIGRATION_INVENTORY_VALUE")
        if consumer["validation"] not in {"pending", "ready", "blocked"}:
            raise TargetViolation("MIGRATION_READINESS")
        _timestamp(consumer["due_at"], "MIGRATION_DUE_AT")


def validate_inventory_scope(inventory: Mapping[str, Any]) -> None:
    if set(inventory) != set(INVENTORY_KEYS):
        raise TargetViolation("MIGRATION_INVENTORY_SCOPE")
    for key in INVENTORY_KEYS:
        values = inventory[key]
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise TargetViolation("MIGRATION_INVENTORY_SCOPE")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise TargetViolation("MIGRATION_INVENTORY_SCOPE")


def validate_component_compatibility(
    required_components: Mapping[str, str],
    target_ranges: Mapping[str, str],
) -> None:
    if not required_components or set(required_components) != set(target_ranges):
        raise TargetViolation("MIGRATION_COMPONENT_SET")
    for component, version in required_components.items():
        try:
            if not isinstance(version, str) or not isinstance(
                target_ranges[component], str
            ):
                raise ValueError
            if not SimpleSpec(target_ranges[component]).match(Version(version)):
                raise TargetViolation("MIGRATION_UNSUPPORTED_COMPONENT")
        except TargetViolation:
            raise
        except (ValueError, TypeError) as error:
            raise TargetViolation("MIGRATION_COMPONENT_VERSION") from error


def build_migration_manifest(
    *,
    migration_id: str,
    source_release: str,
    target_release: str,
    source_release_sha256: str,
    target_release_sha256: str,
    phase: str,
    horizons: Mapping[str, Any],
    consumers: Sequence[Mapping[str, Any]],
    inventory: Mapping[str, Sequence[str]] | None = None,
    component_ranges: Mapping[str, str],
    required_components: Mapping[str, str],
    launch_disabled: bool,
    owner: str,
    actor: str,
    created_at: str,
) -> dict[str, Any]:
    _text(migration_id, "MIGRATION_ID")
    _text(source_release, "MIGRATION_RELEASE")
    _text(target_release, "MIGRATION_RELEASE")
    try:
        if Version(target_release) <= Version(source_release):
            raise TargetViolation("MIGRATION_RELEASE_ORDER")
    except TargetViolation:
        raise
    except ValueError as error:
        raise TargetViolation("MIGRATION_RELEASE_VERSION") from error
    _sha(source_release_sha256, "MIGRATION_SOURCE_CHECKSUM")
    _sha(target_release_sha256, "MIGRATION_TARGET_CHECKSUM")
    if phase not in PHASES:
        raise TargetViolation("MIGRATION_PHASE")
    horizon = calculate_compatibility_horizon(horizons)
    validate_consumer_inventory(consumers)
    if inventory is None:
        raise TargetViolation("MIGRATION_INVENTORY_REQUIRED")
    inventory_scope = dict(inventory)
    validate_inventory_scope(inventory_scope)
    validate_component_compatibility(required_components, component_ranges)
    if not isinstance(launch_disabled, bool) or not launch_disabled:
        raise TargetViolation("MIGRATION_LAUNCH_MUST_BE_DISABLED")
    _text(owner, "MIGRATION_OWNER")
    _text(actor, "MIGRATION_ACTOR")
    _timestamp(created_at)
    manifest = {
        "schema_version": "1.0.0",
        "migration_id": migration_id,
        "source_release": source_release,
        "target_release": target_release,
        "source_release_sha256": source_release_sha256,
        "target_release_sha256": target_release_sha256,
        "phase": phase,
        "horizons": dict(horizons),
        "compatibility_horizon": horizon,
        "consumers": [dict(consumer) for consumer in consumers],
        "inventory": inventory_scope,
        "component_ranges": dict(component_ranges),
        "required_components": dict(required_components),
        "launch_disabled": launch_disabled,
        "owner": owner,
        "actor": actor,
        "created_at": created_at,
    }
    manifest["manifest_sha256"] = _digest(manifest)
    return manifest


def validate_migration_manifest(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "migration_id",
        "source_release",
        "target_release",
        "source_release_sha256",
        "target_release_sha256",
        "phase",
        "horizons",
        "compatibility_horizon",
        "consumers",
        "inventory",
        "component_ranges",
        "required_components",
        "launch_disabled",
        "owner",
        "actor",
        "created_at",
        "manifest_sha256",
    }
    if set(manifest) != required or manifest.get("schema_version") != "1.0.0":
        raise TargetViolation("MIGRATION_SHAPE")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if manifest["manifest_sha256"] != _digest(unsigned):
        raise TargetViolation("MIGRATION_CHECKSUM")
    if not isinstance(manifest["horizons"], Mapping):
        raise TargetViolation("MIGRATION_HORIZON_UNKNOWN")
    if (
        calculate_compatibility_horizon(manifest["horizons"])
        != manifest["compatibility_horizon"]
    ):
        raise TargetViolation("MIGRATION_HORIZON_MISMATCH")
    _text(manifest["migration_id"], "MIGRATION_ID")
    _text(manifest["source_release"], "MIGRATION_RELEASE")
    _text(manifest["target_release"], "MIGRATION_RELEASE")
    try:
        if Version(manifest["target_release"]) <= Version(manifest["source_release"]):
            raise TargetViolation("MIGRATION_RELEASE_ORDER")
    except TargetViolation:
        raise
    except (ValueError, TypeError) as error:
        raise TargetViolation("MIGRATION_RELEASE_VERSION") from error
    if manifest["phase"] not in PHASES:
        raise TargetViolation("MIGRATION_PHASE")
    _text(manifest["owner"], "MIGRATION_OWNER")
    _text(manifest["actor"], "MIGRATION_ACTOR")
    if manifest["launch_disabled"] is not True:
        raise TargetViolation("MIGRATION_LAUNCH_MUST_BE_DISABLED")
    validate_consumer_inventory(manifest["consumers"])
    if not isinstance(manifest["inventory"], Mapping):
        raise TargetViolation("MIGRATION_INVENTORY_SCOPE")
    validate_inventory_scope(manifest["inventory"])
    if set(manifest["inventory"]["consumers"]) != {
        str(item["consumer_id"]) for item in manifest["consumers"]
    }:
        raise TargetViolation("MIGRATION_INVENTORY_CONSUMERS")
    if not isinstance(manifest["component_ranges"], Mapping) or not isinstance(
        manifest["required_components"], Mapping
    ):
        raise TargetViolation("MIGRATION_COMPONENT_SET")
    validate_component_compatibility(
        manifest["required_components"], manifest["component_ranges"]
    )
    _schema_validate(manifest, "migration-manifest.schema.json", "MIGRATION_SCHEMA")
    _sha(manifest["source_release_sha256"], "MIGRATION_SOURCE_CHECKSUM")
    _sha(manifest["target_release_sha256"], "MIGRATION_TARGET_CHECKSUM")
    _timestamp(manifest["created_at"])


def validate_cutover(
    manifest: Mapping[str, Any],
    acknowledgement: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    validate_migration_manifest(manifest)
    if manifest["phase"] != "cutover":
        raise TargetViolation("MIGRATION_PHASE")
    if any(consumer["validation"] != "ready" for consumer in manifest["consumers"]):
        raise TargetViolation("MIGRATION_READINESS")
    _schema_validate(
        acknowledgement,
        "migration-acknowledgement.schema.json",
        "MIGRATION_ACKNOWLEDGEMENT_SCHEMA",
    )
    required = {
        "migration_id",
        "target_release",
        "target_release_sha256",
        "horizon_watermark",
        "acknowledged_at",
        "issued_at",
        "expires_at",
        "actor",
        "plan_sha256",
    }
    if (
        set(acknowledgement) != required
        or acknowledgement["migration_id"] != manifest["migration_id"]
    ):
        raise TargetViolation("MIGRATION_ACKNOWLEDGEMENT")
    if (
        acknowledgement["target_release"] != manifest["target_release"]
        or acknowledgement["target_release_sha256"] != manifest["target_release_sha256"]
    ):
        raise TargetViolation("MIGRATION_ACKNOWLEDGEMENT")
    if acknowledgement["horizon_watermark"] != manifest["compatibility_horizon"]:
        raise TargetViolation("MIGRATION_HORIZON_MISMATCH")
    _timestamp(acknowledgement["acknowledged_at"])
    _timestamp(acknowledgement["issued_at"])
    _timestamp(acknowledgement["expires_at"])
    if acknowledgement["actor"] != manifest["actor"]:
        raise TargetViolation("MIGRATION_ACKNOWLEDGEMENT")
    _sha(acknowledgement["plan_sha256"], "MIGRATION_ACKNOWLEDGEMENT")
    if now is not None and datetime.fromisoformat(
        acknowledgement["expires_at"].replace("Z", "+00:00")
    ).astimezone(timezone.utc) <= now.astimezone(timezone.utc):
        raise TargetViolation("MIGRATION_ACKNOWLEDGEMENT_STALE")
    if now is not None:
        issued = datetime.fromisoformat(
            acknowledgement["issued_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        acknowledged = datetime.fromisoformat(
            acknowledgement["acknowledged_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if issued > acknowledged or acknowledged > now.astimezone(timezone.utc):
            raise TargetViolation("MIGRATION_ACKNOWLEDGEMENT_STALE")


def validate_phase_evidence(
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    """Require an immutable, complete offline record before a phase is reported successful."""
    validate_migration_manifest(manifest)
    required = {
        "migration_id",
        "phase",
        "operation_id",
        "status",
        "checkpoint_id",
        "resumed",
        "source_count",
        "target_count",
        "source_checksum",
        "target_checksum",
        "observed_at",
        "verified_at",
        "source_release_sha256",
        "target_release_sha256",
        "source_schema_sha256",
        "target_schema_sha256",
        "access_pattern_sha256",
        "reducer_invariants_passed",
        "launch_disabled",
        "empty_scope_justification",
    }
    if (
        set(evidence) != required
        or evidence["migration_id"] != manifest["migration_id"]
    ):
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_SHAPE")
    if evidence["phase"] != manifest["phase"] or evidence["status"] != "verified":
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_STATUS")
    if not isinstance(evidence["resumed"], bool):
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_CHECKPOINT")
    _text(evidence["operation_id"], "MIGRATION_OPERATION_ID")
    _text(evidence["checkpoint_id"], "MIGRATION_CHECKPOINT_ID")
    if any(
        isinstance(evidence[key], bool)
        or not isinstance(evidence[key], int)
        or evidence[key] < 0
        for key in ("source_count", "target_count")
    ):
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_COUNTS")
    if evidence["source_count"] != evidence["target_count"]:
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_COUNTS")
    if evidence["source_count"] == 0:
        _text(evidence["empty_scope_justification"], "MIGRATION_PHASE_EVIDENCE_SCOPE")
    elif evidence["empty_scope_justification"] != "":
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_SCOPE")
    if (
        evidence["source_release_sha256"] != manifest["source_release_sha256"]
        or evidence["target_release_sha256"] != manifest["target_release_sha256"]
    ):
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_RELEASE")
    _sha(evidence["source_schema_sha256"], "MIGRATION_PHASE_EVIDENCE_SCHEMA")
    _sha(evidence["target_schema_sha256"], "MIGRATION_PHASE_EVIDENCE_SCHEMA")
    _sha(evidence["access_pattern_sha256"], "MIGRATION_PHASE_EVIDENCE_ACCESS")
    if (
        evidence["source_schema_sha256"] != evidence["target_schema_sha256"]
        or evidence["reducer_invariants_passed"] is not True
        or evidence["launch_disabled"] is not True
    ):
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_SAFETY")
    _sha(evidence["source_checksum"], "MIGRATION_PHASE_EVIDENCE_CHECKSUM")
    _sha(evidence["target_checksum"], "MIGRATION_PHASE_EVIDENCE_CHECKSUM")
    if evidence["source_checksum"] != evidence["target_checksum"]:
        raise TargetViolation("MIGRATION_PHASE_EVIDENCE_CHECKSUM")
    _timestamp(evidence["observed_at"], "MIGRATION_PHASE_EVIDENCE_TIMESTAMP")
    _timestamp(evidence["verified_at"], "MIGRATION_PHASE_EVIDENCE_TIMESTAMP")
    if now is not None:
        expiry = datetime.fromisoformat(
            str(manifest["created_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        observed = datetime.fromisoformat(
            str(evidence["observed_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        verified = datetime.fromisoformat(
            str(evidence["verified_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if (
            observed < expiry
            or observed > verified
            or verified > now.astimezone(timezone.utc)
        ):
            raise TargetViolation("MIGRATION_PHASE_EVIDENCE_FRESHNESS")


def validate_predecessor_evidence(
    manifest: Mapping[str, Any], predecessor: Mapping[str, Any] | None
) -> None:
    """Require the immediately preceding verified phase for a state transition."""
    expected = {"migrate": "expand", "cutover": "migrate", "rollback": "cutover"}.get(
        str(manifest["phase"])
    )
    if expected is None:
        return
    if (
        predecessor is None
        or predecessor.get("migration_id") != manifest["migration_id"]
    ):
        raise TargetViolation("MIGRATION_PREDECESSOR_REQUIRED")
    if predecessor.get("phase") != expected or predecessor.get("status") != "verified":
        raise TargetViolation("MIGRATION_PHASE_ORDER")
    _text(predecessor.get("operation_id"), "MIGRATION_OPERATION_ID")
    _text(predecessor.get("manifest_sha256"), "MIGRATION_PREDECESSOR_BINDING")
    _sha(predecessor["manifest_sha256"], "MIGRATION_PREDECESSOR_BINDING")


def validate_phase_state(
    state: Mapping[str, Any], manifest: Mapping[str, Any], operation_id: str
) -> None:
    """Reject duplicate operations and non-monotonic phase state."""
    required = {"migration_id", "manifest_sha256", "completed_phases", "operation_ids"}
    if (
        set(state) != required
        or state["migration_id"] != manifest["migration_id"]
        or state["manifest_sha256"] != manifest["manifest_sha256"]
    ):
        raise TargetViolation("MIGRATION_STATE_BINDING")
    if not isinstance(state["completed_phases"], list) or not isinstance(
        state["operation_ids"], list
    ):
        raise TargetViolation("MIGRATION_STATE_SHAPE")
    if len(set(state["completed_phases"])) != len(state["completed_phases"]) or len(
        set(state["operation_ids"])
    ) != len(state["operation_ids"]):
        raise TargetViolation("MIGRATION_STATE_DUPLICATE")
    if operation_id in state["operation_ids"]:
        raise TargetViolation("MIGRATION_OPERATION_DUPLICATE")
    expected = {
        "expand": [],
        "migrate": ["expand"],
        "cutover": ["expand", "migrate"],
        "rollback": ["expand", "migrate", "cutover"],
    }[manifest["phase"]]
    if any(phase not in state["completed_phases"] for phase in expected):
        raise TargetViolation("MIGRATION_STATE_ORDER")


def validate_plan_binding(
    plan: Mapping[str, Any], manifest: Mapping[str, Any], *, now: datetime | None = None
) -> None:
    """Bind cutover to a fresh, reviewed, target-specific plan decision."""
    required = {
        "plan_sha256",
        "policy_sha256",
        "approval_id",
        "target_manifest_sha256",
        "environment",
        "expires_at",
        "migration_id",
        "source_commit",
    }
    if (
        set(plan) != required
        or plan.get("environment") != "production"
        or plan["migration_id"] != manifest["migration_id"]
    ):
        raise TargetViolation("MIGRATION_PLAN_BINDING")
    for key in ("plan_sha256", "policy_sha256", "target_manifest_sha256"):
        _sha(plan[key], "MIGRATION_PLAN_BINDING")
    _text(plan["approval_id"], "MIGRATION_APPROVAL")
    _text(plan["source_commit"], "MIGRATION_PLAN_BINDING")
    if len(plan["source_commit"]) != 40 or any(
        char not in "0123456789abcdef" for char in plan["source_commit"]
    ):
        raise TargetViolation("MIGRATION_PLAN_BINDING")
    if plan["target_manifest_sha256"] != manifest["target_release_sha256"]:
        raise TargetViolation("MIGRATION_PLAN_TARGET_BINDING")
    _timestamp(plan["expires_at"], "MIGRATION_PLAN_FRESHNESS")
    if now is not None and datetime.fromisoformat(
        plan["expires_at"].replace("Z", "+00:00")
    ).astimezone(timezone.utc) <= now.astimezone(timezone.utc):
        raise TargetViolation("MIGRATION_PLAN_STALE")


def validate_state_migration_evidence(
    state: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    required = {
        "moved_blocks",
        "imports",
        "ordering",
        "expected_plan_impact",
        "rollback_limitations",
        "plan_sha256",
    }
    if set(state) != required or state["plan_sha256"] != plan["plan_sha256"]:
        raise TargetViolation("MIGRATION_STATE_EVIDENCE")
    for key in ("moved_blocks", "imports"):
        if not isinstance(state[key], list) or any(
            not isinstance(item, str) or not item.strip() for item in state[key]
        ):
            raise TargetViolation("MIGRATION_STATE_EVIDENCE")
    for key in ("ordering", "expected_plan_impact", "rollback_limitations"):
        _text(state[key], "MIGRATION_STATE_EVIDENCE")
    _sha(state["plan_sha256"], "MIGRATION_STATE_EVIDENCE")


def validate_ownership_evidence(
    ownership: Mapping[str, Any], *, now: datetime | None = None
) -> None:
    required = {
        "process_manager_principal",
        "cell_root",
        "job_root",
        "source_major",
        "target_major",
        "supported_previous_major",
        "observed_at",
    }
    if set(ownership) != required:
        raise TargetViolation("MIGRATION_OWNERSHIP_EVIDENCE")
    for key in ("process_manager_principal", "cell_root", "job_root"):
        _text(ownership[key], "MIGRATION_OWNERSHIP_EVIDENCE")
    if any(
        isinstance(ownership[key], bool)
        or not isinstance(ownership[key], int)
        or ownership[key] < 0
        for key in ("source_major", "target_major")
    ):
        raise TargetViolation("MIGRATION_OWNERSHIP_EVIDENCE")
    if ownership["supported_previous_major"] is not True:
        raise TargetViolation("MIGRATION_OWNERSHIP_EVIDENCE")
    _timestamp(ownership["observed_at"], "MIGRATION_OWNERSHIP_EVIDENCE")
    catalog_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "v1"
        / "catalogs"
        / "migration.json"
    )
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        expected = catalog["ownership"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise TargetViolation("MIGRATION_OWNERSHIP_CATALOG") from error
    if (
        not isinstance(expected, Mapping)
        or expected.get("stable_within_major") is not True
    ):
        raise TargetViolation("MIGRATION_OWNERSHIP_CATALOG")
    if any(
        ownership[key] != expected[catalog_key]
        for key, catalog_key in (
            ("process_manager_principal", "process_manager"),
            ("cell_root", "cell_root"),
            ("job_root", "job_root"),
        )
    ):
        raise TargetViolation("MIGRATION_OWNERSHIP_BINDING")
    if now is not None:
        observed = datetime.fromisoformat(
            ownership["observed_at"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if observed > now.astimezone(timezone.utc):
            raise TargetViolation("MIGRATION_OWNERSHIP_FRESHNESS")


def validate_rollback(
    manifest: Mapping[str, Any],
    *,
    known_good_release: str,
    evidence_supported: bool,
    rollback_evidence: Mapping[str, Any] | None = None,
) -> None:
    validate_migration_manifest(manifest)
    if manifest["phase"] != "rollback" or manifest["launch_disabled"] is not True:
        raise TargetViolation("MIGRATION_ROLLBACK_GUARD")
    if known_good_release != manifest["source_release"] or not evidence_supported:
        raise TargetViolation("MIGRATION_ROLLBACK_COMPATIBILITY")
    if rollback_evidence is None:
        raise TargetViolation("MIGRATION_ROLLBACK_EVIDENCE_REQUIRED")
    validate_phase_evidence(manifest, rollback_evidence)
