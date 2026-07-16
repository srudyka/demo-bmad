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
