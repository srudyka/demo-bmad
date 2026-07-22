module "job" {
  source = "../.."

  environment         = "dev"
  application         = "sample"
  job_name            = "daily"
  owner               = "platform-example"
  repository_id       = "123456789"
  terraform_root_id   = "sample-root"
  apply_role_id       = "sample-plan-role"
  account_id          = "123456789012"
  region              = "us-east-1"
  ecs_cluster_arn     = "arn:aws:ecs:us-east-1:123456789012:cluster/example"
  image               = "example.invalid/sample@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  schedule_expression = "rate(1 day)"
  cpu                 = 256
  memory              = 512
  runtime = {
    max_runtime_seconds = 900
    idempotency         = "idempotent"
  }
  overlap_policy = "reject"
  networking = {
    subnet_ids         = ["subnet-0123456789abcdef0"]
    security_group_ids = ["sg-0123456789abcdef0"]
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
