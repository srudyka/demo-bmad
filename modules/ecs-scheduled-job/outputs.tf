output "name" {
  description = "Stable scheduled job name."
  value       = local.name
}

output "schedule_name" {
  description = "EventBridge Scheduler schedule name."
  value       = aws_scheduler_schedule.this.name
}

output "schedule_arn" {
  description = "EventBridge Scheduler schedule ARN."
  value       = aws_scheduler_schedule.this.arn
}

output "task_definition_arn" {
  description = "ECS task definition ARN including revision."
  value       = aws_ecs_task_definition.this.arn
}

output "task_definition_family" {
  description = "ECS task definition family."
  value       = aws_ecs_task_definition.this.family
}

output "log_group_name" {
  description = "CloudWatch log group name for container logs."
  value       = aws_cloudwatch_log_group.this.name
}

output "log_group_arn" {
  description = "CloudWatch log group ARN for container logs."
  value       = aws_cloudwatch_log_group.this.arn
}

output "scheduler_dlq_name" {
  description = "SQS DLQ name for Scheduler target delivery failures."
  value       = aws_sqs_queue.scheduler_dlq.name
}

output "scheduler_dlq_arn" {
  description = "SQS DLQ ARN for Scheduler target delivery failures."
  value       = aws_sqs_queue.scheduler_dlq.arn
}

output "scheduler_dlq_url" {
  description = "SQS DLQ URL for Scheduler target delivery failures."
  value       = aws_sqs_queue.scheduler_dlq.url
}

output "execution_role_arn" {
  description = "ECS task execution role ARN used by the task definition."
  value       = local.execution_role_arn
}

output "task_role_arn" {
  description = "ECS task role ARN used by the task definition."
  value       = local.task_role_arn
}

output "scheduler_role_arn" {
  description = "EventBridge Scheduler invocation role ARN."
  value       = local.scheduler_role_arn
}

output "task_failure_event_rule_name" {
  description = "EventBridge rule name that detects stopped tasks with non-zero container exit codes."
  value       = aws_cloudwatch_event_rule.task_failure.name
}

output "task_failure_alarm_name" {
  description = "CloudWatch alarm name for task runtime failures."
  value       = aws_cloudwatch_metric_alarm.task_failure.alarm_name
}

output "scheduler_dlq_alarm_name" {
  description = "CloudWatch alarm name for Scheduler DLQ messages."
  value       = aws_cloudwatch_metric_alarm.scheduler_dlq_visible_messages.alarm_name
}
