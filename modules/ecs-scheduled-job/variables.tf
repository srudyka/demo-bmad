variable "environment" {
  description = "Non-production deployment environment for this scheduled job."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", var.environment)) && !contains(["prod", "latest", "current"], var.environment)
    error_message = "environment must be lowercase and non-production for Epic 2."
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
      can(regex("^rate\\([1-9][0-9]* (minute|minutes|hour|hours|day|days)\\)$", var.schedule_expression)) ||
      (can(regex("^cron\\([^()]+\\)$", var.schedule_expression)) && length(split(" ", trimprefix(trimsuffix(var.schedule_expression, ")"), "cron("))) == 6)
    )
    error_message = "schedule_expression must be a rate(...) or cron(...) expression."
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
    )
    error_message = "cpu must be within the supported positive Fargate range."
  }
}

variable "memory" {
  description = "Requested Fargate memory MiB for later task-definition creation."
  type        = number
  validation {
    condition     = var.memory > 0 && var.memory <= 122880
    error_message = "memory must be within the supported positive Fargate range."
  }
}

variable "command" {
  description = "Optional non-secret container command declaration."
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Non-secret application configuration retained for later task publication."
  type        = map(string)
  default     = {}
}

variable "secret_references" {
  description = "Exact Secrets Manager or SSM references; secret values are never accepted."
  type        = list(string)
  default     = []
  validation {
    condition     = alltrue([for value in var.secret_references : !strcontains(value, "=") && !strcontains(value, " ")])
    error_message = "secret_references must contain references only, never key/value pairs or plaintext."
  }
}

variable "permissions" {
  description = "Reviewable application permission declarations retained for the later IAM story."
  type = list(object({
    actions    = set(string)
    resources  = set(string)
    conditions = optional(map(string), {})
  }))
  default = []
}

variable "runtime" {
  description = "Declared runtime expectations for the scheduled job."
  type = object({
    max_runtime_seconds = number
    idempotency         = string
  })
  validation {
    condition     = var.runtime.max_runtime_seconds > 0 && contains(["idempotent", "application-lock", "duplicate-safe"], var.runtime.idempotency)
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
  description = "Private networking declaration reserved for later task resources."
  type = object({
    subnet_ids         = set(string)
    security_group_ids = set(string)
  })
  validation {
    condition = (
      length(var.networking.subnet_ids) > 0 && length(var.networking.security_group_ids) > 0 &&
      alltrue([for subnet_id in var.networking.subnet_ids : can(regex("^subnet-[0-9a-f]{8,}$", subnet_id))]) &&
      alltrue([for group_id in var.networking.security_group_ids : can(regex("^sg-[0-9a-f]{8,}$", group_id))])
    )
    error_message = "networking must declare at least one private subnet and security group."
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
