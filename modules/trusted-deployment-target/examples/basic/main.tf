terraform {
  backend "s3" {
    bucket       = "production-platform-state"
    key          = "production/us-east-1/envs/production/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" { region = "us-east-1" }

module "target" {
  source = "../.."

  name                     = "production-platform"
  account_id               = "123456789012"
  environment              = "production"
  region                   = "us-east-1"
  repository_owner_id      = "11111111"
  repository_id            = "42424243"
  plan_workflow_ref        = "org/workflows/.github/workflows/plan.yml"
  apply_workflow_ref       = "org/workflows/.github/workflows/apply.yml"
  oidc_provider_arn        = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
  plan_oidc_subject        = "repository_owner_id:11111111:repository_id:42424243:environment:production:job_workflow_ref:org/workflows/.github/workflows/plan.yml@0123456789abcdef0123456789abcdef01234567"
  apply_oidc_subject       = "repository_owner_id:11111111:repository_id:42424243:environment:production:job_workflow_ref:org/workflows/.github/workflows/apply.yml@0123456789abcdef0123456789abcdef01234567"
  state_bucket_arn         = "arn:aws:s3:::production-platform-state"
  state_bucket_name        = "production-platform-state"
  state_key                = "production/us-east-1/envs/production/terraform.tfstate"
  permissions_boundary_arn = "arn:aws:iam::123456789012:policy/production-platform-permissions-boundary"
  apply_actions            = ["ec2:DescribeVpcs"]
  apply_resource_arns      = ["arn:aws:ec2:us-east-1:123456789012:vpc/vpc-0123456789abcdef0"]
  apply_resource_prefixes  = ["arn:aws:ec2:us-east-1:123456789012:vpc/"]
  tags = {
    Environment = "production"
    Application = "platform"
    Service     = "deployment"
    Owner       = "platform-security"
    ManagedBy   = "Terraform"
  }
}
