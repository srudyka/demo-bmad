output "schedule_name" {
  description = "Example schedule name."
  value       = module.scheduled_job.schedule_name
}

output "log_group_name" {
  description = "Example log group name."
  value       = module.scheduled_job.log_group_name
}
