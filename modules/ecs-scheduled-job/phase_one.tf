data "aws_iam_policy_document" "scheduler_delivery_assume_role" {
  statement {
    sid     = "AllowExactCellSchedulerGroup"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [local.contract_integrations.scheduler_schedule_group.arn]
    }
  }
}

resource "aws_iam_role" "scheduler_delivery" {
  name                 = "${local.name_prefix}-scheduler-delivery"
  path                 = local.role_path
  assume_role_policy   = data.aws_iam_policy_document.scheduler_delivery_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.merged_tags
}

data "aws_iam_policy_document" "scheduler_delivery" {
  statement {
    sid       = "SendOnlyToCellSchedulerQueues"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [local.contract_integrations.scheduler_ingress.arn, local.contract_integrations.scheduler_dlq.arn]
  }

  statement {
    sid       = "UseCellSchedulerQueueDataKey"
    effect    = "Allow"
    actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
    resources = [local.contract.encryption.kms_key_arn]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "kms:EncryptionContext:aws:sqs:arn"
      values   = [local.contract_integrations.scheduler_ingress.arn, local.contract_integrations.scheduler_dlq.arn]
    }
  }
}

resource "aws_iam_role_policy" "scheduler_delivery" {
  name   = "${local.name_prefix}-scheduler-delivery-v1"
  role   = aws_iam_role.scheduler_delivery.id
  policy = data.aws_iam_policy_document.scheduler_delivery.json
}

resource "aws_scheduler_schedule" "job" {
  name                         = local.name_prefix
  group_name                   = local.scheduler_schedule_group_name
  kms_key_arn                  = local.contract.encryption.kms_key_arn
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_time_zone
  start_date                   = var.activation_start
  end_date                     = var.activation_end
  state                        = var.activation.enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = local.contract_integrations.scheduler_ingress.arn
    role_arn = aws_iam_role.scheduler_delivery.arn
    input = jsonencode({
      account_id               = var.account_id
      config_version           = local.config_version
      event_type               = "occurrence.launch.v1"
      job_id                   = local.job_id
      ownership_generation     = try(var.registrar_receipt.owner_generation, 0)
      producer_id              = "scheduler"
      region                   = var.region
      schedule_arn             = local.schedule_arn
      schedule_generation      = local.schedule_generation
      schedule_group_arn       = local.contract_integrations.scheduler_schedule_group.arn
      scheduler_scheduled_time = "<aws.scheduler.scheduled-time>"
      schema_version           = "1.0.0"
      source_queue_arn         = local.contract_integrations.scheduler_ingress.arn
    })

    dead_letter_config {
      arn = local.contract_integrations.scheduler_dlq.arn
    }

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }
  }

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = !var.activation.enabled || var.activation.task_definition_arn == aws_ecs_task_definition.job.arn
      error_message = "ACTIVATION_TASK_REVISION_MISMATCH: phase-two enablement must bind the exact task-definition revision published by this job module."
    }

    precondition {
      condition = (
        !var.activation.enabled || (
          var.activation.account_id == var.account_id &&
          var.activation.region == var.region &&
          var.activation.job_id == local.job_id &&
          var.activation.config_version == local.config_version &&
          var.activation.contract_version == local.contract.contract_version &&
          var.activation.contract_checksum == local.contract.checksum &&
          var.activation.schedule_generation == local.schedule_generation &&
          var.activation.schedule_arn == local.schedule_arn &&
          var.activation.schedule_group_arn == local.contract_integrations.scheduler_schedule_group.arn &&
          var.activation.scheduler_delivery_role_id == aws_iam_role.scheduler_delivery.unique_id &&
          var.activation.launch_role_id == aws_iam_role.launch.unique_id &&
          var.activation.owner_generation == try(var.registrar_receipt.owner_generation, 0) &&
          try(timecmp(var.activation.horizon_watermark, timeadd(var.activation_start, "24h")), -1) >= 0 &&
          var.activation.deployment_identity_id == sha256(local.deployment_identity_json) &&
          cell_config_acknowledgement.config.result == "MATERIALIZED" &&
          cell_config_acknowledgement.config.conformance_result == var.activation.conformance_result &&
          cell_config_acknowledgement.config.horizon_watermark == var.activation.horizon_watermark &&
          cell_config_acknowledgement.config.validation_evidence == var.activation.validation_evidence
        )
      )
      error_message = "ACTIVATION_ACK_MISMATCH: only the exact current MATERIALIZED generation with at least 24 hours of expected horizon may enable the schedule."
    }
  }

  depends_on = [terraform_data.declaration_validation, cell_config_acknowledgement.config]
}

resource "cell_config_publication" "config" {
  provider              = cell.publisher
  job_id                = local.job_id
  config_version        = local.config_version
  object_key            = "jobs/${local.job_id}/config/${local.config_version}.json"
  contract_endpoint_url = local.contract_integrations.config_publisher.endpoint_url
  config_document       = local.config_document_json
  contract_version      = local.contract.contract_version
  ownership_generation  = try(var.registrar_receipt.owner_generation, 0)
  publisher_role_arn    = var.config_publisher_role_arn

  depends_on = [terraform_data.declaration_validation]

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = can(regex("^[0-9a-f]{64}$", local.config_version))
      error_message = "CONFIG_VERSION_INVALID: CONFIG must use its lowercase SHA-256 content hash."
    }
  }

}

resource "cell_config_acknowledgement" "config" {
  provider                    = cell.validator
  account_id                  = var.account_id
  environment                 = var.environment
  job_id                      = local.job_id
  config_version              = local.config_version
  contract_endpoint_url       = local.contract_integrations.config_validator.endpoint_url
  contract_version            = local.contract.contract_version
  contract_checksum           = local.contract.checksum
  ownership_generation        = try(var.registrar_receipt.owner_generation, 0)
  schedule_generation         = local.schedule_generation
  schedule_arn                = local.schedule_arn
  schedule_group_arn          = local.contract_integrations.scheduler_schedule_group.arn
  scheduler_delivery_role_arn = aws_iam_role.scheduler_delivery.arn
  scheduler_delivery_role_id  = aws_iam_role.scheduler_delivery.unique_id
  task_family                 = aws_ecs_task_definition.job.family
  task_definition_arn         = aws_ecs_task_definition.job.arn
  launch_role_arn             = aws_iam_role.launch.arn
  launch_role_id              = aws_iam_role.launch.unique_id
  publisher_role_arn          = var.config_validator_role_arn != "" ? var.config_validator_role_arn : var.config_publisher_role_arn
  repository_id               = var.repository_id
  terraform_root_id           = var.terraform_root_id
  required_lifecycle          = var.activation.enabled ? "MATERIALIZED" : "VALIDATED"

  depends_on = [cell_config_publication.config]

  lifecycle {
    prevent_destroy = true
  }
}
