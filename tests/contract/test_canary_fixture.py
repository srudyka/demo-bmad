from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path

from tests.contract.support.contracts import (
    build_schema_registry,
    canonical_json_bytes,
    config_hash,
    schedule_generation,
    validate_contract_instance,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "fixtures" / "canary"
CELL_ROOT = REPOSITORY_ROOT / "modules" / "ecs-scheduled-job-platform"
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts"


def fixture_contents(filename: str) -> str:
    return (FIXTURE_ROOT / filename).read_text(encoding="utf-8")


def test_canary_fixture_is_an_isolated_locked_backend_free_root() -> None:
    for filename in (
        "main.tf",
        "variables.tf",
        "outputs.tf",
        "versions.tf",
        "README.md",
        ".terraform.lock.hcl",
    ):
        assert (FIXTURE_ROOT / filename).is_file(), filename

    contents = "\n".join(
        fixture_contents(filename)
        for filename in ("main.tf", "variables.tf", "outputs.tf", "versions.tf")
    )
    assert 'backend "' not in contents
    assert "terraform_remote_state" not in contents
    assert 'provider "aws"' in fixture_contents("main.tf")
    assert 'alias               = "config_publisher"' in fixture_contents("main.tf")


def test_canary_fixture_keeps_cell_ownership_boundaries_intact() -> None:
    contents = fixture_contents("main.tf")
    for prohibited in (
        'resource "aws_dynamodb_table',
        'resource "aws_sqs_queue_policy"',
        'resource "aws_scheduler_schedule_group"',
        'resource "aws_ssm_parameter"',
        "aws_dynamodb_table_item",
    ):
        assert prohibited not in contents

    assert contents.count('resource "aws_sqs_queue"') == 1
    assert 'resource "aws_sqs_queue" "test_notification_sink"' in contents

    assert 'resource "aws_s3_object" "config_candidate"' in contents
    assert "provider               = aws.config_publisher" in contents
    assert "prevent_destroy = true" in contents


def test_canary_roles_network_schedule_and_config_are_narrow_and_disabled() -> None:
    contents = fixture_contents("main.tf")
    variables = fixture_contents("variables.tf")

    for role in ("launch", "execution", "task", "scheduler_delivery"):
        assert f'resource "aws_iam_role" "{role}"' in contents
    assert 'identifiers = ["ecs-tasks.amazonaws.com"]' in contents
    assert "var.cell_process_manager_role_arn" in contents
    assert "local.schedule_arn" in contents
    assert 'variable = "aws:SourceArn"' in contents
    assert 'actions   = ["iam:PassRole"]' in contents
    assert 'variable = "iam:PassedToService"' in contents
    assert "ecs:RunTask" not in contents
    assert 'state                        = "DISABLED"' in contents
    assert "arn      = var.cell_scheduler_source_queue_arn" in contents
    assert 'mode = "OFF"' in contents
    assert 'assign_public_ip   = "DISABLED"' in contents
    assert "repository@sha256" in variables
    assert "FARGATE_CPU_MEMORY_INVALID" in contents
    assert "CANARY_CELL_INPUT_MISMATCH" in contents
    assert "CANARY_SCHEDULE_INVALID" in contents
    assert "CANARY_ECR_IMAGE_MISMATCH" in contents
    assert "retention_in_days = var.log_retention_days" in contents
    assert 'resource "aws_sqs_queue" "test_notification_sink"' in contents
    assert "message_retention_seconds = 1209600" in contents
    assert 'scheduler_scheduled_time = "<aws.scheduler.scheduled-time>"' in contents
    assert (
        "occurrence_id"
        not in contents.split("input = jsonencode({", 1)[1].split("})", 1)[0]
    )
    assert 'event_type               = "occurrence.launch.v1"' in contents
    assert "source_queue_arn         = var.cell_scheduler_source_queue_arn" in contents
    assert 'session_name = "platform-canary-config-publisher"' in contents
    assert (
        "tags = {"
        not in contents.split('provider "aws" {', 2)[2].split("locals {", 1)[0]
    )
    assert 'config_lifecycle      = "PUBLISHED"' in fixture_contents("outputs.tf")


def test_canary_config_is_content_addressed_and_secret_free() -> None:
    contents = fixture_contents("main.tf")
    outputs = fixture_contents("outputs.tf")

    for requirement in (
        "deployment_identity_id = sha256(jsonencode(local.deployment_identity))",
        "config_version = sha256(jsonencode(local.config_body))",
        'sha256("schedule/v1\\n${jsonencode(local.schedule_contract)}")',
        'key                    = "jobs/${var.job_id}/config/${local.config_version}.json"',
        "secret_references",
        'server_side_encryption = "aws:kms"',
        "CONFIG_VERSION_INVALID",
    ):
        assert requirement in contents
    assert "secret_references" not in outputs
    assert re.search(r"JOB_COMPLETED_SUCCESSFULLY", contents)


def test_canary_config_and_deployment_identity_use_strict_contract_helpers() -> None:
    schemas, registry = build_schema_registry(CONTRACTS_ROOT / "v1" / "schemas")
    task_definition_arn = (
        "arn:aws:ecs:us-east-1:111111111111:task-definition/dev-platform-canary:1"
    )
    deployment_identity = {
        "account_id": "111111111111",
        "artifact_checksums": {"config_schema": "a" * 64},
        "contract_version": "1.0.0",
        "environment": "dev",
        "image_digest": f"sha256:{'b' * 64}",
        "module_versions": {"ecs_scheduled_job": "1.0.0"},
        "region": "us-east-1",
        "resolved_platform": {"fargate": "LATEST", "lambda_runtime": "python3.14"},
        "source_commit": "c" * 40,
        "task_definition_arn": task_definition_arn,
        "tool_versions": {"terraform": "1.15.8"},
        "workflow": {
            "job_workflow_ref": "org/repository/.github/workflows/apply.yml@deadbeef",
            "run_id": 1,
            "workflow_sha": "d" * 40,
        },
    }
    deployment_identity_document = {
        "deployment_identity_id": sha256(
            canonical_json_bytes(deployment_identity)
        ).hexdigest(),
        "identity": deployment_identity,
        "schema_version": "1.0.0",
    }
    schedule = {
        "activation_end": None,
        "activation_start": "2027-01-01T00:00:00.000Z",
        "evaluator_version": "schedule-evaluator/1.0.0",
        "expression": "rate(1 day)",
        "flexible_time_window": "OFF",
        "start_anchor": "2027-01-01T00:00:00.000Z",
        "time_zone": "UTC",
        "tzdb_version": "2026b",
    }
    config = {
        "cluster_arn": "arn:aws:ecs:us-east-1:111111111111:cluster/dev-platform",
        "completion_window_seconds": 3600,
        "deployment_identity_id": deployment_identity_document[
            "deployment_identity_id"
        ],
        "job_id": "dev/platform/canary",
        "logs": {
            "log_group_arn": "arn:aws:logs:us-east-1:111111111111:log-group:/platform/jobs/dev-platform-canary:*",
            "retention_days": 30,
        },
        "network": {
            "assign_public_ip": "DISABLED",
            "security_group_ids": ["sg-0123abcd"],
            "subnet_ids": ["subnet-0123abcd"],
        },
        "notification_target_arn": "arn:aws:sns:us-east-1:111111111111:dev-platform-canary-test-notifications",
        "overlap_policy": "APPLICATION_IDEMPOTENT",
        "owner_generation": 1,
        "role_arns": {
            "execution": "arn:aws:iam::111111111111:role/dev-platform-canary-execution",
            "launch": "arn:aws:iam::111111111111:role/dev-platform-canary-launch",
            "task": "arn:aws:iam::111111111111:role/dev-platform-canary-task",
        },
        "schedule": schedule,
        "schedule_arn": "arn:aws:scheduler:us-east-1:111111111111:schedule/dev-platform-scheduler/dev-platform-canary",
        "schedule_generation": schedule_generation(schedule),
        "scheduler_delivery_role_id": "AROASCHEDULEREXAMPLE",
        "secret_references": [],
        "task_definition_arn": task_definition_arn,
    }
    config_document = {
        "config": config,
        "config_version": config_hash(config),
        "schema_version": "1.0.0",
    }
    assert (
        validate_contract_instance(
            schemas[
                "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:deployment-identity"
            ],
            deployment_identity_document,
            registry,
        )
        == ()
    )
    assert (
        validate_contract_instance(
            schemas["urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:config"],
            config_document,
            registry,
        )
        == ()
    )


def test_cell_bootstrap_limits_the_if_none_match_exception_to_the_canary_role() -> None:
    contents = (CELL_ROOT / "main.tf").read_text(encoding="utf-8")
    match = re.search(
        r'sid\s+=\s+"DenyConfigOverwriteWithoutIfNoneMatch"(?P<body>.*?)\n  }',
        contents,
        re.DOTALL,
    )
    assert match is not None
    assert "ArnNotEquals" in match.group("body")
    assert "aws:PrincipalArn" in match.group("body")
    assert "aws_iam_role.canary_config_publisher.arn" in match.group("body")
    assert "not_principals" not in match.group("body")
