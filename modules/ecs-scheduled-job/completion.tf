resource "aws_lambda_permission" "log_ingestor" {
  count          = var.completion_policy.detection_mode == "occurrence-aware" ? 1 : 0
  statement_id   = "AllowExactJobLogGroupCompletion"
  action         = "lambda:InvokeFunction"
  function_name  = local.contract_integrations.log_ingestor.arn
  principal      = "logs.${var.region}.amazonaws.com"
  source_account = var.account_id
  source_arn     = "${aws_cloudwatch_log_group.job.arn}:*"
}

resource "aws_cloudwatch_log_subscription_filter" "completion" {
  count           = var.completion_policy.detection_mode == "occurrence-aware" ? 1 : 0
  name            = "${local.name_prefix}-completion"
  log_group_name  = aws_cloudwatch_log_group.job.name
  filter_pattern  = local.completion_filter_pattern
  destination_arn = local.contract_integrations.log_ingestor.arn

  depends_on = [aws_lambda_permission.log_ingestor, terraform_data.declaration_validation]
}

resource "aws_cloudwatch_log_metric_filter" "best_effort_success" {
  count          = var.completion_policy.detection_mode == "best-effort" ? 1 : 0
  name           = "${local.name_prefix}-best-effort-success"
  log_group_name = aws_cloudwatch_log_group.job.name
  pattern        = local.completion_filter_pattern

  metric_transformation {
    name      = "BestEffortCompletionMarker"
    namespace = "cell/jobs"
    value     = "1"
    dimensions = {
      job_id      = local.job_id
      environment = var.environment
      state       = "MARKER_SEEN"
    }
  }
}
