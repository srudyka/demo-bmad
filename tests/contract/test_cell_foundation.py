from __future__ import annotations

import hashlib
import re
from pathlib import Path

from tests.contract.support.contracts import (
    build_schema_registry,
    canonical_json_bytes,
    cell_contract_checksum,
    load_json_strict,
    validate_contract_instance,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"
MODULE_ROOT = REPOSITORY_ROOT / "modules" / "ecs-scheduled-job-platform"
FOUNDATION_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "contract"
    / "fixtures"
    / "cell-foundation-contract.json"
)


def module_contents(filename: str) -> str:
    return (MODULE_ROOT / filename).read_text(encoding="utf-8")


def test_cell_foundation_declares_only_owned_bootstrap_registration_config_and_discovery() -> (
    None
):
    contents = module_contents("main.tf")

    for address in (
        'resource "aws_dynamodb_table" "namespace_registry"',
        'resource "aws_dynamodb_table" "configuration_registry"',
        'resource "aws_s3_bucket" "config_inbox"',
        'resource "aws_s3_bucket_logging" "config_inbox"',
        'resource "aws_ssm_parameter" "cell_contract"',
        'resource "aws_dynamodb_table_item" "canary_job_reservation"',
        'resource "aws_iam_role" "process_manager"',
        'resource "aws_scheduler_schedule_group" "cell"',
        'resource "aws_sqs_queue" "scheduler_ingress"',
    ):
        assert address in contents

    prohibited = (
        "aws_ecs_task_definition",
        'resource "aws_scheduler_schedule"',
        "aws_sns_topic",
        "terraform_remote_state",
    )
    assert not any(resource in contents for resource in prohibited)


def test_cell_canary_bootstrap_has_no_runtime_processing_or_launch_authority() -> None:
    contents = module_contents("main.tf")

    for requirement in (
        'name                 = "${local.name_prefix}-process-manager-v1"',
        'identifiers = ["lambda.amazonaws.com"]',
        "permissions_boundary = var.permissions_boundary_arn",
        'name                       = "${local.name_prefix}-scheduler-ingress"',
        'name                      = "${local.name_prefix}-scheduler-dlq"',
        "message_retention_seconds = 1209600",
        "maxReceiveCount     = 5",
        'identifiers = ["scheduler.amazonaws.com"]',
        "aws_scheduler_schedule_group.cell.arn",
        "aws_iam_role.canary_config_publisher.arn",
        "prevent_destroy      = true",
        "replace_triggered_by = [terraform_data.canary_reservation_identity]",
        'resource "aws_lambda_function" "evidence_normalizer"',
        'resource "aws_lambda_event_source_mapping" "evidence_normalizer"',
        'function_response_types            = ["ReportBatchItemFailures"]',
        "visibility_timeout_seconds = 6 * var.normalizer.timeout_seconds + var.normalizer.batch_window_seconds",
        'sid       = "UseOnlyCellQueueKeys"',
        'variable = "kms:EncryptionContext:aws:sqs:arn"',
        "schedule/${aws_scheduler_schedule_group.cell.name}/${local.name_prefix}-canary",
    ):
        assert requirement in contents

    for prohibited in (
        "ecs:RunTask",
        "iam:PassRole",
        "aws_sns_topic",
    ):
        assert prohibited not in contents


def test_cell_contract_includes_the_new_cell_owned_canary_integrations() -> None:
    contents = module_contents("main.tf")
    for integration in (
        "canary_config_publisher = {",
        "process_manager = {",
        "scheduler_dlq = {",
        "scheduler_ingress = {",
        "scheduler_schedule_group = {",
        "normalizer_ingress = {",
        "normalizer_quarantine = {",
        "evidence_normalizer = {",
        "materializer_ingress = {",
        "materializer_dlq = {",
        "occurrence_materializer = {",
        "materializer_tick = {",
    ):
        assert integration in contents
    assert "aws_iam_role.process_manager.arn" in contents
    assert "aws_sqs_queue.scheduler_ingress.arn" in contents
    assert "aws_cloudwatch_event_rule.materializer_tick.arn" in contents


def test_cell_foundation_storage_and_recovery_controls_are_explicit() -> None:
    contents = module_contents("main.tf")

    for requirement in (
        "force_destroy = false",
        'sse_algorithm     = "aws:kms"',
        "bucket_key_enabled = true",
        'status = "Enabled"',
        "block_public_acls       = true",
        "ignore_public_acls      = true",
        "block_public_policy     = true",
        "restrict_public_buckets = true",
        'object_ownership = "BucketOwnerEnforced"',
        "point_in_time_recovery",
        "deletion_protection_enabled",
        "NonCanonicalConfigObjectKey",
        "DenyInsecureTransport",
        "DenyUnencryptedConfigWrites",
        "DenyUnregisteredConfigWriter",
        "DenyConfigOverwriteWithoutIfNoneMatch",
        "target_bucket = var.access_log_bucket_name",
        "ACCESS_LOG_BUCKET_MUST_BE_SEPARATE",
        "CELL_CONTRACT_STANDARD_TIER_LIMIT",
        "KMS_KEY_REGION_MISMATCH",
    ):
        assert requirement in contents

    assert re.search(r"^\s*expiration\s*\{", contents, re.MULTILINE) is None
    assert "noncurrent_version_expiration" not in contents
    assert "aws_s3_bucket_notification" not in contents


def test_namespace_contract_defines_deterministic_conditional_failures() -> None:
    contents = (MODULE_ROOT / "README.md").read_text(encoding="utf-8")
    for code in (
        "NAMESPACE_DUPLICATE_RESERVATION",
        "NAMESPACE_CROSS_NAMESPACE_CLAIM",
        "NAMESPACE_STALE_OWNER_GENERATION",
        "NAMESPACE_UNAUTHORIZED_MUTATION",
        "NAMESPACE_TOMBSTONED_JOB_ID",
        "NAMESPACE_TRANSFER_CONDITION_FAILED",
    ):
        assert code in contents
    assert "ConditionExpression" in contents
    for requirement in (
        "PK=NAMESPACE#<environment>#<application>",
        "SK=AUTHORIZATION",
        "PK=JOB#<job_id>",
        "SK=RESERVATION",
        "attribute_not_exists(pk) AND attribute_not_exists(sk)",
        "owner_generation = :expected_owner_generation",
        "transfer_state = :quiescent",
        "PK=JOB#<job_id>` and `SK=CONFIG#<config_version>",
    ):
        assert requirement in contents


def test_contract_ownership_uses_ssm_discovery_and_canonical_config_key() -> None:
    ownership = load_json_strict(CONTRACTS_ROOT / "v1" / "catalogs" / "ownership.json")
    edges = {edge["integration"]: edge for edge in ownership["edges"]}

    assert edges["cell-contract-publication"]["resource_arn_shape"] == (
        "arn:aws:ssm:<region>:<account>:parameter/"
        "platform/ecs-scheduled-jobs/<environment>/<region>/contract"
    )
    assert edges["job-config-publication"]["resource_arn_shape"] == (
        "arn:aws:s3:::<cell-config-bucket>/jobs/<job-id>/config/<config-version>.json"
    )


def test_cell_contract_checksum_is_semantic_and_fixture_backed() -> None:
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "schemas" / "valid-instances.json"
    )
    cell_contract = next(
        case["instance"] for case in fixture["cases"] if case["name"] == "cell contract"
    )
    schemas, registry = build_schema_registry(CONTRACTS_ROOT / "v1" / "schemas")

    assert cell_contract["checksum"] == cell_contract_checksum(cell_contract)
    assert (
        validate_contract_instance(
            schemas[
                "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:cell-contract"
            ],
            cell_contract,
            registry,
            secret_policy=load_json_strict(
                CONTRACTS_ROOT / "v1" / "catalogs" / "secret-safety.json"
            ),
        )
        == ()
    )

    changed = dict(cell_contract)
    changed["metric_namespace"] = "Platform/Changed"
    assert cell_contract_checksum(changed) != cell_contract["checksum"]


def test_generated_cell_foundation_contract_has_independent_jcs_proof() -> None:
    cell_contract = load_json_strict(FOUNDATION_FIXTURE)
    schemas, registry = build_schema_registry(CONTRACTS_ROOT / "v1" / "schemas")

    body = dict(cell_contract)
    body.pop("checksum")
    assert cell_contract["checksum"] == (
        "42ed9d18a3d0e7d09873c5f14eabc00a28625deaf19904251f12d85f3ea5c857"
    )
    assert (
        cell_contract["checksum"]
        == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    assert (
        validate_contract_instance(
            schemas[
                "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:cell-contract"
            ],
            cell_contract,
            registry,
            secret_policy=load_json_strict(
                CONTRACTS_ROOT / "v1" / "catalogs" / "secret-safety.json"
            ),
        )
        == ()
    )

    contents = module_contents("main.tf")
    for integration in (
        "config_inbox",
        "configuration_registry",
        "namespace_registry",
    ):
        assert integration in contents
    assert "aws_s3_bucket_notification" not in contents


def test_cell_contract_rejects_invalid_checksum_identity_and_ranges() -> None:
    cell_contract = load_json_strict(FOUNDATION_FIXTURE)
    schemas, registry = build_schema_registry(CONTRACTS_ROOT / "v1" / "schemas")
    schema = schemas[
        "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:cell-contract"
    ]

    invalid_checksum = dict(cell_contract)
    invalid_checksum["checksum"] = "0" * 64
    invalid_path = dict(cell_contract)
    invalid_path["discovery_path"] = (
        "/platform/ecs-scheduled-jobs/prod/us-east-1/contract"
    )
    invalid_ranges = dict(cell_contract)
    invalid_ranges["supported_ranges"] = dict(cell_contract["supported_ranges"])
    invalid_ranges["supported_ranges"]["config"] = "definitely-not-a-range"

    for invalid, expected_code in (
        (invalid_checksum, "CELL_CONTRACT_CHECKSUM_MISMATCH"),
        (invalid_path, "CELL_CONTRACT_DISCOVERY_PATH_MISMATCH"),
        (invalid_ranges, "CELL_CONTRACT_RANGE_INVALID"),
    ):
        issues = validate_contract_instance(schema, invalid, registry)
        assert expected_code in {issue.code for issue in issues}


def test_terraform_contract_checksum_uses_only_ascii_restricted_values() -> None:
    contents = module_contents("main.tf")
    variables = module_contents("variables.tf")

    assert "sha256(jsonencode(local.cell_contract_body))" in contents
    assert "local.cell_contract_json_is_jcs_safe" in contents
    assert "CELL_CONTRACT_JSON_NOT_JCS_SAFE" in contents
    assert "CELL_CONTRACT_STANDARD_TIER_LIMIT" in contents
    assert "^[ -~]+$" in variables


def test_module_source_has_no_secrets_or_hard_coded_deployment_identity() -> None:
    source = "\n".join(
        module_contents(filename)
        for filename in ("main.tf", "variables.tf", "outputs.tf")
    )
    assert not re.search(r"AKIA[0-9A-Z]{16}", source)
    assert "111111111111" not in source
    assert hashlib.sha256(source.encode("utf-8")).hexdigest()


def test_cell_security_scan_exceptions_are_narrow_and_documented() -> None:
    validation = (REPOSITORY_ROOT / "scripts" / "validate.py").read_text(
        encoding="utf-8"
    )
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

    assert '"security:terraform:platform-cell"' in validation
    assert '"modules/ecs-scheduled-job-platform"' in validation
    assert (
        '"--skip-check",\n            "CKV_AWS_50,CKV_AWS_116,CKV_AWS_117,CKV_AWS_144,CKV_AWS_272,CKV_AWS_301,CKV_AWS_356,CKV2_AWS_51,CKV2_AWS_62"'
        in validation
    )
    assert "checkov:skip=CKV_AWS_144" not in module_contents("main.tf")
    assert "CKV_AWS_144" in readme
    assert "CKV2_AWS_62" in readme
    assert "CKV_AWS_117" in readme
    assert re.search(r"automatic cross-Region\s+failover", readme)
    assert "event consumer" in readme
