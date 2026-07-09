variable "name" {
  description = "Stable name for this scheduled job. Used in resource names and tags."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,51}[a-z0-9]$", var.name))
    error_message = "name must be 3-53 characters and use lowercase letters, numbers, and hyphens. The limit leaves room for IAM role suffixes."
  }
}

variable "environment" {
  description = "Deployment environment, such as dev, staging, or prod."
  type        = string
}

variable "application" {
  description = "Application or platform capability that owns this job."
  type        = string
}

variable "service" {
  description = "Service name for tagging and ownership."
  type        = string
}

variable "owner" {
  description = "Owning team or contact for this scheduled job."
  type        = string
}

variable "cost_center" {
  description = "Optional cost center tag value."
  type        = string
  default     = null
}

variable "repository" {
  description = "Optional source repository tag value."
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional tags to apply to all supported resources."
  type        = map(string)
  default     = {}
}

variable "cluster_arn" {
  description = "ARN of the ECS cluster that will run the scheduled task."
  type        = string

  validation {
    condition     = can(regex("^arn:aws[a-zA-Z-]*:ecs:", var.cluster_arn))
    error_message = "cluster_arn must be an ECS cluster ARN."
  }
}

variable "subnet_ids" {
  description = "Private subnet IDs for the Fargate task ENI."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) > 0
    error_message = "At least one subnet ID is required."
  }
}

variable "security_group_ids" {
  description = "Security group IDs for the Fargate task ENI."
  type        = list(string)

  validation {
    condition     = length(var.security_group_ids) > 0
    error_message = "At least one security group ID is required."
  }
}

variable "assign_public_ip" {
  description = "Whether the task ENI should receive a public IP. Keep false for internal jobs."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Container image URI for the scheduled job."
  type        = string

  validation {
    condition     = !can(regex(":latest$", var.container_image))
    error_message = "container_image must not use the mutable latest tag."
  }
}

variable "container_name" {
  description = "Optional container name. Defaults to name."
  type        = string
  default     = null
}

variable "command" {
  description = "Optional command override for the scheduled container."
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Non-secret environment variables for the container."
  type        = map(string)
  default     = {}

  validation {
    condition     = length(setintersection(keys(var.environment_variables), keys(var.secrets))) == 0
    error_message = "environment_variables and secrets must not define the same container environment variable name."
  }
}

variable "secrets" {
  description = "Map of container environment variable name to Secrets Manager or SSM Parameter ARN."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for arn in values(var.secrets) : can(regex("^arn:aws[a-zA-Z-]*:(secretsmanager|ssm):", arn))
    ])
    error_message = "secrets values must be Secrets Manager or SSM Parameter Store ARNs."
  }
}

variable "kms_key_arns" {
  description = "Optional KMS key ARNs needed by the execution role to decrypt injected secrets."
  type        = list(string)
  default     = []
}

variable "cpu" {
  description = "Fargate task CPU units."
  type        = number

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.cpu)
    error_message = "cpu must be one of 256, 512, 1024, 2048, or 4096."
  }
}

variable "memory" {
  description = "Fargate task memory in MiB."
  type        = number

  validation {
    condition     = var.memory >= 512
    error_message = "memory must be at least 512 MiB."
  }
}

variable "ephemeral_storage_gib" {
  description = "Optional Fargate ephemeral storage in GiB. AWS default is used when null."
  type        = number
  default     = null

  validation {
    condition     = var.ephemeral_storage_gib == null || (var.ephemeral_storage_gib >= 21 && var.ephemeral_storage_gib <= 200)
    error_message = "ephemeral_storage_gib must be null or between 21 and 200."
  }
}

variable "platform_version" {
  description = "Fargate platform version."
  type        = string
  default     = "LATEST"
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression, for example rate(5 minutes) or cron(0 3 * * ? *)."
  type        = string

  validation {
    condition     = can(regex("^(rate|cron|at)\\(", var.schedule_expression))
    error_message = "schedule_expression must start with rate(, cron(, or at(."
  }
}

variable "schedule_expression_timezone" {
  description = "Timezone for the schedule expression."
  type        = string
  default     = "UTC"
}

variable "schedule_group_name" {
  description = "Optional EventBridge Scheduler group. Defaults to name so metrics are job-scoped."
  type        = string
  default     = null
}

variable "schedule_state" {
  description = "Scheduler state."
  type        = string
  default     = "ENABLED"

  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.schedule_state)
    error_message = "schedule_state must be ENABLED or DISABLED."
  }
}

variable "schedule_input_json" {
  description = "Optional JSON string passed to the ECS task target."
  type        = string
  default     = null

  validation {
    condition     = var.schedule_input_json == null || can(jsondecode(var.schedule_input_json))
    error_message = "schedule_input_json must be valid JSON when set."
  }
}

variable "maximum_retry_attempts" {
  description = "Maximum Scheduler retry attempts for failed target invocation."
  type        = number
  default     = 2

  validation {
    condition     = var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185
    error_message = "maximum_retry_attempts must be between 0 and 185."
  }
}

variable "maximum_event_age_in_seconds" {
  description = "Maximum event age for Scheduler retry policy."
  type        = number
  default     = 3600

  validation {
    condition     = var.maximum_event_age_in_seconds >= 60 && var.maximum_event_age_in_seconds <= 86400
    error_message = "maximum_event_age_in_seconds must be between 60 and 86400."
  }
}

variable "dead_letter_queue_arn" {
  description = "Optional SQS queue ARN for events Scheduler cannot deliver."
  type        = string
  default     = null
}

variable "task_policy_statements" {
  description = "Least-privilege IAM statements attached to the task role for job-specific AWS access."
  type = list(object({
    sid       = string
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
    condition = alltrue([
      for statement in var.task_policy_statements : contains(["Allow", "Deny"], statement.effect)
    ])
    error_message = "task_policy_statements effect must be Allow or Deny."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 30
}

variable "log_group_name" {
  description = "Optional CloudWatch log group name. Defaults to /ecs/scheduled/<name>."
  type        = string
  default     = null
}

variable "alarm_action_arns" {
  description = "SNS topic or incident-management action ARNs for alarm state."
  type        = list(string)
  default     = []
}

variable "task_failure_event_target_arns" {
  description = "Optional EventBridge target ARNs for ECS STOPPED task events with non-zero container exit codes. Defaults to alarm_action_arns when empty."
  type        = list(string)
  default     = []
}

variable "ok_action_arns" {
  description = "Optional action ARNs for OK state."
  type        = list(string)
  default     = []
}

variable "failed_invocation_alarm_threshold" {
  description = "Threshold for Scheduler target errors and dropped invocations."
  type        = number
  default     = 1
}

variable "alarm_period_seconds" {
  description = "CloudWatch alarm period in seconds."
  type        = number
  default     = 300
}

variable "alarm_evaluation_periods" {
  description = "Number of periods evaluated by Scheduler alarms."
  type        = number
  default     = 1
}
