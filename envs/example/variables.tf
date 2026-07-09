variable "aws_region" {
  description = "AWS region for the target account."
  type        = string
}

variable "assume_role_arn" {
  description = "Role ARN used by CI or operators to manage scheduled jobs in the target account."
  type        = string
}

variable "environment" {
  description = "Example environment name."
  type        = string
  default     = "dev"
}

variable "cluster_arn" {
  description = "Target ECS cluster ARN."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for scheduled job ENIs."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs for scheduled job ENIs."
  type        = list(string)
}

variable "container_image" {
  description = "Container image URI for the example job."
  type        = string
}

variable "example_parameter_path_arn" {
  description = "Scoped SSM parameter path ARN this example job may read, for example arn:aws:ssm:us-east-1:123456789012:parameter/dev/platform/nightly-example/*."
  type        = string
}

variable "alarm_action_arns" {
  description = "SNS topic or incident-management action ARNs for failed scheduled jobs."
  type        = list(string)
  default     = []
}
