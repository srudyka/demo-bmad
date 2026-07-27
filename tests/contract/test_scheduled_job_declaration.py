from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"


def test_job_module_has_required_iam_interface_and_no_future_workload_resources() -> (
    None
):
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
        "permissions_boundary_arn",
        "cell_process_manager_role_arn",
        "ecr_repository_arn",
        "secret_mode",
        "secret_kms_key_arn",
        "application_secret_network_path",
        "customer_managed_policy_attachments",
    ):
        assert f'variable "{name}"' in variables
    assert 'data "aws_ssm_parameter" "cell_contract"' in main
    assert 'resource "terraform_data" "declaration_validation"' in main
    assert (
        'resource "aws_iam_role" "launch"' in main
        or 'resource "aws_iam_role" "launch"' in (MODULE / "iam.tf").read_text()
    )
    assert 'resource "aws_iam_role" "execution"' in (MODULE / "iam.tf").read_text()
    assert 'resource "aws_iam_role" "task"' in (MODULE / "iam.tf").read_text()
    assert 'output "job_id"' in outputs
    assert 'output "reservation"' in outputs
    assert 'output "job_iam"' in outputs
    for prohibited in (
        'resource "aws_cloudwatch_metric_alarm"',
        "terraform_remote_state",
        "null_resource",
        "secret_value",
    ):
        assert all(prohibited not in path.read_text() for path in MODULE.glob("*.tf"))


def test_job_iam_policies_keep_responsibilities_separate() -> None:
    iam = (MODULE / "iam.tf").read_text()
    assert 'sid       = "RunCanonicalJobTaskFamily"' in iam
    assert 'sid       = "PassOnlyThisJobsEcsRoles"' in iam
    assert 'variable = "iam:PassedToService"' in iam
    assert 'sid       = "EcrAuthorizationTokenServiceRequiredWildcard"' in iam
    assert 'sid       = "WriteOnlyThisJobsLogs"' in iam
    assert "aws:SourceAccount" in iam
    assert "aws:SourceArn" in iam
    assert (
        "iam:PassRole" not in iam.split('data "aws_iam_policy_document" "task"', 1)[1]
    )


def test_basic_example_is_synthetic_and_immutable() -> None:
    example = (MODULE / "examples" / "basic" / "main.tf").read_text()
    assert "example.invalid" in example
    assert "@sha256:" in example
    assert ":latest" not in example
    assert ".tfvars" not in example


def test_completion_evidence_is_cell_contract_bound_and_occurrence_aware() -> None:
    completion = (MODULE / "completion.tf").read_text()
    main = (MODULE / "main.tf").read_text()
    platform = (ROOT / "modules" / "ecs-scheduled-job-platform" / "main.tf").read_text()

    assert (
        'resource "aws_cloudwatch_log_subscription_filter" "completion"' in completion
    )
    assert "local.completion_filter_pattern" in completion
    assert "source_account = var.account_id" in completion
    assert 'var.completion_policy.detection_mode == "occurrence-aware"' in completion
    assert (
        'resource "aws_cloudwatch_log_metric_filter" "best_effort_success"'
        in completion
    )
    assert "dimensions = {}" in platform
    assert "terraform_data.declaration_validation" in completion
    assert "operational_metadata" in main
    assert 'auth_mode        = "CELL_LOG_SUBSCRIPTION"' in platform
    assert "log_ingestor" in platform
