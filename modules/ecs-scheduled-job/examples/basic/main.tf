module "scheduled_job" {
  source = "../.."

  tags = {
    Environment = "dev"
    Application = "platform"
    Service     = "cleanup-job"
    Owner       = "platform-team"
    ManagedBy   = "Terraform"
    Repository  = "demo-bmad"
  }

  cluster_arn  = "arn:aws:ecs:us-east-1:123456789012:cluster/dev-platform-cluster"
  cluster_name = "dev-platform-cluster"

  subnet_ids = [
    "subnet-0123456789abcdef0",
    "subnet-0fedcba9876543210"
  ]

  security_group_ids = [
    "sg-0123456789abcdef0"
  ]

  container_image = "public.ecr.aws/docker/library/alpine:3.20.3"
  container_command = [
    "sh",
    "-c",
    "echo scheduled job started && date && echo scheduled job completed"
  ]

  environment_variables = {
    LOG_LEVEL = "info"
  }

  compute = {
    cpu    = 256
    memory = 512
  }

  schedule_expression               = "rate(1 hour)"
  maximum_retry_attempts            = 3
  log_retention_days                = 365
  alarm_sns_topic_arns              = []
  scheduler_failure_alarm_threshold = 1
}
