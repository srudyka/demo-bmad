data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_partition" "current" {}

data "aws_ssm_parameter" "cell_contract" {
  name            = "/platform/ecs-scheduled-jobs/${var.environment}/${var.region}/contract"
  with_decryption = false
}

data "aws_vpc" "declared" {
  id = var.networking.vpc_id
}

data "aws_subnet" "declared" {
  for_each = toset(var.networking.subnet_ids)
  id       = each.value
}

data "aws_security_group" "existing" {
  for_each = var.networking.security_group_mode == "existing" ? var.networking.security_group_ids : toset([])
  id       = each.value
}

data "aws_vpc_security_group_rules" "existing" {
  for_each = var.networking.security_group_mode == "existing" ? var.networking.security_group_ids : toset([])

  filter {
    name   = "group-id"
    values = [each.value]
  }
}

locals {
  existing_rule_ids = toset(flatten([
    for group_rules in values(data.aws_vpc_security_group_rules.existing) : group_rules.ids
  ]))
}

data "aws_vpc_security_group_rule" "existing" {
  for_each = local.existing_rule_ids

  security_group_rule_id = each.value
}

data "aws_security_group" "egress_destination" {
  for_each = toset([
    for rule in values(var.networking.egress_rules) : try(rule.referenced_security_group_id, "")
    if try(rule.referenced_security_group_id, "") != ""
  ])

  id = each.value
}

data "aws_prefix_list" "egress_destination" {
  for_each = toset([
    for rule in values(var.networking.egress_rules) : try(rule.prefix_list_id, "")
    if try(rule.prefix_list_id, "") != ""
  ])

  prefix_list_id = each.value
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
  merged_tags                   = merge(var.tags, local.protected_tags)
  contract_integrations         = try(local.contract.integrations, {})
  network_catalog               = try(jsondecode(file("${path.module}/../../contracts/v1/catalogs/network.json")), null)
  network_catalog_valid         = try(local.network_catalog.schema_version == "1.0.0" && local.network_catalog.policy_version == "1.0.0" && local.network_catalog.unknown_policy_disposition == "BLOCK" && length(local.network_catalog.finding_severity) > 0 && local.network_catalog.exception_policy.owner != "" && contains(local.network_catalog.enforcement_stages, local.network_catalog.exception_policy.enforcement_stage), false)
  required_network_dependencies = toset(try(local.network_catalog.required_dependency_evidence, []))
  secret_dependencies = toset(compact(concat(
    [for reference in var.secret_references : strcontains(reference, ":secretsmanager:") ? "secrets-manager" : "ssm"],
    var.secret_kms_key_arn == null ? [] : ["kms"],
  )))
  all_required_network_dependencies = setunion(local.required_network_dependencies, local.secret_dependencies, var.networking.application_dependencies)
  existing_rules                    = values(data.aws_vpc_security_group_rule.existing)
  log_group_name                    = "/platform/jobs/${replace(local.job_id, "/", "-")}"
  effective_log_retention_days      = var.log_retention_days == null ? (var.environment == "prod" ? 90 : 30) : var.log_retention_days
  deployment_identity = {
    source_revision  = var.source_revision
    module_version   = var.module_version
    image            = var.image
    account_id       = var.account_id
    region           = var.region
    environment      = var.environment
    job_id           = local.job_id
    platform_version = var.platform_version
  }
  deployment_identity_json = jsonencode(local.deployment_identity)
  network_path_findings = concat(
    !local.network_catalog_valid || var.networking.policy_version != try(local.network_catalog.policy_version, "") ? ["NETWORK_POLICY_UNKNOWN"] : [],
    flatten([for dependency in local.all_required_network_dependencies : contains(keys(var.networking.dependency_reachability), dependency) ? [] : ["NETWORK_DEPENDENCY_REACHABILITY_MISSING"]]),
  )
  role_path = "/platform/ecs-scheduled-jobs/${try(local.contract.cell.cell_id, "unknown")}/v1/"
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
        try(local.contract.iam.permissions_boundary_arn, "") != "" &&
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

    precondition {
      condition = (
        can(regex("^arn:${data.aws_partition.current.partition}:iam::${var.account_id}:policy/", var.permissions_boundary_arn)) &&
        can(regex("^arn:${data.aws_partition.current.partition}:iam::${var.account_id}:role/", var.cell_process_manager_role_arn)) &&
        can(regex("^arn:${data.aws_partition.current.partition}:ecr:${var.region}:${var.account_id}:repository/", var.ecr_repository_arn)) &&
        (var.secret_kms_key_arn == null || can(regex("^arn:${data.aws_partition.current.partition}:kms:${var.region}:${var.account_id}:key/", var.secret_kms_key_arn))) &&
        can(regex("^arn:${data.aws_partition.current.partition}:kms:${var.region}:${var.account_id}:key/", try(local.contract.encryption.kms_key_arn, ""))) &&
        try(local.contract_integrations.process_manager.arn, "") == var.cell_process_manager_role_arn &&
        try(local.contract.iam.permissions_boundary_arn, "") == var.permissions_boundary_arn
      )
      error_message = "JOB_IAM_IDENTITY_INVALID: boundary, ECR repository, and Process Manager role must match the target Cell identity and contract."
    }

    precondition {
      condition     = length(local.name_prefix) + length("-execution") <= 64 && length(local.name_prefix) + length("-launch") <= 64 && length(local.name_prefix) + length("-task") <= 64
      error_message = "JOB_IAM_NAME_INVALID: derived role names must fit the IAM role name limit."
    }

    precondition {
      condition     = var.secret_mode != "application-pull" || length(var.secret_references) == 0 || var.application_secret_network_path != null
      error_message = "JOB_SECRET_NETWORK_PATH_REQUIRED: application-pull mode requires secret-free private network-path metadata."
    }

    precondition {
      condition     = length(var.secret_references) == 0 || var.secret_kms_key_arn != null
      error_message = "JOB_SECRET_KMS_REQUIRED: declared secret references require an explicit customer-managed KMS key."
    }

    precondition {
      condition = alltrue([
        for permission in var.permissions : alltrue([for resource in permission.resources : !startswith(resource, "arn:") || can(regex("^arn:${data.aws_partition.current.partition}:[^:]+:[^:]*:(${var.account_id}|):.+$", resource))])
      ])
      error_message = "JOB_PERMISSION_RESOURCE_INVALID: application resources must be same-account or explicitly global ARNs."
    }

    precondition {
      condition = alltrue([
        for permission in var.permissions : alltrue([for action in permission.actions : contains(local.catalog_task_actions, action)])
      ])
      error_message = "JOB_PERMISSION_CATALOG_BLOCKING: every task-role action must be present in the versioned IAM catalog."
    }

    precondition {
      condition = alltrue([
        for reference in var.secret_references : can(regex("^arn:${data.aws_partition.current.partition}:(secretsmanager|ssm):${var.region}:${var.account_id}:.+$", reference))
      ])
      error_message = "JOB_SECRET_REFERENCE_INVALID: every secret reference must match the target partition, account, and Region."
    }

    precondition {
      condition     = endswith(split("@", var.image)[0], split("repository/", var.ecr_repository_arn)[1])
      error_message = "JOB_IMAGE_REPOSITORY_MISMATCH: immutable image repository must match ecr_repository_arn."
    }

    precondition {
      condition = alltrue([
        for attachment in var.customer_managed_policy_attachments : contains(var.approved_customer_managed_policy_arns, attachment.policy_arn) && startswith(attachment.policy_arn, "arn:${data.aws_partition.current.partition}:iam::${var.account_id}:policy/") && sha256(data.aws_iam_policy.customer_managed[attachment.policy_arn].policy) == attachment.document_sha256
      ])
      error_message = "JOB_IAM_ATTACHMENT_INVALID: every attachment must be same-account and explicitly allowlisted."
    }

    precondition {
      condition = var.secret_mode != "ecs-agent" || alltrue([
        for attachment in var.customer_managed_policy_attachments : !strcontains(lower(data.aws_iam_policy.customer_managed[attachment.policy_arn].policy), "secretsmanager:getsecretvalue") && !strcontains(lower(data.aws_iam_policy.customer_managed[attachment.policy_arn].policy), "ssm:getparameters") && !strcontains(lower(data.aws_iam_policy.customer_managed[attachment.policy_arn].policy), "kms:decrypt")
      ])
      error_message = "JOB_IAM_ATTACHMENT_SECRET_LEAK: ECS-agent secret/KMS permissions cannot be attached to the task role."
    }

    precondition {
      condition = (
        local.network_catalog_valid &&
        var.networking.policy_version == try(local.network_catalog.policy_version, "")
      )
      error_message = "NETWORK_POLICY_UNKNOWN: network policy version is absent or unsupported."
    }

    precondition {
      condition = (
        length(var.networking.subnet_ids) > 0 &&
        (var.networking.security_group_mode == "existing" ? length(var.networking.security_group_ids) > 0 : length(var.networking.security_group_ids) == 0) &&
        setsubtract(toset(keys(var.networking.subnet_evidence)), var.networking.subnet_ids) == toset([]) &&
        setsubtract(var.networking.subnet_ids, toset(keys(var.networking.subnet_evidence))) == toset([]) &&
        alltrue([for subnet_id, evidence in var.networking.subnet_evidence : evidence.account_id == var.account_id && evidence.region == var.region && evidence.vpc_id == var.networking.vpc_id && evidence.classification == "private" && contains(try(local.network_catalog.private_subnet_evidence.accepted_methods, []), evidence.method) && length(trimspace(evidence.availability_zone)) > 0 && length(trimspace(evidence.evidence_id)) > 0 && data.aws_subnet.declared[subnet_id].availability_zone == evidence.availability_zone && can(regex(try(local.network_catalog.supported_az_pattern, "^$"), evidence.availability_zone))])
      )
      error_message = "NETWORK_SUBNET_NOT_PRIVATE: every subnet must have complete approved private-subnet evidence and match the declared network."
    }

    precondition {
      condition = alltrue([for rule in values(var.networking.egress_rules) : (
        rule.protocol != "-1" &&
        rule.protocol != "all" &&
        rule.from_port >= 0 && rule.to_port >= rule.from_port && rule.to_port <= 65535 &&
        length(compact([try(rule.cidr_ipv4, null), try(rule.cidr_ipv6, null), try(rule.prefix_list_id, null), try(rule.referenced_security_group_id, null)])) == 1 &&
        !contains(["0.0.0.0/0", "::/0"], try(rule.cidr_ipv4, "")) &&
        !contains(["0.0.0.0/0", "::/0"], try(rule.cidr_ipv6, ""))
      )])
      error_message = "NETWORK_EGRESS_UNRESTRICTED / NETWORK_EGRESS_ALL_PROTOCOLS: created security-group egress must be explicit and bounded."
    }

    precondition {
      condition = (
        data.aws_vpc.declared.id == var.networking.vpc_id &&
        data.aws_vpc.declared.owner_id == var.account_id &&
        alltrue([for subnet in data.aws_subnet.declared : subnet.vpc_id == var.networking.vpc_id && subnet.owner_id == var.account_id && subnet.availability_zone != ""]) &&
        alltrue([for group in data.aws_security_group.existing : group.vpc_id == var.networking.vpc_id]) &&
        alltrue([for group in data.aws_security_group.egress_destination : group.vpc_id == var.networking.vpc_id]) &&
        alltrue([for prefix_list in data.aws_prefix_list.egress_destination : length(prefix_list.cidr_blocks) > 0]) &&
        setsubtract(keys(var.networking.security_group_owner_account_ids), var.networking.security_group_ids) == toset([]) &&
        setsubtract(var.networking.security_group_ids, toset(keys(var.networking.security_group_owner_account_ids))) == toset([]) &&
        alltrue([for group_id, owner_id in var.networking.security_group_owner_account_ids : owner_id == var.account_id])
      )
      error_message = "NETWORK_SUBNET_VPC_MISMATCH: VPC, subnet, security-group, account, or Region evidence does not match the declaration."
    }

    precondition {
      condition     = alltrue([for evidence in values(var.networking.subnet_evidence) : evidence.classification == "private" && evidence.account_id == var.account_id && evidence.region == var.region && evidence.vpc_id == var.networking.vpc_id && contains(local.network_catalog.private_subnet_evidence.accepted_methods, evidence.method)])
      error_message = "NETWORK_SUBNET_NOT_PRIVATE: every supplied subnet must have approved private-subnet evidence."
    }

    precondition {
      condition = alltrue([
        for rule in local.existing_rules : (
          rule.is_egress &&
          rule.ip_protocol != "-1" && rule.from_port >= 0 && rule.to_port >= rule.from_port && rule.to_port <= 65535 &&
          length(compact([try(rule.cidr_ipv4, null), try(rule.cidr_ipv6, null), try(rule.prefix_list_id, null), try(rule.referenced_security_group_id, null)])) == 1 &&
          !contains(["0.0.0.0/0", "::/0"], try(rule.cidr_ipv4, "")) && !contains(["0.0.0.0/0", "::/0"], try(rule.cidr_ipv6, ""))
        )
      ])
      error_message = "NETWORK_SECURITY_GROUP_PUBLIC_INGRESS / NETWORK_EGRESS_UNRESTRICTED: existing security groups must have no ingress and no unrestricted or all-protocol egress."
    }

    precondition {
      condition     = length(local.network_path_findings) == 0
      error_message = "NETWORK_DEPENDENCY_REACHABILITY_MISSING: every required platform and secret dependency needs approved path evidence."
    }

    precondition {
      condition = alltrue([
        for dependency, reachability in var.networking.dependency_reachability : (
          contains(try(local.network_catalog.dependency_paths, []), reachability.path_kind) &&
          contains(local.all_required_network_dependencies, dependency) &&
          length(reachability.identifiers) > 0 &&
          alltrue([for identifier in reachability.identifiers : !strcontains(lower(identifier), "secret") && length(trimspace(identifier)) > 0])
        )
      ])
      error_message = "NETWORK_DEPENDENCY_REACHABILITY_INVALID: dependency paths must use approved kinds and secret-free identifiers."
    }

    precondition {
      condition = var.secret_mode != "application-pull" || (
        length(var.secret_references) == 0 ||
        (var.application_secret_network_path != null && alltrue([for dependency in local.secret_dependencies : contains(keys(var.networking.dependency_reachability), dependency) && var.networking.dependency_reachability[dependency].path_kind == var.application_secret_network_path.kind && var.networking.dependency_reachability[dependency].identifiers == toset(var.application_secret_network_path.identifiers)]))
      )
      error_message = "NETWORK_SECRET_PATH_MISMATCH: application-pull secret access requires an exact declared private dependency path."
    }
  }
}
