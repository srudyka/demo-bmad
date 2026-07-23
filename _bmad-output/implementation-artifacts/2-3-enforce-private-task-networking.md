---
baseline_commit: 69c1f71
---

# Story 2.3: Enforce Private Task Networking

Status: done

## Story

As a Cloud Infrastructure Owner,
I want job networking validated against an explicit private-network policy,
so that scheduled tasks cannot gain public exposure or unintended egress.

## Acceptance Criteria

1. Given the organization requires explicit network classifications, when the
   module validates networking, then a checked-in, versioned network policy
   catalog defines private-subnet evidence, security-group rules, dependency
   reachability evidence, exception ownership, severity, and enforcement stage;
   an absent, malformed, unsupported, or unknown policy version fails closed
   with an actionable finding.

2. Given a consumer supplies a VPC and subnet IDs, when a trusted plan evaluates
   them, then every subnet is verified against the declared account, Region,
   VPC, availability-zone support, and catalog private-subnet classification.
   Empty inputs, public or unknown classification, stale IDs, duplicate IDs,
   mismatched VPC/account/Region, and unsupported availability configuration
   must fail with stable finding codes. Validation must not infer private status
   from a variable name or an unnamed convention.

3. Given ECS networking is rendered for any Environment, when the task network
   configuration is produced, then it is `awsvpc` with explicit subnet and
   security-group IDs and `assignPublicIp = DISABLED`. The consumer interface
   must not expose a switch that can enable a public IP, add a public interface,
   or silently fall back to a default subnet or security group.

4. Given consumers supply existing security groups, when trusted policy
   analysis inspects them, then each group is proven to belong to the declared
   VPC and its ingress and egress are evaluated for IPv4/IPv6 CIDRs, referenced
   security groups, prefix lists, ports, protocols, default-rule drift, stale
   references, and cross-VPC/account exposure. Public ingress, unrestricted
   egress, cross-VPC references, stale rules, and policy mismatches receive the
   catalog-defined non-production severity and remain production-blocking.

5. Given module-created security-group mode is selected, when Terraform plans
   the group and its rules, then it has no ingress and only explicitly declared
   security-group, prefix-list, or bounded CIDR egress with declared protocol
   and port ranges. Implicit default egress, `0.0.0.0/0`, `::/0`, all-protocol
   rules, and unreviewed rule expansion are rejected unless a later governed
   production exception authorizes the exact scope. The module owns only this
   per-job group and must not alter supplied/shared groups.

6. Given the task needs ECR, S3, CloudWatch Logs, Secrets Manager, SSM, KMS,
   or application dependencies, when reachability inputs are validated, then
   each dependency maps to an approved NAT path, VPC endpoint, PrivateLink,
   proxy, stable egress, or internal network path with non-sensitive evidence
   identifiers. Missing or contradictory evidence is reported; the module does
   not create routes, NAT gateways, endpoints, subnets, route tables, or other
   consumer network infrastructure.

7. Given ECS-agent or application-pull secrets are configured, when network
   policy is evaluated, then the exact endpoint or controlled egress path is
   consistent with Story 2.2’s selected secret mode, role, resource, account,
   Region, and KMS conditions. Secret retrieval requires no public ingress, and
   no secret value or decrypted material appears in Terraform input, plan,
   output, CONFIG metadata, fixture, or documentation.

8. Given networking validation succeeds, when module outputs are inspected,
   then outputs expose only non-sensitive VPC ID, subnet IDs, security-group
   IDs, public-IP policy, network-policy version, and dependency-reachability
   identifiers required by Story 2.4/2.5 CONFIG handoff. Route tables, gateways,
   endpoints, shared groups, subnets, and unrelated networking remain outside
   this module’s ownership boundary.

9. Given networking changes are tested, when policy fixtures and module tests
   run, then they cover private/public classification, mismatched VPC/account/
   Region, stale IDs, existing and created groups, IPv4/IPv6 exposure, default
   egress, cross-VPC references, missing endpoint evidence, valid bounded access,
   policy-version mismatch, and governed exception metadata. Changed Terraform
   roots and the module-local basic example pass backend-free validation; live
   AWS assertions run only with an explicitly trusted context.

10. Given a networking change must be rolled back, when the prior known-good
    network declaration and evidence are restored, then task generation remains
    disabled until the restored evidence is revalidated. Rollback must never
    delete or mutate shared consumer subnets, routes, gateways, endpoints, or
    security groups.

## Tasks / Subtasks

- [x] 1. Establish the versioned network-policy contract (AC: 1, 4, 5, 6, 9)
  - [x] Add a checked-in network policy catalog under `contracts/v1/catalogs`
    with a schema/checksum/manifest update using the repository contract
    conventions.
  - [x] Define stable policy version, private-subnet evidence requirements,
    allowed security-group rule forms, dependency path kinds, finding codes,
    non-production severities, enforcement stages, and exception fields.
  - [x] Reject missing, malformed, unsupported, or unknown catalog versions;
    do not encode the policy only in Terraform descriptions or test names.

- [x] 2. Expand the job networking interface without breaking Story 2.1/2.2
  addresses (AC: 2, 3, 7, 8, 10)
  - [x] Add explicit declared VPC identity, subnet evidence, security-group
    mode, policy version, dependency reachability, and secret-network-path
    bindings with descriptions, types, and meaningful validations.
  - [x] Preserve existing `networking.subnet_ids` and
    `networking.security_group_ids` semantics or provide reviewed migration
    guidance; do not introduce a permissive `assign_public_ip` input.
  - [x] Validate account, Region, VPC, subnet, group, policy, and secret-mode
    identity alignment before task-generation consumers can use the outputs.

- [x] 3. Implement trusted subnet and VPC evidence validation (AC: 2, 9)
  - [x] Use explicit AWS data sources or an equivalent trusted-plan evidence
    boundary to validate subnet ownership, Region, VPC association, AZ support,
    and the catalog’s private classification method.
  - [x] Keep cloud-dependent evidence distinct from credential-free contract
    tests; fail closed when evidence is unavailable rather than treating an
    unknown subnet as private.
  - [x] Emit deterministic findings for empty/public/unknown/stale/mismatched
    and unsupported subnet inputs, without leaking account-specific secrets.

- [x] 4. Validate supplied security groups and create only bounded job groups
  (AC: 4, 5, 9, 10)
  - [x] Inspect supplied-group VPC association and ingress/egress rule shape,
    including IPv4/IPv6 CIDRs, ports, protocols, referenced groups, prefix
    lists, stale references, default-rule drift, and cross-VPC/account scope.
  - [x] In created-group mode, use stable job ownership/tags, no ingress,
    revoke implicit default egress, and create explicit egress rule resources
    only from a bounded typed declaration.
  - [x] Reject wildcard destinations, all protocols, implicit expansion,
    unreviewed exceptions, and mutations to shared or supplied groups.

- [x] 5. Validate dependency reachability and secret-path consistency (AC: 6, 7)
  - [x] Require secret-free evidence for ECR, S3, CloudWatch Logs, Secrets
    Manager, SSM, KMS, and declared application dependencies.
  - [x] Validate each dependency against an approved NAT, endpoint,
    PrivateLink, proxy, stable-egress, or internal-path identifier; report
    missing evidence without creating network infrastructure.
  - [x] Cross-check ECS-agent versus application-pull mode against Story 2.2
    role/resource/KMS outputs and reject a path that grants public ingress or
    contradicts the selected mode.

- [x] 6. Publish network handoff outputs and documentation (AC: 3, 8, 10)
  - [x] Expose stable, non-sensitive network outputs needed by the future task
    definition and CONFIG stories, including the hard-coded public-IP policy
    and exact catalog version.
  - [x] Update the module README and basic example with ownership boundaries,
    input/output contract, private-path assumptions, dependency evidence,
    security-group modes, validation commands, and rollback behavior.
  - [x] State clearly that this story does not create routes, NAT, endpoints,
    subnets, shared groups, task definitions, logs, schedules, or CONFIG.

- [x] 7. Add positive, negative, and migration coverage (AC: 2, 4, 5, 6, 9)
  - [x] Add checked-in fixtures for every named network finding and catalog
    exception path, with no real IDs, credentials, endpoint secrets, or state.
  - [x] Add contract/module tests for existing and created groups, IPv4/IPv6,
    default egress, public/private subnet evidence, dependency gaps, and
    secret-mode role/path isolation.
  - [x] Add static assertions proving no route/NAT/endpoint/subnet/shared-group
    resource is created and that public-IP configuration cannot be enabled.

- [x] 8. Run the complete validation and migration gates (AC: 1, 8, 9, 10)
  - [x] Run Terraform format, backend-free init/validate for the module and
    basic example, contract/runtime tests, Ruff, strict mypy, Checkov, hygiene,
    and `git diff --check`.
  - [x] Run the repository validator with the pinned `uv` version and retain
    credential-free evidence separately from any live AWS qualification.
  - [x] Confirm checksums, compatibility metadata, stable Terraform addresses,
    and rollback documentation are complete before moving the story to review.

### Review Findings

- [x] [Review][Patch] Trusted subnet evidence can be fabricated and does not validate AZ support or duplicates [modules/ecs-scheduled-job/main.tf:223-232; modules/ecs-scheduled-job/variables.tf:309-321] — consumer-supplied classification, Region, and availability zone are accepted without comparison to the AWS subnet’s actual availability zone or a supported-AZ catalog; `set(string)` silently removes duplicate subnet IDs; public/unknown/stale/unsupported cases do not produce their stable catalog finding codes. Validate private classification from trusted route/subnet evidence, compare actual AZ and Region, preserve duplicate detection, and map each failure to its catalog code.
- [x] [Review][Patch] Existing security-group analysis omits required ownership and rule-scope checks [modules/ecs-scheduled-job/main.tf:246-268] — only VPC membership, empty ingress, protocol, and unrestricted CIDRs are checked. Account ownership, ports, referenced security groups, prefix lists, stale references, cross-VPC/account scope, and default-rule drift are not evaluated, allowing a non-compliant shared group to pass. Inspect every rule field and resolve referenced destinations against the declared VPC/account.
- [x] [Review][Patch] Created security-group destinations are not trusted or exception-governed [modules/ecs-scheduled-job/main.tf:234-244; modules/ecs-scheduled-job/network.tf:13-24] — arbitrary SG/prefix-list IDs and malformed CIDRs can be applied after only a one-destination check; the catalog lists exception fields but the module has no exception input or validation. Validate destination existence, VPC/account scope, identifier shape, CIDR/protocol/port bounds, and exact governed exception metadata.
- [x] [Review][Patch] Secret network-path consistency is incomplete and bypassable [modules/ecs-scheduled-job/main.tf:46-50,287-293; modules/ecs-scheduled-job/variables.tf:211-225] — only application-pull mode and the first secret reference are checked; path kind/identifiers are not compared with dependency evidence, mixed providers are ignored, and ECS-agent mode has no equivalent consistency check. Normalize every provider and require exact mode/provider/path bindings.
- [x] [Review][Patch] Dependency reachability evidence accepts arbitrary keys and unverifiable identifiers [modules/ecs-scheduled-job/main.tf:45-54,271-284] — required-key presence, an allowed path kind, non-empty identifiers, and absence of the substring `secret` are insufficient to prove ECR/S3/Logs/secret/application reachability. Constrain dependency keys and identifier shapes, bind evidence to each dependency, and reject evidence unrelated to the declared network/security-group path.
- [x] [Review][Patch] Malformed network catalogs do not fail closed with a stable policy finding [modules/ecs-scheduled-job/main.tf:44-54,215-221; contracts/v1/catalogs/network.json:1-88] — `jsondecode` and direct field access assume catalog shape, while severity, finding ownership, and non-production/production enforcement metadata are not defined or consumed. Validate catalog integrity/shape and define machine-readable finding severity, owner, enforcement stage, and exception policy before use.
- [x] [Review][Patch] Network tests assert source text instead of exercising the validation behavior [tests/contract/test_scheduled_job_networking.py:10-105] — no fixture suite or negative/positive execution covers public/private classification, stale IDs, IPv4/IPv6, cross-VPC rules, missing endpoints, policy mismatch, or governed exceptions. Add fixture-backed contract cases and trusted-plan tests for the AC9 matrix.
- [x] [Review][Patch] Rollback can destroy a created security group still referenced by a task revision [modules/ecs-scheduled-job/network.tf:1-11; modules/ecs-scheduled-job/outputs.tf:67-72] — switching from created to existing mode removes the job-owned group without lifecycle protection or a two-phase migration guard. Preserve the group until task/config references are disabled and restored network evidence is revalidated.
- [x] [Review][Patch] Checkov’s attachment exception is module-wide [scripts/validate.py:187-200] — skipping `CKV2_AWS_5` for the entire job module can hide future unattached security groups. Scope the exception to the Story 2.3 resource through an auditable structural test or remove it once Story 2.4 attaches the group.

## Dev Notes

### Current state and implementation boundary

- Story 2.1 established the declaration and reservation interface. Story 2.2
  now owns the three job IAM roles and exposes secret-mode/network-path metadata.
- The current `networking` object contains subnet and security-group IDs but is
  still a declaration-only placeholder. Story 2.3 owns network validation and
  the optional per-job security group; it must not quietly turn the placeholder
  into task-definition or schedule ownership.
- Story 2.4 consumes exact role and network outputs to create the Fargate task
  and logs. Story 2.5 consumes the same evidence for disabled schedule and CONFIG
  publication. Do not create those resources here.
- The Cell root and consumer account own shared subnets, route tables, NAT
  gateways, endpoints, and shared security groups. This module may create only
  a clearly job-owned security group in explicit created-group mode.

### Network contract

- The canonical task posture is Fargate `awsvpc`, explicit private subnet IDs,
  explicit security-group IDs, and `assignPublicIp = DISABLED`. There is no
  public-interface escape hatch and no default-resource fallback.
- Treat `unknown` cloud evidence as a blocking finding. A name containing
  `private`, a subnet tag alone, or a locally supplied boolean is not sufficient
  unless the versioned catalog explicitly defines it as qualifying evidence.
- Existing groups are inspected, not repaired. A non-compliant supplied group
  blocks deployment and identifies the exact rule/finding; the module must not
  revoke or rewrite consumer-owned rules.
- Created-group mode must use a default-deny posture: no ingress, no implicit
  default egress, and only explicit bounded egress rules. Security-group and
  prefix-list references must be proven to be in the declared network scope;
  CIDR destinations require explicit protocol and port bounds.
- Network reachability is evidence metadata, not a claim that Terraform has
  tested packet flow. The declaration must identify the exact approved path and
  the dependency it serves, while live route/endpoint qualification remains a
  trusted-environment concern.

### Suggested typed interface

The implementation may evolve the exact HCL shape, but it must preserve stable
existing inputs and express the following concepts explicitly:

- declared VPC ID and target account/Region binding;
- subnet IDs plus catalog-qualified private-subnet evidence;
- `security_group_mode = "existing" | "create"`;
- existing group IDs or created-group bounded egress rules;
- exact network policy catalog version;
- dependency-to-path evidence for platform and application dependencies;
- non-sensitive identifiers for endpoint/proxy/NAT/internal-path evidence.

Do not add an input that allows `assign_public_ip = ENABLED`, arbitrary network
interfaces, unrestricted egress, route mutation, or secret values.

### Terraform and AWS guidance

- Use the AWS provider’s subnet, VPC, and security-group data sources only as
  trusted evidence inputs; provider read failures must produce a blocking,
  actionable result rather than an optimistic plan.
- If a created group uses separate ingress/egress rule resources, make the
  default egress removal explicit and preserve stable `for_each` keys for rule
  migration. Avoid inline rules that can reintroduce implicit defaults through
  provider behavior.
- Keep all resource names and tags consistent with Stories 2.1/2.2. Never
  hardcode account IDs, Regions, subnet IDs, ARNs, or environment defaults.
- Preserve resource addresses and output types. Intentional interface changes
  require `moved` blocks or explicit migration notes and a rollback path.

### Cross-story authority and handoffs

- Authoritative network declaration: the job module’s typed inputs and
  validated output evidence. Authoritative classification: the versioned
  network policy catalog plus trusted subnet/security-group evidence.
- Writer: the consumer Terraform root declares inputs; this module validates
  them and owns only an optional job security group. It does not write Cell
  state or mutate shared networking.
- IAM: Story 2.2 owns task/execution role permissions. This story proves the
  network path is compatible with the selected secret mode and role resources;
  it must not add IAM permissions or duplicate role creation.
- Observability: network validation findings and failed task/network signals
  are handoffs to later operational/readiness stories. Do not create alarms or
  dashboards in this story.
- Rollback: restore the prior network declaration/catalog/evidence, keep task
  generation disabled, revalidate, then allow later stories to consume it.
  Never delete shared networking or a security group referenced by a prior
  task/configuration revision.

### Project standards

- Follow `_bmad-output/project-context.md` and
  `_bmad/custom/standards/aws-terraform-implementation.md`.
- Use Terraform `>= 1.10, < 2.0` and AWS provider `>= 6.0, < 7.0` with committed
  lock conventions. Every new variable/output needs a description and useful
  validation.
- Keep credential-free validation separate from live AWS qualification. Do not
  claim that local fixtures prove deployed route, NAT, endpoint, or packet-flow
  behavior.
- Document security, ownership, operational impact, cost considerations, and
  rollback in the README and story evidence.

### AWS references

- [Amazon ECS task networking options for Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)
- [Network security best practices for Amazon ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-network.html)
- [Fargate task definition requirements](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html)
- [Amazon VPC security group rules](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html)
- [Amazon VPC endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)

## Testing Requirements

Minimum evidence before code review:

1. Contract tests for catalog versioning, schema/checksum registration, finding
   severity, unknown-policy fail-closed behavior, and governed exceptions.
2. Trusted-evidence tests for private/public/unknown subnet classification,
   VPC/account/Region mismatch, stale IDs, AZ support, and empty inputs.
3. Security-group tests for existing and created modes, no ingress, explicit
   bounded egress, IPv4/IPv6 exposure, default egress, cross-VPC references,
   stale rules, prefix lists, ports, protocols, and shared-resource ownership.
4. Dependency tests for valid and missing ECR/S3/Logs/Secrets/SSM/KMS/app paths,
   NAT/endpoint/PrivateLink/proxy/stable-egress evidence, and secret-mode
   consistency with Story 2.2.
5. Static tests proving `awsvpc`, explicit network IDs, disabled public IP, no
   public-interface input, no network-infrastructure creation, no secret values,
   and no future Story 2.4/2.5 resources.
6. Backend-free Terraform init/validate for the changed module and basic
   example, plus format, strict type checks, repository tests, Checkov, hygiene,
   and `git diff --check`.

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2 and Story 2.3 acceptance
  criteria; Story 2.4–2.6 handoff requirements.
- `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md` — AD-13 private workload networking, ownership boundaries, and minimum network contract.
- `_bmad-output/implementation-artifacts/2-1-declare-and-reserve-a-scheduled-job.md` — declaration, identity, and reservation contract.
- `_bmad-output/implementation-artifacts/2-2-create-least-privilege-job-iam-roles.md` — role separation, secret modes, network-path handoff, and review hardening.
- `modules/ecs-scheduled-job/` — current interface, ownership boundary, and basic example to extend without address drift.
- `fixtures/canary/` — existing private-network declaration and contract-fixture patterns; do not copy its future-runtime resources into the job module.
- `contracts/v1/schemas/config.schema.json` — downstream network shape consumed by CONFIG.
- `_bmad/custom/standards/aws-terraform-implementation.md` — required AWS Terraform implementation standard.

## Dev Agent Record

### Implementation Plan

- Added the versioned network policy catalog and registered its integrity data.
- Expanded the job module with explicit private-network inputs, trusted AWS
  evidence lookups, fail-closed preconditions, optional bounded job security
  group creation, dependency reachability validation, and handoff outputs.
- Added contract/static tests, updated the synthetic example and README, and
  centralized the Story 2.3-to-2.4 Checkov sequencing exception in validation.

### Completion Notes

- Implemented private VPC/subnet identity and catalog-qualified evidence checks.
- Enforced explicit `awsvpc` handoff semantics with `assign_public_ip = DISABLED`.
- Existing security groups are inspected without mutation; created groups have
  no ingress, no implicit default egress, and only bounded explicit rules.
- Required ECR, S3, CloudWatch Logs, and selected secret-provider reachability
  evidence is required without creating consumer networking infrastructure.
- Credential-free validation remains separate from live AWS qualification.
- Review hardening added provider-backed security-group rule inspection,
  destination scope checks, all-provider secret-path matching, catalog shape
  validation, fixture-backed network cases, a protected created-group
  rollback path, and a scoped Checkov exception guard.

### Validation Evidence

- Full repository tests: `198 passed, 217 subtests passed`.
- Terraform module and basic example: valid; platform and canary roots: valid.
- Ruff format/lint: passed for scoped repository paths.
- mypy: `Success: no issues found in 61 source files`.
- Checkov job module: 82 passed, 0 failed, 0 skipped after the centralized
  sequencing exception; repository hygiene passed.
- `git diff --check`: passed.
- The repository validator reached provider initialization but could not
  download AWS provider 6.54.0 because `releases.hashicorp.com` reset the
  connection; direct module/example validation and all credential-free checks
  passed.

## File List

- `_bmad-output/implementation-artifacts/2-3-enforce-private-task-networking.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `contracts/v1/catalogs/network.json`
- `modules/ecs-scheduled-job/README.md`
- `modules/ecs-scheduled-job/examples/basic/main.tf`
- `modules/ecs-scheduled-job/main.tf`
- `modules/ecs-scheduled-job/network.tf`
- `modules/ecs-scheduled-job/outputs.tf`
- `modules/ecs-scheduled-job/variables.tf`
- `scripts/validate.py`
- `tests/contract/test_repository_structure.py`
- `tests/contract/test_scheduled_job_declaration.py`
- `tests/contract/test_scheduled_job_iam.py`
- `tests/contract/test_scheduled_job_networking.py`

## Change Log

- 2026-07-23: Implemented Story 2.3 private networking contract, validation,
  optional bounded security group, reachability evidence, tests, and docs.
- 2026-07-23: Marked implementation complete and ready for code review.
- 2026-07-23: Applied all code-review patches and marked Story 2.3 done.
