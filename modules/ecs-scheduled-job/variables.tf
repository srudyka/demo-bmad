variable "environment" {
  description = "Non-production deployment environment for this scheduled job."
  type        = string
  validation {
    condition     = can(regex("^(dev|test|qa|staging)(-[a-z0-9-]+)?$", var.environment))
    error_message = "environment must use an explicit non-production name: dev, test, qa, or staging, optionally with a bounded suffix."
  }
}

variable "application" {
  description = "Application namespace owning the scheduled job."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", var.application)) && !contains(["platform", "system", "latest", "current"], var.application)
    error_message = "application must be lowercase letters, numbers, or hyphens."
  }
}

variable "job_name" {
  description = "Stable application job segment used to derive the canonical job ID."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", var.job_name)) && !startswith(var.job_name, "platform-") && !contains(["latest", "current"], var.job_name)
    error_message = "job_name must be lowercase, stable, and must not use the reserved platform- prefix."
  }
}

variable "owner" {
  description = "Application owner or on-call identifier for the reservation."
  type        = string
  validation {
    condition     = length(trimspace(var.owner)) > 0 && can(regex("^[ -~]+$", var.owner))
    error_message = "owner must be nonempty printable ASCII."
  }
}

variable "repository_id" {
  description = "Immutable source repository identifier bound to the reservation."
  type        = string
  validation {
    condition     = can(regex("^[0-9]+$", var.repository_id))
    error_message = "repository_id must be an immutable numeric repository identifier."
  }
}

variable "terraform_root_id" {
  description = "Immutable repository/root identity bound to the reservation."
  type        = string
  validation {
    condition     = length(trimspace(var.terraform_root_id)) > 0 && !strcontains(var.terraform_root_id, "..")
    error_message = "terraform_root_id must be nonempty and must not traverse paths."
  }
}

variable "apply_role_id" {
  description = "Immutable apply-role identifier authorized to own the reservation."
  type        = string
  validation {
    condition     = length(trimspace(var.apply_role_id)) > 0
    error_message = "apply_role_id must be nonempty."
  }
}

variable "account_id" {
  description = "Target AWS account ID that must match the discovered Cell Contract."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account ID."
  }
}

variable "config_publisher_role_arn" {
  description = "Dedicated same-account Cell publisher role used for create-only CONFIG publication."
  type        = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:role/(?:[A-Za-z0-9+=,.@_-]+/)*[A-Za-z0-9+=,.@_-]+$", var.config_publisher_role_arn))
    error_message = "config_publisher_role_arn must be an exact IAM role ARN."
  }
}

variable "config_validator_role_arn" {
  description = "Cell-owned IAM role used by the acknowledgement validator provider boundary."
  type        = string
  default     = ""

  validation {
    condition = var.config_validator_role_arn == "" || can(regex(
      "^arn:[a-z0-9-]+:iam::[0-9]{12}:role/(?:[A-Za-z0-9+=,.@_-]+/)*[A-Za-z0-9+=,.@_-]+$",
      var.config_validator_role_arn,
    ))
    error_message = "config_validator_role_arn must be empty or an exact IAM role ARN."
  }
}

variable "region" {
  description = "Target AWS Region that must match the discovered Cell Contract."
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}(?:-gov|-iso|-isob|-iso-b)?-[a-z]+-[0-9]+$", var.region))
    error_message = "region must be a valid AWS Region-shaped value."
  }
}

variable "ecs_cluster_arn" {
  description = "Existing ECS cluster ARN consumed by later job-resource stories."
  type        = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:ecs:[a-z0-9-]+:[0-9]{12}:cluster/[A-Za-z0-9/_-]+$", var.ecs_cluster_arn))
    error_message = "ecs_cluster_arn must be an exact ECS cluster ARN."
  }
}

variable "image" {
  description = "Immutable container image reference; tags must be digests."
  type        = string
  validation {
    condition     = can(regex("^[^@]+@sha256:[0-9a-f]{64}$", var.image))
    error_message = "image must use an immutable sha256 digest and cannot use latest."
  }
}

variable "schedule_expression" {
  description = "Recurring EventBridge schedule expression retained for later activation."
  type        = string
  validation {
    condition = (
      can(regex("^rate\\((1 (minute|hour|day)|[1-9][0-9]* (minutes|hours|days))\\)$", var.schedule_expression)) ||
      can(regex("^cron\\([0-9*/,-]+ [0-9*/,-]+ \\* \\* \\? \\*\\)$", var.schedule_expression)) ||
      can(regex("^cron\\([0-9*/,-]+ [0-9*/,-]+ \\? \\* [A-Z0-7?,L-]+ \\*\\)$", var.schedule_expression)) ||
      can(regex("^cron\\([0-9*/,-]+ [0-9*/,-]+ [0-9,L?*/-]+ \\* \\? \\*\\)$", var.schedule_expression))
    )
    error_message = "schedule_expression must be a rate(...) or cron(...) expression."
  }
}

variable "schedule_time_zone" {
  description = "IANA time zone used by the disabled recurring Scheduler schedule."
  type        = string
  default     = "UTC"
  validation {
    condition     = can(regex("^(UTC|[A-Za-z]+/[A-Za-z0-9_.+-]+)$", var.schedule_time_zone))
    error_message = "schedule_time_zone must be UTC or an IANA Area/Location time zone."
  }
}

variable "activation_start" {
  description = "RFC 3339 UTC future anchor for the phase-one schedule and CONFIG contract."
  type        = string
  validation {
    condition     = can(formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", var.activation_start)) && can(regex("^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\\.[0-9]{3}Z$", var.activation_start))
    error_message = "activation_start must be a canonical RFC 3339 UTC timestamp with millisecond precision."
  }
}

variable "activation" {
  description = "Explicit phase-two materialized acknowledgement. Keep disabled until the exact Cell generation has a verified horizon."
  type = object({
    enabled                    = bool
    lifecycle                  = string
    account_id                 = string
    region                     = string
    job_id                     = string
    config_version             = string
    contract_version           = string
    contract_checksum          = string
    schedule_generation        = string
    schedule_arn               = string
    schedule_group_arn         = string
    scheduler_delivery_role_id = string
    launch_role_id             = string
    task_definition_arn        = string
    owner_generation           = number
    horizon_watermark          = string
    conformance_result         = string
    validation_evidence        = string
    deployment_identity_id     = string
  })
  default = {
    enabled                    = false
    lifecycle                  = "PUBLISHED"
    account_id                 = ""
    region                     = ""
    job_id                     = ""
    config_version             = ""
    contract_version           = ""
    contract_checksum          = ""
    schedule_generation        = ""
    schedule_arn               = ""
    schedule_group_arn         = ""
    scheduler_delivery_role_id = ""
    launch_role_id             = ""
    task_definition_arn        = ""
    owner_generation           = 0
    horizon_watermark          = ""
    conformance_result         = "PENDING"
    validation_evidence        = ""
    deployment_identity_id     = ""
  }

  validation {
    condition = (
      !var.activation.enabled || (
        var.environment != "prod" &&
        var.activation.lifecycle == "MATERIALIZED" &&
        var.activation.conformance_result == "PASS" &&
        var.activation.owner_generation >= 1 &&
        can(regex("^[0-9a-f]{64}$", var.activation.config_version)) &&
        can(regex("^[0-9a-f]{64}$", var.activation.schedule_generation)) &&
        can(regex("^[0-9a-f]{64}$", var.activation.contract_checksum)) &&
        length(var.activation.validation_evidence) > 0 &&
        can(formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", var.activation.horizon_watermark))
      )
    )
    error_message = "ACTIVATION_ACK_INVALID: phase-two enablement requires a non-production MATERIALIZED acknowledgement with PASS conformance, immutable hashes, evidence, and a valid horizon."
  }
}

variable "activation_end" {
  description = "Optional RFC 3339 UTC exclusive end of the activation window."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.activation_end == null || (can(formatdate("YYYY-MM-DD'T'hh:mm:ss'Z'", var.activation_end)) && can(regex("^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\\.[0-9]{3}Z$", var.activation_end)))
    error_message = "activation_end must be null or a canonical RFC 3339 UTC timestamp with millisecond precision."
  }
}

variable "maximum_retry_attempts" {
  description = "EventBridge Scheduler delivery retry attempts for the disabled schedule."
  type        = number
  default     = 3
  validation {
    condition     = var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185 && floor(var.maximum_retry_attempts) == var.maximum_retry_attempts
    error_message = "maximum_retry_attempts must be a whole number from 0 through 185."
  }
}

variable "maximum_event_age_seconds" {
  description = "Maximum age of an undelivered Scheduler event in seconds."
  type        = number
  default     = 3600
  validation {
    condition     = var.maximum_event_age_seconds >= 60 && var.maximum_event_age_seconds <= 86400 && floor(var.maximum_event_age_seconds) == var.maximum_event_age_seconds
    error_message = "maximum_event_age_seconds must be a whole number from 60 through 86400."
  }
}

variable "cpu" {
  description = "Requested Fargate CPU units for later task-definition creation."
  type        = number
  validation {
    condition = contains(
      [
        "256:512", "256:1024", "256:2048", "512:1024", "512:2048", "512:3072", "512:4096",
        "1024:2048", "1024:3072", "1024:4096", "1024:5120", "1024:6144", "1024:7168", "1024:8192",
        "2048:4096", "2048:5120", "2048:6144", "2048:7168", "2048:8192", "2048:9216", "2048:10240", "2048:11264", "2048:12288", "2048:13312", "2048:14336", "2048:15360", "2048:16384",
        "4096:8192", "4096:9216", "4096:10240", "4096:11264", "4096:12288", "4096:13312", "4096:14336", "4096:15360", "4096:16384", "4096:17408", "4096:18432", "4096:19456", "4096:20480", "4096:21504", "4096:22528", "4096:23552", "4096:24576", "4096:25600", "4096:26624", "4096:27648", "4096:28672", "4096:29696", "4096:30720",
      ],
      format("%.0f:%.0f", var.cpu, var.memory),
    ) && floor(var.cpu) == var.cpu && floor(var.memory) == var.memory
    error_message = "cpu must be within the supported positive Fargate range."
  }
}

variable "memory" {
  description = "Requested Fargate memory MiB for later task-definition creation."
  type        = number
  validation {
    condition     = var.memory > 0 && var.memory <= 122880 && floor(var.memory) == var.memory
    error_message = "memory must be within the supported positive Fargate range."
  }
}

variable "platform_version" {
  description = "Pinned Linux Fargate platform version used by the task definition."
  type        = string
  default     = "1.4.0"
  validation {
    condition     = contains(["1.4.0", "1.5.0", "LATEST"], var.platform_version)
    error_message = "platform_version must be an approved Fargate platform version."
  }
}

variable "operating_system_family" {
  description = "Fargate runtime operating-system family for the task definition."
  type        = string
  default     = "LINUX"
  validation {
    condition     = var.operating_system_family == "LINUX"
    error_message = "Only the approved Linux Fargate operating-system family is supported."
  }
}

variable "cpu_architecture" {
  description = "Fargate CPU architecture for the immutable task runtime."
  type        = string
  default     = "X86_64"
  validation {
    condition     = contains(["X86_64", "ARM64"], var.cpu_architecture)
    error_message = "cpu_architecture must be X86_64 or ARM64."
  }
}

variable "ephemeral_storage_gib" {
  description = "Optional Fargate ephemeral storage in GiB; values must use the supported expanded-storage range."
  type        = number
  default     = 21
  validation {
    condition     = var.ephemeral_storage_gib >= 21 && var.ephemeral_storage_gib <= 200 && floor(var.ephemeral_storage_gib) == var.ephemeral_storage_gib
    error_message = "ephemeral_storage_gib must be a whole number from 21 through 200 GiB."
  }
}

variable "command" {
  description = "Optional non-secret container command declaration."
  type        = list(string)
  default     = []
}

variable "entrypoint" {
  description = "Optional non-secret container entrypoint declaration."
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Non-secret application configuration retained for later task publication."
  type        = map(string)
  default     = {}
  validation {
    condition = alltrue([
      for name, value in var.environment_variables : (
        can(regex("^[A-Z][A-Z0-9_]{0,127}$", name)) &&
        !contains(["JOB_ID", "OCCURRENCE_ID", "CONFIG_VERSION", "ATTEMPT_NO", "TASK_ARN", "DEPLOYMENT_IDENTITY", "SOURCE_REVISION", "MODULE_VERSION", "SECRET_MODE", "SECRET_REFERENCE_LOCATORS", "SECRET_NETWORK_PATH"], name) &&
        !strcontains(lower(name), "secret") &&
        !strcontains(lower(name), "password") &&
        !strcontains(lower(name), "token") &&
        !strcontains(lower(name), "credential") &&
        !strcontains(value, "=")
      )
    ])
    error_message = "environment_variables must be uppercase non-secret names and cannot override reserved runtime identity fields."
  }
}

variable "secret_references" {
  description = "Exact Secrets Manager or SSM references; secret values are never accepted."
  type        = list(string)
  default     = []
  validation {
    condition = alltrue([
      for value in var.secret_references :
      !strcontains(value, "=") && !strcontains(value, " ") && can(regex("^arn:[a-z0-9-]+:(secretsmanager|ssm):[a-z0-9-]+:[0-9]{12}:.+$", value))
    ])
    error_message = "secret_references must contain exact Secrets Manager or SSM ARNs only, never key/value pairs or plaintext."
  }
}

variable "secret_environment_names" {
  description = "Non-secret environment names paired by position with secret_references; values are never accepted."
  type        = list(string)
  default     = []
  validation {
    condition = (
      (length(var.secret_references) == 0 && length(var.secret_environment_names) == 0) ||
      length(var.secret_environment_names) == length(var.secret_references)
      ) && length(distinct(var.secret_environment_names)) == length(var.secret_environment_names) && alltrue([
        for name in var.secret_environment_names : can(regex("^[A-Z][A-Z0-9_]{0,127}$", name)) && !contains(["JOB_ID", "OCCURRENCE_ID", "CONFIG_VERSION", "ATTEMPT_NO", "TASK_ARN", "DEPLOYMENT_IDENTITY", "SOURCE_REVISION", "MODULE_VERSION", "SECRET_MODE", "SECRET_REFERENCE_LOCATORS", "SECRET_NETWORK_PATH"], name)
    ])
    error_message = "secret_environment_names must be unique, uppercase, non-reserved names matching secret_references by position."
  }
}

variable "log_retention_days" {
  description = "Optional CloudWatch log retention override; non-production defaults to 30 days and production to 90 days."
  type        = number
  default     = null
  nullable    = true
  validation {
    condition     = var.log_retention_days == null || contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be an AWS-supported retention value."
  }
}

variable "source_revision" {
  description = "Immutable source revision recorded in Deployment Identity; no source contents are accepted."
  type        = string
  default     = "unknown"
  validation {
    condition     = can(regex("^[A-Za-z0-9._/-]{1,128}$", var.source_revision)) && !strcontains(var.source_revision, "secret")
    error_message = "source_revision must be a bounded non-secret revision identifier."
  }
}

variable "module_version" {
  description = "Semantic module version recorded in Deployment Identity."
  type        = string
  default     = "1.0.0"
  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.module_version))
    error_message = "module_version must be a semantic version."
  }
}

variable "permissions_boundary_arn" {
  description = "Cell-approved same-account customer-managed IAM permissions boundary required on all three job roles."
  type        = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:policy/platform-[A-Za-z0-9/_+=,.@-]+$", var.permissions_boundary_arn))
    error_message = "permissions_boundary_arn must be a platform-owned customer-managed IAM policy ARN."
  }
}

variable "cell_process_manager_role_arn" {
  description = "Exact stable Cell-major Process Manager role ARN allowed to assume the job-launch role."
  type        = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:role/platform-[A-Za-z0-9/_+=,.@-]+$", var.cell_process_manager_role_arn))
    error_message = "cell_process_manager_role_arn must be an exact same-account platform Process Manager role ARN."
  }
}

variable "ecr_repository_arn" {
  description = "Exact same-account ECR repository from which the immutable job image is pulled."
  type        = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:ecr:[a-z0-9-]+:[0-9]{12}:repository/[A-Za-z0-9/_-]+$", var.ecr_repository_arn))
    error_message = "ecr_repository_arn must be an exact ECR repository ARN."
  }
}

variable "secret_mode" {
  description = "Secret delivery mode: ecs-agent grants references to execution, application-pull grants them to task."
  type        = string
  default     = "ecs-agent"
  validation {
    condition     = contains(["ecs-agent", "application-pull"], var.secret_mode)
    error_message = "secret_mode must be ecs-agent or application-pull."
  }
}

variable "secret_kms_key_arn" {
  description = "Optional same-account customer-managed KMS key used to decrypt the declared secret references."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.secret_kms_key_arn == null || can(regex("^arn:[a-z0-9-]+:kms:[a-z0-9-]+:[0-9]{12}:key/[0-9a-f-]+$", var.secret_kms_key_arn))
    error_message = "secret_kms_key_arn must be a same-account KMS key ARN when provided."
  }
}

variable "application_secret_network_path" {
  description = "Secret-free network path metadata required when application-pull mode is selected; networking resources belong to Story 2.3."
  type = object({
    kind        = string
    identifiers = set(string)
  })
  default  = null
  nullable = true
  validation {
    condition = var.application_secret_network_path == null || (
      contains(["vpc-endpoint", "private-subnets"], var.application_secret_network_path.kind) &&
      length(var.application_secret_network_path.identifiers) > 0 &&
      alltrue([for identifier in var.application_secret_network_path.identifiers : length(trimspace(identifier)) > 0])
    )
    error_message = "application_secret_network_path must name a supported private path and at least one identifier."
  }
}

variable "permissions" {
  description = "Reviewable task-role application permissions with stable statement IDs and optional StringEquals conditions."
  type = list(object({
    statement_id = optional(string, "ApplicationPermission")
    actions      = set(string)
    resources    = set(string)
    conditions   = optional(map(string), {})
  }))
  default = []
  validation {
    condition = alltrue(flatten([
      for permission in var.permissions : [
        length(trimspace(permission.statement_id)) > 0,
        length(permission.actions) > 0,
        length(permission.resources) > 0,
        alltrue([for action in permission.actions : !contains([
          "*", "iam:PassRole", "iam:CreateUser", "iam:CreateAccessKey", "iam:AttachRolePolicy",
          "iam:PutRolePolicy", "iam:UpdateAssumeRolePolicy", "iam:PutRolePermissionsBoundary",
          "iam:DeleteRolePermissionsBoundary", "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion",
          "iam:DeleteRole", "sts:AssumeRole", "dynamodb:PutItem", "s3:PutBucketPolicy"
        ], action) && !strcontains(action, "*") && !startswith(action, "iam:") && !startswith(action, "organizations:")]),
        alltrue([for resource in permission.resources : resource != "*" && !strcontains(resource, "*") && !strcontains(resource, "CONFIG")])
      ]
    ])) && length(distinct([for permission in var.permissions : permission.statement_id])) == length(var.permissions)
    error_message = "permissions require unique nonempty statements with explicit non-wildcard same-account workload actions/resources; IAM, control-plane, ledger, CONFIG, and wildcard escalation is rejected."
  }
}

variable "approved_customer_managed_policy_arns" {
  description = "Cell-approved allowlist of same-account customer-managed policy ARNs permitted for this job."
  type        = set(string)
  default     = []
}

variable "customer_managed_policy_attachments" {
  description = "Explicitly governed same-account policy attachments with a reviewed version and boundary-compatibility assertion."
  type = list(object({
    policy_arn          = string
    version_id          = string
    document_sha256     = string
    allowlisted         = bool
    boundary_compatible = bool
  }))
  default = []
  validation {
    condition = alltrue([
      for attachment in var.customer_managed_policy_attachments :
      can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:policy/[A-Za-z0-9/_+=,.@-]+$", attachment.policy_arn)) &&
      length(trimspace(attachment.version_id)) > 0 && attachment.allowlisted && attachment.boundary_compatible
      && can(regex("^[0-9a-f]{64}$", attachment.document_sha256))
    ])
    error_message = "customer-managed attachments must be same-account policy ARNs with nonempty governed versions, allowlisting, and boundary compatibility."
  }
}

variable "runtime" {
  description = "Declared runtime expectations for the scheduled job."
  type = object({
    max_runtime_seconds = number
    idempotency         = string
  })
  validation {
    condition     = var.runtime.max_runtime_seconds > 0 && floor(var.runtime.max_runtime_seconds) == var.runtime.max_runtime_seconds && contains(["idempotent", "application-lock", "duplicate-safe"], var.runtime.idempotency)
    error_message = "runtime must declare a positive max runtime and a supported idempotency mode."
  }
}

variable "overlap_policy" {
  description = "Whether overlapping scheduled occurrences are allowed by the application."
  type        = string
  validation {
    condition     = contains(["allow", "reject", "lock"], var.overlap_policy)
    error_message = "overlap_policy must be allow, reject, or lock."
  }
}

variable "networking" {
  description = "Explicit private-network declaration and secret-free reachability evidence consumed by later task resources."
  type = object({
    vpc_id              = string
    subnet_ids          = list(string)
    security_group_ids  = optional(set(string), [])
    security_group_mode = optional(string, "existing")
    policy_version      = string
    subnet_evidence = optional(map(object({
      account_id        = string
      region            = string
      vpc_id            = string
      availability_zone = string
      classification    = string
      evidence_id       = string
      method            = string
      route_table_id    = string
    })), {})
    egress_rules = optional(map(object({
      protocol                     = string
      from_port                    = number
      to_port                      = number
      cidr_ipv4                    = optional(string)
      cidr_ipv6                    = optional(string)
      prefix_list_id               = optional(string)
      referenced_security_group_id = optional(string)
    })), {})
    dependency_reachability = optional(map(object({
      path_kind   = string
      identifiers = set(string)
    })), {})
    application_dependencies         = optional(set(string), [])
    security_group_owner_account_ids = optional(map(string), {})
  })
  validation {
    condition = (
      can(regex("^vpc-[0-9a-f]{8,}$", var.networking.vpc_id)) &&
      length(var.networking.subnet_ids) > 0 &&
      length(distinct(var.networking.subnet_ids)) == length(var.networking.subnet_ids) &&
      alltrue([for subnet_id in var.networking.subnet_ids : can(regex("^subnet-[0-9a-f]{8,}$", subnet_id))]) &&
      alltrue([for group_id in var.networking.security_group_ids : can(regex("^sg-[0-9a-f]{8,}$", group_id))]) &&
      contains(["existing", "create"], var.networking.security_group_mode) &&
      can(regex("^1\\.0\\.0$", var.networking.policy_version))
      && alltrue([for rule in values(var.networking.egress_rules) : (
        (try(rule.cidr_ipv4, null) == null || can(cidrhost(rule.cidr_ipv4, 0))) &&
        (try(rule.cidr_ipv6, null) == null || can(cidrhost(rule.cidr_ipv6, 0))) &&
        (try(rule.prefix_list_id, null) == null || can(regex("^pl-[0-9a-f]{8,}$", rule.prefix_list_id))) &&
        (try(rule.referenced_security_group_id, null) == null || can(regex("^sg-[0-9a-f]{8,}$", rule.referenced_security_group_id)))
      )])
    )
    error_message = "networking must declare canonical VPC/subnet/security-group IDs, an explicit mode, and supported policy version."
  }
}

variable "notification" {
  description = "Secret-free notification and Runbook metadata consumed by later alert integration."
  type = object({
    target_arn  = string
    runbook_uri = string
  })
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:.+$", var.notification.target_arn)) && can(regex("^https://.+$", var.notification.runbook_uri))
    error_message = "notification must contain an exact AWS target ARN and HTTPS Runbook URI."
  }
}

variable "tags" {
  description = "Consumer tags merged with protected platform metadata."
  type        = map(string)
  default     = {}
}

variable "registrar_receipt" {
  description = "Secret-free receipt returned by the Cell-owned Registrar after its conditional namespace claim. The module fails closed when it is absent or mismatched."
  type = object({
    pk               = string
    sk               = string
    job_id           = string
    namespace_key    = string
    lifecycle        = string
    owner_generation = number
    tombstoned       = bool
    transfer_state   = string
  })
  default  = null
  nullable = true
}
