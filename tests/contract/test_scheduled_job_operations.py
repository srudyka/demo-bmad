import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"


def test_operational_output_contract_is_explicit_and_redacted() -> None:
    outputs = (MODULE / "outputs.tf").read_text()
    required_outputs = {
        "job_identity",
        "schedule",
        "task",
        "logs",
        "config",
        "operations",
        "alarms",
        "dashboard",
    }
    for name in required_outputs:
        assert f'output "{name}"' in outputs
    assert "type = object({" in outputs
    assert "sensitive" in outputs
    assert "raw_config" not in outputs.lower()
    assert "validation_evidence    =" not in outputs
    assert "validation_evidence_hash" in outputs
    assert "secret_values" not in outputs


def test_deployment_identity_has_bounded_optional_workflow_metadata() -> None:
    variables = (MODULE / "variables.tf").read_text()
    main = (MODULE / "main.tf").read_text()
    task = (MODULE / "task.tf").read_text()
    for name in ("workflow_identity", "deployment_run_reference"):
        assert f'variable "{name}"' in variables
        assert name in main
    assert "task_definition_revision" in main
    assert "image_digest" in main
    assert "DEPLOYMENT_IDENTITY" in task
    assert "workflow_identity" in task
    assert "deployment_run_reference" in task


def test_optional_dashboard_is_fixed_bounded_and_job_owned() -> None:
    dashboard = (MODULE / "dashboard.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    catalog = json.loads((ROOT / "contracts/v1/catalogs/dashboard.json").read_text())
    for name in ("dashboard", "aws_cloudwatch_dashboard"):
        assert name in dashboard
    for widget in catalog["widgets"]:
        assert "widget.metric" in dashboard
        assert "widget.dimensions" in dashboard
        assert all(
            dimension
            in {
                "QueueName",
                "LogGroupName",
                "cell_id",
                "component",
                "environment",
                "failure_plane",
                "job_id",
                "state",
            }
            for dimension in widget["dimensions"]
        )
        assert not set(widget["dimensions"]) & {
            "occurrence_id",
            "task_arn",
            "log_stream",
            "error_text",
        }
    assert "SEARCH(" not in dashboard
    assert 'variable "dashboard"' in variables
    assert "max_widgets" in variables
    assert "max_metrics" in variables
    assert "max_queries" in variables
    assert "estimated_monthly_cost_usd" in variables


def test_dashboard_disabled_does_not_own_required_signal_resources() -> None:
    dashboard = (MODULE / "dashboard.tf").read_text()
    assert "dashboard_enabled" in dashboard
    assert "count          = local.dashboard_enabled ? 1 : 0" in dashboard
    assert (
        "var.dashboard.enabled ? local.dashboard_widget_count : 0"
        in (MODULE / "outputs.tf").read_text()
    )
    assert 'resource "aws_cloudwatch_metric_alarm"' not in dashboard
    assert 'resource "aws_cloudwatch_log_group"' not in dashboard
    assert 'resource "aws_sqs_queue"' not in dashboard
    assert "dashboard_enabled" in dashboard


def test_operator_documentation_uses_outputs_not_terraform_state() -> None:
    readme = (MODULE / "README.md").read_text()
    for term in (
        "Operational Outputs",
        "aws scheduler get-schedule",
        "aws ecs describe-tasks",
        "aws logs",
        "CONFIG acknowledgement",
        "Cell health",
        "Terraform state",
        "dashboard",
        "rollback",
    ):
        assert term.lower() in readme.lower()
    assert "terraform show" not in readme.lower()


def test_contract_and_identity_guards_are_declared() -> None:
    main = (MODULE / "main.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    assert "notification_target_arn" in main
    assert "alert_router.notification_target_arn" in main
    assert "required_operational_integrations_available" in outputs
    assert "cell_config_acknowledgement.config.result" in outputs
    for field in (
        "schedule_generation",
        "cell_contract_version",
        "cell_contract_checksum",
        "task_definition_revision",
        "config_hash",
    ):
        assert field in main or field in outputs
    assert "workflow_identity" in variables
    assert "deployment_run_reference" in variables
