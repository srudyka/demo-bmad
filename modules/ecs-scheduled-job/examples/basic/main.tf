provider "cell" {
  alias              = "publisher"
  endpoint_url       = "https://example.execute-api.us-east-1.amazonaws.com/v1/publish"
  region             = "us-east-1"
  publisher_role_arn = "arn:aws:iam::123456789012:role/platform-example-config-publisher"
}

provider "cell" {
  alias              = "validator"
  endpoint_url       = "https://example.execute-api.us-east-1.amazonaws.com/v1/validate"
  region             = "us-east-1"
  publisher_role_arn = "arn:aws:iam::123456789012:role/platform-example-config-validator"
}

module "job" {
  source = "../.."

  providers = {
    cell.publisher = cell.publisher
    cell.validator = cell.validator
  }

  environment                   = "dev"
  application                   = "sample"
  job_name                      = "daily"
  owner                         = "platform-example"
  repository_id                 = "123456789"
  terraform_root_id             = "sample-root"
  apply_role_id                 = "sample-plan-role"
  account_id                    = "123456789012"
  config_publisher_role_arn     = "arn:aws:iam::123456789012:role/platform-example-config-publisher"
  config_validator_role_arn     = "arn:aws:iam::123456789012:role/platform-example-config-validator"
  region                        = "us-east-1"
  ecs_cluster_arn               = "arn:aws:ecs:us-east-1:123456789012:cluster/example"
  permissions_boundary_arn      = "arn:aws:iam::123456789012:policy/platform-example-job-boundary"
  cell_process_manager_role_arn = "arn:aws:iam::123456789012:role/platform-example-process-manager-v1"
  ecr_repository_arn            = "arn:aws:ecr:us-east-1:123456789012:repository/sample"
  image                         = "example.invalid/sample@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  source_revision               = "example-revision-0001"
  module_version                = "1.0.0"
  schedule_expression           = "rate(1 day)"
  schedule_time_zone            = "UTC"
  activation_start              = "2099-01-01T00:00:00.000Z"
  maximum_retry_attempts        = 3
  maximum_event_age_seconds     = 3600
  cpu                           = 256
  memory                        = 512
  runtime = {
    max_runtime_seconds = 900
    idempotency         = "idempotent"
  }
  overlap_policy = "reject"
  secret_mode    = "ecs-agent"
  networking = {
    vpc_id              = "vpc-0123456789abcdef0"
    subnet_ids          = ["subnet-0123456789abcdef0"]
    security_group_ids  = ["sg-0123456789abcdef0"]
    security_group_mode = "existing"
    policy_version      = "1.0.0"
    subnet_evidence = {
      "subnet-0123456789abcdef0" = {
        account_id        = "123456789012"
        region            = "us-east-1"
        vpc_id            = "vpc-0123456789abcdef0"
        availability_zone = "us-east-1a"
        classification    = "private"
        evidence_id       = "approved-subnet-catalog-example"
        method            = "approved-subnet-catalog"
        route_table_id    = "rtb-0123456789abcdef0"
      }
    }
    security_group_owner_account_ids = {
      "sg-0123456789abcdef0" = "123456789012"
    }
    dependency_reachability = {
      ecr = {
        path_kind   = "vpc-endpoint"
        identifiers = ["vpce-0123456789abcdef0"]
      }
      s3 = {
        path_kind   = "vpc-endpoint"
        identifiers = ["pl-0123456789abcdef0"]
      }
      cloudwatch-logs = {
        path_kind   = "vpc-endpoint"
        identifiers = ["vpce-0123456789abcdef1"]
      }
    }
  }
  notification = {
    target_arn  = "arn:aws:sns:us-east-1:123456789012:example-notifications"
    runbook_uri = "https://example.invalid/runbooks/sample-daily"
  }
  tags = {
    CostCenter = "example"
  }
  registrar_receipt = {
    pk               = "JOB#dev/sample/daily"
    sk               = "RESERVATION"
    job_id           = "dev/sample/daily"
    namespace_key    = "NAMESPACE#dev#sample"
    lifecycle        = "RESERVED"
    owner_generation = 1
    tombstoned       = false
    transfer_state   = "quiescent"
  }
}

# The application emits structured start, success, and failure completion
# records with job_id, occurrence_id, config_version, attempt_no, timestamp,
# status, and sanitized error_reason. No secret values are present here.
