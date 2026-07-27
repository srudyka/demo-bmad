output "job_id" {
  description = "Canonical environment/application/job identity reserved by this declaration."
  type        = string
  sensitive   = false
  value       = local.job_id
}

output "job_identity" {
  description = "Stable non-sensitive operational identity and lifecycle contract for this scheduled job."
  type = object({
    job_id                   = string
    application              = string
    environment              = string
    account_id               = string
    region                   = string
    cell_id                  = string
    owner                    = string
    owner_generation         = number
    contract_version         = string
    contract_checksum        = string
    module_version           = string
    platform_version         = string
    source_revision          = string
    image_digest             = string
    workflow_identity        = string
    deployment_run_reference = string
    schedule_generation      = string
    config_hash              = string
    task_definition_revision = number
    cell_contract_version    = string
    cell_contract_checksum   = string
    deployment_identity_id   = string
    lifecycle_requested      = string
    lifecycle_acknowledged   = string
    lifecycle_state_source   = string
  })
  value = {
    job_id                   = local.job_id
    application              = var.application
    environment              = var.environment
    account_id               = var.account_id
    region                   = var.region
    cell_id                  = local.contract.cell.cell_id
    owner                    = var.owner
    owner_generation         = try(var.registrar_receipt.owner_generation, 0)
    contract_version         = local.contract.contract_version
    contract_checksum        = local.contract.checksum
    module_version           = var.module_version
    platform_version         = var.platform_version
    source_revision          = var.source_revision
    image_digest             = try(split("@", var.image)[1], "")
    workflow_identity        = var.workflow_identity
    deployment_run_reference = var.deployment_run_reference
    schedule_generation      = local.schedule_generation
    config_hash              = local.config_version
    task_definition_revision = aws_ecs_task_definition.job.revision
    cell_contract_version    = local.contract.contract_version
    cell_contract_checksum   = local.contract.checksum
    deployment_identity_id   = local.deployment_identity_id
    lifecycle_requested      = var.activation.enabled ? "MATERIALIZED" : "PUBLISHED"
    lifecycle_acknowledged   = try(cell_config_acknowledgement.config.result, "UNKNOWN")
    lifecycle_state_source   = "cell_config_acknowledgement.config"
  }
}

output "schedule" {
  description = "Stable schedule, delivery, retry, and lifecycle references for operator use."
  type = object({
    expression                = string
    time_zone                 = string
    activation_start          = string
    activation_end            = string
    flexible_time_window      = string
    generation                = string
    arn                       = string
    group_arn                 = string
    target_queue_arn          = string
    target_dlq_arn            = string
    maximum_retry_attempts    = number
    maximum_event_age_seconds = number
    declared_state            = string
    acknowledged_state        = string
  })
  value = {
    expression                = var.schedule_expression
    time_zone                 = var.schedule_time_zone
    activation_start          = var.activation_start
    activation_end            = var.activation_end
    flexible_time_window      = "OFF"
    generation                = local.schedule_generation
    arn                       = aws_scheduler_schedule.job.arn
    group_arn                 = try(local.contract_integrations.scheduler_schedule_group.arn, "")
    target_queue_arn          = try(local.contract_integrations.scheduler_ingress.arn, "")
    target_dlq_arn            = try(local.contract_integrations.scheduler_dlq.arn, "")
    maximum_retry_attempts    = var.maximum_retry_attempts
    maximum_event_age_seconds = var.maximum_event_age_seconds
    declared_state            = var.activation.enabled ? "ENABLED" : "DISABLED"
    acknowledged_state        = try(cell_config_acknowledgement.config.result, "UNKNOWN")
  }
}

output "task" {
  description = "Stable task-definition, cluster, image digest, and role references without application data."
  type = object({
    arn                = string
    family             = string
    revision           = number
    image_digest       = string
    cluster_arn        = string
    execution_role_arn = string
    task_role_arn      = string
    launch_role_arn    = string
    platform_version   = string
    network_mode       = string
  })
  value = {
    arn                = aws_ecs_task_definition.job.arn
    family             = aws_ecs_task_definition.job.family
    revision           = aws_ecs_task_definition.job.revision
    image_digest       = try(split("@", var.image)[1], "")
    cluster_arn        = var.ecs_cluster_arn
    execution_role_arn = aws_iam_role.execution.arn
    task_role_arn      = aws_iam_role.task.arn
    launch_role_arn    = aws_iam_role.launch.arn
    platform_version   = var.platform_version
    network_mode       = "awsvpc"
  }
}

output "logs" {
  description = "Stable CloudWatch Logs identities and bounded subscription metadata; log contents are never exposed."
  type = object({
    name              = string
    arn               = string
    retention_in_days = number
    kms_key_id        = string
    subscription_arn  = string
    destination_arn   = string
    filter_pattern    = string
  })
  value = {
    name              = aws_cloudwatch_log_group.job.name
    arn               = aws_cloudwatch_log_group.job.arn
    retention_in_days = aws_cloudwatch_log_group.job.retention_in_days
    kms_key_id        = try(aws_cloudwatch_log_group.job.kms_key_id, "")
    subscription_arn  = try(aws_cloudwatch_log_subscription_filter.completion[0].id, "")
    destination_arn   = try(aws_cloudwatch_log_subscription_filter.completion[0].destination_arn, "")
    filter_pattern    = local.completion_filter_pattern
  }
}

output "config" {
  description = "Secret-safe CONFIG version, object key, contract, and authoritative acknowledgement metadata."
  type = object({
    version                = string
    hash                   = string
    object_key             = string
    contract_version       = string
    contract_checksum      = string
    owner_generation       = number
    acknowledgement_result = string
    conformance_result     = string
    horizon_watermark      = string
    evidence_hash          = string
  })
  value = {
    version                = local.config_version
    hash                   = local.config_version
    object_key             = "jobs/${local.job_id}/config/${local.config_version}.json"
    contract_version       = local.contract.contract_version
    contract_checksum      = local.contract.checksum
    owner_generation       = try(var.registrar_receipt.owner_generation, 0)
    acknowledgement_result = try(cell_config_acknowledgement.config.result, "UNKNOWN")
    conformance_result     = try(cell_config_acknowledgement.config.conformance_result, "UNKNOWN")
    horizon_watermark      = try(cell_config_acknowledgement.config.horizon_watermark, "")
    evidence_hash          = local.acknowledgement_evidence_hash
  }
}

output "operations" {
  description = "Approved operator route, ownership, notification, and Cell integration references."
  type = object({
    owner                            = string
    runbook_uri                      = string
    notification_target_arn          = string
    escalation_class                 = string
    detection_mode                   = string
    routing_enabled                  = bool
    occurrence_ledger_arn            = string
    deadline_scanner_arn             = string
    alert_router_arn                 = string
    cell_health_metric_namespace     = string
    available                        = bool
    unavailable_reason               = string
    occurrence_state_reference       = string
    config_acknowledgement_reference = string
    cell_health_reference            = string
  })
  value = {
    owner                            = var.owner
    runbook_uri                      = var.notification.runbook_uri
    notification_target_arn          = var.notification.target_arn
    escalation_class                 = var.completion_policy.escalation_classification
    detection_mode                   = var.completion_policy.detection_mode
    routing_enabled                  = var.completion_policy.routing_enabled
    occurrence_ledger_arn            = try(local.contract_integrations.occurrence_ledger.arn, "")
    deadline_scanner_arn             = try(local.contract_integrations.deadline_scanner.arn, "")
    alert_router_arn                 = try(local.contract_integrations.alert_router.arn, "")
    cell_health_metric_namespace     = try(local.contract.metric_namespace, "")
    available                        = local.required_operational_integrations_available
    unavailable_reason               = local.required_operational_integrations_available ? "" : "CELL_OPERATIONAL_INTEGRATION_UNAVAILABLE"
    occurrence_state_reference       = try(local.contract_integrations.occurrence_ledger.arn, "")
    config_acknowledgement_reference = try(local.contract_integrations.config_validator.endpoint_url, "")
    cell_health_reference            = try(local.contract_integrations.cell_health.arn, "")
  }
}

output "alarms" {
  description = "Alarm references with explicit ownership; required alerting remains independent of the optional dashboard."
  type = object({
    job_owned_arns       = list(string)
    cell_health_arns     = map(string)
    alert_router_arn     = string
    dashboard_dependency = string
    available            = bool
    unavailable_reason   = string
  })
  value = {
    job_owned_arns       = []
    cell_health_arns     = try(local.contract_integrations.cell_health.alarm_arns, {})
    alert_router_arn     = try(local.contract_integrations.alert_router.arn, "")
    dashboard_dependency = "NONE"
    available            = local.required_operational_integrations_available
    unavailable_reason   = local.required_operational_integrations_available ? "" : "CELL_OPERATIONAL_INTEGRATION_UNAVAILABLE"
  }
}

output "dashboard" {
  description = "Optional bounded per-job operational dashboard identity and scale metadata."
  type = object({
    enabled                    = bool
    name                       = string
    arn                        = string
    body_sha256                = string
    widget_count               = number
    metric_count               = number
    query_count                = number
    estimated_monthly_cost_usd = number
  })
  value = {
    enabled                    = var.dashboard.enabled
    name                       = var.dashboard.enabled ? aws_cloudwatch_dashboard.job[0].dashboard_name : ""
    arn                        = var.dashboard.enabled ? aws_cloudwatch_dashboard.job[0].dashboard_arn : ""
    body_sha256                = var.dashboard.enabled ? sha256(local.dashboard_body_json) : ""
    widget_count               = var.dashboard.enabled ? local.dashboard_widget_count : 0
    metric_count               = var.dashboard.enabled ? local.dashboard_metric_count : 0
    query_count                = var.dashboard.enabled ? local.dashboard_query_count : 0
    estimated_monthly_cost_usd = var.dashboard.enabled ? local.dashboard_estimated_monthly_cost_usd : 0
  }
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
  type        = any
  sensitive   = false
  value       = local.reservation_request
}

output "protected_tags" {
  description = "Protected metadata applied to later job-owned resources."
  type        = any
  sensitive   = false
  value       = local.merged_tags
}

output "normalized_schedule" {
  description = "Validated schedule identity retained for later activation."
  type        = any
  sensitive   = false
  value = {
    expression = var.schedule_expression
    job_id     = local.job_id
  }
}

output "job_iam" {
  description = "Stable job-owned IAM role identities and policy review metadata; no secrets are exposed."
  type        = any
  sensitive   = false
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
  type        = any
  sensitive   = false
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
  type        = any
  sensitive   = false
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
  type        = any
  sensitive   = false
  value = {
    name              = aws_cloudwatch_log_group.job.name
    arn               = aws_cloudwatch_log_group.job.arn
    retention_in_days = aws_cloudwatch_log_group.job.retention_in_days
    kms_key_id        = aws_cloudwatch_log_group.job.kms_key_id
  }
}

output "completion_policy" {
  description = "Bounded completion detection and operational routing policy for this job."
  type        = any
  sensitive   = false
  value = {
    detection_mode            = var.completion_policy.detection_mode
    escalation_classification = var.completion_policy.escalation_classification
    alarms_enabled            = var.completion_policy.alarms_enabled
    routing_enabled           = var.completion_policy.routing_enabled
    coverage_label            = var.completion_policy.detection_mode == "best-effort" ? "REDUCED_NON_PRODUCTION" : "OCCURRENCE_AWARE"
    success_metric_filter     = try(aws_cloudwatch_log_metric_filter.best_effort_success[0].name, null)
  }
}

output "deployment_identity" {
  description = "Bounded, secret-free deployment identity for the task revision and later CONFIG publication."
  type        = any
  sensitive   = false
  value = merge(local.deployment_identity, {
    task_definition_arn = aws_ecs_task_definition.job.arn
    task_family         = aws_ecs_task_definition.job.family
    task_revision       = aws_ecs_task_definition.job.revision
    log_group_name      = aws_cloudwatch_log_group.job.name
  })
}

output "phase_one" {
  description = "Secret-free disabled phase-one schedule, delivery role, CONFIG publication, and PUBLISHED lifecycle handoff."
  type        = any
  sensitive   = false
  value = {
    lifecycle                   = "PUBLISHED"
    schedule_arn                = aws_scheduler_schedule.job.arn
    schedule_group_arn          = local.contract_integrations.scheduler_schedule_group.arn
    scheduler_delivery_role_arn = aws_iam_role.scheduler_delivery.arn
    scheduler_delivery_role_id  = aws_iam_role.scheduler_delivery.unique_id
    task_definition_arn         = aws_ecs_task_definition.job.arn
    launch_role_arn             = aws_iam_role.launch.arn
    config_version              = local.config_version
    config_key                  = "jobs/${local.job_id}/config/${local.config_version}.json"
    owner_generation            = try(var.registrar_receipt.owner_generation, 0)
    activation_start            = var.activation_start
    deployment_identity         = local.deployment_identity
    launch_authorized           = false
  }
}

output "phase_two" {
  description = "Explicit non-production activation handoff and exact materialized acknowledgement identity."
  type        = any
  sensitive   = false
  value = {
    lifecycle                = try(cell_config_acknowledgement.config.result, "UNKNOWN") == "MATERIALIZED" ? "ENABLED" : try(cell_config_acknowledgement.config.result, "UNKNOWN")
    schedule_state           = try(cell_config_acknowledgement.config.result, "UNKNOWN") == "MATERIALIZED" && var.activation.enabled ? "ENABLED" : "DISABLED"
    launch_authorized        = try(cell_config_acknowledgement.config.result, "UNKNOWN") == "MATERIALIZED" && var.activation.enabled
    job_id                   = local.job_id
    config_version           = local.config_version
    schedule_arn             = local.schedule_arn
    schedule_generation      = local.schedule_generation
    owner_generation         = try(var.registrar_receipt.owner_generation, 0)
    horizon_watermark        = var.activation.horizon_watermark
    conformance_result       = var.activation.conformance_result
    validation_evidence      = local.acknowledgement_evidence_hash
    validation_evidence_hash = local.acknowledgement_evidence_hash
    deployment_identity_id   = var.activation.deployment_identity_id
  }
}
