from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"


def test_declaration_module_has_required_interface_and_no_workload_resources() -> None:
    variables = (MODULE / "variables.tf").read_text()
    main = (MODULE / "main.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    for name in (
        "environment",
        "application",
        "job_name",
        "repository_id",
        "terraform_root_id",
        "account_id",
        "region",
        "ecs_cluster_arn",
        "image",
        "schedule_expression",
        "runtime",
        "overlap_policy",
        "networking",
        "notification",
        "secret_references",
        "permissions",
        "tags",
    ):
        assert f'variable "{name}"' in variables
    assert 'data "aws_ssm_parameter" "cell_contract"' in main
    assert 'resource "terraform_data" "declaration_validation"' in main
    assert 'output "job_id"' in outputs
    assert 'output "reservation"' in outputs
    for prohibited in (
        'resource "aws_ecs_task_definition"',
        'resource "aws_iam_role"',
        'resource "aws_scheduler_schedule"',
        "terraform_remote_state",
        "null_resource",
        "secret_value",
    ):
        assert prohibited not in main


def test_basic_example_is_synthetic_and_immutable() -> None:
    example = (MODULE / "examples" / "basic" / "main.tf").read_text()
    assert "example.invalid" in example
    assert "@sha256:" in example
    assert ":latest" not in example
    assert ".tfvars" not in example
