import hashlib
import json
from pathlib import Path

import rfc8785


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"


def test_phase_one_owns_disabled_scheduler_and_config_only() -> None:
    terraform = "\n".join(path.read_text() for path in MODULE.glob("*.tf"))
    assert 'resource "aws_scheduler_schedule" "job"' in terraform
    assert (
        'state                        = var.activation.enabled ? "ENABLED" : "DISABLED"'
        in terraform
    )
    assert 'state                        = "ENABLED"' not in terraform
    assert 'resource "cell_config_publication" "config"' in terraform
    assert "provider" in (MODULE / "phase_one.tf").read_text()
    assert "cell.publisher" in (MODULE / "phase_one.tf").read_text()
    assert (
        "publisher_role_arn    = var.config_publisher_role_arn"
        in (MODULE / "phase_one.tf").read_text()
    )
    assert (
        "config_publisher_role_arn" in (MODULE / "examples/basic/main.tf").read_text()
    )
    assert 'resource "aws_ecs_task_definition" "job"' in terraform
    assert 'resource "aws_scheduler_schedule" "job"' in terraform
    assert "arn      = local.contract_integrations.scheduler_ingress.arn" in terraform
    assert "arn = local.contract_integrations.scheduler_dlq.arn" in terraform
    assert 'resource "aws_scheduler_schedule" "job"' in terraform
    assert (
        "aws_scheduler_schedule.job"
        not in (MODULE / "phase_one.tf")
        .read_text()
        .split('resource "aws_scheduler_schedule"', 1)[0]
    )


def test_scheduler_delivery_role_is_exact_and_separate() -> None:
    phase_one = (MODULE / "phase_one.tf").read_text()
    assert 'identifiers = ["scheduler.amazonaws.com"]' in phase_one
    assert 'variable = "aws:SourceAccount"' in phase_one
    assert 'variable = "aws:SourceArn"' in phase_one
    assert "local.contract_integrations.scheduler_schedule_group.arn" in phase_one
    assert 'actions   = ["sqs:SendMessage"]' in phase_one
    assert 'actions   = ["sqs:SendMessage", "sqs:*"' not in phase_one
    assert 'actions   = ["kms:GenerateDataKey", "kms:Decrypt"]' in phase_one
    assert "local.contract_integrations.scheduler_ingress.arn" in phase_one
    assert "local.contract_integrations.scheduler_dlq.arn" in phase_one
    assert "ACTIVATION_WINDOW_INVALID" in (MODULE / "main.tf").read_text()
    assert "iana-timezones.txt" in (MODULE / "main.tf").read_text()


def test_schedule_and_config_are_content_addressed_and_secret_safe() -> None:
    main = (MODULE / "main.tf").read_text()
    phase_one = (MODULE / "phase_one.tf").read_text()
    schema = (ROOT / "contracts/v1/schemas/config.schema.json").read_text()
    assert "schedule_generation" in main
    assert 'sha256("schedule/v1\\n${jsonencode(local.schedule_body)}")' in main
    assert "config_version" in main
    assert "config_json          = jsonencode(local.config_body)" in main
    assert "config_version       = lower(sha256(local.config_json))" in main
    assert "config_hash_canonicalization" in main
    assert "object_key" in phase_one
    assert '"jobs/${local.job_id}/config/${local.config_version}.json"' in phase_one
    assert "aws_s3_object" not in phase_one
    assert "prevent_destroy = true" in phase_one
    assert "occurrence_id" not in main
    assert "secret_values" not in main
    assert '"config_version"' in schema


def test_publisher_role_and_cell_policy_are_not_ambient() -> None:
    phase_one = (MODULE / "phase_one.tf").read_text()
    platform = (ROOT / "modules" / "ecs-scheduled-job-platform" / "main.tf").read_text()
    assert "publisher_role_arn    = var.config_publisher_role_arn" in phase_one
    assert 'resource = "cell_config_publication"' not in phase_one
    assert "s3:PutObject" in platform
    assert "jobs/*/config/*.json" in platform


def test_phase_one_outputs_publish_without_authorizing_launch() -> None:
    outputs = (MODULE / "outputs.tf").read_text()
    assert 'output "phase_one"' in outputs
    assert "lifecycle" in outputs
    assert '"PUBLISHED"' in outputs
    assert "launch_authorized" in outputs
    assert "= false" in outputs
    for term in (
        "schedule_arn",
        "scheduler_delivery_role_id",
        "config_version",
        "config_key",
        "owner_generation",
        "activation_start",
    ):
        assert term in outputs


def test_phase_two_requires_exact_materialized_acknowledgement() -> None:
    phase_one = (MODULE / "phase_one.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    assert 'variable "activation"' in variables
    for field in (
        "lifecycle",
        "config_version",
        "schedule_generation",
        "schedule_arn",
        "owner_generation",
        "horizon_watermark",
        "conformance_result",
    ):
        assert field in variables
    for field in (
        "config_version",
        "schedule_generation",
        "schedule_arn",
        "owner_generation",
        "horizon_watermark",
    ):
        assert f"activation.{field}" in phase_one
    assert "activation.lifecycle" in variables
    assert "activation.conformance_result" in variables
    assert "activation.enabled" in phase_one
    assert "sha256(local.deployment_identity_json)" in phase_one
    assert (
        'required_lifecycle          = var.activation.enabled ? "MATERIALIZED" : "VALIDATED"'
        in phase_one
    )
    assert 'cell_config_acknowledgement.config.result == "MATERIALIZED"' in phase_one
    assert "cell_config_acknowledgement.config.horizon_watermark" in phase_one
    assert "cell_config_acknowledgement.config.validation_evidence" in phase_one
    assert "cell_config_acknowledgement.config]" in phase_one
    assert 'regex("^(dev|test|qa|staging)' in variables
    assert "maximum_event_age_seconds" in phase_one
    assert "maximum_retry_attempts" in phase_one
    assert '"MATERIALIZED"' in variables
    assert 'output "phase_two"' in outputs


def test_phase_two_preserves_brokered_cell_target() -> None:
    phase_one = (MODULE / "phase_one.tf").read_text()
    assert "local.contract_integrations.scheduler_ingress.arn" in phase_one
    assert "arn      = aws_ecs_cluster" not in phase_one
    assert "ecs:RunTask" not in phase_one


def test_phase_one_fixture_covers_forbidden_boundaries() -> None:
    fixture = json.loads(
        (ROOT / "contracts/v1/fixtures/phase-one/cases.json").read_text()
    )
    assert {case["name"] for case in fixture["cases"]} >= {
        "disabled-schedule-exact-queue",
        "reject-direct-ecs-target",
        "reject-config-secret-value",
        "config-hash-is-content-addressed",
        "reject-wrong-job-config-prefix",
        "reject-protected-cell-state-write",
        "reject-overwrite-without-if-none-match",
        "reject-cross-account-schedule-group",
    }
    for case in fixture["cases"]:
        if case["name"] == "config-hash-is-content-addressed":
            body = rfc8785.dumps(case["body"])
            assert hashlib.sha256(body).hexdigest() == case["config_version"]
