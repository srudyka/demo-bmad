variable "environment" {
  description = "Example environment value; replace in an environment root."
  type        = string
  default     = "dev"
}

variable "application" {
  description = "Example platform application name."
  type        = string
  default     = "platform"
}

variable "service" {
  description = "Example service tag."
  type        = string
  default     = "ecs-scheduled-jobs"
}

variable "owner" {
  description = "Example owning team tag."
  type        = string
  default     = "platform-engineering"
}

variable "cell_id" {
  description = "Example stable Cell identifier."
  type        = string
  default     = "dev-platform-cell"
}

variable "kms_key_arn" {
  description = "Fictitious structural KMS ARN for validation only; provide an approved key in a real root."
  type        = string
  default     = "arn:aws:kms:us-east-1:000000000000:key/00000000-0000-0000-0000-000000000000"
}

variable "access_log_bucket_name" {
  description = "Fictitious private access-log bucket name for validation only."
  type        = string
  default     = "example-platform-access-logs"
}

variable "metric_namespace" {
  description = "Example reserved metric namespace."
  type        = string
  default     = "Platform/EcsScheduledJobs"
}

variable "enable_recovery_protection" {
  description = "Example non-production recovery protection setting."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Example optional tags; required Cell tags are supplied by the module."
  type        = map(string)
  default = {
    CostCenter = "platform"
    Repository = "example-repository"
    ManagedBy  = "consumer-override-is-ignored"
  }
}

variable "permissions_boundary_arn" {
  description = "Fictitious IAM boundary ARN for validation only."
  type        = string
  default     = "arn:aws:iam::000000000000:policy/platform-boundary"
}

variable "canary_reservation" {
  description = "Fictitious platform-owned canary reservation for validation only."
  type = object({
    apply_role_arn    = string
    apply_role_id     = string
    application       = string
    account_id        = string
    environment       = string
    job_id            = string
    owner             = string
    owner_generation  = number
    region            = string
    repository_id     = string
    terraform_root_id = string
  })
  default = {
    apply_role_arn    = "arn:aws:iam::000000000000:role/platform-canary-apply"
    apply_role_id     = "AROACANARYEXAMPLE"
    application       = "platform"
    account_id        = "000000000000"
    environment       = "dev"
    job_id            = "dev/platform/canary"
    owner             = "platform-engineering"
    owner_generation  = 1
    region            = "us-east-1"
    repository_id     = "example/platform-terraform"
    terraform_root_id = "fixtures/canary"
  }
}
