variable "account_id" {
  description = "Disposable non-production AWS account that owns the canary fixture."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account ID."
  }
}

variable "region" {
  description = "Explicit AWS Region for the canary fixture."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]+$", var.region))
    error_message = "region must be a canonical AWS Region name."
  }
}

variable "environment" {
  description = "Non-production environment for this fixture."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,11}$", var.environment)) && var.environment != "prod"
    error_message = "environment must be a canonical non-production environment."
  }
}

variable "application" {
  description = "Application tag for the platform-owned canary."
  type        = string
}

variable "service" {
  description = "Service tag for the platform-owned canary."
  type        = string
}

variable "owner" {
  description = "Owning Platform Engineering team or on-call identifier."
  type        = string
}

variable "repository_id" {
  description = "Immutable repository identifier bound by the Cell reservation."
  type        = string
}

variable "terraform_root_id" {
  description = "Repository-relative Terraform root identifier bound by the Cell reservation."
  type        = string
}

variable "apply_role_arn" {
  description = "Exact CI apply role ARN trusted to assume the Cell-owned CONFIG publisher role."
  type        = string

  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$", var.apply_role_arn))
    error_message = "apply_role_arn must be an IAM role ARN."
  }
}

variable "job_id" {
  description = "Canonical reserved canary job ID: environment/application/job."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$", var.job_id))
    error_message = "job_id must use the canonical environment/application/job form."
  }
}

variable "ownership_generation" {
  description = "Positive immutable ownership generation from the Cell reservation."
  type        = number

  validation {
    condition     = var.ownership_generation >= 1 && floor(var.ownership_generation) == var.ownership_generation
    error_message = "ownership_generation must be a positive whole number."
  }
}

variable "cell_contract_parameter_arn" {
  description = "Explicit SSM Cell Contract ARN retained as discovery evidence; it is never read through Terraform remote state."
  type        = string
}

variable "cell_config_inbox_bucket" {
  description = "Cell-owned CONFIG inbox bucket name supplied from the Cell Contract."
  type        = string
}

variable "cell_kms_key_arn" {
  description = "Cell-approved customer-managed KMS key ARN for logs, SQS, and CONFIG."
  type        = string
}

variable "cell_process_manager_role_arn" {
  description = "Stable Cell-major Process Manager role ARN that alone can assume the launch role."
  type        = string
}

variable "cell_scheduler_group_name" {
  description = "Cell-owned EventBridge Scheduler schedule-group name."
  type        = string
}

variable "cell_scheduler_source_queue_arn" {
  description = "Cell-owned Scheduler source queue ARN."
  type        = string
}

variable "cell_scheduler_dlq_arn" {
  description = "Cell-owned Scheduler DLQ ARN."
  type        = string
}

variable "cell_config_publisher_role_arn" {
  description = "Cell-owned tagged role used only for this canary's CONFIG publication."
  type        = string
}

variable "permissions_boundary_arn" {
  description = "Approved IAM permissions boundary applied to each canary role."
  type        = string
}

variable "ecs_cluster_arn" {
  description = "Existing approved ECS cluster ARN; the fixture never creates or mutates the cluster."
  type        = string
}

variable "private_subnet_ids" {
  description = "Existing private subnet IDs for eventual Fargate task networking."
  type        = set(string)

  validation {
    condition     = length(var.private_subnet_ids) > 0 && alltrue([for id in var.private_subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    error_message = "private_subnet_ids must contain at least one canonical subnet ID."
  }
}

variable "security_group_ids" {
  description = "Existing least-privilege security group IDs for eventual Fargate task networking."
  type        = set(string)

  validation {
    condition     = length(var.security_group_ids) > 0 && alltrue([for id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", id))])
    error_message = "security_group_ids must contain at least one canonical security group ID."
  }
}

variable "image_uri" {
  description = "Immutable canary image URI using a lower-case SHA-256 digest."
  type        = string

  validation {
    condition     = can(regex("^.+@sha256:[0-9a-f]{64}$", var.image_uri))
    error_message = "image_uri must use repository@sha256:<64 lowercase hex>."
  }
}

variable "ecr_repository_arn" {
  description = "Exact ECR repository ARN that contains image_uri."
  type        = string
}

variable "cpu" {
  description = "Explicit supported Fargate CPU units for the canary task."
  type        = number
}

variable "memory" {
  description = "Explicit supported Fargate memory MiB for the canary task."
  type        = number
}

variable "command" {
  description = "Non-secret canary container command override."
  type        = list(string)
}

variable "log_retention_days" {
  description = "Bounded CloudWatch log retention in days."
  type        = number

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a CloudWatch Logs supported retention value."
  }
}

variable "schedule_expression" {
  description = "Explicit recurring EventBridge Scheduler expression for the disabled canary."
  type        = string
}

variable "schedule_time_zone" {
  description = "Explicit IANA time zone for the disabled canary schedule."
  type        = string
}

variable "activation_start" {
  description = "Future canonical UTC activation anchor retained while the schedule is disabled."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$", var.activation_start))
    error_message = "activation_start must use canonical UTC RFC 3339 format with millisecond precision."
  }
}

variable "maximum_event_age_seconds" {
  description = "Bounded Scheduler delivery age in seconds."
  type        = number

  validation {
    condition     = var.maximum_event_age_seconds >= 60 && var.maximum_event_age_seconds <= 86400 && floor(var.maximum_event_age_seconds) == var.maximum_event_age_seconds
    error_message = "maximum_event_age_seconds must be a whole number from 60 through 86400."
  }
}

variable "maximum_retry_attempts" {
  description = "Bounded Scheduler delivery retry attempts."
  type        = number

  validation {
    condition     = var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185 && floor(var.maximum_retry_attempts) == var.maximum_retry_attempts
    error_message = "maximum_retry_attempts must be a whole number from 0 through 185."
  }
}

variable "completion_window_seconds" {
  description = "Expected completion window used by later occurrence-aware deadline detection."
  type        = number

  validation {
    condition     = var.completion_window_seconds >= 60 && var.completion_window_seconds <= 86400 && floor(var.completion_window_seconds) == var.completion_window_seconds
    error_message = "completion_window_seconds must be a whole number from 60 through 86400."
  }
}

variable "overlap_policy" {
  description = "Explicit application-owned overlap safety contract."
  type        = string

  validation {
    condition     = contains(["APPLICATION_IDEMPOTENT", "APPLICATION_LOCKED"], var.overlap_policy)
    error_message = "overlap_policy must declare application idempotency or locking."
  }
}

variable "source_commit" {
  description = "Immutable source commit recorded in Deployment Identity."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.source_commit))
    error_message = "source_commit must be a lowercase 40-character commit SHA."
  }
}

variable "workflow_ref" {
  description = "Immutable GitHub workflow reference recorded in Deployment Identity."
  type        = string
}

variable "workflow_sha" {
  description = "Immutable GitHub workflow commit SHA recorded in Deployment Identity."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.workflow_sha))
    error_message = "workflow_sha must be a lowercase 40-character commit SHA."
  }
}

variable "workflow_run_id" {
  description = "Positive GitHub workflow run ID recorded in Deployment Identity."
  type        = number

  validation {
    condition     = var.workflow_run_id >= 1 && floor(var.workflow_run_id) == var.workflow_run_id
    error_message = "workflow_run_id must be a positive whole number."
  }
}

variable "tags" {
  description = "Additional non-secret canary tags; required tags override collisions."
  type        = map(string)
  default     = {}
}
