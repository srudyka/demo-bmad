output "cell_id" {
  description = "Stable Cell identifier published in the discovery contract."
  value       = var.cell_id
}

output "namespace_registry" {
  description = "Name and ARN of the Cell-owned namespace reservation registry."
  value = {
    arn  = aws_dynamodb_table.namespace_registry.arn
    name = aws_dynamodb_table.namespace_registry.name
  }
}

output "config_inbox" {
  description = "Name and ARN of the Cell-owned CONFIG candidate inbox."
  value = {
    arn  = aws_s3_bucket.config_inbox.arn
    name = aws_s3_bucket.config_inbox.bucket
  }
}

output "configuration_registry" {
  description = "Name and ARN of the Cell-owned immutable CONFIG registry."
  value = {
    arn  = aws_dynamodb_table.configuration_registry.arn
    name = aws_dynamodb_table.configuration_registry.name
  }
}

output "cell_contract" {
  description = "SSM discovery contract identifiers, version, and semantic checksum for consumers."
  value = {
    checksum       = local.cell_contract_checksum
    parameter_arn  = aws_ssm_parameter.cell_contract.arn
    parameter_name = aws_ssm_parameter.cell_contract.name
    version        = var.contract_version
  }
}

output "metric_namespace" {
  description = "Reserved bounded CloudWatch metric namespace for future Cell integrations."
  value       = var.metric_namespace
}

output "process_manager" {
  description = "Cell-owned deterministic occurrence Process Manager identifiers."
  value = {
    arn                  = aws_iam_role.process_manager.arn
    function_arn         = aws_lambda_function.process_manager.arn
    id                   = aws_iam_role.process_manager.unique_id
    log_group_name       = aws_cloudwatch_log_group.process_manager.name
    occurrence_table_arn = aws_dynamodb_table.occurrence_ledger.arn
    task_arn_index_name  = "task-arn"
    launch_role_arn      = var.canary_normalizer_registration.canary_launch_role_arn
    mapping_uuid         = aws_lambda_event_source_mapping.process_manager.uuid
  }
}

output "occurrence_ledger" {
  description = "Encrypted occurrence ledger table identifiers."
  value = {
    arn  = aws_dynamodb_table.occurrence_ledger.arn
    name = aws_dynamodb_table.occurrence_ledger.name
  }
}

output "scheduler_ingress" {
  description = "Cell-owned EventBridge Scheduler ingress queue, DLQ, and schedule-group identifiers."
  value = {
    dlq_arn            = aws_sqs_queue.scheduler_dlq.arn
    queue_arn          = aws_sqs_queue.scheduler_ingress.arn
    schedule_group_arn = aws_scheduler_schedule_group.cell.arn
  }
}

output "evidence_normalizer" {
  description = "Cell-owned canonical evidence ingress, quarantine, and normalizer runtime identifiers."
  value = {
    function_arn         = aws_lambda_function.evidence_normalizer.arn
    ingress_dlq_arn      = aws_sqs_queue.normalizer_ingress_dlq.arn
    ingress_queue_arn    = aws_sqs_queue.normalizer_ingress.arn
    log_group_name       = aws_cloudwatch_log_group.evidence_normalizer.name
    quarantine_dlq_arn   = aws_sqs_queue.normalizer_quarantine_dlq.arn
    quarantine_queue_arn = aws_sqs_queue.normalizer_quarantine.arn
    role_arn             = aws_iam_role.evidence_normalizer.arn
  }
}

output "occurrence_materializer" {
  description = "Independent expected-occurrence materializer identifiers and authenticated source queue."
  value = {
    function_arn = aws_lambda_function.occurrence_materializer.arn
    queue_arn    = aws_sqs_queue.materializer_ingress.arn
    dlq_arn      = aws_sqs_queue.materializer_dlq.arn
    role_arn     = aws_iam_role.occurrence_materializer.arn
    rule_arn     = aws_cloudwatch_event_rule.materializer_tick.arn
  }
}

output "canary_registration" {
  description = "Immutable platform-owned bootstrap canary reservation and its narrowly scoped CONFIG publisher role."
  value = {
    config_publisher_role_arn = aws_iam_role.canary_config_publisher.arn
    job_id                    = var.canary_reservation.job_id
    owner_generation          = var.canary_reservation.owner_generation
  }
}
