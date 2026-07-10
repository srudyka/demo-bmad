output "schedule_name" {
  description = "EventBridge Scheduler schedule name."
  value       = module.ecs_scheduled_job.schedule_name
}

output "task_definition_arn" {
  description = "ECS task definition ARN."
  value       = module.ecs_scheduled_job.task_definition_arn
}

output "log_group_name" {
  description = "CloudWatch Log Group name."
  value       = module.ecs_scheduled_job.log_group_name
}
