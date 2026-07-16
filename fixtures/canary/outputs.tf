output "canary" {
  description = "Secret-free disabled canary identifiers and PUBLISHED CONFIG evidence."
  value = {
    config_hash           = local.config_version
    config_lifecycle      = "PUBLISHED"
    job_id                = var.job_id
    log_group_name        = aws_cloudwatch_log_group.canary.name
    notification_sink_arn = aws_sqs_queue.test_notification_sink.arn
    ownership_generation  = var.ownership_generation
    roles = {
      execution_arn = aws_iam_role.execution.arn
      execution_id  = aws_iam_role.execution.unique_id
      launch_arn    = aws_iam_role.launch.arn
      launch_id     = aws_iam_role.launch.unique_id
      task_arn      = aws_iam_role.task.arn
      task_id       = aws_iam_role.task.unique_id
    }
    schedule_arn               = aws_scheduler_schedule.canary.arn
    scheduler_dlq_arn          = var.cell_scheduler_dlq_arn
    scheduler_source_queue_arn = var.cell_scheduler_source_queue_arn
    task_definition_arn        = aws_ecs_task_definition.canary.arn
    task_revision              = aws_ecs_task_definition.canary.revision
  }
}
