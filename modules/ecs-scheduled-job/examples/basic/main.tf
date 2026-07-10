module "scheduled_job" {
  source = "../.."

  environment = "dev"
  application = "platform"
  service     = "sample-job"
  owner       = "platform-team"
  repository  = "github.com/example/platform"

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids

  container_image     = var.container_image
  container_command   = ["sh", "-c", "echo scheduled job completed"]
  schedule_expression = "rate(1 day)"
  alarm_actions       = var.alarm_actions

  enable_ecr_pull_permissions = length(var.ecr_repository_arns) > 0
  ecr_repository_arns         = var.ecr_repository_arns
}
