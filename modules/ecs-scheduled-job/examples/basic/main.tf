provider "aws" {
  region = var.aws_region
}

module "example_report_job" {
  source = "../.."

  environment = "dev"
  application = "platform"
  service     = "scheduled-jobs"
  job_name    = "report-job"
  owner       = "platform"
  repository  = "demo-bmad"

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids

  container_image   = var.container_image
  container_command = ["sh", "-c", "echo ecs scheduled job example"]

  schedule_expression = "rate(1 day)"
  log_retention_days  = 30
  alarm_actions       = var.alarm_actions

  tags = {
    Example = "basic"
  }
}
