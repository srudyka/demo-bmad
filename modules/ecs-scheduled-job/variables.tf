variable "environment" {
  description = "Deployment environment name, such as dev, staging, or prod."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,14}[a-z0-9]$", var.environment))
    error_message = "environment must be 2-16 lowercase letters, numbers, or hyphens, and must start and end with a letter or number."
  }
}

variable "application" {
  description = "Application name used in resource names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,14}[a-z0-9]$", var.application))
    error_message = "application must be 2-16 lowercase letters, numbers, or hyphens, and must start and end with a letter or number."
  }
}

variable "service" {
  description = "Scheduled job service/component name used in resource names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,14}[a-z0-9]$", var.service))
    error_message = "service must be 2-16 lowercase letters, numbers, or hyphens, and must start and end with a letter or number."
  }
}

variable "owner" {
  description = "Owning team or person for required AWS tags."
  type        = string

  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner must be non-empty."
  }
}

variable "repository" {
  description = "Source repository URL or slug for AWS tags."
  type        = string
  default     = ""
}

variable "cost_center" {
  description = "Optional cost center tag value."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags merged with required tags. Required tags win on key conflicts."
  type        = map(string)
  default     = {}
}

variable "cluster_arn" {
  description = "ARN of the ECS cluster where the scheduled task runs."
  type        = string

  validation {
    condition     = can(regex("^arn:aws[a-z-]*:ecs:[a-z0-9-]+:[0-9]{12}:cluster/.+", var.cluster_arn))
    error_message = "cluster_arn must be a valid ECS cluster ARN."
  }
}

variable "subnet_ids" {
  description = "Private subnet IDs for the Fargate task ENIs."
  type        = list(string)

  validation {
    condition = (
      length(var.subnet_ids) > 0 &&
      length(var.subnet_ids) <= 16 &&
      length(distinct(var.subnet_ids)) == length(var.subnet_ids) &&
      alltrue([for id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    )
    error_message = "subnet_ids must contain 1-16 distinct subnet IDs."
  }
}

variable "security_group_ids" {
  description = "Security group IDs attached to the Fargate task ENIs."
  type        = list(string)

  validation {
    condition = (
      length(var.security_group_ids) > 0 &&
      length(var.security_group_ids) <= 5 &&
      length(distinct(var.security_group_ids)) == length(var.security_group_ids) &&
      alltrue([for id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", id))])
    )
    error_message = "security_group_ids must contain 1-5 distinct security group IDs."
  }
}

variable "assign_public_ip" {
  description = "Whether to assign a public IP to the Fargate task. Keep false for internal jobs."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Immutable container image reference for the scheduled job."
  type        = string

  validation {
    condition = (
      length(trimspace(var.container_image)) > 0 &&
      can(regex("(:[^/:@]+|@sha256:[0-9a-f]{64})$", var.container_image)) &&
      !endswith(var.container_image, ":latest")
    )
    error_message = "container_image must be immutable: include a non-latest tag or sha256 digest."
  }
}

variable "container_name" {
  description = "Name of the primary ECS container."
  type        = string
  default     = "job"
}

variable "container_command" {
  description = "Optional container command override."
  type        = list(string)
  default     = []
}

variable "container_entrypoint" {
  description = "Optional container entrypoint override."
  type        = list(string)
  default     = []
}

variable "container_environment" {
  description = "Non-secret environment variables for the container. Do not pass secrets here."
  type        = map(string)
  default     = {}
}

variable "container_secrets" {
  description = "Secret environment variables for the container, mapped from name to Secrets Manager or SSM valueFrom ARN."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for value_from in values(var.container_secrets) : startswith(value_from, "arn:")])
    error_message = "container_secrets values must be ARNs so execution-role permissions can be scoped exactly."
  }
}

variable "cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096, 8192, 16384, 32768], var.cpu)
    error_message = "cpu must be one of 256, 512, 1024, 2048, 4096, 8192, 16384, or 32768."
  }
}

variable "memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512

  validation {
    condition     = var.memory >= 512 && var.memory <= 249856
    error_message = "memory must be between 512 and 249856 MiB."
  }
}

variable "task_count" {
  description = "Number of Fargate tasks launched per schedule invocation."
  type        = number
  default     = 1

  validation {
    condition     = var.task_count >= 1 && var.task_count <= 10
    error_message = "task_count must be between 1 and 10."
  }
}

variable "platform_version" {
  description = "Fargate platform version used by EventBridge Scheduler RunTask."
  type        = string
  default     = "1.4.0"
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression, for example rate(5 minutes) or cron(0 3 * * ? *)."
  type        = string

  validation {
    condition = (
      can(regex("^rate\\([1-9][0-9]* (minute|minutes|hour|hours|day|days)\\)$", var.schedule_expression)) ||
      can(regex("^cron\\([^)]{9,}\\)$", var.schedule_expression)) ||
      can(regex("^at\\([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\)$", var.schedule_expression))
    )
    error_message = "schedule_expression must be a valid-looking rate(...), cron(...), or at(YYYY-MM-DDTHH:MM:SS) expression."
  }
}

variable "schedule_expression_timezone" {
  description = "Timezone used to evaluate the schedule expression."
  type        = string
  default     = "UTC"
}

variable "schedule_group_name" {
  description = "Existing EventBridge Scheduler group name."
  type        = string
  default     = "default"
}

variable "schedule_enabled" {
  description = "Whether the schedule is enabled."
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
  description = "Maximum flexible time window in minutes when flexible_time_window_mode is FLEXIBLE."
  type        = number
  default     = 5

  validation {
    condition     = var.maximum_window_in_minutes >= 1 && var.maximum_window_in_minutes <= 1440
    error_message = "maximum_window_in_minutes must be between 1 and 1440."
  }
}

variable "maximum_event_age_in_seconds" {
  description = "Maximum event age for EventBridge Scheduler retry policy."
  type        = number
  default     = 3600

  validation {
    condition     = var.maximum_event_age_in_seconds >= 60 && var.maximum_event_age_in_seconds <= 86400
    error_message = "maximum_event_age_in_seconds must be between 60 and 86400."
  }
}

variable "maximum_retry_attempts" {
  description = "Maximum retry attempts before EventBridge Scheduler sends failed delivery to the DLQ."
  type        = number
  default     = 3

  validation {
    condition     = var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185
    error_message = "maximum_retry_attempts must be between 0 and 185."
  }
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days."
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a valid CloudWatch Logs retention value."
  }
}

variable "dlq_message_retention_seconds" {
  description = "SQS DLQ message retention period in seconds."
  type        = number
  default     = 1209600

  validation {
    condition     = var.dlq_message_retention_seconds >= 60 && var.dlq_message_retention_seconds <= 1209600
    error_message = "dlq_message_retention_seconds must be between 60 and 1209600."
  }
}

variable "alarm_actions" {
  description = "SNS topic or other CloudWatch alarm action ARNs."
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "Optional CloudWatch OK action ARNs."
  type        = list(string)
  default     = []
}

variable "alarm_evaluation_periods" {
  description = "Evaluation periods for module-created CloudWatch alarms."
  type        = number
  default     = 1
}

variable "dlq_visible_messages_alarm_threshold" {
  description = "Visible message threshold for the DLQ backlog alarm."
  type        = number
  default     = 1
}

variable "scheduler_target_error_alarm_threshold" {
  description = "Target error count threshold for the EventBridge Scheduler alarm."
  type        = number
  default     = 1
}

variable "task_failure_alarm_threshold" {
  description = "Non-zero container exit count threshold for the ECS task failure alarm."
  type        = number
  default     = 1
}

variable "enable_ecr_pull_permissions" {
  description = "Whether to include ECR pull permissions in the execution role."
  type        = bool
  default     = false
}

variable "ecr_repository_arns" {
  description = "ECR repository ARNs the execution role may pull from. ecr:GetAuthorizationToken still requires Resource * by AWS design."
  type        = list(string)
  default     = []
}

variable "execution_secret_arns" {
  description = "Secrets Manager or SSM Parameter ARNs the execution role may read for ECS container secrets."
  type        = list(string)
  default     = []
}

variable "kms_key_arns" {
  description = "KMS key ARNs the execution role may decrypt for configured secrets."
  type        = list(string)
  default     = []
}

variable "task_managed_policy_arns" {
  description = "Managed policy ARNs to attach to the ECS task role for application permissions."
  type        = list(string)
  default     = []
}

variable "task_policy_statements" {
  description = "Inline IAM statements for the ECS task role. Keep resources scoped to the job's application needs."
  type = list(object({
    sid       = optional(string)
    effect    = optional(string, "Allow")
    actions   = list(string)
    resources = list(string)
    conditions = optional(list(object({
      test     = string
      variable = string
      values   = list(string)
    })), [])
  }))
  default = []

  validation {
    condition     = alltrue([for statement in var.task_policy_statements : !contains(statement.resources, "*") || length(statement.conditions) > 0])
    error_message = "task_policy_statements may use Resource * only when at least one IAM condition is supplied."
  }
}
