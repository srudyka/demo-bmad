variable "aws_region" {
  description = "AWS region for this account/environment."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "application" {
  description = "Application name."
  type        = string
  default     = "platform"
}

variable "service" {
  description = "Scheduled job service name."
  type        = string
  default     = "sample-job"
}

variable "owner" {
  description = "Owning team or person."
  type        = string
  default     = "platform-team"
}

variable "repository" {
  description = "Source repository tag value."
  type        = string
  default     = "github.com/example/platform"
}

variable "cost_center" {
  description = "Optional cost center tag value."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional AWS tags."
  type        = map(string)
  default     = {}
}

variable "cluster_arn" {
  description = "Account-local ECS cluster ARN."
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for the scheduled task."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for the scheduled task."
  type        = list(string)
}

variable "container_image" {
  description = "Immutable container image tag."
  type        = string
}

variable "container_command" {
  description = "Container command override."
  type        = list(string)
  default     = []
}

variable "container_environment" {
  description = "Non-secret environment variables."
  type        = map(string)
  default     = {}
}

variable "container_secrets" {
  description = "Secret environment variable references."
  type        = map(string)
  default     = {}
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression."
  type        = string
}

variable "schedule_expression_timezone" {
  description = "Timezone for the schedule expression."
  type        = string
  default     = "UTC"
}

variable "schedule_enabled" {
  description = "Whether the schedule is enabled."
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "Alarm action ARNs."
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "Alarm OK action ARNs."
  type        = list(string)
  default     = []
}

variable "ecr_repository_arns" {
  description = "ECR repository ARNs the execution role may pull from."
  type        = list(string)
  default     = []
}

variable "execution_secret_arns" {
  description = "Secret ARNs the execution role may read."
  type        = list(string)
  default     = []
}

variable "kms_key_arns" {
  description = "KMS key ARNs the execution role may decrypt."
  type        = list(string)
  default     = []
}

variable "task_managed_policy_arns" {
  description = "Managed policy ARNs for application task permissions."
  type        = list(string)
  default     = []
}

variable "task_policy_statements" {
  description = "Inline IAM statements for application task permissions."
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
}
