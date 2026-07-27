locals {
  dashboard_enabled          = var.dashboard.enabled
  dashboard_metric_namespace = try(local.contract.metric_namespace, "Platform/EcsScheduledJobs")
  dashboard_catalog          = try(jsondecode(file("${path.module}/../../contracts/v1/catalogs/dashboard.json")), null)
  dashboard_catalog_valid = try(
    local.dashboard_catalog.schema_version == "1.0.0" &&
    local.dashboard_catalog.max_widgets == 8 &&
    local.dashboard_catalog.max_metrics == 40 &&
    local.dashboard_catalog.max_queries == 0 &&
    length(local.dashboard_catalog.widgets) == 7 &&
    alltrue([for widget in local.dashboard_catalog.widgets : (
      length(widget.dimensions) > 0 &&
      alltrue([for dimension in widget.dimensions : contains(["QueueName", "LogGroupName", "cell_id", "component", "environment", "failure_plane", "job_id", "state"], dimension)]) &&
      !contains(widget.dimensions, "occurrence_id") &&
      !contains(widget.dimensions, "task_arn") &&
      !contains(widget.dimensions, "log_stream") &&
      !contains(widget.dimensions, "error_text")
    )]),
    false,
  )
  dashboard_dimension_values = {
    QueueName     = try(regex("arn:[^:]+:sqs:[^:]+:[^:]+:(.+)$", local.contract_integrations.scheduler_dlq.arn)[0], "")
    LogGroupName  = aws_cloudwatch_log_group.job.name
    cell_id       = try(local.contract.cell.cell_id, "")
    component     = "alert-router"
    environment   = var.environment
    failure_plane = "materialization"
    job_id        = local.job_id
    state         = "SUCCEEDED"
  }
  dashboard_widgets = concat([
    {
      type   = "text"
      x      = 0
      y      = 0
      width  = 24
      height = 3
      properties = {
        markdown = "# Scheduled job operations\n\n**Job:** `${local.job_id}`  \n**Runbook:** ${var.notification.runbook_uri}  \nThis optional view uses the versioned Cell dashboard catalog. Required alarms, evidence, routing, and Cell health do not depend on this dashboard."
      }
    },
    ], [for index, widget in local.dashboard_catalog.widgets : {
      type   = "metric"
      x      = 0
      y      = 3 + (index * 6)
      width  = 12
      height = 6
      properties = {
        title  = widget.title
        view   = "timeSeries"
        region = var.region
        period = var.dashboard.refresh_seconds
        start  = "-${var.dashboard.time_range_hours}h"
        stat   = widget.stat
        metrics = [concat(
          [widget.namespace == "$${cell_metric_namespace}" ? local.dashboard_metric_namespace : widget.namespace, widget.metric],
          flatten([for dimension in widget.dimensions : [dimension, lookup(local.dashboard_dimension_values, dimension, "")]]),
        )]
        yAxis = { left = { min = 0 } }
      }
  }])
  dashboard_body         = { widgets = local.dashboard_widgets }
  dashboard_body_json    = jsonencode(local.dashboard_body)
  dashboard_widget_count = length(local.dashboard_widgets)
  dashboard_metric_count = length(local.dashboard_catalog.widgets)
  dashboard_query_count  = 0
  dashboard_estimated_monthly_cost_usd = local.dashboard_enabled ? (
    (local.dashboard_widget_count * 0.01) + (local.dashboard_metric_count * 0.01)
  ) : 0
}

resource "aws_cloudwatch_dashboard" "job" {
  count          = local.dashboard_enabled ? 1 : 0
  dashboard_name = "${local.name_prefix}-operations"
  dashboard_body = local.dashboard_body_json

  lifecycle {
    precondition {
      condition = (
        local.dashboard_catalog_valid &&
        local.dashboard_widget_count <= var.dashboard.max_widgets &&
        local.dashboard_metric_count <= var.dashboard.max_metrics &&
        local.dashboard_query_count <= var.dashboard.max_queries
      )
      error_message = "DASHBOARD_CONTRACT_INVALID: generated dashboard must match the versioned metric/dimension catalog and configured limits."
    }
    precondition {
      condition     = local.dashboard_estimated_monthly_cost_usd <= var.dashboard.estimated_monthly_cost_usd
      error_message = "DASHBOARD_COST_BUDGET_EXCEEDED: configured dashboard cost budget is below the bounded estimate."
    }
  }
}
