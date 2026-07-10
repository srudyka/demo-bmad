variable "environment" {
  description = "Deployment environment name used in resource names and required tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,11}$", var.environment))
    error_message = "environment must be 2-12 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "application" {
  description = "Application name used in resource names and required tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,23}$", var.application))
    error_message = "application must be 2-24 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "service" {
  description = "Service tag value for ownership and cost reporting."
  type        = string

  validation {
    condition     = length(trimspace(var.service)) > 0
    error_message = "service must not be empty."
  }
}

variable "job_name" {
  description = "Scheduled job component name used in resource names."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,23}$", var.job_name))
    error_message = "job_name must be 2-24 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "owner" {
  description = "Owner tag value for operational accountability."
  type        = string

  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner must not be empty."
  }
}

variable "cost_center" {
  description = "Optional CostCenter tag value."
  type        = string
  default     = null
}

variable "repository" {
  description = "Optional Repository tag value."
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional non-sensitive tags. Required ownership tags are merged by the module."
  type        = map(string)
  default     = {}
}

variable "cluster_arn" {
  description = "ARN of the ECS cluster that EventBridge Scheduler targets."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:cluster/.+", var.cluster_arn))
    error_message = "cluster_arn must be a valid ECS cluster ARN."
  }
}

variable "subnet_ids" {
  description = "Private subnet IDs used by the Fargate task network configuration."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) > 0 && alltrue([for id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    error_message = "subnet_ids must contain at least one valid subnet ID."
  }
}

variable "security_group_ids" {
  description = "Security group IDs attached to the Fargate task."
  type        = list(string)

  validation {
    condition     = length(var.security_group_ids) > 0 && alltrue([for id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", id))])
    error_message = "security_group_ids must contain at least one valid security group ID."
  }
}

variable "assign_public_ip" {
  description = "Whether to assign a public IP to the Fargate task. Keep false for private scheduled workloads."
  type        = bool
  default     = false
}

variable "container_name" {
  description = "Name of the container in the ECS task definition."
  type        = string
  default     = "job"

  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{1,64}$", var.container_name))
    error_message = "container_name must be 1-64 letters, numbers, underscores, or hyphens."
  }
}

variable "container_image" {
  description = "Immutable container image reference. Use a digest, semantic release tag, or commit SHA tag. The latest tag and floating channel tags are rejected."
  type        = string

  validation {
    condition = (
      can(regex("@sha256:[0-9a-fA-F]{64}$", var.container_image)) ||
      (
        can(regex(":[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", var.container_image)) &&
        !can(regex(":latest$", lower(var.container_image))) &&
        (
          can(regex(":(v)?[0-9]+\\.[0-9]+\\.[0-9]+([._-][A-Za-z0-9]+)?$", lower(var.container_image))) ||
          can(regex(":[0-9a-f]{7,40}$", lower(var.container_image)))
        )
      )
    )
    error_message = "container_image must include a sha256 digest, semantic release tag, or commit SHA tag; latest, tagless, and floating channel tags are rejected."
  }
}

variable "container_command" {
  description = "Optional container command override stored in the task definition."
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Non-sensitive environment variables for the container. Do not put secrets here."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for key, _ in var.environment_variables : can(regex("^[A-Za-z_][A-Za-z0-9_]*$", key))])
    error_message = "environment variable names must be valid shell-style identifiers."
  }

  validation {
    condition = alltrue([
      for key, _ in var.environment_variables :
      !can(regex("(password|passwd|secret|token|api_?key|private_?key|credential)", lower(key)))
    ])
    error_message = "environment_variables must not contain obvious secret-like keys; use container_secrets for sensitive values."
  }
}

variable "container_secrets" {
  description = "Container secrets as ECS secret references. value_from must be an SSM Parameter Store or Secrets Manager ARN, not a plaintext value."
  type = list(object({
    name       = string
    value_from = string
  }))
  default = []

  validation {
    condition = alltrue([
      for secret in var.container_secrets :
      can(regex("^[A-Za-z_][A-Za-z0-9_]*$", secret.name)) &&
      can(regex("^arn:[^:]+:(ssm|secretsmanager):[^:]+:[0-9]{12}:.+", secret.value_from))
    ])
    error_message = "container_secrets entries must use valid environment names and SSM or Secrets Manager ARNs."
  }
}

variable "secret_kms_key_arns" {
  description = "Optional KMS key ARNs needed to decrypt SecureString parameters or Secrets Manager secrets."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for arn in var.secret_kms_key_arns : can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/.+", arn))])
    error_message = "secret_kms_key_arns must contain valid KMS key ARNs."
  }
}

variable "cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096, 8192, 16384], var.cpu)
    error_message = "cpu must be a valid Fargate CPU value."
  }
}

variable "memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512
}

variable "ephemeral_storage_gib" {
  description = "Optional Fargate ephemeral storage size in GiB. Set null for the platform default."
  type        = number
  default     = null

  validation {
    condition     = var.ephemeral_storage_gib == null || (var.ephemeral_storage_gib >= 21 && var.ephemeral_storage_gib <= 200)
    error_message = "ephemeral_storage_gib must be null or between 21 and 200."
  }
}

variable "task_count" {
  description = "Number of tasks Scheduler starts for each invocation."
  type        = number
  default     = 1

  validation {
    condition     = var.task_count >= 1 && var.task_count <= 10
    error_message = "task_count must be between 1 and 10."
  }
}

variable "platform_version" {
  description = "ECS Fargate platform version."
  type        = string
  default     = "1.4.0"

  validation {
    condition     = contains(["1.4.0"], var.platform_version)
    error_message = "platform_version must be pinned to a supported Fargate platform version such as 1.4.0."
  }
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression, such as rate(5 minutes), cron(...), or at(...)."
  type        = string

  validation {
    condition     = can(regex("^(rate|cron|at)\\(.+\\)$", var.schedule_expression))
    error_message = "schedule_expression must start with rate(...), cron(...), or at(...)."
  }
}

variable "schedule_timezone" {
  description = "IANA time zone for the schedule expression."
  type        = string
  default     = "UTC"
}

variable "schedule_group_name" {
  description = "EventBridge Scheduler schedule group name."
  type        = string
  default     = "default"

  validation {
    condition     = can(regex("^[A-Za-z0-9._-]{1,64}$", var.schedule_group_name))
    error_message = "schedule_group_name must be 1-64 letters, numbers, dots, underscores, or hyphens."
  }
}

variable "create_schedule_group" {
  description = "Whether to create schedule_group_name. Leave false when using the default or a centrally managed Scheduler group."
  type        = bool
  default     = false
}

variable "schedule_enabled" {
  description = "Whether the schedule is enabled. Set false for emergency stop or rollback."
  type        = bool
  default     = true
}

variable "flexible_time_window_mode" {
  description = "EventBridge Scheduler flexible time window mode."
  type        = string
  default     = "OFF"

  validation {
    condition     = contains(["OFF", "FLEXIBLE"], var.flexible_time_window_mode)
    error_message = "flexible_time_window_mode must be OFF or FLEXIBLE."
  }
}

variable "maximum_window_in_minutes" {
  description = "Maximum flexible window in minutes when flexible_time_window_mode is FLEXIBLE."
  type        = number
  default     = null

  validation {
    condition     = var.maximum_window_in_minutes == null || (var.maximum_window_in_minutes >= 1 && var.maximum_window_in_minutes <= 1440)
    error_message = "maximum_window_in_minutes must be null or between 1 and 1440."
  }
}

variable "maximum_retry_attempts" {
  description = "Maximum Scheduler retry attempts for target delivery failures."
  type        = number
  default     = 3

  validation {
    condition     = var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185
    error_message = "maximum_retry_attempts must be between 0 and 185."
  }
}

variable "maximum_event_age_in_seconds" {
  description = "Maximum age in seconds for Scheduler delivery retries."
  type        = number
  default     = 3600

  validation {
    condition     = var.maximum_event_age_in_seconds >= 60 && var.maximum_event_age_in_seconds <= 86400
    error_message = "maximum_event_age_in_seconds must be between 60 and 86400."
  }
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days."
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a valid CloudWatch Logs retention value."
  }
}

variable "log_kms_key_id" {
  description = "Optional KMS key ARN for CloudWatch Logs encryption."
  type        = string
  default     = null
}

variable "alarm_actions" {
  description = "Optional CloudWatch alarm action ARNs, such as SNS topic ARNs."
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "Optional CloudWatch OK action ARNs."
  type        = list(string)
  default     = []
}

variable "dlq_visible_messages_alarm_threshold" {
  description = "Visible message count that triggers the scheduler DLQ alarm."
  type        = number
  default     = 1

  validation {
    condition     = var.dlq_visible_messages_alarm_threshold >= 1
    error_message = "dlq_visible_messages_alarm_threshold must be at least 1."
  }
}

variable "task_failure_alarm_evaluation_periods" {
  description = "Evaluation periods for the ECS stopped-task failure alarm."
  type        = number
  default     = 1

  validation {
    condition     = var.task_failure_alarm_evaluation_periods >= 1 && var.task_failure_alarm_evaluation_periods <= 10
    error_message = "task_failure_alarm_evaluation_periods must be between 1 and 10."
  }
}

variable "ecr_repository_arns" {
  description = "Optional private ECR repository ARNs the execution role may pull from. Leave empty for public registries."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for arn in var.ecr_repository_arns : can(regex("^arn:[^:]+:ecr:[^:]+:[0-9]{12}:repository/.+", arn))])
    error_message = "ecr_repository_arns must contain valid ECR repository ARNs."
  }
}

variable "execution_role_arn" {
  description = "Optional existing ECS task execution role ARN. If set, task_role_arn must also be set."
  type        = string
  default     = null

  validation {
    condition     = var.execution_role_arn == null || can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+", var.execution_role_arn))
    error_message = "execution_role_arn must be null or a valid IAM role ARN."
  }
}

variable "task_role_arn" {
  description = "Optional existing ECS task role ARN. If set, execution_role_arn must also be set."
  type        = string
  default     = null

  validation {
    condition     = var.task_role_arn == null || can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+", var.task_role_arn))
    error_message = "task_role_arn must be null or a valid IAM role ARN."
  }
}

variable "scheduler_role_arn" {
  description = "Optional existing EventBridge Scheduler role ARN."
  type        = string
  default     = null

  validation {
    condition     = var.scheduler_role_arn == null || can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+", var.scheduler_role_arn))
    error_message = "scheduler_role_arn must be null or a valid IAM role ARN."
  }
}

variable "task_policy_json" {
  description = "Optional least-privilege IAM policy JSON attached to the created task role. Ignored when task_role_arn is supplied."
  type        = string
  default     = null

  validation {
    condition     = var.task_policy_json == null || (can(jsondecode(var.task_policy_json)) && can(jsondecode(var.task_policy_json).Statement))
    error_message = "task_policy_json must be null or valid IAM policy JSON with a Statement field."
  }
}
