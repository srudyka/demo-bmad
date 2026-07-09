locals {
  common_tags = {
    Environment = var.environment
    Application = "platform"
    Service     = "ecs-scheduled-jobs"
    Owner       = "platform-engineering"
    ManagedBy   = "Terraform"
    Repository  = "demo-bmad"
  }
}

module "nightly_example_job" {
  source = "../../modules/ecs-scheduled-job"

  providers = {
    aws = aws.target
  }

  name        = "${var.environment}-platform-nightly-example"
  environment = var.environment
  application = local.common_tags.Application
  service     = local.common_tags.Service
  owner       = local.common_tags.Owner
  repository  = local.common_tags.Repository
  tags        = local.common_tags

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.private_subnet_ids
  security_group_ids = var.security_group_ids
  assign_public_ip   = false

  container_image = var.container_image
  command         = ["python", "-m", "jobs.nightly"]
  cpu             = 256
  memory          = 512

  schedule_expression          = "cron(0 6 * * ? *)"
  schedule_expression_timezone = "UTC"
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600

  environment_variables = {
    JOB_NAME    = "nightly-example"
    ENVIRONMENT = var.environment
  }

  task_policy_statements = [
    {
      sid       = "ReadApplicationParameterPath"
      actions   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
      resources = [var.example_parameter_path_arn]
    }
  ]

  log_retention_days = 30
  alarm_action_arns  = var.alarm_action_arns
}
