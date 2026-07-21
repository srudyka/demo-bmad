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

variable "canary_normalizer_registration" {
  description = "Cell-controlled Scheduler identity binding for the platform-owned canary normalizer."
  type = object({
    account_id                 = string
    config_version             = string
    environment                = string
    job_id                     = string
    owner_generation           = number
    region                     = string
    schedule_arn               = string
    schedule_generation        = string
    schedule_group_arn         = string
    scheduler_delivery_role_id = string
    source_queue_arn           = string
    canary_launch_role_arn     = string
  })

  validation {
    condition = (
      can(regex("^[0-9]{12}$", var.canary_normalizer_registration.account_id)) &&
      can(regex("^[0-9a-f]{64}$", var.canary_normalizer_registration.config_version)) &&
      can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.canary_normalizer_registration.region)) &&
      can(regex("^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$", var.canary_normalizer_registration.job_id)) &&
      var.canary_normalizer_registration.owner_generation >= 1 &&
      floor(var.canary_normalizer_registration.owner_generation) == var.canary_normalizer_registration.owner_generation &&
      can(regex("^[0-9a-f]{64}$", var.canary_normalizer_registration.schedule_generation)) &&
      can(regex("^AROA[A-Z0-9]+$", var.canary_normalizer_registration.scheduler_delivery_role_id)) &&
      can(regex("^arn:aws:sqs:[a-z]{2}(-gov)?-[a-z]+-[0-9]+:[0-9]{12}:[A-Za-z0-9_-]{1,80}$", var.canary_normalizer_registration.source_queue_arn)) &&
      can(regex("^arn:aws:scheduler:[a-z]{2}(-gov)?-[a-z]+-[0-9]+:[0-9]{12}:schedule-group/[A-Za-z0-9_-]{1,64}$", var.canary_normalizer_registration.schedule_group_arn)) &&
      can(regex("^arn:aws:scheduler:[a-z]{2}(-gov)?-[a-z]+-[0-9]+:[0-9]{12}:schedule/[A-Za-z0-9_-]{1,64}/[A-Za-z0-9_-]{1,64}$", var.canary_normalizer_registration.schedule_arn)) &&
      can(regex("^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$", var.canary_normalizer_registration.canary_launch_role_arn))
    )
    error_message = "canary_normalizer_registration must contain canonical Cell, Scheduler, generation, and immutable role-ID values."
  }
}

variable "ecs_cluster_arn" {
  description = "Exact Cell ECS cluster ARN accepted by the ECS task-state EventBridge rule."
  type        = string

  validation {
    condition     = can(regex("^arn:[a-z0-9-]+:ecs:[a-z]{2}(-gov)?-[a-z]+-[0-9]+:[0-9]{12}:cluster/[A-Za-z0-9_-]{1,255}$", var.ecs_cluster_arn))
    error_message = "ecs_cluster_arn must be an exact ECS cluster ARN in the provider account and Region."
  }
}

variable "normalizer" {
  description = "Explicit trusted Evidence Normalizer artifact and Lambda/SQS controls."
  type = object({
    artifact_path        = string
    artifact_source_hash = string
    batch_size           = number
    batch_window_seconds = number
    log_retention_days   = number
    max_receive_count    = number
    reserved_concurrency = number
    timeout_seconds      = number
  })

  validation {
    condition = (
      length(var.normalizer.artifact_path) > 0 &&
      can(regex("^[A-Za-z0-9+/]{43}=$", var.normalizer.artifact_source_hash)) &&
      var.normalizer.batch_size >= 1 && var.normalizer.batch_size <= 10 &&
      var.normalizer.batch_window_seconds >= 0 && var.normalizer.batch_window_seconds <= 300 &&
      var.normalizer.timeout_seconds >= 1 && var.normalizer.timeout_seconds <= 900 &&
      var.normalizer.reserved_concurrency >= 2 && var.normalizer.reserved_concurrency <= 1000 &&
      var.normalizer.max_receive_count >= 5 && var.normalizer.max_receive_count <= 1000 &&
      contains([365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.normalizer.log_retention_days)
    )
    error_message = "normalizer must use the published artifact, Lambda, SQS redrive, and log-retention bounds."
  }
}

variable "log_ingestor" {
  description = "Explicit trusted completion log-ingestor artifact and bounded Lambda controls."
  type = object({
    artifact_path        = string
    artifact_source_hash = string
    batch_size           = number
    batch_window_seconds = number
    log_retention_days   = number
    reserved_concurrency = number
    timeout_seconds      = number
  })

  validation {
    condition = (
      length(var.log_ingestor.artifact_path) > 0 &&
      can(regex("^[A-Za-z0-9+/]{43}=$", var.log_ingestor.artifact_source_hash)) &&
      var.log_ingestor.batch_size >= 1 && var.log_ingestor.batch_size <= 10 &&
      var.log_ingestor.batch_window_seconds >= 0 && var.log_ingestor.batch_window_seconds <= 300 &&
      var.log_ingestor.timeout_seconds >= 1 && var.log_ingestor.timeout_seconds <= 900 &&
      var.log_ingestor.reserved_concurrency >= 2 && var.log_ingestor.reserved_concurrency <= 1000 &&
      contains([365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_ingestor.log_retention_days)
    )
    error_message = "log_ingestor must use a published artifact and bounded Lambda controls."
  }
}

variable "materializer" {
  description = "Explicit trusted Occurrence Materializer artifact and Lambda/SQS controls."
  type = object({
    artifact_path        = string
    artifact_source_hash = string
    batch_size           = number
    batch_window_seconds = number
    log_retention_days   = number
    max_receive_count    = number
    reserved_concurrency = number
    timeout_seconds      = number
  })

  validation {
    condition = (
      length(var.materializer.artifact_path) > 0 &&
      can(regex("^[A-Za-z0-9+/]{43}=$", var.materializer.artifact_source_hash)) &&
      var.materializer.batch_size >= 1 && var.materializer.batch_size <= 10 &&
      var.materializer.batch_window_seconds >= 0 && var.materializer.batch_window_seconds <= 300 &&
      var.materializer.timeout_seconds >= 1 && var.materializer.timeout_seconds <= 900 &&
      var.materializer.reserved_concurrency >= 2 && var.materializer.reserved_concurrency <= 1000 &&
      var.materializer.max_receive_count >= 5 && var.materializer.max_receive_count <= 1000 &&
      contains([365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.materializer.log_retention_days)
    )
    error_message = "materializer must use a published artifact and bounded Lambda/SQS controls."
  }
}

variable "process_manager" {
  description = "Explicit trusted Process Manager artifact and bounded Lambda/event-source controls."
  type = object({
    artifact_path        = string
    artifact_source_hash = string
    batch_size           = number
    batch_window_seconds = number
    log_retention_days   = number
    reserved_concurrency = number
    timeout_seconds      = number
  })

  validation {
    condition = (
      length(var.process_manager.artifact_path) > 0 &&
      can(regex("^[A-Za-z0-9+/]{43}=$", var.process_manager.artifact_source_hash)) &&
      var.process_manager.batch_size >= 1 && var.process_manager.batch_size <= 10 &&
      var.process_manager.batch_window_seconds >= 0 && var.process_manager.batch_window_seconds <= 300 &&
      var.process_manager.timeout_seconds >= 1 && var.process_manager.timeout_seconds <= 900 &&
      var.process_manager.reserved_concurrency >= 2 && var.process_manager.reserved_concurrency <= 1000 &&
      contains([365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.process_manager.log_retention_days)
    )
    error_message = "process_manager must use a published artifact and bounded Lambda/event-source controls."
  }
}

variable "deadline_scanner" {
  description = "Explicit trusted deadline scanner artifact and bounded Lambda/reconciliation controls."
  type = object({
    artifact_path            = string
    artifact_source_hash     = string
    batch_size               = number
    batch_window_seconds     = number
    lookback_seconds         = number
    maximum_lateness_seconds = number
    max_receive_count        = number
    page_size                = number
    reserved_concurrency     = number
    timeout_seconds          = number
    log_retention_days       = number
  })

  validation {
    condition = (
      length(var.deadline_scanner.artifact_path) > 0 &&
      can(regex("^[A-Za-z0-9+/]{43}=$", var.deadline_scanner.artifact_source_hash)) &&
      var.deadline_scanner.batch_size >= 1 && var.deadline_scanner.batch_size <= 10 &&
      var.deadline_scanner.batch_window_seconds >= 0 && var.deadline_scanner.batch_window_seconds <= 300 &&
      var.deadline_scanner.lookback_seconds >= 60 && var.deadline_scanner.lookback_seconds <= 86400 &&
      var.deadline_scanner.maximum_lateness_seconds >= 60 && var.deadline_scanner.maximum_lateness_seconds <= 86400 &&
      var.deadline_scanner.max_receive_count >= 5 && var.deadline_scanner.max_receive_count <= 1000 &&
      var.deadline_scanner.page_size >= 1 && var.deadline_scanner.page_size <= 100 &&
      var.deadline_scanner.reserved_concurrency >= 2 && var.deadline_scanner.reserved_concurrency <= 1000 &&
      var.deadline_scanner.timeout_seconds >= 1 && var.deadline_scanner.timeout_seconds <= 900 &&
      contains([365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.deadline_scanner.log_retention_days)
    )
    error_message = "deadline_scanner must use bounded scanner, queue, checkpoint, and log controls."
  }
}

variable "alert_router" {
  description = "Explicit trusted Alert Router artifact and bounded Stream/reconciliation controls."
  type = object({
    stream_enabled                     = bool
    reconciliation_enabled             = bool
    notifications_enabled              = bool
    artifact_path                      = string
    artifact_source_hash               = string
    batch_size                         = number
    batch_window_seconds               = number
    maximum_record_age_seconds         = number
    maximum_retry_attempts             = number
    reconciliation_page_size           = number
    reconciliation_schedule_expression = string
    reserved_concurrency               = number
    timeout_seconds                    = number
    log_retention_days                 = number
    notification_target_arn            = string
    runbook_uri                        = string
  })

  validation {
    condition = (
      can(var.alert_router.stream_enabled) &&
      can(var.alert_router.reconciliation_enabled) &&
      can(var.alert_router.notifications_enabled) &&
      (var.environment != "prod" || var.alert_router.stream_enabled || var.alert_router.reconciliation_enabled) &&
      (var.environment != "prod" || var.alert_router.notifications_enabled) &&
      length(var.alert_router.artifact_path) > 0 &&
      can(regex("^[A-Za-z0-9+/]{43}=$", var.alert_router.artifact_source_hash)) &&
      var.alert_router.batch_size >= 1 && var.alert_router.batch_size <= 100 &&
      var.alert_router.batch_window_seconds >= 0 && var.alert_router.batch_window_seconds <= 300 &&
      var.alert_router.maximum_record_age_seconds >= 60 && var.alert_router.maximum_record_age_seconds <= 86400 &&
      var.alert_router.maximum_retry_attempts >= 1 && var.alert_router.maximum_retry_attempts <= 10000 &&
      var.alert_router.reconciliation_page_size >= 1 && var.alert_router.reconciliation_page_size <= 100 &&
      can(regex("^rate\\([1-9][0-9]* (minute|minutes)\\)$", var.alert_router.reconciliation_schedule_expression)) &&
      var.alert_router.reserved_concurrency >= 2 && var.alert_router.reserved_concurrency <= 1000 &&
      var.alert_router.timeout_seconds >= 1 && var.alert_router.timeout_seconds <= 900 &&
      contains([365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.alert_router.log_retention_days) &&
      can(regex("^arn:[a-z0-9-]+:sns:[a-z0-9-]+:[0-9]{12}:[A-Za-z0-9_.:/=-]+$", var.alert_router.notification_target_arn)) &&
      can(regex("^https://", var.alert_router.runbook_uri))
    )
    error_message = "alert_router must use a published artifact, bounded Stream/reconciliation controls, an exact SNS target, and an HTTPS runbook."
  }
}
