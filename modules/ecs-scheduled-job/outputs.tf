output "schedule_arn" {
  description = "ARN of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.this.arn
}

output "schedule_group_name" {
  description = "Name of the EventBridge Scheduler group used for job-scoped metrics."
  value       = aws_scheduler_schedule_group.this.name
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition revision."
  value       = aws_ecs_task_definition.this.arn
}

output "task_execution_role_arn" {
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

output "log_group_name" {
  description = "CloudWatch log group for the scheduled task."
  value       = aws_cloudwatch_log_group.this.name
}

output "target_errors_alarm_name" {
  description = "CloudWatch alarm name for Scheduler target errors."
  value       = aws_cloudwatch_metric_alarm.target_errors.alarm_name
}

output "dropped_invocations_alarm_name" {
  description = "CloudWatch alarm name for dropped Scheduler invocations."
  value       = aws_cloudwatch_metric_alarm.dropped_invocations.alarm_name
}

output "task_failures_event_rule_name" {
  description = "EventBridge rule name for ECS stopped task events with non-zero container exit codes."
  value       = aws_cloudwatch_event_rule.task_failures.name
}
