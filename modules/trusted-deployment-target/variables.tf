variable "name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9-]{3,50}$", var.name))
    error_message = "name must be a lowercase DNS-safe deployment target name."
  }
}
variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account ID."
  }
}
variable "environment" { type = string }
variable "region" {
  type = string
  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.region))
    error_message = "region must be an AWS Region."
  }
}
variable "oidc_provider_arn" {
  type = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:oidc-provider/token\\.actions\\.githubusercontent\\.com$", var.oidc_provider_arn))
    error_message = "oidc_provider_arn must identify the GitHub Actions OIDC provider."
  }
}
variable "repository_owner_id" { type = string }
variable "repository_id" { type = string }
variable "plan_workflow_ref" { type = string }
variable "apply_workflow_ref" { type = string }
variable "plan_oidc_subject" {
  type = string
  validation {
    condition     = can(regex("^repository_owner_id:${var.repository_owner_id}:repository_id:${var.repository_id}:environment:${var.environment}:job_workflow_ref:${var.plan_workflow_ref}@[0-9a-f]{40}$", var.plan_oidc_subject))
    error_message = "plan_oidc_subject must use immutable IDs and a full workflow SHA."
  }
}
variable "apply_oidc_subject" {
  type = string
  validation {
    condition     = can(regex("^repository_owner_id:${var.repository_owner_id}:repository_id:${var.repository_id}:environment:${var.environment}:job_workflow_ref:${var.apply_workflow_ref}@[0-9a-f]{40}$", var.apply_oidc_subject))
    error_message = "apply_oidc_subject must use immutable IDs and a full workflow SHA."
  }
}
variable "state_bucket_arn" {
  type = string
  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:s3:::[a-z0-9.-]{3,63}$", var.state_bucket_arn))
    error_message = "state_bucket_arn must be an S3 bucket ARN."
  }
}
variable "state_bucket_name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9.-]{3,63}$", var.state_bucket_name))
    error_message = "state_bucket_name must be a valid S3 bucket name."
  }
}
variable "state_key" {
  type = string
  validation {
    condition     = length(var.state_key) > 0 && !strcontains(var.state_key, "*") && !strcontains(var.state_key, "..")
    error_message = "state_key must be a non-wildcard isolated path."
  }
}
variable "apply_actions" {
  type    = list(string)
  default = []
  validation {
    condition     = alltrue([for action in var.apply_actions : !contains(["iam:CreateUser", "iam:CreateAccessKey", "iam:UpdateAssumeRolePolicy", "iam:PassRole", "sts:AssumeRole"], action)])
    error_message = "apply_actions contains a forbidden authorization action."
  }
}
variable "apply_resource_arns" {
  type    = list(string)
  default = []
  validation {
    condition     = alltrue([for arn in var.apply_resource_arns : !strcontains(arn, "*") && (startswith(arn, "arn:aws:s3:::") || strcontains(arn, ":${var.account_id}:")) && (startswith(arn, "arn:aws:iam::") || startswith(arn, "arn:aws:s3:::") || strcontains(arn, ":${var.region}:"))])
    error_message = "apply_resource_arns must be exact, non-wildcard resources in the manifest account and Region."
  }
}
variable "apply_resource_prefixes" {
  type = list(string)
  validation {
    condition     = length(var.apply_resource_prefixes) > 0 && alltrue([for prefix in var.apply_resource_prefixes : length(prefix) > 0 && !strcontains(prefix, "*")])
    error_message = "apply_resource_prefixes must contain explicit non-wildcard manifest namespaces."
  }
}
variable "permissions_boundary_arn" { type = string }
variable "tags" {
  type = map(string)
  validation {
    condition     = alltrue([for key in ["Environment", "Application", "Service", "Owner", "ManagedBy"] : contains(keys(var.tags), key)])
    error_message = "required ownership tags are missing."
  }
}

variable "plan_session_duration" {
  type    = number
  default = 1800
  validation {
    condition     = var.plan_session_duration >= 900 && var.plan_session_duration <= 3600
    error_message = "plan_session_duration must be 900..3600 seconds."
  }
}

variable "apply_session_duration" {
  type    = number
  default = 1800
  validation {
    condition     = var.apply_session_duration >= 900 && var.apply_session_duration <= 3600
    error_message = "apply_session_duration must be 900..3600 seconds."
  }
}
