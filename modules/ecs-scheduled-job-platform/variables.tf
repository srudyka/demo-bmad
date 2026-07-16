variable "environment" {
  description = "Canonical deployment environment for this account/Region Cell."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,11}$", var.environment))
    error_message = "environment must be 1-12 lowercase letters, numbers, or hyphens."
  }
}

variable "application" {
  description = "Platform application name used in protected tags and resource names."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,15}$", var.application))
    error_message = "application must be 1-16 lowercase letters, numbers, or hyphens."
  }
}

variable "service" {
  description = "Service tag value for the Platform Cell."
  type        = string

  validation {
    condition     = can(regex("^[ -~]+$", var.service))
    error_message = "service must be a nonempty printable ASCII string."
  }
}

variable "owner" {
  description = "Owning team or on-call identifier used in protected tags."
  type        = string

  validation {
    condition     = can(regex("^[ -~]+$", var.owner))
    error_message = "owner must be a nonempty printable ASCII string."
  }
}

variable "cell_id" {
  description = "Stable Cell identifier published in the Cell Contract."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{0,127}$", var.cell_id))
    error_message = "cell_id must be 1-128 lowercase letters, numbers, or hyphens."
  }
}

variable "kms_key_arn" {
  description = "Approved customer-managed KMS key ARN used to encrypt Cell data."
  type        = string

  validation {
    condition = can(
      regex("^arn:[a-z0-9-]+:kms:[a-z0-9-]+:[0-9]{12}:key/[0-9a-fA-F-]+$", var.kms_key_arn),
    )
    error_message = "kms_key_arn must be a customer-managed KMS key ARN."
  }
}

variable "access_log_bucket_name" {
  description = "Existing private S3 bucket approved to receive CONFIG inbox access logs."
  type        = string

  validation {
    condition = can(
      regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.access_log_bucket_name),
    )
    error_message = "access_log_bucket_name must be a valid 3-63 character lowercase S3 bucket name."
  }
}

variable "metric_namespace" {
  description = "Reserved bounded CloudWatch metric namespace published for later Cell integrations."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9/_-]{1,255}$", var.metric_namespace))
    error_message = "metric_namespace must contain only letters, numbers, slash, underscore, or hyphen."
  }
}

variable "contract_version" {
  description = "Semantic version of the Cell Contract published by this foundation."
  type        = string
  default     = "1.0.0"

  validation {
    condition     = can(regex("^1\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$", var.contract_version))
    error_message = "contract_version must be a canonical semantic version within the supported Cell range >=1.0.0,<2.0.0."
  }
}

variable "enable_recovery_protection" {
  description = "Enables DynamoDB deletion protection for Cell registries; required for prod. PITR is always enabled."
  type        = bool

  validation {
    condition     = var.environment != "prod" || var.enable_recovery_protection
    error_message = "enable_recovery_protection must be true when environment is prod."
  }
}

variable "incomplete_multipart_upload_days" {
  description = "Bounded number of days before incomplete CONFIG multipart uploads are aborted."
  type        = number
  default     = 7

  validation {
    condition = (
      var.incomplete_multipart_upload_days >= 1 &&
      var.incomplete_multipart_upload_days <= 365 &&
      floor(var.incomplete_multipart_upload_days) == var.incomplete_multipart_upload_days
    )
    error_message = "incomplete_multipart_upload_days must be a whole number from 1 through 365."
  }
}

variable "tags" {
  description = "Additional non-secret tags. Required platform tags are set by the module and override collisions."
  type        = map(string)
  default     = {}
}

variable "permissions_boundary_arn" {
  description = "Approved IAM permissions-boundary ARN applied to Cell bootstrap roles."
  type        = string

  validation {
    condition = can(
      regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:policy/[A-Za-z0-9+=,.@_/-]+$", var.permissions_boundary_arn),
    )
    error_message = "permissions_boundary_arn must be an IAM managed-policy ARN."
  }
}

variable "canary_reservation" {
  description = "Platform-controlled immutable reservation for the one non-production canary before the general Registrar exists."
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

  validation {
    condition = (
      can(regex("^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$", var.canary_reservation.job_id)) &&
      can(regex("^arn:[a-z0-9-]+:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$", var.canary_reservation.apply_role_arn)) &&
      can(regex("^[0-9]{12}$", var.canary_reservation.account_id)) &&
      var.canary_reservation.owner_generation >= 1 &&
      floor(var.canary_reservation.owner_generation) == var.canary_reservation.owner_generation &&
      alltrue([
        for value in [
          var.canary_reservation.apply_role_id,
          var.canary_reservation.repository_id,
          var.canary_reservation.terraform_root_id,
          var.canary_reservation.owner,
        ] : can(regex("^[ -~]+$", value))
      ])
    )
    error_message = "canary_reservation must contain a canonical job ID, exact apply identity, account, nonempty ASCII ownership fields, and a positive whole generation."
  }
}
