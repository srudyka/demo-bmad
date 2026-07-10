variable "aws_region" {
  description = "AWS region used by the provider."
  type        = string
}

variable "cluster_arn" {
  description = "Existing ECS cluster ARN for the scheduled job."
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for the scheduled Fargate task."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for the scheduled Fargate task."
  type        = list(string)
}

variable "container_image" {
  description = "Immutable container image reference for the example job. Use a digest, semantic release tag, or commit SHA tag."
  type        = string
}

variable "alarm_actions" {
  description = "Optional alarm action ARNs, such as SNS topic ARNs."
  type        = list(string)
  default     = []
}
