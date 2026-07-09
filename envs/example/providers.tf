provider "aws" {
  alias  = "target"
  region = var.aws_region

  assume_role {
    role_arn = var.assume_role_arn
  }

  default_tags {
    tags = local.common_tags
  }
}
