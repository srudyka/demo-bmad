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
