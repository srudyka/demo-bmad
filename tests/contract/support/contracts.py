from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, reset_tzpath

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from referencing import Registry, Resource
import rfc8785
from semantic_version import SimpleSpec, Version  # type: ignore[import-untyped]


class ContractViolation(ValueError):
    """Raised when checked-in contract data violates a stable package rule."""


@dataclass(frozen=True)
class ContractIssue:
    code: str
    pointer: str
    message: str


JOB_ID_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,62}/"
    r"[a-z0-9][a-z0-9-]{0,62}/"
    r"[a-z0-9][a-z0-9-]{0,62}$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EPOCH_MINUTE_PATTERN = re.compile(r"^(0|[1-9][0-9]*)$")
SEMVER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
MAX_SAFE_INTEGER = 9_007_199_254_740_991
CANONICAL_INTEGER = r"(0|[1-9][0-9]*)"
DAILY_CRON = re.compile(
    rf"^cron\(({CANONICAL_INTEGER}) ({CANONICAL_INTEGER}) \* \* \? \*\)$"
)
WEEKLY_CRON = re.compile(
    rf"^cron\(({CANONICAL_INTEGER}) ({CANONICAL_INTEGER}) \? \* "
    r"(SUN|MON|TUE|WED|THU|FRI|SAT) \*\)$"
)
MONTHLY_CRON = re.compile(
    rf"^cron\(({CANONICAL_INTEGER}) ({CANONICAL_INTEGER}) "
    rf"({CANONICAL_INTEGER}) \* \? \*\)$"
)
RATE_EXPRESSION = re.compile(
    rf"^rate\(({CANONICAL_INTEGER}) (minute|minutes|hour|hours|day|days)\)$"
)
SCHEDULE_FIELDS = {
    "activation_end",
    "activation_start",
    "evaluator_version",
    "expression",
    "flexible_time_window",
    "start_anchor",
    "time_zone",
    "tzdb_version",
}
WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractViolation(f"JSON_DUPLICATE_KEY: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ContractViolation(f"JSON_NON_FINITE_NUMBER: {value}")


def load_json_strict(path: Path) -> dict[str, Any]:
    return load_json_bytes_strict(path.read_bytes())


def load_json_bytes_strict(data: bytes) -> dict[str, Any]:
    if len(data) > 262_144:
        raise ContractViolation("JSON_MESSAGE_TOO_LARGE")
    if data.startswith(b"\xef\xbb\xbf"):
        raise ContractViolation("JSON_UTF8_BOM")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ContractViolation("JSON_INVALID_UTF8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as error:
        raise ContractViolation(f"JSON_INVALID_SYNTAX: {error.msg}") from error
    if not isinstance(value, dict):
        raise ContractViolation("JSON_ROOT_NOT_OBJECT")
    _validate_json_strings(value, depth=0)
    return value


def _validate_json_strings(value: Any, *, depth: int) -> None:
    if depth > 64:
        raise ContractViolation("JSON_MAX_DEPTH")
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ContractViolation("JSON_UNPAIRED_SURROGATE")
        if unicodedata.normalize("NFC", value) != value:
            raise ContractViolation("JSON_STRING_NOT_NFC")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ContractViolation("JSON_NON_FINITE_NUMBER: parsed float")
    elif isinstance(value, dict):
        for key, child in value.items():
            _validate_json_strings(key, depth=depth + 1)
            _validate_json_strings(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_json_strings(child, depth=depth + 1)


def build_schema_registry(
    schemas_root: Path,
) -> tuple[dict[str, dict[str, Any]], Registry[Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    for path in sorted(schemas_root.rglob("*.schema.json")):
        schema = load_json_strict(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or schema_id in schemas:
            raise ContractViolation(f"SCHEMA_ID_INVALID_OR_DUPLICATE: {path}")
        schemas[schema_id] = schema
        resources.append((schema_id, Resource.from_contents(schema)))
    return schemas, Registry().with_resources(resources)


def validate_contract_instance(
    schema: dict[str, Any],
    instance: dict[str, Any],
    registry: Registry[Any],
    *,
    secret_policy: dict[str, Any] | None = None,
) -> tuple[ContractIssue, ...]:
    validator = Draft202012Validator(schema, registry=registry)
    issues: list[ContractIssue] = []
    for error in sorted(
        validator.iter_errors(instance), key=lambda item: list(item.path)
    ):
        pointer = "".join(f"/{part}" for part in error.absolute_path) or "/"
        issues.append(ContractIssue("SCHEMA_VALIDATION_FAILED", pointer, error.message))
    _validate_semantic_timestamps(instance, "", issues)
    schema_id = schema.get("$id")
    if schema_id == "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:config":
        _validate_config_semantics(instance, issues)
    if (
        schema_id
        == "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:cell-contract"
    ):
        _validate_cell_contract_semantics(instance, issues)
    if schema_id in {
        "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:command",
        "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:payload:command-authorized",
    }:
        command = instance.get("command", instance)
        if isinstance(command, dict):
            _validate_canonical_command(
                command, "/command" if "command" in instance else "", issues
            )
    if (
        schema_id
        == "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:evidence-envelope"
    ):
        if secret_policy is None:
            issues.append(
                ContractIssue(
                    "SECRET_POLICY_REQUIRED",
                    "/",
                    "evidence validation requires the checked-in secret-safety policy",
                )
            )
        else:
            try:
                screen_secret_safety(instance, secret_policy)
            except ContractViolation as error:
                issues.append(
                    ContractIssue(str(error).split(":", 1)[0], "/", str(error))
                )
    return tuple(issues)


def canary_reservation_decision(
    *,
    cell_account_id: str,
    cell_region: str,
    authorization: dict[str, Any],
    request: dict[str, Any],
    existing_reservation: dict[str, Any] | None,
) -> str:
    """Model the one-canary bootstrap declaration's deterministic rejection path."""
    if (
        request.get("account_id") != cell_account_id
        or request.get("region") != cell_region
    ):
        return "NAMESPACE_UNAUTHORIZED_MUTATION"

    for field in ("repository_id", "terraform_root_id"):
        if request.get(field) != authorization.get(field):
            return "NAMESPACE_CROSS_NAMESPACE_CLAIM"
    for field in ("apply_role_id", "account_id", "region"):
        if request.get(field) != authorization.get(field):
            return "NAMESPACE_UNAUTHORIZED_MUTATION"

    if existing_reservation is None:
        return "CREATED"
    if existing_reservation.get("tombstoned") is True:
        return "NAMESPACE_TOMBSTONED_JOB_ID"
    if existing_reservation.get("owner_generation") != request.get("owner_generation"):
        return "NAMESPACE_STALE_OWNER_GENERATION"

    immutable_fields = (
        "account_id",
        "apply_role_id",
        "environment",
        "job_id",
        "owner",
        "owner_generation",
        "region",
        "repository_id",
        "terraform_root_id",
    )
    if all(
        existing_reservation.get(field) == request.get(field)
        for field in immutable_fields
    ):
        return "IDEMPOTENT"
    return "NAMESPACE_DUPLICATE_RESERVATION"


def _validate_semantic_timestamps(
    value: Any, pointer: str, issues: list[ContractIssue]
) -> None:
    if isinstance(value, dict):
        for name, child in value.items():
            child_pointer = f"{pointer}/{name}"
            if isinstance(child, str) and (
                name.endswith("_at")
                or name.endswith("_time")
                or name
                in {
                    "activation_end",
                    "activation_start",
                    "expectation_horizon",
                    "scanner_watermark",
                    "start_anchor",
                }
            ):
                try:
                    _parse_canonical_timestamp(child)
                except ContractViolation:
                    issues.append(
                        ContractIssue(
                            "TIMESTAMP_NONCANONICAL",
                            child_pointer,
                            "timestamp is not a real canonical UTC millisecond instant",
                        )
                    )
            _validate_semantic_timestamps(child, child_pointer, issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_semantic_timestamps(child, f"{pointer}/{index}", issues)


def _validate_config_semantics(
    instance: dict[str, Any], issues: list[ContractIssue]
) -> None:
    config = instance.get("config")
    declared_hash = instance.get("config_version")
    if not isinstance(config, dict) or not isinstance(declared_hash, str):
        return
    try:
        actual_hash = config_hash(config)
    except ContractViolation as error:
        issues.append(ContractIssue(str(error), "/config", str(error)))
        return
    if declared_hash != actual_hash:
        issues.append(
            ContractIssue(
                "CONFIG_HASH_MISMATCH",
                "/config_version",
                "config_version must be the RFC 8785 SHA-256 of config",
            )
        )
    schedule = config.get("schedule")
    declared_generation = config.get("schedule_generation")
    if not isinstance(schedule, dict) or not isinstance(declared_generation, str):
        return
    try:
        actual_generation = schedule_generation(schedule)
    except ContractViolation as error:
        issues.append(ContractIssue(str(error), "/config/schedule", str(error)))
        return
    if declared_generation != actual_generation:
        issues.append(
            ContractIssue(
                "SCHEDULE_GENERATION_MISMATCH",
                "/config/schedule_generation",
                "schedule_generation must bind the normalized schedule/v1 body",
            )
        )


def _validate_canonical_command(
    command: dict[str, Any], pointer: str, issues: list[ContractIssue]
) -> None:
    if command.get("form") != "canonical":
        return
    required = ("job_id", "original_occurrence_id", "config_version", "command_id")
    if not all(isinstance(command.get(field), str) for field in required):
        return
    try:
        expected = manual_occurrence_id(
            command["job_id"],
            command["original_occurrence_id"],
            command["config_version"],
            command["command_id"],
        )
    except ContractViolation as error:
        issues.append(ContractIssue(str(error), pointer or "/", str(error)))
        return
    if command.get("synthetic_occurrence_id") != expected:
        issues.append(
            ContractIssue(
                "COMMAND_SYNTHETIC_OCCURRENCE_MISMATCH",
                f"{pointer}/synthetic_occurrence_id",
                "synthetic_occurrence_id must bind occurrence/manual/v1 bytes",
            )
        )
    if command.get("command_type") == "RERUN":
        if command.get("replay_of_occurrence_id") != command.get(
            "original_occurrence_id"
        ):
            issues.append(
                ContractIssue(
                    "COMMAND_REPLAY_LINK_MISMATCH",
                    f"{pointer}/replay_of_occurrence_id",
                    "RERUN replay_of_occurrence_id must equal original_occurrence_id",
                )
            )
        if (
            not isinstance(command.get("schedule_generation"), str)
            or SHA256_PATTERN.fullmatch(command["schedule_generation"]) is None
        ):
            issues.append(
                ContractIssue(
                    "COMMAND_SCHEDULE_GENERATION_INVALID",
                    f"{pointer}/schedule_generation",
                    "RERUN schedule_generation must be a SHA-256 value",
                )
            )


def screen_secret_safety(value: Any, policy: dict[str, Any]) -> None:
    forbidden_names = tuple(
        re.compile(pattern) for pattern in policy["forbidden_field_name_patterns"]
    )
    forbidden_values = tuple(
        re.compile(pattern) for pattern in policy["forbidden_value_patterns"]
    )
    allowed_names = set(policy["allowed_reference_field_names"])

    def walk(candidate: Any, pointer: str) -> None:
        if isinstance(candidate, dict):
            for name, child in candidate.items():
                child_pointer = f"{pointer}/{name}"
                if name not in allowed_names and any(
                    pattern.search(name) for pattern in forbidden_names
                ):
                    raise ContractViolation(f"SECRET_FORBIDDEN_FIELD: {child_pointer}")
                walk(child, child_pointer)
        elif isinstance(candidate, list):
            for index, child in enumerate(candidate):
                walk(child, f"{pointer}/{index}")
        elif isinstance(candidate, str) and any(
            pattern.search(candidate) for pattern in forbidden_values
        ):
            raise ContractViolation(f"SECRET_FORBIDDEN_VALUE: {pointer}")

    walk(value, "")


def artifact_digest(path: Path) -> str:
    data = path.read_bytes()
    try:
        data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ContractViolation(f"ARTIFACT_INVALID_UTF8: {path}") from error
    if b"\r" in data:
        raise ContractViolation(f"ARTIFACT_NON_LF_LINE_ENDING: {path}")
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise ContractViolation(f"ARTIFACT_FINAL_NEWLINE: {path}")
    return hashlib.sha256(data).hexdigest()


def validate_manifest(contracts_root: Path, manifest: dict[str, Any]) -> None:
    root = contracts_root.resolve()
    controlled_files: set[str] = set()
    for required_root in manifest["artifact_roots"]:
        if Path(required_root).is_absolute() or "\\" in required_root:
            raise ContractViolation(f"MANIFEST_PATH_ESCAPE: {required_root}")
        candidate = (root / required_root).resolve()
        if not candidate.is_relative_to(root):
            raise ContractViolation(f"MANIFEST_PATH_ESCAPE: {required_root}")
        if not candidate.is_dir():
            raise ContractViolation(f"MANIFEST_ROOT_MISSING: {required_root}")
        controlled_files.update(
            path.relative_to(root).as_posix()
            for path in candidate.rglob("*")
            if path.is_file()
        )
    for version_root in root.iterdir():
        if version_root.is_dir() and re.fullmatch(r"v[1-9][0-9]*", version_root.name):
            controlled_files.update(
                path.relative_to(root).as_posix()
                for path in version_root.rglob("*")
                if path.is_file()
            )

    seen: set[str] = set()
    for item in manifest["artifacts"]:
        relative = item["path"]
        if Path(relative).is_absolute() or "\\" in relative:
            raise ContractViolation(f"MANIFEST_PATH_ESCAPE: {relative}")
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root):
            raise ContractViolation(f"MANIFEST_PATH_ESCAPE: {relative}")
        if relative in seen:
            raise ContractViolation(f"MANIFEST_DUPLICATE_ARTIFACT: {relative}")
        seen.add(relative)
        if not candidate.is_file():
            raise ContractViolation(f"MANIFEST_ARTIFACT_MISSING: {relative}")
        if artifact_digest(candidate) != item["sha256"]:
            raise ContractViolation(f"MANIFEST_CHECKSUM_MISMATCH: {relative}")
    unreferenced = controlled_files - seen
    if unreferenced:
        raise ContractViolation(
            "MANIFEST_UNREFERENCED_ARTIFACT: " + ", ".join(sorted(unreferenced))
        )


def classify_semantic_change(before: dict[str, Any], after: dict[str, Any]) -> str:
    if before == after:
        return "patch"
    before_properties = before.get("properties", {})
    after_properties = after.get("properties", {})
    before_required = set(before.get("required", []))
    after_required = set(after.get("required", []))

    if not isinstance(before_properties, dict) or not isinstance(
        after_properties, dict
    ):
        return "major"
    if not set(before_properties).issubset(after_properties):
        return "major"
    if before_required - after_required:
        return "major"
    if after_required - before_required:
        return "major"
    for name in before_properties:
        if before_properties[name] != after_properties[name]:
            return "major"
    if set(after_properties) - set(before_properties):
        return "minor"
    return "major"


def semantic_surface_digest(manifest: dict[str, Any]) -> str:
    semantic_artifacts = [
        {"path": item["path"], "sha256": item["sha256"]}
        for item in sorted(manifest["artifacts"], key=lambda item: item["path"])
        if re.fullmatch(r"v[1-9][0-9]*/(catalogs|schemas)/.+", item["path"])
    ]
    return hashlib.sha256(canonical_json_bytes(semantic_artifacts)).hexdigest()


def validate_release(contracts_root: Path, manifest: dict[str, Any]) -> None:
    package_version = manifest["package_version"]
    release_path = contracts_root / "releases" / f"{package_version}.json"
    if not release_path.is_file():
        raise ContractViolation("RELEASE_SNAPSHOT_MISSING")
    release = load_json_strict(release_path)
    if release.get("package_version") != package_version:
        raise ContractViolation("RELEASE_VERSION_MISMATCH")
    if release.get("predecessor_release") != manifest.get("predecessor_release"):
        raise ContractViolation("RELEASE_PREDECESSOR_MISMATCH")
    if release.get("semantic_surface_sha256") != semantic_surface_digest(manifest):
        raise ContractViolation("RELEASE_SEMANTIC_SURFACE_MISMATCH")

    migration = release.get("migration")
    expected_migration = f"migrations/v{package_version}.md"
    if (
        migration != expected_migration
        or not (contracts_root / expected_migration).is_file()
    ):
        raise ContractViolation("RELEASE_MIGRATION_MISSING")
    migration_text = (contracts_root / expected_migration).read_text("utf-8")
    expected_metadata = (
        f'<!-- compatibility-release: {{"package_version":"{package_version}",'
        f'"predecessor_release":{json.dumps(manifest.get("predecessor_release"), separators=(",", ":"))},'
        f'"classification":"{release.get("classification")}"}} -->'
    )
    if expected_metadata not in migration_text:
        raise ContractViolation("RELEASE_MIGRATION_DISAGREEMENT")

    predecessor_version = manifest.get("predecessor_release")
    if predecessor_version is None:
        if release.get("classification") != "initial" or not manifest.get(
            "initial_release"
        ):
            raise ContractViolation("RELEASE_INITIAL_STATE")
        return
    predecessor_path = contracts_root / "releases" / f"{predecessor_version}.json"
    if not predecessor_path.is_file():
        raise ContractViolation("RELEASE_PREDECESSOR_MISSING")
    predecessor = load_json_strict(predecessor_path)
    previous = Version(predecessor_version)
    current = Version(package_version)
    changed = predecessor.get("semantic_surface_sha256") != release.get(
        "semantic_surface_sha256"
    )
    expected_classification = "major" if changed else "patch"
    if release.get("classification") != expected_classification:
        raise ContractViolation("RELEASE_CLASSIFICATION_MISMATCH")
    if expected_classification == "major":
        valid_bump = current.major > previous.major
    else:
        valid_bump = current.major == previous.major and current > previous
    if not valid_bump:
        raise ContractViolation("RELEASE_VERSION_BUMP_MISMATCH")


def canonical_json_bytes(value: Any) -> bytes:
    _validate_canonical_profile(value)
    try:
        return rfc8785.dumps(value)
    except (rfc8785.FloatDomainError, rfc8785.IntegerDomainError) as error:
        raise ContractViolation("CANONICAL_JSON_DOMAIN") from error


def _validate_canonical_profile(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ContractViolation("CANONICAL_INTEGER_OUT_OF_RANGE")
        return
    if isinstance(value, float):
        raise ContractViolation("CANONICAL_FLOAT_FORBIDDEN")
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ContractViolation("CANONICAL_STRING_NOT_NFC")
        return
    if isinstance(value, list):
        for child in value:
            _validate_canonical_profile(child)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractViolation("CANONICAL_KEY_NOT_STRING")
            _validate_canonical_profile(key)
            _validate_canonical_profile(child)
        return
    raise ContractViolation("CANONICAL_TYPE_FORBIDDEN")


def config_hash(config_body: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(config_body)).hexdigest()


def cell_contract_checksum(cell_contract: dict[str, Any]) -> str:
    """Hash the RFC 8785 Cell Contract body with its self-checksum omitted."""

    body = dict(cell_contract)
    body.pop("checksum", None)
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _validate_cell_contract_semantics(
    cell_contract: dict[str, Any], issues: list[ContractIssue]
) -> None:
    checksum = cell_contract.get("checksum")
    if not isinstance(checksum, str):
        return
    try:
        expected = cell_contract_checksum(cell_contract)
    except ContractViolation as error:
        issues.append(ContractIssue(str(error), "/checksum", str(error)))
        return
    if checksum != expected:
        issues.append(
            ContractIssue(
                "CELL_CONTRACT_CHECKSUM_MISMATCH",
                "/checksum",
                "checksum must equal SHA-256 of RFC 8785 bytes with checksum omitted",
            )
        )

    cell = cell_contract.get("cell")
    discovery_path = cell_contract.get("discovery_path")
    if isinstance(cell, dict) and isinstance(discovery_path, str):
        environment = cell.get("environment")
        region = cell.get("region")
        if isinstance(environment, str) and isinstance(region, str):
            expected_path = (
                f"/platform/ecs-scheduled-jobs/{environment}/{region}/contract"
            )
            if discovery_path != expected_path:
                issues.append(
                    ContractIssue(
                        "CELL_CONTRACT_DISCOVERY_PATH_MISMATCH",
                        "/discovery_path",
                        "discovery_path must match the contract Cell environment and Region",
                    )
                )

    declared_ranges: list[tuple[str, Any]] = []
    supported_ranges = cell_contract.get("supported_ranges")
    if isinstance(supported_ranges, dict):
        declared_ranges.extend(
            (f"/supported_ranges/{name}", value)
            for name, value in supported_ranges.items()
        )
    integrations = cell_contract.get("integrations")
    if isinstance(integrations, dict):
        for name, integration in integrations.items():
            if isinstance(integration, dict):
                declared_ranges.append(
                    (
                        f"/integrations/{name}/schema_range",
                        integration.get("schema_range"),
                    )
                )
    for pointer, declared_range in declared_ranges:
        if not isinstance(declared_range, str):
            continue
        try:
            SimpleSpec(declared_range)
        except ValueError:
            issues.append(
                ContractIssue(
                    "CELL_CONTRACT_RANGE_INVALID",
                    pointer,
                    "declared compatibility range must be a semantic-version SimpleSpec",
                )
            )


def occurrence_bytes(job_id: str, schedule_generation: str, epoch_minute: str) -> bytes:
    if JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ContractViolation("IDENTITY_JOB_ID_NONCANONICAL")
    if SHA256_PATTERN.fullmatch(schedule_generation) is None:
        raise ContractViolation("IDENTITY_GENERATION_NONCANONICAL")
    if EPOCH_MINUTE_PATTERN.fullmatch(epoch_minute) is None:
        raise ContractViolation("IDENTITY_EPOCH_NONCANONICAL")
    return f"occurrence/v1\n{job_id}\n{schedule_generation}\n{epoch_minute}".encode(
        "utf-8"
    )


def occurrence_id(job_id: str, schedule_generation: str, epoch_minute: str) -> str:
    return hashlib.sha256(
        occurrence_bytes(job_id, schedule_generation, epoch_minute)
    ).hexdigest()


def scheduler_producer_event_bytes(
    schedule_arn: str, scheduled_time: str, config_version: str, owner_generation: int
) -> bytes:
    """Return the contract-owned immutable Scheduler producer-event bytes."""

    if not schedule_arn.startswith("arn:aws:scheduler:"):
        raise ContractViolation("SCHEDULER_IDENTITY_ARN_NONCANONICAL")
    if SHA256_PATTERN.fullmatch(config_version) is None:
        raise ContractViolation("SCHEDULER_IDENTITY_CONFIG_NONCANONICAL")
    if owner_generation < 1:
        raise ContractViolation("SCHEDULER_IDENTITY_OWNER_GENERATION_INVALID")
    _parse_canonical_timestamp(scheduled_time)
    return (
        f"scheduler/v1\n{schedule_arn}\n{scheduled_time}\n{config_version}\n{owner_generation}"
    ).encode("ascii")


def scheduler_producer_event_id(
    schedule_arn: str, scheduled_time: str, config_version: str, owner_generation: int
) -> str:
    return hashlib.sha256(
        scheduler_producer_event_bytes(
            schedule_arn, scheduled_time, config_version, owner_generation
        )
    ).hexdigest()


def materializer_producer_event_bytes(
    job_id: str,
    schedule_generation: str,
    scheduled_time: str,
    config_version: str,
    owner_generation: int,
) -> bytes:
    """Return immutable bytes for one materialized expected occurrence."""

    if JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ContractViolation("MATERIALIZER_IDENTITY_JOB_ID_NONCANONICAL")
    if SHA256_PATTERN.fullmatch(schedule_generation) is None:
        raise ContractViolation("MATERIALIZER_IDENTITY_GENERATION_NONCANONICAL")
    if SHA256_PATTERN.fullmatch(config_version) is None:
        raise ContractViolation("MATERIALIZER_IDENTITY_CONFIG_NONCANONICAL")
    if owner_generation < 1:
        raise ContractViolation("MATERIALIZER_IDENTITY_OWNER_GENERATION_INVALID")
    _parse_canonical_timestamp(scheduled_time)
    return (
        "materializer/v1\n"
        f"{job_id}\n{schedule_generation}\n{scheduled_time}\n"
        f"{config_version}\n{owner_generation}"
    ).encode("ascii")


def materializer_producer_event_id(
    job_id: str,
    schedule_generation: str,
    scheduled_time: str,
    config_version: str,
    owner_generation: int,
) -> str:
    return hashlib.sha256(
        materializer_producer_event_bytes(
            job_id,
            schedule_generation,
            scheduled_time,
            config_version,
            owner_generation,
        )
    ).hexdigest()


def validate_schedule_contract(schedule: dict[str, Any]) -> None:
    if set(schedule) != SCHEDULE_FIELDS:
        raise ContractViolation("SCHEDULE_FIELDS")
    if schedule["flexible_time_window"] != "OFF":
        raise ContractViolation("SCHEDULE_FLEXIBLE_WINDOW")
    if schedule["evaluator_version"] != "schedule-evaluator/1.0.0":
        raise ContractViolation("SCHEDULE_EVALUATOR_VERSION")
    if schedule["tzdb_version"] != "2026b":
        raise ContractViolation("SCHEDULE_TZDB_VERSION")

    start_anchor = _parse_canonical_timestamp(schedule["start_anchor"])
    activation_start = _parse_canonical_timestamp(schedule["activation_start"])
    activation_end_value = schedule["activation_end"]
    if activation_end_value is not None:
        activation_end = _parse_canonical_timestamp(activation_end_value)
        if activation_end <= activation_start:
            raise ContractViolation("SCHEDULE_ACTIVATION_WINDOW")
    if start_anchor > activation_start:
        raise ContractViolation("SCHEDULE_ANCHOR_AFTER_ACTIVATION")

    _schedule_zone(schedule["time_zone"])
    expression = schedule["expression"]
    rate_match = RATE_EXPRESSION.fullmatch(expression)
    if rate_match is not None:
        count = int(rate_match.group(1))
        unit = rate_match.group(3)
        singular = unit in {"minute", "hour", "day"}
        if count < 1 or (count == 1) != singular:
            raise ContractViolation("SCHEDULE_RATE_GRAMMAR")
        return
    for pattern, bounds in (
        (DAILY_CRON, (59, 23, None)),
        (WEEKLY_CRON, (59, 23, None)),
        (MONTHLY_CRON, (59, 23, 31)),
    ):
        match = pattern.fullmatch(expression)
        if match is None:
            continue
        if int(match.group(1)) > bounds[0] or int(match.group(3)) > bounds[1]:
            raise ContractViolation("SCHEDULE_CRON_BOUNDS")
        if bounds[2] is not None and int(match.group(5)) not in range(1, bounds[2] + 1):
            raise ContractViolation("SCHEDULE_CRON_BOUNDS")
        return
    raise ContractViolation("SCHEDULE_EXPRESSION_UNSUPPORTED")


def _schedule_zone(name: str) -> ZoneInfo:
    if importlib.metadata.version("tzdata") != "2026.2":
        raise ContractViolation("SCHEDULE_TZDATA_PACKAGE")
    reset_tzpath(())
    ZoneInfo.clear_cache()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise ContractViolation("SCHEDULE_TIME_ZONE") from error


def _parse_canonical_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (TypeError, ValueError) as error:
        raise ContractViolation("SCHEDULE_TIMESTAMP") from error
    if not isinstance(value, str) or len(value) != 24:
        raise ContractViolation("SCHEDULE_TIMESTAMP")
    return parsed.replace(tzinfo=UTC)


def _format_canonical_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def schedule_generation(schedule: dict[str, Any]) -> str:
    validate_schedule_contract(schedule)
    data = b"schedule/v1\n" + canonical_json_bytes(schedule)
    return hashlib.sha256(data).hexdigest()


def expand_schedule(
    schedule: dict[str, Any], window_start: str, window_end: str
) -> tuple[str, ...]:
    validate_schedule_contract(schedule)
    lower = _parse_canonical_timestamp(window_start)
    upper = _parse_canonical_timestamp(window_end)
    if upper <= lower:
        raise ContractViolation("SCHEDULE_EVALUATION_WINDOW")
    anchor = _parse_canonical_timestamp(schedule["start_anchor"])
    activation_start = _parse_canonical_timestamp(schedule["activation_start"])
    activation_end = (
        _parse_canonical_timestamp(schedule["activation_end"])
        if schedule["activation_end"] is not None
        else None
    )
    effective_lower = max(lower, anchor, activation_start)
    effective_upper = min(upper, activation_end) if activation_end else upper
    if effective_upper <= effective_lower:
        return ()

    rate_match = RATE_EXPRESSION.fullmatch(schedule["expression"])
    if rate_match is not None:
        count = int(rate_match.group(1))
        seconds = {
            "minute": 60,
            "minutes": 60,
            "hour": 3600,
            "hours": 3600,
            "day": 86400,
            "days": 86400,
        }[rate_match.group(3)]
        step = timedelta(seconds=count * seconds)
        cursor = anchor
        if cursor < effective_lower:
            steps = max(0, int((effective_lower - cursor) // step))
            cursor += steps * step
            while cursor < effective_lower:
                cursor += step
        result: list[str] = []
        while cursor < effective_upper:
            result.append(_format_canonical_timestamp(cursor))
            cursor += step
        return tuple(result)

    return _expand_cron(schedule, effective_lower, effective_upper)


def _expand_cron(
    schedule: dict[str, Any], lower: datetime, upper: datetime
) -> tuple[str, ...]:
    zone = _schedule_zone(schedule["time_zone"])
    expression = schedule["expression"]
    daily = DAILY_CRON.fullmatch(expression)
    weekly = WEEKLY_CRON.fullmatch(expression)
    monthly = MONTHLY_CRON.fullmatch(expression)
    match = daily or weekly or monthly
    if match is None:
        raise ContractViolation("SCHEDULE_EXPRESSION_UNSUPPORTED")
    minute = int(match.group(1))
    hour = int(match.group(3))
    local_start = (lower.astimezone(zone) - timedelta(days=2)).date()
    local_end = (upper.astimezone(zone) + timedelta(days=2)).date()
    current = local_start
    occurrences: set[datetime] = set()
    while current <= local_end:
        if weekly is not None and current.weekday() != WEEKDAYS[weekly.group(5)]:
            current += timedelta(days=1)
            continue
        if monthly is not None and current.day != int(monthly.group(5)):
            current += timedelta(days=1)
            continue
        candidate = datetime.combine(current, time(hour, minute), zone).replace(fold=0)
        instant = candidate.astimezone(UTC)
        round_trip = instant.astimezone(zone)
        if (
            round_trip.replace(tzinfo=None) == candidate.replace(tzinfo=None)
            and lower <= instant < upper
        ):
            occurrences.add(instant)
        current += timedelta(days=1)
    return tuple(_format_canonical_timestamp(value) for value in sorted(occurrences))


def reduce_occurrence_state(
    evidence: list[dict[str, Any]], catalog: dict[str, Any]
) -> str:
    accepted = [item for item in evidence if item.get("accepted", True)]
    if len(accepted) > catalog["maximum_fixture_events"]:
        raise ContractViolation("REDUCER_FIXTURE_TOO_LARGE")

    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    conflict = False
    for item in accepted:
        key = (item["producer_id"], item["producer_event_id"])
        previous = deduplicated.get(key)
        if previous is None:
            deduplicated[key] = item
        elif previous["digest"] != item["digest"]:
            conflict = True
    facts = tuple(deduplicated.values())

    task_arns = {
        item["task_arn"]
        for item in facts
        if item.get("task_arn") is not None
        and item["kind"] in {"TASK_RUNNING", "TASK_STOPPED"}
    }
    completions = [item for item in facts if item["kind"] == "COMPLETION"]
    if conflict or len(task_arns) > 1 or len(completions) > 1:
        return "AMBIGUOUS"

    expected = any(item["kind"] == "EXPECTED" for item in facts)
    started = any(item["kind"] in {"TASK_RUNNING", "TASK_STOPPED"} for item in facts)
    launch_failed = any(item["kind"] == "LAUNCH_FAILED" for item in facts)
    stopped_zero = any(
        item["kind"] == "TASK_STOPPED" and item.get("exit_code") == 0 for item in facts
    )
    stopped_nonzero = any(
        item["kind"] == "TASK_STOPPED" and item.get("exit_code") != 0 for item in facts
    )
    completion = completions[0] if completions else None
    if completion is not None and completion.get("task_arn") not in task_arns:
        return "AMBIGUOUS"
    completion_success = (
        completion is not None
        and completion.get("marker_status") == "SUCCESS"
        and completion.get("task_arn") in task_arns
    )
    failure = (
        launch_failed
        or stopped_nonzero
        or (completion is not None and completion.get("marker_status") == "FAILURE")
    )
    success = stopped_zero and completion_success
    if (success and failure) or (completion_success and stopped_nonzero):
        return "AMBIGUOUS"

    deadlines = [item for item in facts if item["kind"] == "DEADLINE"]
    deadline_at = min(
        (item["deadline_at"] for item in deadlines),
        default=None,
    )
    if deadline_at is not None:
        if success and completion is not None:
            if completion["fact_time"] <= deadline_at:
                return "SUCCEEDED"
            return "AMBIGUOUS"
        if failure:
            return "FAILED"
        return "OVERDUE" if started else "MISSED"
    if success:
        return "SUCCEEDED"
    if failure:
        return "FAILED"
    if started:
        return "STARTED"
    if expected or any(item.get("config_proven", False) for item in facts):
        return "EXPECTED"
    return "AMBIGUOUS"


def _catalog_template_matches(value: str, template: str) -> bool:
    escaped = re.escape(template)
    pattern = re.sub(r"<[^>]+>", r"[^:/\\s]+", escaped)
    return re.fullmatch(pattern, value) is not None


def evaluate_iam_case(case: dict[str, Any], catalog: dict[str, Any]) -> None:
    role = catalog["roles"].get(case["role"])
    if role is None:
        raise ContractViolation("IAM_UNKNOWN_ROLE")
    if case["action"] not in role["actions"]:
        raise ContractViolation("IAM_ACTION_NOT_ALLOWED")
    if not any(
        _catalog_template_matches(case["principal"], trust) for trust in role["trust"]
    ):
        raise ContractViolation("IAM_PRINCIPAL_NOT_TRUSTED")
    if not any(
        _catalog_template_matches(case["resource"], resource)
        for resource in role["resources"]
    ):
        raise ContractViolation("IAM_RESOURCE_NOT_ALLOWED")
    if case.get("principal_role_id") is not None and not case[
        "principal_role_id"
    ].startswith(case["registered_role_id_prefix"]):
        raise ContractViolation("IAM_STALE_PRINCIPAL")
    if case["role"] == "scheduler-delivery":
        expected_account = case["resource"].split(":")[4]
        if case.get("source_account") != expected_account:
            raise ContractViolation("IAM_SOURCE_ACCOUNT")
        if case.get("source_arn") != case.get("registered_schedule_group_arn"):
            raise ContractViolation("IAM_SOURCE_ARN")
    if case["action"] == "iam:PassRole":
        if case.get("passed_to_service") != "ecs-tasks.amazonaws.com":
            raise ContractViolation("IAM_PASSED_TO_SERVICE")
        if case["resource"] not in case.get("approved_pass_role_arns", []):
            raise ContractViolation("IAM_CROSS_JOB_RESOURCE")
    if case["role"] == "process-manager":
        if not case.get("boundary_present", False):
            raise ContractViolation("IAM_BOUNDARY_REQUIRED")
        if case["resource"] != case.get("approved_launch_role_arn"):
            raise ContractViolation("IAM_CROSS_JOB_RESOURCE")


def evaluate_producer_authority(case: dict[str, Any], catalog: dict[str, Any]) -> None:
    producer = catalog["producers"].get(case["producer_id"])
    if producer is None:
        raise ContractViolation("PRODUCER_UNKNOWN")
    if case["event_type"] not in producer["event_types"]:
        raise ContractViolation("PRODUCER_EVENT_TYPE")
    metadata = case["metadata"]
    registered_metadata = case.get("registered_metadata", {})
    required_metadata = producer.get("authority_metadata", [])
    if case["producer_id"] == "log-ingestor" and metadata.get(
        "ledger_task_arn_index"
    ) != registered_metadata.get("ledger_task_arn_index"):
        raise ContractViolation("PRODUCER_WRONG_BINDING")
    if not isinstance(registered_metadata, dict) or any(
        metadata.get(name) != registered_metadata.get(name)
        for name in required_metadata
    ):
        raise ContractViolation("PRODUCER_AUTHORITY")
    raw_shape = producer.get("raw_shape", {})
    if "source" in raw_shape and metadata.get("source") != raw_shape["source"]:
        raise ContractViolation("PRODUCER_AUTHORITY")
    if case["producer_id"] == "scheduler" and not metadata.get(
        "sender_role_id", ""
    ).startswith(registered_metadata.get("sender_role_id_prefix", "")):
        raise ContractViolation("PRODUCER_AUTHORITY")


def evaluate_oidc_case(case: dict[str, Any], catalog: dict[str, Any]) -> None:
    if case["aud"] != catalog["audience"]:
        raise ContractViolation("OIDC_AUDIENCE")
    if case["sub"] != catalog["subject"]:
        raise ContractViolation("OIDC_SUBJECT")


def evaluate_lifecycle_case(case: dict[str, Any], catalog: dict[str, Any]) -> None:
    if case.get("timed_out", False):
        raise ContractViolation("LIFECYCLE_TIMEOUT")
    legal_targets = catalog["legal_transitions"].get(case["current"], [])
    if case["target"] not in legal_targets:
        raise ContractViolation("LIFECYCLE_TRANSITION")
    if case["ack"].get("ownership_generation") != case["expected"].get(
        "ownership_generation"
    ):
        raise ContractViolation("LIFECYCLE_STALE_GENERATION")
    if case["ack"] != case["expected"]:
        raise ContractViolation("LIFECYCLE_ACK_MISMATCH")
    if set(case["ack"]) != set(catalog["acknowledgement_bindings"]):
        raise ContractViolation("LIFECYCLE_ACK_BINDINGS")


def evaluate_queue_case(case: dict[str, Any]) -> None:
    if not 0 <= case["message_bytes"] <= 262_144:
        raise ContractViolation("QUEUE_MESSAGE_SIZE")
    if not 1 <= case["batch_size"] <= 10:
        raise ContractViolation("QUEUE_BATCH_SIZE")
    if not 1 <= case["function_timeout_seconds"] <= 900:
        raise ContractViolation("QUEUE_FUNCTION_TIMEOUT")
    if not 0 <= case["batch_window_seconds"] <= 300:
        raise ContractViolation("QUEUE_BATCH_WINDOW")
    minimum_visibility = (
        6 * case["function_timeout_seconds"] + case["batch_window_seconds"]
    )
    if not minimum_visibility <= case["visibility_seconds"] <= 43_200:
        raise ContractViolation("QUEUE_VISIBILITY")
    if not 2 <= case["maximum_concurrency"] <= 1_000:
        raise ContractViolation("QUEUE_CONCURRENCY")
    if case["maximum_concurrency"] > case["reserved_concurrency"]:
        raise ContractViolation("QUEUE_CONCURRENCY_RESERVED")
    if not case["dlq"]:
        raise ContractViolation("QUEUE_DLQ_REQUIRED")
    if (
        case["retention_seconds"] != 1_209_600
        or case["dlq_retention_seconds"] != 1_209_600
    ):
        raise ContractViolation("QUEUE_RETENTION")
    if not 5 <= case["max_receive_count"] <= 1_000:
        raise ContractViolation("QUEUE_MAX_RECEIVE")
    if not case["encrypted"] or case["queue_type"] != "standard":
        raise ContractViolation("QUEUE_ENCRYPTION")
    if (
        case["partial_batch_response"] != "ReportBatchItemFailures"
        or not case["failed_message_ids"]
    ):
        raise ContractViolation("QUEUE_PARTIAL_BATCH")
    if case["provisioned_poller"]:
        raise ContractViolation("QUEUE_PROVISIONED_POLLER")
    if not case["finite_retry_horizon"]:
        raise ContractViolation("QUEUE_RETRY_UNBOUNDED")


def evaluate_ecs_retry_case(case: dict[str, Any]) -> None:
    token = case["client_token"]
    if not 1 <= len(token.encode("ascii", errors="ignore")) <= 64 or any(
        not 0x20 <= ord(character) <= 0x7E for character in token
    ):
        raise ContractViolation("ECS_CLIENT_TOKEN")
    if not case["identical_parameters"]:
        raise ContractViolation("ECS_IDEMPOTENCY_PARAMETERS")
    if not case["same_cluster"]:
        raise ContractViolation("ECS_IDEMPOTENCY_CLUSTER")
    if case["attempt_no"] != 0:
        raise ContractViolation("ECS_ATTEMPT_NUMBER")
    if case["failures"]:
        raise ContractViolation("ECS_RUN_TASK_FAILURES")
    if not 0 <= case["safe_retry_deadline_seconds"] <= 3_600:
        raise ContractViolation("ECS_SAFE_RETRY_HORIZON")
    if case["elapsed_seconds"] < 0:
        raise ContractViolation("ECS_ELAPSED_SECONDS")
    if (
        case["elapsed_seconds"] > case["safe_retry_deadline_seconds"]
        and not case["authoritative_recovery"]
    ):
        raise ContractViolation("ECS_SAFE_RETRY_DEADLINE")


def evaluate_compatibility_case(case: dict[str, Any], catalog: dict[str, Any]) -> None:
    component_range = catalog["component_ranges"].get(case["component"])
    if component_range is None:
        raise ContractViolation("COMPATIBILITY_UNKNOWN_COMPONENT")
    version = Version(case["version"])
    if version.prerelease and not case.get("allow_prerelease", False):
        raise ContractViolation("COMPATIBILITY_PRERELEASE_FORBIDDEN")
    if version.build and not case.get("allow_build", False):
        raise ContractViolation("COMPATIBILITY_BUILD_FORBIDDEN")
    if not case.get("migration_present", False):
        raise ContractViolation("COMPATIBILITY_MIGRATION_MISSING")
    if (version.prerelease and case.get("allow_prerelease", False)) or (
        version.build and case.get("allow_build", False)
    ):
        version = Version(f"{version.major}.{version.minor}.{version.patch}")
    if not SimpleSpec(component_range).match(version):
        raise ContractViolation("COMPATIBILITY_UNSUPPORTED_VERSION")


def validate_uuid_v7(value: str, error_code: str) -> None:
    if value != value.lower():
        raise ContractViolation(error_code)
    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise ContractViolation(error_code) from error
    if parsed.version != 7 or parsed.variant != uuid.RFC_4122:
        raise ContractViolation(error_code)


def validate_operator_request(request: dict[str, Any], catalog: dict[str, Any]) -> None:
    forbidden_ids = {
        "occurrence_id",
        "original_occurrence_id",
        "synthetic_occurrence_id",
        "command_id",
    }
    if forbidden_ids.intersection(request):
        raise ContractViolation("COMMAND_CALLER_OWNED_ID")
    if {"producer_id", "evidence"}.intersection(request):
        raise ContractViolation("COMMAND_CALLER_AUTHORITY")
    required = {
        "schema_version",
        "form",
        "request_id",
        "job_id",
        "scheduled_time",
        "actor",
        "approval_reference",
        "reason",
    }
    if set(request) != required or request["form"] != "operator_request":
        raise ContractViolation("COMMAND_REQUEST_SHAPE")
    if SEMVER_PATTERN.fullmatch(request["schema_version"]) is None or not request[
        "schema_version"
    ].startswith("1."):
        raise ContractViolation("COMMAND_SCHEMA_VERSION")
    validate_uuid_v7(request["request_id"], "COMMAND_REQUEST_ID")
    if JOB_ID_PATTERN.fullmatch(request["job_id"]) is None:
        raise ContractViolation("COMMAND_JOB_ID")
    try:
        _parse_canonical_timestamp(request["scheduled_time"])
    except ContractViolation as error:
        raise ContractViolation("COMMAND_SCHEDULED_TIME") from error
    for name in ("actor", "approval_reference", "reason"):
        if not isinstance(request[name], str) or not request[name]:
            raise ContractViolation("COMMAND_REQUEST_FIELD")
    if len(request["reason"]) > 1_024:
        raise ContractViolation("COMMAND_REQUEST_FIELD")
    if request.keys() & set(catalog["operator_request"]["forbidden_caller_fields"]):
        raise ContractViolation("COMMAND_CALLER_AUTHORITY")


def manual_occurrence_bytes(
    job_id: str,
    original_occurrence_id: str,
    config_version: str,
    command_id: str,
) -> bytes:
    if JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise ContractViolation("COMMAND_JOB_ID")
    if SHA256_PATTERN.fullmatch(original_occurrence_id) is None:
        raise ContractViolation("COMMAND_ORIGINAL_OCCURRENCE_ID")
    if SHA256_PATTERN.fullmatch(config_version) is None:
        raise ContractViolation("COMMAND_CONFIG_VERSION")
    validate_uuid_v7(command_id, "COMMAND_ID")
    return (
        "occurrence/manual/v1\n"
        f"{job_id}\n{original_occurrence_id}\n{config_version}\n{command_id}"
    ).encode("utf-8")


def manual_occurrence_id(
    job_id: str,
    original_occurrence_id: str,
    config_version: str,
    command_id: str,
) -> str:
    return hashlib.sha256(
        manual_occurrence_bytes(
            job_id, original_occurrence_id, config_version, command_id
        )
    ).hexdigest()
