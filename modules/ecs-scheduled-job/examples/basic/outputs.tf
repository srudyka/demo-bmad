output "schedule_name" {
  description = "Created EventBridge Scheduler schedule name."
  value       = module.scheduled_job.schedule_name
}

output "task_definition_arn" {
  description = "Created ECS task definition ARN."
  value       = module.scheduled_job.task_definition_arn
}

output "log_group_name" {
  description = "Created CloudWatch log group name."
  value       = module.scheduled_job.log_group_name
}

output "task_failure_log_group_name" {
  description = "Created ECS task failure event log group name."
  value       = module.scheduled_job.task_failure_log_group_name
}

output "dlq_url" {
  description = "Created scheduler dead-letter queue URL."
  value       = module.scheduled_job.dlq_url
}

output "alarm_names" {
  description = "Created CloudWatch alarm names."
  value       = module.scheduled_job.alarm_names
}
