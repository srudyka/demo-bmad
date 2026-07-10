output "schedule_name" {
  description = "Created EventBridge Scheduler schedule name."
  value       = module.example_report_job.schedule_name
}

output "task_definition_arn" {
  description = "Created ECS task definition ARN."
  value       = module.example_report_job.task_definition_arn
}

output "log_group_name" {
  description = "CloudWatch log group for container output."
  value       = module.example_report_job.log_group_name
}

output "scheduler_dlq_arn" {
  description = "Scheduler delivery failure DLQ ARN."
  value       = module.example_report_job.scheduler_dlq_arn
}
