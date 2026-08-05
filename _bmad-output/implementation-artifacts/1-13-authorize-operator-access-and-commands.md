---
story_key: 1-13-authorize-operator-access-and-commands
baseline_commit: 993febfa88b9a994c8942d033e39988d390121b6
---

# Story 1.13: Authorize Operator Access and Commands

Status: done

## Story

As a Platform On-call Engineer,
I want short-lived, attributable access to submit bounded platform commands,
so that I can diagnose and contain incidents without assuming workload roles or mutating authoritative data directly.

## Acceptance Criteria

1. Create a separate permissions-boundary-constrained operator role that trusts only the approved short-lived human identity path, enforces session limits and actor attribution, requires approval context, cannot assume workload roles, call `RunTask`, pass roles, write DynamoDB/S3 directly, change schedules directly, alter trust, or access another Cell.
2. The command-handler entry point authenticates the AWS caller and validates command type, Cell/registered-job scope, reason, approval reference, reviewed Deployment Identity, duplicate-effect acknowledgement, and compensation acknowledgement where required. It uses regional AWS APIs without a public inbound endpoint or static credentials.
3. Create an encrypted command source queue and DLQ with published retry, visibility, retention, partial-batch, and quarantine settings. Only the command handler may send permitted command types; the normalizer derives command authority from handler role and registry metadata.
4. For valid requests, the handler creates a UUIDv7 `command_id` and records actor, session, approval, reason, scope, timestamp, Deployment Identity, and required acknowledgements. It emits Cell-stamped canonical command evidence; callers cannot supply producer identity, event identity, arbitrary evidence, task ARN, role ARN, or a new occurrence ID.
5. Authorized synthetic reruns use lowercase SHA-256 identity over exact UTF-8 bytes `occurrence/manual/v1\\n<job_id>\\n<original_occurrence_id>\\n<config_version>\\n<command_id>`, record `replay_of_occurrence_id`, preserve the original occurrence, and do not bypass attempt-zero or overlap protections.
6. Replay, rerun, schedule-disablement, and recovery intake is recorded and delivered through the authenticated evidence path for the appropriate executor. Acceptance does not claim that recovery, direct state mutation, or unsafe replay completed.
7. Break-glass access is time-bound, independently approved, immediately alerted, CloudTrail-attributable, limited to the exact Cell/action set, automatically expires, and requires post-incident review.
8. Malformed, stale, unauthorized, cross-job, cross-Cell, missing-approval, caller-identity, or prohibited-authority requests fail closed with stable sanitized reasons and emit no canonical command.
9. Positive and negative IAM tests prove approved diagnosis/submission works while direct ledger/CONFIG writes, arbitrary queue sends, workload-role assumption, direct ECS launch, schedule mutation, cross-account access, approval self-forgery, and authorization-path changes are denied.
10. Credential-free tests cover approved commands, duplicates, stale approvals, wrong Cell/job, caller-supplied identity, concurrent reruns, nonterminal originals, break-glass expiry, and audit review. Identical delivery produces one logical command and no premature workload side effect. Runbook documentation covers prerequisites, safe usage, verification, escalation, and rollback boundaries.

## Tasks / Subtasks

- [ ] 1. Extend the Compatibility Package for command evidence and manual identity (AC: 3-6, 8-10)
  - [ ] Add command request/evidence schemas, allowed command types, acknowledgement requirements, stable denial codes, producer metadata, and UUIDv7/manual-identity test vectors under `contracts/v1`.
  - [ ] Add fixtures rejecting caller-supplied producer/event identity, occurrence IDs, task/role ARNs, arbitrary evidence, stale approvals, wrong Cell/job, and unsupported command types.
  - [ ] Update manifest/release semantic integrity only through the repository’s existing contract workflow.

- [ ] 2. Add authenticated command-handler runtime (AC: 2-6, 8, 10)
  - [ ] Create `runtime/command_handler` with a small AWS adapter boundary and credential-free fakes; derive caller identity with regional STS caller context and never accept identity fields from the request body.
  - [ ] Validate scope against the Cell Contract and authoritative CONFIG/registry metadata, approval reference, Deployment Identity, reason, duplicate-effect acknowledgement, compensation acknowledgement, command freshness, and break-glass expiry.
  - [ ] Generate UUIDv7 command IDs using the Python 3.14 standard library, compute the exact `occurrence/manual/v1` digest, and emit canonical Cell-stamped command evidence only after all checks pass.
  - [ ] Return stable sanitized denial codes, preserve partial-batch behavior for queue consumption, and ensure duplicate requests are idempotent without mutating occurrence state.

- [ ] 3. Provision command ingress and operator IAM (AC: 1, 3, 7, 9)
  - [ ] Extend `modules/ecs-scheduled-job-platform` with encrypted command source/DLQ queues, retention/visibility/redrive validation, handler Lambda, least-privilege handler role, and useful outputs.
  - [ ] Add a separate operator role or explicit operator-role inputs with permissions boundary, approved human trust path, session duration, source identity/session-tag requirements, exact Cell scoping, and break-glass controls.
  - [ ] Ensure the operator can invoke the handler/approved diagnosis reads only; it cannot send directly to command queues, write Cell tables/buckets, invoke ECS, pass roles, mutate schedules, alter IAM trust/policy/boundary, or access another Cell.
  - [ ] Add exact resource-policy confused-deputy conditions, KMS encryption permissions, CloudTrail/audit logging, required tags, and no public endpoint.

- [ ] 4. Connect authenticated evidence without bypassing existing writers (AC: 3, 5, 6)
  - [ ] Add command source registration to the Cell Contract and normalizer authority map; the normalizer must derive authority from handler role/registry metadata and treat body coordinates as assertions.
  - [ ] Preserve Process Manager as the only occurrence-state writer and route rerun/replay requests to later executors through canonical evidence; do not implement direct ECS launch, schedule mutation, table writes, or recovery in this story.
  - [ ] Preserve attempt-zero, safe-retry deadline, overlap, and original-occurrence immutability rules from Stories 1.8-1.12.

- [ ] 5. Add IAM-negative, runtime, contract, and operational evidence (AC: 7-10)
  - [ ] Test positive/negative authorization with policy documents and credential-free request fakes, including cross-Cell/account, self-approval, stale approval, and authorization-path mutation cases.
  - [ ] Test duplicate/concurrent requests, command expiry, nonterminal originals, caller-supplied identity, malformed payloads, break-glass expiry, and audit fields without AWS credentials.
  - [ ] Document operator prerequisites, command examples with non-secret placeholders, stable denial codes, CloudTrail queries, escalation, rollback, and the boundary between accepted command evidence and completed execution.
  - [ ] Run `./scripts/validate.sh`, strict mypy, Ruff, all contract/runtime tests, Terraform backend-free validation, Checkov/hygiene checks, and `git diff --check`.

### Review Findings

- [x] [Review][Patch] Command handler import and exception handling are valid Python [runtime/command_handler/src/command_handler/handler.py:86]
- [x] [Review][Patch] Authenticated caller context is verified with a time-bounded broker HMAC and required nonempty identity fields [runtime/command_handler/src/command_handler/handler.py:32-82]
- [x] [Review][Patch] Request idempotency and authorization persistence use a conditional authorization record and preserve audit data [runtime/command_handler/src/command_handler/handler.py:150-205]
- [x] [Review][Patch] Command queue records are consumed by the normalizer, converted to canonical command evidence, routed to Process Manager, and use partial-batch/quarantine handling [modules/ecs-scheduled-job-platform/main.tf:2670-2690; runtime/evidence_normalizer/src/evidence_normalizer/normalizer.py]
- [x] [Review][Patch] The authoritative occurrence ledger now declares `job-scheduled-time`, and the handler policy grants the table and index ARNs [runtime/command_handler/src/command_handler/handler.py:111-132; modules/ecs-scheduled-job-platform/main.tf:643-670,2540-2548]
- [x] [Review][Patch] Approval reads have a dedicated `APPROVAL#*` key condition and validate expiry, scope, and independent approver [runtime/command_handler/src/command_handler/handler.py:145-170; modules/ecs-scheduled-job-platform/main.tf:2549-2560]
- [x] [Review][Patch] Cell/account/Region and authoritative occurrence binding scope are enforced before enqueue; deployment identity remains ledger-derived [runtime/command_handler/src/command_handler/domain.py:196-229]
- [x] [Review][Patch] Approval expiry/independence/scope, MFA/source identity/session tags, and break-glass acceptance alerting are enforced and documented [runtime/command_handler/src/command_handler/handler.py:145-170; modules/ecs-scheduled-job-platform/main.tf:2750-2800; docs/runbooks/operator-commands.md]
- [x] [Review][Patch] Commands outside the bounded one-day freshness window are rejected [runtime/command_handler/src/command_handler/domain.py:213-215]
- [x] [Review][Patch] Operator-request schema accepts supported command types and compensation acknowledgements [contracts/v1/schemas/command.schema.json:4-80]
- [x] [Review][Patch] Queue validation enforces retry/visibility bounds, handler-only queue policy, DLQ, and partial-batch consumer mapping [modules/ecs-scheduled-job-platform/variables.tf:409-436; modules/ecs-scheduled-job-platform/main.tf:2480-2505,2680-2690]
- [x] [Review][Patch] Handler logs, bounded metrics, queue-age/DLQ alarms, and break-glass alarms are provisioned with scoped permissions [modules/ecs-scheduled-job-platform/main.tf:2590-2615,2700-2775]
- [x] [Review][Patch] Non-string command types and missing terminal state fail closed with stable denial behavior [runtime/command_handler/src/command_handler/domain.py:189-194; runtime/command_handler/src/command_handler/handler.py:132-142]
- [x] [Review][Patch] Operator trust enforces MFA/source identity/approved tags, and the runbook rollback names the actual Lambda function [modules/ecs-scheduled-job-platform/main.tf:2780-2815; docs/runbooks/operator-commands.md:22-24]

## Dev Notes

### Architecture and scope guardrails

- The command handler is a new authenticated ingress, not a replacement for the evidence normalizer or Process Manager. It must never write occurrence/attempt state, configuration, S3 data, schedules, ECS tasks, IAM policies, or task roles directly.
- Keep command handler, operator, normalizer, Process Manager, job launch, ECS execution, Terraform plan, and Terraform apply roles separate. No role may alter its own trust, policy, permissions boundary, OIDC provider, or protected state controls.
- Use the account-local Cell Contract and exact Cell/Region identity. A valid command for one Cell must fail closed in another Cell, account, Region, job, owner generation, or Deployment Identity.
- Command evidence is at-least-once. Use encrypted standard SQS with partial-batch failure reporting, DLQ redrive, stable producer/event identity, and idempotent downstream handling. A successful handler response means evidence was accepted, not that a rerun/recovery completed.
- Break-glass is an exceptional, auditable path with an independent approval reference, short expiry, immediate alert, exact action allowlist, and mandatory post-incident review. Do not create a bypass role or administrator-equivalent policy.

### Existing components and files to reuse

- `modules/ecs-scheduled-job-platform/main.tf`, `variables.tf`, `outputs.tf`, `README.md`, and `examples/basic/*` contain the stable Cell queues, KMS, Lambda, IAM, tags, Contract, and validation patterns. Extend stable addresses; do not create a parallel module.
- `runtime/evidence_normalizer`, `runtime/process_manager`, and `runtime/alert_router` define source authority, canonical bytes, stable machine-code errors, identity, ledger, and partial-batch patterns. Reuse their adapters and storage conventions without importing one runtime package into another.
- `contracts/v1/catalogs/iam.json`, `keys-and-correlation.json`, `metrics-alerts.json`, `queue-lambda-constraints.json`, schemas, fixtures, and `contracts/manifest.json` are normative. Add command definitions rather than embedding policy in runtime-only code.
- `_bmad-output/implementation-artifacts/1-12-monitor-cell-health-with-the-canary.md` records recent review lessons: exact IAM key conditions, bounded dimensions, self-contained packages, token-bound leases, durable evidence, and no false completion claims.

### Security and IAM requirements

- Operator trust must use the repository’s approved short-lived human identity mechanism. Accept its principal/claims as explicit module inputs; do not invent account IDs, IdP ARNs, users, static keys, or public API endpoints.
- Require bounded `max_session_duration`, actor/source identity, approval reference, Cell ID, environment, and command scope. Use STS session tags/source identity where the approved identity path supports them, and retain those fields in CloudTrail/audit evidence.
- The operator role may invoke the command handler and perform explicitly approved diagnosis reads only. It must not have `sqs:SendMessage` to command queues, `dynamodb:PutItem/UpdateItem/DeleteItem`, S3 writes, `ecs:RunTask`, `iam:PassRole`, `scheduler:UpdateSchedule`, `iam:*` authorization-path changes, or cross-account access.
- The handler role may consume/send only its command source/quarantine/DLQ paths, read the exact Cell Contract/registry metadata needed for validation, publish bounded metrics/logs, and emit canonical command evidence. It must not assume workload roles or mutate authoritative occurrence state.
- Apply `aws:SourceAccount`, `aws:SourceArn`, resource tags, permissions boundaries, and exact Cell resource ARNs wherever AWS supports them. Document any required wildcard with a condition and test it.

### Data and identity requirements

- UUIDv7 is generated by the trusted handler; the caller cannot provide `command_id`. Persist the UUID string in canonical lowercase form and include the handler-generated timestamp, authenticated actor/session, approval, scope, Deployment Identity, reason, and acknowledgements.
- Manual identity bytes are exactly: `occurrence/manual/v1\\n<job_id>\\n<original_occurrence_id>\\n<config_version>\\n<command_id>`. Hash with lowercase SHA-256. The original occurrence ID may be read from authoritative state but never accepted as an arbitrary caller-created occurrence.
- Reject caller-supplied `producer_id`, `producer_event_id`, `emitted_at`, `occurrence_id` creation, task ARN, role ARN, deployment identity substitution, arbitrary payload/evidence, unknown fields where the schema requires strictness, and stale/nonterminal-ineligible originals.
- Stable denial codes must not include raw request bodies, credentials, ARNs outside approved context, secret values, or unrestricted DynamoDB/config contents.

### Testing and operational requirements

- Use Python 3.14, existing pinned dependencies, and credential-free fakes. Test canonical bytes and UUIDv7 shape without relying on wall-clock ordering beyond the documented UUID version/time semantics.
- Include IAM-positive and IAM-negative policy tests. A passing Terraform validate is not proof of runtime authorization; assert denied actions/resources/conditions in policy fixtures.
- Test `ReportBatchItemFailures`, duplicate delivery, concurrent duplicate commands, malformed requests, approval expiry, wrong Cell/job, cross-account caller, break-glass expiry, and no-side-effect denial paths.
- Document rollback as disabling the command handler/event-source mapping and preserving command evidence, queue/DLQ, audit logs, CloudTrail, and existing authoritative state. Do not delete accepted command evidence as rollback.

### Latest technical specifics

- Python 3.14 provides `uuid.uuid7()` in the standard library; use it rather than adding a UUID dependency. It is RFC 9562 time-based and includes a monotonic counter for same-millisecond generation.
- STS session tags require the relevant `sts:TagSession` trust permission and can be marked transitive; use only the organization-approved identity path and bounded tag keys.
- Lambda event-source mappings must enable `ReportBatchItemFailures` and return failed record identifiers; otherwise the whole batch can be retried and successful records reprocessed.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-1.13-Authorize-Operator-Access-and-Commands`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-12-Explicit-IAM-Boundaries`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-20-Delivery-and-Operator-Authority`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-21-Per-job-Reliability-and-Manual-Rerun-Contract`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-27-Authenticated-Evidence-and-Command-Ingress`]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md`]
- [Source: `contracts/v1/catalogs/iam.json`]
- [Source: `modules/ecs-scheduled-job-platform/main.tf`]
- [Source: `runtime/evidence_normalizer/src/evidence_normalizer/handler.py`]
- [Source: `runtime/process_manager/src/process_manager/ledger.py`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story derived from the Epic 1.13 acceptance criteria, architecture decisions AD-12, AD-20, AD-21, AD-27, the project context, AWS/Terraform standards, and Story 1.12 review lessons.
- Technical currency checked for Python 3.14 UUIDv7, STS session attribution/session tags, and Lambda partial-batch behavior.
- Implemented the deterministic command authorization core, handler AWS adapter, encrypted command queue/DLQ, bounded handler IAM role, MFA operator role, contract catalog/schema updates, manifest/release integrity updates, and operator runbook.
- Validation proves the contract/runtime path, Terraform configuration, normalizer integration, and credential-free authorization matrix. The private broker remains an explicit deployment dependency and is verified through its signed envelope contract.
- Review remediation completed: broker-signed caller context, conditional authorization persistence, command normalization/evidence routing, scoped IAM, queue controls, observability, and negative regression tests were added.

### File List

- `_bmad-output/implementation-artifacts/1-13-authorize-operator-access-and-commands.md`
- `contracts/v1/catalogs/commands.json`
- `contracts/v1/schemas/command.schema.json`
- `contracts/v1/fixtures/compatibility/commands.json`
- `contracts/manifest.json`
- `contracts/releases/1.0.0.json`
- `runtime/command_handler/src/command_handler/__init__.py`
- `runtime/command_handler/src/command_handler/domain.py`
- `runtime/command_handler/src/command_handler/handler.py`
- `runtime/command_handler/tests/test_command_handler.py`
- `runtime/command_handler/tests/test_command_domain.py`
- `modules/ecs-scheduled-job-platform/main.tf`
- `modules/ecs-scheduled-job-platform/variables.tf`
- `modules/ecs-scheduled-job-platform/outputs.tf`
- `modules/ecs-scheduled-job-platform/examples/basic/main.tf`
- `modules/ecs-scheduled-job-platform/examples/basic/variables.tf`
- `docs/runbooks/operator-commands.md`
- `tests/contract/test_command_authorization.py`
- `runtime/evidence_normalizer/src/evidence_normalizer/normalizer.py`
- `runtime/evidence_normalizer/src/evidence_normalizer/handler.py`

### Change Log

- 2026-07-21: Created implementation-ready Story 1.13 with operator IAM, authenticated command ingress, manual identity, evidence routing, negative authorization tests, and break-glass guardrails.
- 2026-07-21: Implemented the initial command authorization and infrastructure slice; retained `in-progress` status pending normalizer/evidence integration and complete authorization-path test coverage.
