from __future__ import annotations

import base64
from copy import deepcopy
from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    build_schema_registry,
    load_json_bytes_strict,
    load_json_strict,
    screen_secret_safety,
    validate_contract_instance,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"
SCHEMAS_ROOT = CONTRACTS_ROOT / "v1" / "schemas"
FIXTURES_ROOT = CONTRACTS_ROOT / "v1" / "fixtures" / "schemas"
SECRET_POLICY = CONTRACTS_ROOT / "v1" / "catalogs" / "secret-safety.json"


def test_every_schema_is_unique_meta_valid_local_and_manifest_listed() -> None:
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")
    schemas, _registry = build_schema_registry(SCHEMAS_ROOT)

    assert len(schemas) == 19
    assert len(set(schemas)) == len(schemas)
    assert set(manifest["schemas"]) == set(schemas)


def test_all_valid_schema_instances_pass() -> None:
    cases = load_json_strict(FIXTURES_ROOT / "valid-instances.json")
    schemas, registry = build_schema_registry(SCHEMAS_ROOT)
    policy = load_json_strict(SECRET_POLICY)

    for case in cases["cases"]:
        issues = validate_contract_instance(
            schemas[case["schema_id"]], case["instance"], registry, secret_policy=policy
        )
        assert issues == (), case["name"]


def test_every_required_boundary_field_is_enforced() -> None:
    cases = load_json_strict(FIXTURES_ROOT / "valid-instances.json")
    schemas, registry = build_schema_registry(SCHEMAS_ROOT)
    policy = load_json_strict(SECRET_POLICY)

    for case in cases["cases"]:
        schema = schemas[case["schema_id"]]
        if case["kind"] != "required-boundary":
            continue
        for required in schema["required"]:
            invalid = dict(case["instance"])
            invalid.pop(required)
            issues = validate_contract_instance(
                schema, invalid, registry, secret_policy=policy
            )
            assert issues, f"{case['name']} accepted missing {required}"


def test_invalid_schema_instances_fail_with_expected_pointer() -> None:
    cases = load_json_strict(FIXTURES_ROOT / "invalid-instances.json")
    schemas, registry = build_schema_registry(SCHEMAS_ROOT)
    policy = load_json_strict(SECRET_POLICY)

    for case in cases["cases"]:
        issues = validate_contract_instance(
            schemas[case["schema_id"]], case["instance"], registry, secret_policy=policy
        )
        assert case["expected_pointer"] in {issue.pointer for issue in issues}, case[
            "name"
        ]


def test_raw_parser_rejects_noncanonical_json_bytes() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "raw-parser-cases.json")
    for case in fixture["cases"]:
        raw = base64.b64decode(case["input_base64"], validate=True)
        if case["accepted"]:
            assert load_json_bytes_strict(raw) == case["expected"]
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                load_json_bytes_strict(raw)


def test_secret_safety_catalog_accepts_references_and_rejects_values() -> None:
    fixture = load_json_strict(FIXTURES_ROOT / "secret-safety-cases.json")
    policy = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "secret-safety.json")
    for case in fixture["cases"]:
        if case["accepted"]:
            screen_secret_safety(case["input"], policy)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                screen_secret_safety(case["input"], policy)


def test_evidence_extensions_are_screened_by_the_normal_validation_boundary() -> None:
    cases = load_json_strict(FIXTURES_ROOT / "valid-instances.json")
    schemas, registry = build_schema_registry(SCHEMAS_ROOT)
    policy = load_json_strict(SECRET_POLICY)
    evidence = next(
        case["instance"]
        for case in cases["cases"]
        if case["schema_id"].endswith("schema:evidence-envelope")
    )
    invalid = dict(evidence)
    invalid["x-password"] = "forbidden-secret-sentinel:not-a-real-secret"

    issues = validate_contract_instance(
        schemas[
            "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:evidence-envelope"
        ],
        invalid,
        registry,
        secret_policy=policy,
    )

    assert {issue.code for issue in issues} & {
        "SECRET_FORBIDDEN_FIELD",
        "SECRET_FORBIDDEN_VALUE",
    }


def test_config_and_manual_command_identities_bind_their_canonical_bodies() -> None:
    cases = load_json_strict(FIXTURES_ROOT / "valid-instances.json")
    schemas, registry = build_schema_registry(SCHEMAS_ROOT)
    policy = load_json_strict(SECRET_POLICY)
    config = deepcopy(
        next(case["instance"] for case in cases["cases"] if case["name"] == "config")
    )
    config["config_version"] = "0" * 64
    config_issues = validate_contract_instance(
        schemas["urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:config"],
        config,
        registry,
        secret_policy=policy,
    )
    assert "CONFIG_HASH_MISMATCH" in {issue.code for issue in config_issues}

    command_payload = deepcopy(
        next(
            case["instance"]
            for case in cases["cases"]
            if case["name"] == "command payload"
        )
    )
    command_payload["command"]["synthetic_occurrence_id"] = "0" * 64
    command_issues = validate_contract_instance(
        schemas[
            "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:payload:command-authorized"
        ],
        command_payload,
        registry,
        secret_policy=policy,
    )
    assert "COMMAND_SYNTHETIC_OCCURRENCE_MISMATCH" in {
        issue.code for issue in command_issues
    }


def test_config_schedule_rejects_noncanonical_timestamp_and_generation() -> None:
    cases = load_json_strict(FIXTURES_ROOT / "valid-instances.json")
    schemas, registry = build_schema_registry(SCHEMAS_ROOT)
    policy = load_json_strict(SECRET_POLICY)
    config = deepcopy(
        next(case["instance"] for case in cases["cases"] if case["name"] == "config")
    )
    config["config"]["schedule"]["activation_start"] = "2026-02-31T10:00:00.000Z"
    issues = validate_contract_instance(
        schemas["urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:config"],
        config,
        registry,
        secret_policy=policy,
    )

    assert "TIMESTAMP_NONCANONICAL" in {issue.code for issue in issues}
