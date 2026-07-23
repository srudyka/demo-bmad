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
