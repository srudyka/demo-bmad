output "task_definition_arn" {
  description = "ARN of the ECS task definition used by the schedule."
  value       = aws_ecs_task_definition.job.arn
}

output "schedule_arn" {
  description = "ARN of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.job.arn
}

output "schedule_name" {
  description = "Name of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.job.name
}

output "log_group_name" {
  description = "CloudWatch Log Group name for task logs."
  value       = aws_cloudwatch_log_group.job.name
}

output "task_state_event_log_group_name" {
  description = "CloudWatch Log Group name for ECS task state change events."
  value       = aws_cloudwatch_log_group.task_state_events.name
}

output "execution_role_arn" {
  description = "ARN of the ECS task execution role."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ARN of the ECS task role."
  value       = aws_iam_role.task.arn
}

output "scheduler_role_arn" {
  description = "ARN of the EventBridge Scheduler role."
  value       = aws_iam_role.scheduler.arn
}

output "dlq_arn" {
  description = "ARN of the SQS dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "alarm_arns" {
  description = "ARNs of CloudWatch alarms created for the scheduled job."
  value = {
    scheduler_target_errors = aws_cloudwatch_metric_alarm.scheduler_target_errors.arn
    task_failures           = aws_cloudwatch_metric_alarm.task_failures.arn
    dlq_visible_messages    = aws_cloudwatch_metric_alarm.dlq_visible_messages.arn
  }
}
