output "job_id" {
  description = "Canonical environment/application/job identity reserved by this declaration."
  value       = local.job_id
}

output "cell" {
  description = "Validated Cell identity and contract compatibility metadata."
  sensitive   = true
  value = {
    cell_id          = local.contract.cell.cell_id
    account_id       = local.contract.cell.account_id
    region           = local.contract.cell.region
    environment      = local.contract.cell.environment
    contract_version = local.contract.contract_version
    checksum         = local.contract.checksum
    compatible       = true
  }
}

output "reservation" {
  description = "Exact reservation request and lifecycle state; workload resources are not created by this story."
  value       = local.reservation_request
}

output "protected_tags" {
  description = "Protected metadata applied to later job-owned resources."
  value       = local.merged_tags
}

output "normalized_schedule" {
  description = "Validated schedule identity retained for later activation."
  value = {
    expression = var.schedule_expression
    job_id     = local.job_id
  }
}

output "job_iam" {
  description = "Stable job-owned IAM role identities and policy review metadata; no secrets are exposed."
  value = {
    path                 = local.role_path
    boundary_arn         = var.permissions_boundary_arn
    launch_role_arn      = aws_iam_role.launch.arn
    launch_role_id       = aws_iam_role.launch.unique_id
    execution_role_arn   = aws_iam_role.execution.arn
    execution_role_id    = aws_iam_role.execution.unique_id
    task_role_arn        = aws_iam_role.task.arn
    task_role_id         = aws_iam_role.task.unique_id
    secret_mode          = var.secret_mode
    network_path         = var.application_secret_network_path
    policy_statement_ids = concat(["RunCanonicalJobTaskFamily", "PassOnlyThisJobsEcsRoles", "PullImmutableImageFromApprovedRepository", "EcrAuthorizationTokenServiceRequiredWildcard", "WriteOnlyThisJobsLogs"], [for permission in var.permissions : permission.statement_id])
    catalog_findings     = local.policy_catalog_findings
    customer_policy_arns = [for attachment in var.customer_managed_policy_attachments : attachment.policy_arn]
    customer_policy_versions = [for attachment in var.customer_managed_policy_attachments : {
      policy_arn      = attachment.policy_arn
      version_id      = attachment.version_id
      document_sha256 = attachment.document_sha256
    }]
  }
}

output "networking" {
  description = "Validated non-sensitive private-network handoff for the future task definition and CONFIG publication."
  value = {
    vpc_id                    = var.networking.vpc_id
    subnet_ids                = sort(tolist(var.networking.subnet_ids))
    security_group_ids        = var.networking.security_group_mode == "create" ? [aws_security_group.job[0].id] : sort(tolist(var.networking.security_group_ids))
    security_group_mode       = var.networking.security_group_mode
    assign_public_ip          = "DISABLED"
    network_policy_version    = var.networking.policy_version
    dependency_reachability   = var.networking.dependency_reachability
    created_security_group_id = var.networking.security_group_mode == "create" ? aws_security_group.job[0].id : null
  }
}

output "task_definition" {
  description = "Immutable Fargate task-definition identity and runtime settings for later CONFIG publication; no secrets are exposed."
  value = {
    arn                      = aws_ecs_task_definition.job.arn
    family                   = aws_ecs_task_definition.job.family
    revision                 = aws_ecs_task_definition.job.revision
    image                    = var.image
    execution_role_arn       = aws_ecs_task_definition.job.execution_role_arn
    task_role_arn            = aws_ecs_task_definition.job.task_role_arn
    network_mode             = aws_ecs_task_definition.job.network_mode
    requires_compatibilities = aws_ecs_task_definition.job.requires_compatibilities
    platform_version         = var.platform_version
    cpu_architecture         = var.cpu_architecture
    operating_system_family  = var.operating_system_family
    ephemeral_storage_gib    = var.ephemeral_storage_gib
  }
}

output "log_group" {
  description = "Job-owned encrypted CloudWatch log-group identity and retention settings."
  value = {
    name              = aws_cloudwatch_log_group.job.name
    arn               = aws_cloudwatch_log_group.job.arn
    retention_in_days = aws_cloudwatch_log_group.job.retention_in_days
    kms_key_id        = aws_cloudwatch_log_group.job.kms_key_id
  }
}

output "deployment_identity" {
  description = "Bounded, secret-free deployment identity for the task revision and later CONFIG publication."
  value = merge(local.deployment_identity, {
    task_definition_arn = aws_ecs_task_definition.job.arn
    task_family         = aws_ecs_task_definition.job.family
    task_revision       = aws_ecs_task_definition.job.revision
    log_group_name      = aws_cloudwatch_log_group.job.name
  })
}
