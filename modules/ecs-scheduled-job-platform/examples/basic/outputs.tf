output "cell_contract_parameter_name" {
  description = "Canonical SSM parameter name consumed by job roots."
  value       = module.platform.cell_contract.parameter_name
}

output "config_inbox_name" {
  description = "Cell-owned CONFIG inbox bucket name."
  value       = module.platform.config_inbox.name
}
