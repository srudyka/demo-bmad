variable "tags" {
  description = "Required AWS tags. Environment, Application, Service, Owner, and ManagedBy are required and are used for predictable resource naming."
  type        = map(string)

  validation {
    condition = alltrue([
      for key in ["Environment", "Application", "Service", "Owner", "ManagedBy"] :
      length(trimspace(try(var.tags[key], ""))) > 0
    ])
    error_message = "tags must include non-empty Environment, Application, Service, Owner, and ManagedBy values."
  }

  validation {
    condition = alltrue([
      for key in ["Environment", "Application", "Service"] :
      can(regex("^[A-Za-z0-9][A-Za-z0-9-]{1,24}$", try(var.tags[key], "")))
    ])
    error_message = "tags Environment, Application, and Service must be 2-25 characters and contain only letters, numbers, and hyphens."
  }

  validation {
    condition     = length("${try(var.tags["Environment"], "")}-${try(var.tags["Application"], "")}-${try(var.tags["Service"], "")}") <= 54
    error_message = "combined Environment-Application-Service tag values must be 54 characters or fewer to leave room for role suffixes."
  }

  validation {
    condition     = try(var.tags["ManagedBy"], "") == "Terraform"
    error_message = "tags.ManagedBy must be Terraform."
  }
}

variable "cluster_arn" {
  description = "ARN of the ECS cluster that EventBridge Scheduler will run the task on."
  type        = string

  validation {
    condition     = can(regex("^arn:(aws|aws-us-gov|aws-cn):ecs:[a-z0-9-]+:[0-9]{12}:cluster/.+$", var.cluster_arn))
    error_message = "cluster_arn must be a valid ECS cluster ARN."
  }
}

variable "cluster_name" {
  description = "Name of the ECS cluster, used for operator-facing outputs and documentation."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9-_]{0,254}$", var.cluster_name))
    error_message = "cluster_name must be a valid ECS cluster name."
  }
}

variable "subnet_ids" {
  description = "Private subnet IDs used by the scheduled Fargate task."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) > 0 && alltrue([for subnet_id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", subnet_id))])
    error_message = "subnet_ids must contain at least one valid subnet ID."
  }
}

variable "security_group_ids" {
  description = "Security group IDs attached to the scheduled Fargate task."
  type        = list(string)

  validation {
    condition     = length(var.security_group_ids) > 0 && alltrue([for security_group_id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", security_group_id))])
    error_message = "security_group_ids must contain at least one valid security group ID."
  }
}

variable "container_name" {
  description = "Name of the single container in the scheduled task definition."
  type        = string
  default     = "job"

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$", var.container_name))
    error_message = "container_name must be 2-64 characters and contain only letters, numbers, underscores, and hyphens."
  }
}

variable "container_image" {
  description = "Immutable container image reference. Accepts sha256 digests, commit SHA tags, semantic version tags, or release-* tags. latest and untagged images are rejected."
  type        = string

  validation {
    condition = (
      can(regex("@sha256:[0-9A-Fa-f]{64}$", var.container_image)) ||
      can(regex(":[0-9A-Fa-f]{7,64}$", var.container_image)) ||
      can(regex(":v?[0-9]+\\.[0-9]+\\.[0-9]+([-.+][0-9A-Za-z._-]+)?$", var.container_image)) ||
      can(regex(":release-[0-9A-Za-z._-]+$", var.container_image))
    ) && !can(regex(":latest$", lower(var.container_image)))
    error_message = "container_image must use an immutable digest, commit SHA tag, semantic version tag, or release-* tag; latest and untagged images are not allowed."
  }
}

variable "readonly_root_filesystem" {
  description = "Whether the container root filesystem is read-only. Keep true unless the job requires scratch writes to the container filesystem."
  type        = bool
  default     = true
}

variable "container_command" {
  description = "Optional command override for the scheduled job container."
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Non-secret environment variables for the container. Use container_secrets for sensitive values."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for key in keys(var.environment_variables) :
      can(regex("^[A-Za-z_][A-Za-z0-9_]*$", key)) &&
      !can(regex("(?i)(secret|password|passwd|token|key)$", key))
    ])
    error_message = "environment_variables keys must be valid environment variable names and must not look like secret, password, token, or key values."
  }
}

variable "container_secrets" {
  description = "Map of container environment variable name to Secrets Manager secret ARN or SSM parameter ARN. Plaintext values are rejected."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for key in keys(var.container_secrets) :
      can(regex("^[A-Za-z_][A-Za-z0-9_]*$", key))
    ])
    error_message = "container_secrets keys must be valid environment variable names."
  }

  validation {
    condition = alltrue([
      for value in values(var.container_secrets) :
      can(regex("^arn:(aws|aws-us-gov|aws-cn):secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:.+", value)) ||
      can(regex("^arn:(aws|aws-us-gov|aws-cn):ssm:[a-z0-9-]+:[0-9]{12}:parameter/.+", value))
    ])
    error_message = "container_secrets values must be Secrets Manager secret ARNs or SSM parameter ARNs."
  }
}

variable "secret_kms_key_arns" {
  description = "Optional KMS key ARNs required to decrypt customer-managed keys for configured Secrets Manager secrets or SSM parameters."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.secret_kms_key_arns :
      can(regex("^arn:(aws|aws-us-gov|aws-cn):kms:[a-z0-9-]+:[0-9]{12}:key/.+$", arn))
    ])
    error_message = "secret_kms_key_arns must contain valid KMS key ARNs."
  }
}

variable "compute" {
  description = "Fargate CPU and memory combination for the scheduled task."
  type = object({
    cpu    = number
    memory = number
  })

  validation {
    condition = (
      var.compute.cpu == 256 && contains([512, 1024, 2048], var.compute.memory)
      ) || (
      var.compute.cpu == 512 && contains([1024, 2048, 3072, 4096], var.compute.memory)
      ) || (
      var.compute.cpu == 1024 && contains([2048, 3072, 4096, 5120, 6144, 7168, 8192], var.compute.memory)
      ) || (
      var.compute.cpu == 2048 && contains([4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384], var.compute.memory)
      ) || (
      var.compute.cpu == 4096 && contains([8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384, 17408, 18432, 19456, 20480, 21504, 22528, 23552, 24576, 25600, 26624, 27648, 28672, 29696, 30720], var.compute.memory)
      ) || (
      var.compute.cpu == 8192 && contains([16384, 20480, 24576, 28672, 32768, 36864, 40960, 45056, 49152, 53248, 57344, 61440], var.compute.memory)
      ) || (
      var.compute.cpu == 16384 && contains([32768, 40960, 49152, 57344, 65536, 73728, 81920, 90112, 98304, 106496, 114688, 122880], var.compute.memory)
    )
    error_message = "compute must use a valid ECS Fargate CPU and memory combination."
  }
}

variable "ephemeral_storage_gib" {
  description = "Ephemeral storage size in GiB. Fargate default is 20 GiB; values above 20 add an explicit ephemeral_storage block."
  type        = number
  default     = 20

  validation {
    condition     = var.ephemeral_storage_gib >= 20 && var.ephemeral_storage_gib <= 200
    error_message = "ephemeral_storage_gib must be between 20 and 200."
  }
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression such as rate(5 minutes), cron(...), or at(...)."
  type        = string

  validation {
    condition = (
      can(regex("^rate\\((1 (minute|hour|day)|[2-9][0-9]* (minutes|hours|days))\\)$", var.schedule_expression)) ||
      can(regex("^cron\\([^\\n]+\\)$", var.schedule_expression)) ||
      can(regex("^at\\([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\)$", var.schedule_expression))
    )
    error_message = "schedule_expression must be a valid-looking rate(...), cron(...), or at(yyyy-mm-ddThh:mm:ss) expression."
  }
}

variable "schedule_expression_timezone" {
  description = "Timezone for the schedule expression."
  type        = string
  default     = "UTC"

  validation {
    condition     = var.schedule_expression_timezone == "UTC" || can(regex("^[A-Za-z_]+/[A-Za-z0-9_+.-]+$", var.schedule_expression_timezone))
    error_message = "schedule_expression_timezone must be UTC or an IANA timezone-style value such as America/Chicago."
  }
}

variable "schedule_group_name" {
  description = "Optional EventBridge Scheduler group name. When null, the module creates a dedicated group named from Environment-Application-Service to keep alarms isolated."
  type        = string
  default     = null

  validation {
    condition     = var.schedule_group_name == null || can(regex("^[A-Za-z0-9._-]{1,64}$", var.schedule_group_name))
    error_message = "schedule_group_name must be null or 1-64 characters containing only letters, numbers, periods, underscores, and hyphens."
  }
}

variable "schedule_enabled" {
  description = "Whether the schedule is enabled. Set false for emergency stop or rollback."
  type        = bool
  default     = true
}

variable "flexible_time_window" {
  description = "EventBridge Scheduler flexible time window configuration."
  type = object({
    mode                      = string
    maximum_window_in_minutes = optional(number)
  })
  default = {
    mode = "OFF"
  }

  validation {
    condition     = contains(["OFF", "FLEXIBLE"], var.flexible_time_window.mode)
    error_message = "flexible_time_window.mode must be OFF or FLEXIBLE."
  }

  validation {
    condition = (
      var.flexible_time_window.mode == "OFF"
      ? try(var.flexible_time_window.maximum_window_in_minutes, null) == null
      : try(var.flexible_time_window.maximum_window_in_minutes, 0) >= 1 && try(var.flexible_time_window.maximum_window_in_minutes, 0) <= 1440
    )
    error_message = "maximum_window_in_minutes must be omitted when mode is OFF, and must be 1-1440 when mode is FLEXIBLE."
  }
}

variable "maximum_event_age_in_seconds" {
  description = "Maximum age of a scheduler event before it is discarded or sent to the DLQ."
  type        = number
  default     = 3600

  validation {
    condition     = var.maximum_event_age_in_seconds >= 60 && var.maximum_event_age_in_seconds <= 86400
    error_message = "maximum_event_age_in_seconds must be between 60 and 86400."
  }
}

variable "maximum_retry_attempts" {
  description = "Maximum scheduler retry attempts before failed delivery is sent to the DLQ."
  type        = number
  default     = 3

  validation {
    condition     = var.maximum_retry_attempts >= 0 && var.maximum_retry_attempts <= 185
    error_message = "maximum_retry_attempts must be between 0 and 185."
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
  description = "Fargate platform version."
  type        = string
  default     = "1.4.0"

  validation {
    condition     = can(regex("^[0-9]+\\.[0-9]+\\.[0-9]+$", var.platform_version))
    error_message = "platform_version must be pinned to a semantic version such as 1.4.0."
  }
}

variable "runtime_platform" {
  description = "Runtime platform for the Fargate task definition."
  type = object({
    operating_system_family = string
    cpu_architecture        = string
  })
  default = {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  validation {
    condition     = contains(["LINUX"], var.runtime_platform.operating_system_family) && contains(["X86_64", "ARM64"], var.runtime_platform.cpu_architecture)
    error_message = "runtime_platform must use LINUX with X86_64 or ARM64."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 365

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a valid CloudWatch Logs retention value."
  }
}

variable "kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for CloudWatch Logs, SQS DLQ, and EventBridge Scheduler encryption. When null, SQS uses SQS-managed encryption and CloudWatch Logs/Scheduler use service defaults."
  type        = string
  default     = null

  validation {
    condition     = var.kms_key_arn == null || can(regex("^arn:(aws|aws-us-gov|aws-cn):kms:[a-z0-9-]+:[0-9]{12}:key/.+$", var.kms_key_arn))
    error_message = "kms_key_arn must be a valid KMS key ARN when provided."
  }
}

variable "dlq_message_retention_seconds" {
  description = "SQS DLQ message retention in seconds."
  type        = number
  default     = 1209600

  validation {
    condition     = var.dlq_message_retention_seconds >= 60 && var.dlq_message_retention_seconds <= 1209600
    error_message = "dlq_message_retention_seconds must be between 60 and 1209600."
  }
}

variable "alarm_sns_topic_arns" {
  description = "Optional SNS topic ARNs for CloudWatch alarm actions."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.alarm_sns_topic_arns :
      can(regex("^arn:(aws|aws-us-gov|aws-cn):sns:[a-z0-9-]+:[0-9]{12}:.+$", arn))
    ])
    error_message = "alarm_sns_topic_arns must contain valid SNS topic ARNs."
  }
}

variable "alarm_period_seconds" {
  description = "CloudWatch alarm period in seconds."
  type        = number
  default     = 300

  validation {
    condition     = var.alarm_period_seconds > 0
    error_message = "alarm_period_seconds must be greater than 0."
  }
}

variable "alarm_evaluation_periods" {
  description = "CloudWatch alarm evaluation periods."
  type        = number
  default     = 1

  validation {
    condition     = var.alarm_evaluation_periods > 0
    error_message = "alarm_evaluation_periods must be greater than 0."
  }
}

variable "alarm_datapoints_to_alarm" {
  description = "CloudWatch alarm datapoints to alarm."
  type        = number
  default     = 1

  validation {
    condition     = var.alarm_datapoints_to_alarm > 0
    error_message = "alarm_datapoints_to_alarm must be greater than 0."
  }
}

variable "scheduler_failure_alarm_threshold" {
  description = "Threshold for Scheduler target error and dropped invocation alarms."
  type        = number
  default     = 1

  validation {
    condition     = var.scheduler_failure_alarm_threshold > 0
    error_message = "scheduler_failure_alarm_threshold must be greater than 0."
  }
}

variable "dlq_age_alarm_threshold_seconds" {
  description = "Threshold for the DLQ ApproximateAgeOfOldestMessage alarm."
  type        = number
  default     = 300

  validation {
    condition     = var.dlq_age_alarm_threshold_seconds > 0
    error_message = "dlq_age_alarm_threshold_seconds must be greater than 0."
  }
}

variable "ecr_repository_arns" {
  description = "Optional ECR repository ARNs the execution role can pull from. ecr:GetAuthorizationToken still requires Resource=* by AWS design."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.ecr_repository_arns :
      can(regex("^arn:(aws|aws-us-gov|aws-cn):ecr:[a-z0-9-]+:[0-9]{12}:repository/.+$", arn))
    ])
    error_message = "ecr_repository_arns must contain valid ECR repository ARNs."
  }
}
