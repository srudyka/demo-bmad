module "ecs_scheduled_job" {
  source = "../../modules/ecs-scheduled-job"

  environment = var.environment
  application = var.application
  service     = var.service
  owner       = var.owner
  repository  = var.repository
  cost_center = var.cost_center
  tags        = var.tags

  cluster_arn        = var.cluster_arn
  subnet_ids         = var.subnet_ids
  security_group_ids = var.security_group_ids
  assign_public_ip   = false

  container_image       = var.container_image
  container_command     = var.container_command
  container_environment = var.container_environment
  container_secrets     = var.container_secrets

  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_expression_timezone
  schedule_enabled             = var.schedule_enabled

  alarm_actions               = var.alarm_actions
  ok_actions                  = var.ok_actions
  enable_ecr_pull_permissions = length(var.ecr_repository_arns) > 0
  ecr_repository_arns         = var.ecr_repository_arns
  execution_secret_arns       = var.execution_secret_arns
  kms_key_arns                = var.kms_key_arns

  task_managed_policy_arns = var.task_managed_policy_arns
  task_policy_statements   = var.task_policy_statements
}
