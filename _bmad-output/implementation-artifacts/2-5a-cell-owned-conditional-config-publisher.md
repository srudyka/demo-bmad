---
baseline_commit: 51842d8
---

# Story 2.5a: Add the Cell-Owned Conditional CONFIG Publisher

Status: done

## Story

As a Platform Engineer,
I want a Cell-owned publisher API/provider that performs atomic CONFIG creation,
so that job Terraform can publish immutable CONFIG without weakening the Cell
bucket's `If-None-Match: *` protection.

## Context and Dependency

Story 2.5 creates the disabled Scheduler resources and renders the canonical
CONFIG document, but its AWS provider `aws_s3_object` publication cannot send
the required `If-None-Match: *` header. Story 2.5 is therefore still in review.
This story supplies the missing Cell-owned publication boundary. After this
story, Story 2.5 must replace direct S3 publication with this integration and
pass a fresh code review before Story 2.6 consumes the publication.

## Acceptance Criteria

1. The Cell Contract publishes a versioned `config_publisher` integration with
   owner, schema range, protocol version, and an authenticated invocation
   identifier. It is additive and backward-compatible within Contract major 1;
   malformed, cross-account, or non-Cell publisher identities fail consumer
   validation.

2. The Cell provides a private IAM-authenticated publisher interface. It may
   adopt an existing Cell API/provider if one exists; otherwise it must add the
   repository's approved Cell-owned implementation. The interface must accept
   only the canonical CONFIG document, job ID, config version, exact object key,
   and required contract metadata. It must not accept caller-generated
   occurrence IDs or secret values.

3. The publisher authorizes the authenticated caller against the authoritative
   Registrar/namespace ownership record before writing. The caller's identity,
   account, Region, ownership generation, and `PlatformEcsScheduledJobId` must
   bind to the requested job prefix. Payload job IDs and keys are assertions,
   not authorization. Cross-job, stale-generation, cross-account, and
   cross-Region requests are rejected with stable machine-readable errors.

4. The publisher performs one encrypted S3 `PutObject` using
   `IfNoneMatch = "*"` and the registered key
   `jobs/<job_id>/config/<config_version>.json`. It uses the Cell KMS key and
   the required S3/KMS encryption-context conditions. An existing object is
   never overwritten. A retry with identical canonical bytes returns a stable
   idempotent `ALREADY_PUBLISHED` result; a same-key/different-bytes attempt
   returns `CONFIG_VERSION_CONFLICT`.

5. Publisher responses are versioned and secret-free. They include lifecycle
   `PUBLISHED` or a stable rejection code, config version, exact key, job ID,
   ownership generation, publisher protocol version, and an operation/audit
   identifier. They never echo CONFIG secrets or arbitrary request fields.

6. Story 2.5 can invoke the publisher through a supported Terraform/provider
   integration without provisioners, `null_resource`, shell upload commands,
   direct shared-state reads, or a broad Cell write role. The job module no
   longer requires `aws_s3_object` to perform the final CONFIG write, and the
   direct job publisher path cannot bypass the Cell authorization boundary.

7. The publisher has least-privilege IAM: exact CONFIG-prefix writes only,
   required KMS data-key/encrypt/decrypt permissions scoped by bucket and
   encryption context, read access only where needed to verify an idempotent
   retry, and no access to namespace/registry mutation, runtime ledger,
   queues, schedules, ECS, secrets, or other job prefixes.

8. The publisher has bounded operational telemetry: structured logs with job
   ID/config version/result code and no CONFIG secrets; bounded metrics for
   publish success, idempotent retry, conflict, authorization rejection,
   validation rejection, throttling, and internal failure; alarms and a
   runbook for sustained failures, latency, throttling, and conditional-write
   conflicts. Metric dimensions exclude config hashes, keys, occurrence IDs,
   raw request bodies, and unbounded identities.

9. Deployment is backward-compatible and reversible. The Cell publisher is
   deployed and qualified before Story 2.5 switches publication; the schedule
   remains disabled throughout. Rollback leaves existing CONFIG objects and
   prior publisher versions available, disables the new path without deleting
   shared Cell resources, and never falls back silently to an unconditional
   S3 writer.

10. Tests prove the end-to-end contract without AWS credentials: canonical
    request/response vectors, IAM-negative authorization cases, exact
    `If-None-Match` behavior, identical retry, conflicting retry, schema and
    secret safety, cross-prefix/account/Region rejection, bounded telemetry,
    stable resource/provider addresses, and rollback behavior. Terraform
    formatting/validation, provider lockfile validation, Ruff, strict mypy,
    repository tests, Checkov, manifest integrity, and `git diff --check` pass.

## Tasks / Subtasks

- [x] 1. Define the publisher contract and Cell Contract integration (AC: 1, 2, 5)
  - [x] Add normative publisher request/response schemas and stable result codes under `contracts/v1/`.
  - [x] Add the `config_publisher` integration shape to the Cell Contract schema, fixtures, and manifest inventory.
  - [x] Define protocol version, authentication mode, owner, supported config/schema ranges, and exact operation semantics.

- [x] 2. Implement or adopt the Cell-owned conditional publisher (AC: 2–5, 7–9)
  - [x] Reuse Cell Lambda, IAM, logging, metric, alarm, packaging, and naming patterns.
  - [x] Authenticate with IAM and bind the request to the caller role's `PlatformEcsScheduledJobId` tag.
  - [x] Validate canonical CONFIG bytes, version, key, schema, contract, ownership generation field, and secret safety before S3 access.
  - [x] Call S3 `PutObject` with `IfNoneMatch = "*"` and distinguish creation, identical retry, conflict, authorization, and transient failure.
  - [x] Scope S3/KMS permissions to the Cell CONFIG inbox and preserve the existing bucket boundary.

- [x] 3. Add the supported Terraform/provider integration (AC: 6, 9)
  - [x] Implement the maintained `demo-bmad/cell` provider/resource with SigV4-authenticated conditional invocation.
  - [x] Preserve the scheduler address and CONFIG resource address while replacing the direct S3 resource.
  - [x] Make identical retries idempotent and conflicts fail closed.
  - [x] Remove the final direct `aws_s3_object` publication path from Story 2.5.

- [x] 4. Wire discovery, authorization, and operational handoff (AC: 1, 3, 7–9)
  - [x] Publish the integration in the platform module and expose the exact contract/output fields.
  - [x] Require same-account Cell identity, endpoint, auth mode, and protocol compatibility in the job module.
  - [x] Document ownership, deployment order, alarms, failure codes, and safe rollback.

- [x] 5. Add adversarial and end-to-end contract tests (AC: 3–5, 7, 10)
  - [x] Test forged identity/prefix, cross-job key, direct bypass, secret-bearing body, malformed canonical bytes, and unsupported protocol.
  - [x] Test conditional creation, identical retry, conflicting same-key bytes, and stable error classification.
  - [x] Assert the provider invokes only the Cell publisher boundary and the Cell role owns no unrelated platform resources.

- [x] 6. Run quality gates and record live qualification boundary (AC: 9, 10)
  - [x] Run Terraform format/backend-free validation, provider build, Ruff, strict mypy, contract/runtime tests, Checkov, manifest validation, and repository hygiene.
  - [x] Keep credential-free tests separate from live AWS qualification; live qualification remains a deployment prerequisite.

### Review Findings

- [x] [Review][Patch] Replace the internet-reachable Function URL with a private API boundary and bind invocation to the registered Cell integration; the selected decision is private API access. [modules/ecs-scheduled-job-platform/main.tf:1126]
- [x] [Review][Patch] Implement explicit same-account role assumption and a reviewed locked provider mirror/registry; the selected decision is role assumption plus managed distribution. [tools/terraform-provider-cell/main.go:106]
- [x] [Review][Patch] Align CONFIG hashing between Terraform and the publisher — Terraform hashes `jsonencode(local.config_body)` while the publisher hashes RFC8785 bytes of `document["config"]`; normal publications will fail with `CONFIG_HASH_MISMATCH`. [modules/ecs-scheduled-job/main.tf:163; runtime/config_publisher/src/config_publisher/domain.py:93]
- [x] [Review][Patch] Make the Cell publisher an allowed S3 writer — the bucket policy denies principals without `PlatformEcsScheduledJobId`, but the Cell Lambda execution role has only common tags, so its conditional write is denied before application authorization can help. [modules/ecs-scheduled-job-platform/main.tf:1047]
- [x] [Review][Patch] Correct KMS encryption-context authorization — `StringEquals` is used with a `bucket/*` value, so the wildcard is literal and the publisher's S3 encryption context will not match. [modules/ecs-scheduled-job-platform/main.tf:1063]
- [x] [Review][Patch] Enforce the complete CONFIG schema and secret-safety policy at the publisher boundary — runtime validation checks only a mapping, selected key names, and a hash; invalid documents and values such as `api_key` can be stored. [runtime/config_publisher/src/config_publisher/domain.py:68]
- [x] [Review][Patch] Complete and validate the response contract — successful and rejection responses omit the required operation/audit identifier and rejection metadata; the provider accepts any successful `{}` response as publication success. [runtime/config_publisher/src/config_publisher/domain.py:153; tools/terraform-provider-cell/main.go:90]
- [x] [Review][Patch] Bind the provider endpoint to the discovered Cell Contract — the job validates only that the contract endpoint is HTTPS while the provider endpoint is independently configured, allowing CONFIG to be sent to an unintended service. [modules/ecs-scheduled-job/main.tf:242; modules/ecs-scheduled-job/examples/basic/main.tf:1]
- [x] [Review][Patch] Add required bounded publisher telemetry and operational coverage — the runtime emits no structured result logs/custom metrics, and Terraform creates only generic Lambda error/throttle alarms without conflict, authorization, validation, latency, or runbook coverage. [runtime/config_publisher/src/config_publisher/handler.py:33; modules/ecs-scheduled-job-platform/main.tf:1140]
- [x] [Review][Patch] Accept the actual Cell publisher role ARN shape — the job variable rejects IAM role paths while the platform creates the publisher role under `/platform/<cell_id>/v1/`. [modules/ecs-scheduled-job/variables.tf:73; modules/ecs-scheduled-job-platform/main.tf:1049]

## Dev Notes

### Required architecture guardrails

- The Cell owns the publisher service, its execution role, API/resource policy,
  S3/KMS write authority, alarms, and operational runbook. The job root owns
  only its job resources and invokes the registered Cell integration.
- The Registrar/namespace ownership record is authoritative for job identity.
  Do not authorize from an arbitrary `job_id`, object key, request header, or
  caller-supplied ownership generation.
- The Cell publisher is part of the `RESERVED -> PUBLISHED -> VALIDATED ->
  MATERIALIZED -> ENABLED` handshake. It must not validate/acknowledge,
  materialize, enable Scheduler, or write runtime ledger state.
- CONFIG remains append-only and secret-free. Existing CONFIG versions,
  task revisions, logs, and ownership evidence must survive retries and
  rollback. Never implement fallback to unconditional `PutObject`.
- Do not use `Principal = "*"`, public API exposure, broad S3/KMS resources,
  Terraform provisioners, `null_resource`, local shell uploads, or generated
  state. Any service resource policy must use explicit IAM authentication and
  exact account/identity conditions supported by AWS.

### Current repository patterns to preserve

- `modules/ecs-scheduled-job-platform` owns the shared Cell, contract
  publication, Cell Lambdas, IAM boundaries, alarms, and canary publisher role.
  Reuse its artifact, runtime, tags, KMS, and alarm conventions.
- `modules/ecs-scheduled-job` currently renders the canonical CONFIG body and
  uses `modules/ecs-scheduled-job/phase_one.tf` for the disabled schedule and
  direct S3 object. Story 2.5a must provide the replacement publication edge
  without changing scheduler ownership or the canonical CONFIG hash/key.
- `contracts/manifest.json` uses raw UTF-8/LF artifact checksums and declares
  RFC8785 semantic JSON plus NFC strings. Every new schema/fixture must be
  inventoried and its checksum updated.
- The repository seed is Terraform 1.15.8, AWS provider 6.54.0, Python 3.14,
  and uv 0.11.29. Consumer roots use committed lockfiles and CI uses
  `terraform init -lockfile=readonly`.

### Suggested API/provider behavior

Use a request equivalent to:

```json
{
  "protocol_version": "config-publisher/1.0.0",
  "job_id": "dev/sample/daily",
  "config_version": "<64 lowercase hex>",
  "object_key": "jobs/dev/sample/daily/config/<config_version>.json",
  "config_document": {"schema_version": "1.0.0", "config_version": "...", "config": {}},
  "contract_version": "1.0.0",
  "ownership_generation": 1
}
```

The service must canonicalize/validate the document before writing, use the
exact object key derived from the authenticated job ID and version, and issue
the AWS SDK call with `IfNoneMatch="*"`. A 412 response is not automatically a
success: read and compare only enough to establish identical canonical bytes;
otherwise return `CONFIG_VERSION_CONFLICT`. Return stable machine codes and
never return the document, secret references beyond approved locators, or raw
AWS error text.

### Observability and rollback

Use bounded dimensions such as environment, Cell ID, result code, and protocol
version. Include a runbook for API authorization failures, S3 412 conflicts,
KMS denial, throttling, Lambda/API errors, and contract version mismatch. The
safe rollback is: keep all schedules disabled, stop routing new publication
requests to the new integration, retain the publisher version and existing
CONFIG objects for investigation, and require an explicit reviewed migration;
never silently restore direct unconditional S3 writes.

### References

- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.5-Publish-Phase-One-Job-Resources-and-CONFIG`]
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-2.6-Validate-and-Acknowledge-Job-Configuration`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5-Versioned-Event-and-Configuration-Contracts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12-Explicit-IAM-Boundaries`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-14-Bounded-Metrics-and-Enriched-Alerts`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-18-Two-phase-Schedule-Change-and-Rollback`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-25-Single-Terraform-Owner-per-Integration-Edge`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28-Globally-Registered-Job-Ownership`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-29-Publish-Validate-Materialize-Enable-Handshake`]
- [Source: `contracts/v1/schemas/config.schema.json`]
- [Source: `contracts/v1/schemas/cell-contract.schema.json`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `modules/ecs-scheduled-job-platform/README.md`]
- [Source: `modules/ecs-scheduled-job/phase_one.tf`]
- [Source: `_bmad-output/implementation-artifacts/2-5-publish-phase-one-job-resources-and-config.md`]
- [AWS S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
- [AWS S3 PutObject API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)
- [Terraform AWS `aws_s3_object`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Reviewed Epic 2 Stories 2.5 and 2.6, current Story 2.5 implementation and
  review finding, architecture spine, project context, AWS Terraform standard,
  Cell platform contract/Lambda/IAM patterns, and the pinned AWS provider
  schema. The provider does not expose `If-None-Match` on `aws_s3_object`.
- Resolved the prior publisher-boundary blocker by implementing the Cell-owned
  Lambda Function URL, IAM authorization boundary, conditional S3 writer, and
  maintained Terraform provider in this repository. The provider is built by
  the credential-free validation harness through a temporary dev override.

### Completion Notes List

- Story intentionally separates the Cell publisher service/provider from Story
  2.5 so the cross-root IAM, API, contract, observability, and rollback changes
  receive independent review.
- Full validation passed: 214 tests, 223 contract subtests, Terraform validation,
  provider build/tests, Ruff, strict mypy, Checkov, manifest integrity, and
  repository hygiene.

### File List

- `_bmad-output/implementation-artifacts/2-5a-cell-owned-conditional-config-publisher.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `runtime/config_publisher/`
- `tools/terraform-provider-cell/`
- `contracts/v1/schemas/config-publisher-request.schema.json`
- `contracts/v1/schemas/config-publisher-response.schema.json`
- `contracts/v1/fixtures/config-publisher/cases.json`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job/phase_one.tf`
- `scripts/validate.py`
