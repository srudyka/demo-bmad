data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_ssm_parameter" "cell_contract" {
  name            = "/platform/ecs-scheduled-jobs/${var.environment}/${var.region}/contract"
  with_decryption = false
}

locals {
  contract = try(jsondecode(data.aws_ssm_parameter.cell_contract.value), null)
  contract_without_checksum = try({
    for key, value in local.contract : key => value if key != "checksum"
  }, {})
  contract_checksum = sha256(jsonencode(local.contract_without_checksum))
  job_id            = "${var.environment}/${var.application}/${var.job_name}"
  name_prefix       = "${var.environment}-${var.application}-${var.job_name}"
  protected_tags = {
    Environment = var.environment
    Application = var.application
    Service     = "scheduled-job"
    Owner       = var.owner
    ManagedBy   = "Terraform"
    Repository  = var.repository_id
  }
  merged_tags           = merge(var.tags, local.protected_tags)
  contract_integrations = try(local.contract.integrations, {})
  reservation_request = merge({
    pk                = "JOB#${local.job_id}"
    sk                = "RESERVATION"
    job_id            = local.job_id
    namespace_key     = "NAMESPACE#${var.environment}#${var.application}"
    account_id        = var.account_id
    region            = var.region
    environment       = var.environment
    application       = var.application
    repository_id     = var.repository_id
    terraform_root_id = var.terraform_root_id
    apply_role_id     = var.apply_role_id
    owner             = var.owner
    owner_generation  = 1
    lifecycle         = "RESERVED"
    tombstoned        = false
    transfer_state    = "quiescent"
  }, try(var.registrar_receipt, {}))
}

resource "terraform_data" "declaration_validation" {
  input = {
    job_id          = local.job_id
    reservation_key = "JOB#${local.job_id}"
    image           = var.image
  }

  lifecycle {
    precondition {
      condition = (
        var.registrar_receipt != null &&
        try(var.registrar_receipt.pk, "") == "JOB#${local.job_id}" &&
        try(var.registrar_receipt.sk, "") == "RESERVATION" &&
        try(var.registrar_receipt.job_id, "") == local.job_id &&
        try(var.registrar_receipt.namespace_key, "") == "NAMESPACE#${var.environment}#${var.application}" &&
        try(var.registrar_receipt.lifecycle, "") == "RESERVED" &&
        try(var.registrar_receipt.owner_generation, 0) >= 1 &&
        try(var.registrar_receipt.tombstoned, true) == false &&
        try(var.registrar_receipt.transfer_state, "") == "quiescent"
      )
      error_message = "JOB_RESERVATION_NOT_CONFIRMED: an exact authoritative Registrar receipt is required before reporting RESERVED."
    }

    precondition {
      condition = (
        local.contract != null &&
        try(local.contract.schema_version, "") == "1.0.0" &&
        try(local.contract.contract_version, "") == "1.0.0" &&
        try(local.contract.checksum, "") == local.contract_checksum &&
        try(data.aws_ssm_parameter.cell_contract.type, "") == "String" &&
        try(local.contract.cell.account_id, "") == var.account_id &&
        try(local.contract.cell.region, "") == var.region &&
        try(local.contract.cell.environment, "") == var.environment &&
        try(local.contract.cell.cell_id, "") != "" &&
        try(local.contract.discovery_path, "") == data.aws_ssm_parameter.cell_contract.name &&
        try(local.contract.metric_namespace, "") != "" &&
        try(local.contract.encryption.kms_key_arn, "") != "" &&
        length(try(local.contract.supported_ranges, {})) > 0 &&
        alltrue([for range_value in try(values(local.contract.supported_ranges), []) : can(regex("^.+$", range_value))]) &&
        length(try(local.contract.integrations, {})) > 0 &&
        alltrue([for integration in try(values(local.contract.integrations), []) : (
          try(integration.owner, "") != "" &&
          try(integration.schema_range, "") != "" &&
          can(regex("^arn:[a-z0-9-]+:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:.+$", try(integration.arn, "")))
        )]) &&
        try(local.contract_integrations.namespace_registry.owner, "") == "cell-root" &&
        try(local.contract_integrations.namespace_registry.arn, "") != ""
      )
      error_message = "CELL_CONTRACT_INVALID_OR_INCOMPATIBLE: discovered Cell Contract is not exact and compatible."
    }

    precondition {
      condition     = var.account_id == data.aws_caller_identity.current.account_id && var.region == data.aws_region.current.name
      error_message = "JOB_DECLARATION_CELL_MISMATCH: account_id and region must match provider identity."
    }

    precondition {
      condition     = length(local.job_id) <= 194 && can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", local.job_id))
      error_message = "JOB_ID_INVALID: canonical identity exceeds stable naming bounds or uses a reserved namespace."
    }

    precondition {
      condition = (
        alltrue([for key, value in local.merged_tags : length(trimspace(value)) > 0]) &&
        alltrue([for key in setintersection(keys(var.tags), keys(local.protected_tags)) : var.tags[key] == local.protected_tags[key]]) &&
        local.merged_tags.Environment == var.environment &&
        local.merged_tags.Application == var.application
      )
      error_message = "JOB_TAGS_INVALID: protected tags must be nonempty and cannot be overridden."
    }
  }
}
