output "schedule_arn" {
  description = "ARN of the example schedule."
  value       = module.nightly_example_job.schedule_arn
}

output "task_definition_arn" {
  description = "ARN of the example ECS task definition."
  value       = module.nightly_example_job.task_definition_arn
}

output "target_errors_alarm_name" {
  description = "CloudWatch alarm name for Scheduler target errors."
  value       = module.nightly_example_job.target_errors_alarm_name
}
