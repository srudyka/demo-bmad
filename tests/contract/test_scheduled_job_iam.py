from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"


def test_roles_have_stable_identity_and_boundary_contract() -> None:
    iam = (MODULE / "iam.tf").read_text()
    main = (MODULE / "main.tf").read_text()
    assert "path                 = local.role_path" in iam
    assert "permissions_boundary = var.permissions_boundary_arn" in iam
    assert 'local.role_path             = "/platform/ecs-scheduled-jobs/' not in main
    assert 'role_path             = "/platform/ecs-scheduled-jobs/' in main
    for role in ("launch", "execution", "task"):
        assert f'resource "aws_iam_role" "{role}"' in iam


def test_trust_policies_prove_exact_principal_and_confused_deputy_guards() -> None:
    iam = (MODULE / "iam.tf").read_text()
    assert "identifiers = [var.cell_process_manager_role_arn]" in iam
    assert 'variable = "aws:PrincipalArn"' in iam
    assert 'identifiers = ["ecs-tasks.amazonaws.com"]' in iam
    assert 'variable = "aws:SourceAccount"' in iam
    assert 'variable = "aws:SourceArn"' in iam
    assert (
        "arn:${data.aws_partition.current.partition}:ecs:${var.region}:${var.account_id}:*"
        in iam
    )
    assert 'identifiers = ["*"]' not in iam


def test_launch_execution_and_task_policy_boundaries_are_separate() -> None:
    iam = (MODULE / "iam.tf").read_text()
    launch = iam.split('data "aws_iam_policy_document" "launch"', 1)[1].split(
        'resource "aws_iam_role_policy" "launch"', 1
    )[0]
    execution = iam.split('data "aws_iam_policy_document" "execution"', 1)[1].split(
        'resource "aws_iam_role_policy" "execution"', 1
    )[0]
    task = iam.split('data "aws_iam_policy_document" "task"', 1)[1].split(
        'resource "aws_iam_role_policy" "task"', 1
    )[0]
    assert 'actions   = ["ecs:RunTask"]' in launch
    assert 'actions   = ["iam:PassRole"]' in launch
    assert "aws_iam_role.execution.arn, aws_iam_role.task.arn" in launch
    assert "iam:PassedToService" in launch
    assert "EcrAuthorizationTokenServiceRequiredWildcard" in execution
    assert 'resources = ["*"]' in execution
    assert "iam:PassRole" not in execution
    assert "iam:PassRole" not in task
    assert 'resource "aws_iam_role_policy" "task"' in iam


def test_secret_modes_are_mutually_exclusive_and_outputs_are_secret_free() -> None:
    iam = (MODULE / "iam.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    assert 'var.secret_mode == "ecs-agent"' in iam
    assert 'var.secret_mode == "application-pull"' in iam
    assert "secretsmanager_references = [for reference in var.secret_references" in iam
    assert "ssm_references            = [for reference in var.secret_references" in iam
    assert "secret values" not in outputs.lower()
    assert "secret_kms_key_arn" not in outputs


def test_story_boundary_excludes_future_workload_and_cell_resources() -> None:
    terraform = "\n".join(path.read_text() for path in MODULE.glob("*.tf"))
    for prohibited in (
        'resource "aws_ecs_task_definition"',
        'resource "aws_scheduler_schedule"',
        'resource "aws_cloudwatch_log_group"',
        'resource "aws_security_group"',
        'resource "aws_dynamodb_table"',
        'resource "aws_sqs_queue"',
        'resource "aws_lambda_function"',
        "terraform_remote_state",
    ):
        assert prohibited not in terraform
