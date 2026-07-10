output "name" {
  description = "Predictable resource name prefix derived from required tags."
  value       = local.name
}

output "cluster_name" {
  description = "Configured ECS cluster name."
  value       = var.cluster_name
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition used by the schedule."
  value       = aws_ecs_task_definition.this.arn
}

output "task_definition_family" {
  description = "ECS task definition family name."
  value       = aws_ecs_task_definition.this.family
}

output "execution_role_arn" {
  description = "ARN of the ECS task execution role."
  value       = aws_iam_role.execution.arn
}

output "execution_role_name" {
  description = "Name of the ECS task execution role."
  value       = aws_iam_role.execution.name
}

output "task_role_arn" {
  description = "ARN of the ECS application task role."
  value       = aws_iam_role.task.arn
}

output "task_role_name" {
  description = "Name of the ECS application task role."
  value       = aws_iam_role.task.name
}

output "scheduler_role_arn" {
  description = "ARN of the EventBridge Scheduler invocation role."
  value       = aws_iam_role.scheduler.arn
}

output "schedule_arn" {
  description = "Expected EventBridge Scheduler schedule ARN."
  value       = local.schedule_arn
}

output "schedule_name" {
  description = "EventBridge Scheduler schedule name."
  value       = aws_scheduler_schedule.this.name
}

output "schedule_group_name" {
  description = "EventBridge Scheduler schedule group name."
  value       = aws_scheduler_schedule.this.group_name
}

output "log_group_name" {
  description = "CloudWatch log group name for container logs."
  value       = aws_cloudwatch_log_group.this.name
}

output "log_group_arn" {
  description = "CloudWatch log group ARN for container logs."
  value       = aws_cloudwatch_log_group.this.arn
}

output "task_failure_log_group_name" {
  description = "CloudWatch log group name for ECS task stopped failure events."
  value       = aws_cloudwatch_log_group.ecs_task_failures.name
}

output "task_failure_log_group_arn" {
  description = "CloudWatch log group ARN for ECS task stopped failure events."
  value       = aws_cloudwatch_log_group.ecs_task_failures.arn
}

output "dlq_arn" {
  description = "SQS dead-letter queue ARN for failed scheduler deliveries."
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_url" {
  description = "SQS dead-letter queue URL for failed scheduler deliveries."
  value       = aws_sqs_queue.dlq.url
}

output "alarm_names" {
  description = "CloudWatch alarm names created by the module."
  value = {
    ecs_task_failures             = aws_cloudwatch_metric_alarm.ecs_task_failures.alarm_name
    scheduler_target_errors       = aws_cloudwatch_metric_alarm.scheduler_target_errors.alarm_name
    scheduler_dropped_invocations = aws_cloudwatch_metric_alarm.scheduler_dropped_invocations.alarm_name
    dlq_oldest_message_age        = aws_cloudwatch_metric_alarm.dlq_oldest_message_age.alarm_name
  }
}

output "alarm_arns" {
  description = "CloudWatch alarm ARNs created by the module."
  value = {
    ecs_task_failures             = aws_cloudwatch_metric_alarm.ecs_task_failures.arn
    scheduler_target_errors       = aws_cloudwatch_metric_alarm.scheduler_target_errors.arn
    scheduler_dropped_invocations = aws_cloudwatch_metric_alarm.scheduler_dropped_invocations.arn
    dlq_oldest_message_age        = aws_cloudwatch_metric_alarm.dlq_oldest_message_age.arn
  }
}
