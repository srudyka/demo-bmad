terraform {
  required_version = ">= 1.10, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
    cell = {
      source                = "demo-bmad/cell"
      version               = "0.1.0"
      configuration_aliases = [cell.publisher, cell.validator]
    }
  }
}
