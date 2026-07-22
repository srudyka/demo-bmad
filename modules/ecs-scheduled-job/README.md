# ECS Scheduled Job Module

This module is the ownership boundary for one application's scheduled-job
declaration. Story 2.1 validates the declaration and Cell Contract and accepts
only a matching, secret-free receipt from the authoritative Registrar; it
creates no resources for workload execution.

## Required Providers

- Terraform `>= 1.10, < 2.0`
- AWS provider `>= 6.0, < 7.0`

The dated validation seed is Terraform 1.15.8 with AWS provider 6.54.0. The
constraints remain major-bounded so validation can qualify later compatible
patch releases.

## Example

See [`examples/basic`](examples/basic). The example proves declaration wiring
and validation only; it does not provision workload resources.

## Ownership And Assumptions

Application teams consume this module for per-job resources added by later
stories. Shared account/Region resources remain in the Platform Cell module.
This module consumes a published Cell contract and never reads or changes the
Cell root's Terraform state.

## Inputs And Outputs

Inputs cover identity, immutable repository ownership, Cell discovery, ECS
dependencies, schedule, runtime, networking, notifications, configuration,
secret references, permissions, and protected tags. Outputs expose the
canonical job ID, validated Cell metadata, Registrar-confirmed reservation,
protected tags, and normalized schedule identity.

## Security And Observability

No workload IAM, network, secret injection, logging, metric, or alarm resources
are created here. Later stories introduce those controls with the resources
they govern. The Cell Contract is read from SSM and must match account,
Region, Environment, schema, checksum, and integration ownership.

## Reservation and rollback

The reservation identity is `JOB#<environment>/<application>/<job>` and binds
immutable repository/root/apply identity, account, Region, Environment,
namespace, owner, and generation. An authoritative conditional Registrar must
perform the claim before its receipt is passed as `registrar_receipt`; a
missing, mismatched, or stale receipt fails planning. The runtime Registrar
first verifies the Cell namespace authorization and then uses a conditional
write; a read-then-write or unconditional overwrite is unsafe under concurrent
claims. `RESERVED` does not grant launch authority, and tombstoned IDs must not
be reused automatically. Rollback is to stop passing the receipt and remove
the declaration after confirming no later-story resources reference the job.

## Validation

Run the repository validation command, backend-free Terraform validation for
this module and `examples/basic`, contract/runtime tests, Checkov, hygiene, and
`git diff --check`. Do not use real account IDs, credentials, or secrets in
examples.
