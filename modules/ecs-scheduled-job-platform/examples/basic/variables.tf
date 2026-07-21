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

variable "canary_normalizer_registration" {
  description = "Fictitious explicit Scheduler binding for local configuration validation only."
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
  default = {
    account_id                 = "000000000000"
    config_version             = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    environment                = "dev"
    job_id                     = "dev/platform/canary"
    owner_generation           = 1
    region                     = "us-east-1"
    schedule_arn               = "arn:aws:scheduler:us-east-1:000000000000:schedule/dev-platform-scheduler/dev-platform-canary"
    schedule_generation        = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    schedule_group_arn         = "arn:aws:scheduler:us-east-1:000000000000:schedule-group/dev-platform-scheduler"
    scheduler_delivery_role_id = "AROASCHEDULEREXAMPLE"
    source_queue_arn           = "arn:aws:sqs:us-east-1:000000000000:dev-platform-scheduler-ingress"
    canary_launch_role_arn     = "arn:aws:iam::000000000000:role/dev-platform-canary-launch"
  }
}

variable "ecs_cluster_arn" {
  description = "Fictitious Cell ECS cluster ARN for local module validation."
  type        = string
  default     = "arn:aws:ecs:us-east-1:000000000000:cluster/dev-platform"
}

variable "process_manager" {
  description = "Fictitious Process Manager artifact controls for validation only."
  type = object({
    artifact_path        = string
    artifact_source_hash = string
    batch_size           = number
    batch_window_seconds = number
    log_retention_days   = number
    reserved_concurrency = number
    timeout_seconds      = number
  })
  default = {
    artifact_path        = "process-manager.zip"
    artifact_source_hash = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    batch_size           = 10
    batch_window_seconds = 5
    log_retention_days   = 365
    reserved_concurrency = 2
    timeout_seconds      = 30
  }
}

variable "normalizer" {
  description = "Fictitious external artifact and bounded normalizer controls for local configuration validation only."
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
  default = {
    artifact_path        = "/tmp/evidence-normalizer.zip"
    artifact_source_hash = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    batch_size           = 1
    batch_window_seconds = 0
    log_retention_days   = 365
    max_receive_count    = 5
    reserved_concurrency = 2
    timeout_seconds      = 30
  }
}

variable "materializer" {
  description = "Fictitious materializer artifact and controls for local configuration validation only."
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
  default = {
    artifact_path        = "artifacts/occurrence-materializer.zip"
    artifact_source_hash = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    batch_size           = 1
    batch_window_seconds = 0
    log_retention_days   = 365
    max_receive_count    = 5
    reserved_concurrency = 2
    timeout_seconds      = 60
  }
}

variable "log_ingestor" {
  description = "Fictitious completion log-ingestor artifact and controls for local validation."
  type = object({
    artifact_path        = string
    artifact_source_hash = string
    batch_size           = number
    batch_window_seconds = number
    log_retention_days   = number
    reserved_concurrency = number
    timeout_seconds      = number
  })
  default = {
    artifact_path        = "/tmp/log-ingestor.zip"
    artifact_source_hash = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    batch_size           = 1
    batch_window_seconds = 0
    log_retention_days   = 365
    reserved_concurrency = 2
    timeout_seconds      = 30
  }
}

variable "deadline_scanner" {
  description = "Fictitious deadline scanner artifact and controls for local validation."
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
  default = {
    artifact_path            = "/tmp/deadline-scanner.zip"
    artifact_source_hash     = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    batch_size               = 1
    batch_window_seconds     = 0
    lookback_seconds         = 900
    maximum_lateness_seconds = 900
    max_receive_count        = 5
    page_size                = 25
    reserved_concurrency     = 2
    timeout_seconds          = 30
    log_retention_days       = 365
  }
}

variable "alert_router" {
  description = "Fictitious Alert Router artifact and bounded controls for local validation only."
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
  default = {
    stream_enabled                     = true
    reconciliation_enabled             = true
    notifications_enabled              = true
    artifact_path                      = "artifacts/alert-router.zip"
    artifact_source_hash               = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    batch_size                         = 10
    batch_window_seconds               = 5
    maximum_record_age_seconds         = 3600
    maximum_retry_attempts             = 5
    reconciliation_page_size           = 25
    reconciliation_schedule_expression = "rate(1 minute)"
    reserved_concurrency               = 2
    timeout_seconds                    = 30
    log_retention_days                 = 365
    notification_target_arn            = "arn:aws:sns:us-east-1:000000000000:dev-platform-canary"
    runbook_uri                        = "https://runbooks.example.test/platform/canary"
  }
}
