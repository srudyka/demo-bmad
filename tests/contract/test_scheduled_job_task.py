import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"


def test_task_definition_and_log_group_are_job_owned_and_fargate_bound() -> None:
    terraform = "\n".join(path.read_text() for path in MODULE.glob("*.tf"))
    assert 'resource "aws_ecs_task_definition" "job"' in terraform
    assert 'resource "aws_cloudwatch_log_group" "job"' in terraform
    assert 'requires_compatibilities = ["FARGATE"]' in terraform
    assert (
        'network_mode             = "awsvpc"' in terraform
        or 'network_mode = "awsvpc"' in terraform
    )
    assert "aws_iam_role.execution.arn" in terraform
    assert "aws_iam_role.task.arn" in terraform
    assert 'resource "aws_ecs_service"' not in terraform
    assert 'resource "aws_scheduler_schedule" "job"' in terraform
    assert 'resource "aws_cloudwatch_metric_alarm"' not in terraform


def test_task_inputs_cover_platform_storage_identity_and_log_contract() -> None:
    variables = (MODULE / "variables.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    readme = (MODULE / "README.md").read_text()
    for name in (
        "platform_version",
        "cpu_architecture",
        "operating_system_family",
        "ephemeral_storage_gib",
        "entrypoint",
        "secret_environment_names",
        "log_retention_days",
        "source_revision",
        "module_version",
    ):
        assert f'variable "{name}"' in variables
    for name in ("task_definition", "log_group", "deployment_identity"):
        assert f'output "{name}"' in outputs
    for term in (
        "JOB_ID",
        "OCCURRENCE_ID",
        "CONFIG_VERSION",
        "attempt_no",
        "sanitized",
        "zero exit",
        "retention",
        '"event":"start"',
        '"event":"success"',
        '"event":"failure"',
        "SECRET_REFERENCE_LOCATORS",
        "platform_version",
    ):
        assert term in readme


def test_secret_rendering_uses_locator_contract_and_reserved_fields_are_guarded() -> (
    None
):
    task = (MODULE / "task.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    assert "secret_environment_names" in task
    assert "valueFrom" in task
    assert "environment_variables" in task
    assert "reserved" in variables.lower()
    assert '"OCCURRENCE_ID"' in variables
    assert '"CONFIG_VERSION"' in variables
    assert 'var.secret_mode == "ecs-agent"' in task
    assert 'var.secret_mode == "application-pull"' in task
    assert '"SOURCE_REVISION"' in variables
    assert '"MODULE_VERSION"' in variables
    assert '"SECRET_MODE"' in variables


def test_task_preserves_revisions_and_publishes_platform_handoff() -> None:
    task = (MODULE / "task.tf").read_text()
    main = (MODULE / "main.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    assert "skip_destroy             = true" in task
    assert "platform_version = var.platform_version" in main
    assert "platform_version         = var.platform_version" in outputs


def test_basic_example_remains_secret_free_and_declares_completion_contract() -> None:
    example = (MODULE / "examples" / "basic" / "main.tf").read_text()
    assert "source_revision" in example
    assert "module_version" in example
    assert "structured" in example.lower() or "completion" in example.lower()
    assert "secret_environment_names" not in example
    assert "password" not in example.lower()


def test_task_fixture_covers_positive_and_negative_rendering_cases() -> None:
    fixture = json.loads(
        (
            ROOT / "contracts" / "v1" / "fixtures" / "task-definition" / "cases.json"
        ).read_text()
    )
    names = {case["name"] for case in fixture["cases"]}
    assert {
        "valid-fargate",
        "invalid-ephemeral-storage",
        "reserved-environment",
    } <= names

    for case in fixture["cases"]:
        inputs = case["input"]
        findings = []
        if (
            inputs.get("ephemeral_storage_gib", 21) < 21
            or inputs.get("ephemeral_storage_gib", 21) > 200
        ):
            findings.append("TASK_EPHEMERAL_STORAGE_INVALID")
        if inputs.get("environment_name") in {
            "JOB_ID",
            "OCCURRENCE_ID",
            "CONFIG_VERSION",
            "ATTEMPT_NO",
            "TASK_ARN",
        }:
            findings.append("TASK_RESERVED_ENVIRONMENT_FIELD")
        if inputs.get("image", "").endswith(":latest"):
            findings.append("TASK_IMAGE_MUTABLE")
        if inputs.get("log_driver") not in {None, "awslogs"}:
            findings.append("TASK_LOG_CONFIGURATION_INVALID")
        if inputs.get("secret_references") and len(
            inputs.get("secret_environment_names", [])
        ) != len(inputs["secret_references"]):
            findings.append("TASK_SECRET_ENVIRONMENT_MAPPING_INVALID")
        if any(
            isinstance(inputs.get(name), float) and inputs[name] != int(inputs[name])
            for name in ("cpu", "memory")
            if name in inputs
        ):
            findings.append("TASK_FARGATE_NUMBER_NOT_WHOLE")
        if inputs.get("secret_mode") == "application-pull" and inputs.get(
            "ecs_agent_secrets", False
        ):
            findings.append("TASK_APPLICATION_PULL_ECS_SECRET_INJECTION")
        assert findings == case["expected_findings"], case["name"]
