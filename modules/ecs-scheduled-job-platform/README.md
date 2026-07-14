# ECS Scheduled Job Platform Cell Module

This module is the ownership boundary for shared resources in one AWS
account/Region Platform Cell. It intentionally creates no resources in the
repository bootstrap.

## Required Providers

- Terraform `>= 1.10, < 2.0`
- AWS provider `>= 6.0, < 7.0`

The dated validation seed is Terraform 1.15.8 with AWS provider 6.54.0. The
constraints remain major-bounded so validation can qualify later compatible
patch releases.

## Example

See [`examples/basic`](examples/basic). The example proves module wiring and
validation only; it does not provision AWS resources.

## Ownership And Assumptions

Platform Engineering owns this module and the shared Cell resources added by
later stories. The per-job module consumes a published Cell contract; neither
module reads the other root's Terraform state or mutates the other's resources.

## Inputs And Outputs

There are no inputs or outputs in the bootstrap. They will be added with the
capability that needs them, including descriptions and validation.

## Security And Observability

This skeleton has no IAM, network, secret, logging, metric, or alarm behavior.
Those controls must be introduced and tested with the resources they govern.
