variable "aws_region" {
  description = "AWS region for the example provider."
  type        = string
  default     = "us-east-1"
}

variable "cluster_arn" {
  description = "Example ECS cluster ARN supplied by the target AWS account."
  type        = string
}

variable "subnet_ids" {
  description = "Example private subnet IDs supplied by the target AWS account."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Example security group IDs supplied by the target AWS account."
  type        = list(string)
}

variable "container_image" {
  description = "Immutable example image tag."
  type        = string
}

variable "ecr_repository_arns" {
  description = "Optional ECR repositories used by the example image."
  type        = list(string)
  default     = []
}

variable "alarm_actions" {
  description = "Optional alarm action ARNs."
  type        = list(string)
  default     = []
}
