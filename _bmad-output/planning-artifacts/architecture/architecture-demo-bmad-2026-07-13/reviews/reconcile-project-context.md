# Reconciliation: Architecture Spine Against Project Context

## Scope

- Source of mandatory engineering rules: `_bmad-output/project-context.md`
- Architecture reviewed: `ARCHITECTURE-SPINE.md`
- Review lens: AWS, Terraform, CI/CD, security, IAM, observability, reliability, rollback, documentation, and definition of done

## Verdict

**Conditional pass.** The spine preserves the most important runtime invariants: AWS and ECS Fargate as the platform, account-local failure domains, least-privilege workload roles, private ECS networking, safe secret references, isolated encrypted Terraform state, immutable delivery inputs, actionable alarms, replay, and a mechanically credible schedule rollback. No direct architectural contradiction with the project context was found. However, four high-severity and six medium-severity omissions or ambiguities leave implementation teams without binding rules in areas the project context treats as mandatory.

## Findings

### 1. High: CI/CD authority is specified, but mandatory quality gates are not

**Project rule:** Terraform pipelines must run checkout, format check, validation, security scanning, plan, manual production approval, and apply. Terraform work is not complete until `terraform fmt -check` and `terraform validate` pass. Tests are required or their omission must be justified.

**Architecture state:** AD-16 precisely constrains credentials, plan/apply roles, immutable workflow identity, protected production approval, and exact saved-plan application. It says untrusted pull requests run "credential-free checks" but never defines those checks. The Structural Seed names contract and integration tests but no workflow invariant requires them, a security scan, formatting, validation, or policy fixtures to pass.

**Risk:** An implementation can conform to AD-16 while deploying syntactically invalid, unformatted, untested, or policy-violating Terraform through a securely authenticated workflow.

**Required reconciliation:** Add a delivery invariant defining required pull-request and trusted-plan stages: checkout, `terraform fmt -check`, backend-free `terraform validate`, module/example tests, security and policy scans, Terraform plan, and required status checks. Preserve AD-16's separate approved apply. State which failures block every environment and which policy checks, if any, may initially be advisory outside production.

### 2. High: Human production access and administrative audit paths are undefined

**Project rule:** Human roles must be separate from workload roles; administrative actions and production access paths must be auditable and documented. Short-lived credentials are preferred.

**Architecture state:** AD-12 separates Scheduler, runtime, task, plan, and apply roles, but it does not define human operator, incident-response, break-glass, manual-rerun, replay, or backfill authority. AD-11 and Deferred rely on replay and operational backfill without identifying who can invoke them, through which controlled interface, or how the action is recorded.

**Risk:** Operators may reuse workload/deployment permissions or invent direct console procedures, undermining least privilege, separation of duties, and incident auditability.

**Required reconciliation:** Define a short-lived, separately trusted operator access path with least-privilege actions for diagnosis, rerun, replay, schedule disablement, and approved recovery. Require attributable audit logs, approval boundaries for production actions, and a documented break-glass path. Explicitly prohibit human assumption of workload roles.

### 3. High: Infrastructure launch idempotency does not bind application-effect idempotency or bounded retries

**Project rule:** Scheduled jobs should be idempotent where possible; retries use backoff where appropriate and must not be infinite; timeout and idempotency expectations must be explicit; DLQ and replay behavior must be operable.

**Architecture state:** AD-8 makes `RunTask` calls idempotent with `clientToken`, and AD-7 makes evidence processing idempotent. Neither rule requires the job application to tolerate duplicate executions or protect external side effects. AD-11 specifies SQS and Scheduler DLQs but not maximum receive counts, Scheduler retry/event-age bounds, Lambda retry/backoff limits, replay authorization, or poison-message disposition after replay.

**Risk:** The platform state can remain consistent while a duplicate task corrupts application data, or a failing message cycles indefinitely or is replayed unsafely.

**Required reconciliation:** Add a per-job reliability contract for application idempotency, locking or compensating behavior, overlap safety, retry/event-age limits, and manual replay prerequisites. Bind concrete redrive limits and retry ownership for Scheduler, Lambda/SQS, ECS launch, and application-level retries; no layer may imply unlimited retry.

### 4. High: Rollback mechanics omit recovery-time, compatibility, and application side-effect requirements

**Project rule:** Every production deployment must state how to roll back, the exact artifact/version, compatibility and migration constraints, whether rollback is safe for data/schema changes, and expected recovery time.

**Architecture state:** AD-18 gives a strong two-phase schedule-change and rollback sequence and restores pinned Cell, job, and task-definition versions. AD-5 and AD-17 version contracts and require migration notes. The spine does not require a recovery-time estimate, verify backward compatibility of ledger/event/config schema changes during rollback, or address application data effects caused by a task before infrastructure rollback.

**Risk:** A technically restored platform may remain incompatible with queued events or mutated workload data, with no defined recovery expectation or compensating action.

**Required reconciliation:** Extend AD-18 or a rollback companion invariant to require the known-good Deployment Identity, expected recovery time, event/config/ledger compatibility window, migration rollback or forward-fix decision, job-side-effect assessment, compensating action, and post-rollback verification. Destructive cleanup must remain prohibited until both platform and application recovery are confirmed.

### 5. Medium: Mandatory tags are not an architecture invariant

**Project rule:** Every applicable AWS resource uses `Environment`, `Application`, `Service`, `Owner`, `ManagedBy`, and, where applicable, `CostCenter` and `Repository`; `ManagedBy` defaults to `Terraform`.

**Architecture state:** The Capability Map assigns "tags" to the job module, but no AD or convention enumerates required tags, protects their values, or applies them to shared Cell resources as well as per-job resources.

**Risk:** Shared Cell components or new resource types can ship unowned, unallocated, or inconsistently tagged while still conforming to the spine.

**Required reconciliation:** Add a tagging convention for all taggable Cell and job resources, define protected tag merging and required nonempty values, and assign ownership for Cell-level `Application`, `Service`, `Owner`, `CostCenter`, and `Repository` values.

### 6. Medium: Terraform module structure and repository hygiene are incomplete

**Project rule:** Reusable modules use the standard `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, `README.md`, and `examples/` shape; variables and outputs are described; important variables use validation; naming/tag derivation uses locals; account IDs, Regions, ARNs, and environment names are not hardcoded. Provisioners and normal-workflow `null_resource` use are prohibited. `.terraform/`, state, generated plans, credentials, and other generated state files are never committed.

**Architecture state:** The Structural Seed defines module directories and shared examples but not the required module files or per-module examples. AD-15 secures remote state and AD-16 secures short-lived plans, but the spine does not bind module interface quality, validation/locals, hardcoding prohibitions, provisioner restrictions, or repository artifact hygiene.

**Risk:** Different implementers can create incompatible module layouts, hide environment assumptions, add imperative provisioning, or commit sensitive/generated Terraform artifacts without violating an architecture invariant.

**Required reconciliation:** Expand the Structural Seed or add a Terraform convention that binds the repository module shape, documented and validated interfaces, derived naming/tags, no hardcoded deployment identifiers, no routine provisioners/`null_resource`, and explicit ignore/CI checks for `.terraform/`, state, saved plans, credentials, and generated artifacts. Keep the controlled saved plan in AD-16 as a restricted CI artifact only.

### 7. Medium: Encryption requirements are uneven across persisted data

**Project rule:** Encrypt storage by default and use KMS where appropriate; secrets and sensitive tokens must not leak through logs, state, plans, messages, or documentation.

**Architecture state:** AD-11 calls the ingress queue encrypted and AD-15 fully constrains the S3 state backend. Encryption and key-policy expectations are not stated for the Scheduler DLQ, redrive DLQ, DynamoDB ledger and PITR, CloudWatch log groups, SSM contract manifest, or any alarm-notification payload storage. The conventions prevent secret values in configuration and logs but do not classify other operational data such as error reasons or Deployment Identity.

**Risk:** Services may fall back to inconsistent AWS-owned encryption or overly broad customer-managed key policies, and operational payloads may expose sensitive workload context.

**Required reconciliation:** Define the at-rest encryption baseline for every persisted component, when customer-managed KMS keys are required, key-administration and runtime-use separation, and least-privilege key policies. Add an operational-data classification rule for event payloads, error reasons, alerts, and ledger records.

### 8. Medium: CloudWatch logging, retention, dashboard criteria, and runbook contents remain ambiguous

**Project rule:** ECS tasks send logs to CloudWatch Logs; log group names follow the naming convention; retention is explicit and not infinite by default; production components have logs, metrics, alarms, a dashboard when production-critical, known failure modes, and actionable runbook notes.

**Architecture state:** AD-9 consumes structured completion-log evidence and the conventions define log fields and secret exclusion, but no invariant names CloudWatch Logs, requires a per-job log group, defines subscription/ingestion failure behavior, or requires explicit retention. Retention defaults appear under Deferred and A-4 rather than as a binding rule. AD-14 enriches alerts with Runbook context, but the spine does not define the required Runbook content. Centralized dashboards are deferred without stating whether a production-critical Cell or per-job dashboard is required.

**Risk:** Implementations can produce structured logs without durable CloudWatch configuration, lose completion evidence through an unmonitored subscription, retain logs indefinitely, or alert operators into an incomplete runbook.

**Required reconciliation:** Bind per-job CloudWatch log groups, standard names, explicit environment-specific retention, log-ingestion health and alarms, and secret-safe structured fields. Define dashboard applicability for production-critical Cells/jobs. Require runbooks to cover health verification, common alerts and failure modes, logs/dashboards, replay or rerun, redeploy, rollback, dependencies, ownership, and escalation.

### 9. Medium: Cost consideration is deferred rather than included in production readiness

**Project rule:** Production readiness and architecture decisions include cost considerations; tagging supports ownership and allocation.

**Architecture state:** The design adds two schedules per job, account/Region-local Lambda functions, SQS/DLQs, DynamoDB with PITR, per-job alarms, log ingestion, and a one-minute canary. Cost allocation is explicitly deferred, and the spine provides no cost model, scale assumptions, guardrails, or cost-impact acceptance criterion.

**Risk:** The platform's fixed per-Cell and per-job costs can multiply across Accounts and Regions without an understood adoption envelope or alerting threshold.

**Required reconciliation:** Document estimated fixed Cell cost and marginal per-job/run cost at MVP scale, identify dominant cost drivers, set configurable retention/canary guardrails, and add cost impact to production readiness and change review. Full chargeback may remain deferred.

### 10. Medium: Documentation and definition-of-done evidence are not bound to implementation completion

**Project rule:** Completion requires matching implementation, formatting and validation, tests or rationale, security/IAM review, safe secrets, production logs/metrics/alarms, rollback, README/runbook updates, PR impact and risk notes, expected production plan impact, no unrelated refactoring, and no committed secrets or generated state. Terraform module README content is explicitly defined.

**Architecture state:** The Capability Map points to "job docs and production gates," tests appear in the Structural Seed, and a team walkthrough is deferred. There is no completion gate that lists required README, examples, inputs/outputs, providers, assumptions, security, observability, runbook, troubleshooting, rollback, ownership, test evidence, validation evidence, or PR risk/plan evidence.

**Risk:** Architecture-conformant implementation can be declared complete without the operating material or review evidence required by the repository.

**Required reconciliation:** Add a concise architecture definition of done or bind an implementation-readiness checklist that incorporates the project-context completion rules. It should require exact `terraform fmt -check` and `terraform validate` evidence, focused tests and failure injection, security/IAM review, expected plan impact, rollback evidence, README and runbook completeness, and confirmation that the change contains no secrets, generated state, or unrelated work.

## Aligned Load-Bearing Rules

- **AWS platform:** AWS-managed services and ECS Fargate are the selected runtime; the design does not introduce EC2, EKS, or cross-cloud dependencies.
- **Failure isolation:** Account- and Region-local Cells avoid central runtime credentials and cross-account blast radius.
- **Naming:** The `<environment>-<application>-<component>` resource convention is explicit.
- **IAM:** Scheduler, processor, launch, execution, application, plan, and apply permissions are separated and constrained; `iam:PassRole` scope is explicit.
- **Secrets:** Only approved secret references enter configuration; secret values are excluded from messages, state, plans, and logs.
- **Networking:** Fargate uses `awsvpc`, private subnets, minimal security groups, and no public IP; NAT or VPC endpoint prerequisites are documented.
- **Terraform state:** Account/environment/root separation, encrypted and versioned S3 state, public-access blocking, native locking, and exact object permissions are explicit.
- **Supply chain:** Modules, workflows, Actions, providers, and images use immutable or lock-file-controlled identities; production rejects moving image tags.
- **Production authority:** OIDC conditions, separate plan/apply roles, protected approval, exact short-lived saved-plan application, and controlled concurrency are strong.
- **Observability model:** The design distinguishes expected occurrence, launch, runtime, completion, and Cell-health failures; bounded metrics and context-rich alarms avoid cardinality and response ambiguity.
- **Reliability mechanisms:** Conditional state transitions, idempotent evidence processing, DLQs, partial-batch response, canary health, replay through the canonical path, and no automatic task cancellation are explicit.
- **Rollback mechanics:** Schedule-pair disable/drain/update/verify sequencing, pinned version restoration, replay, alarm verification, and delayed cleanup form a credible base, subject to finding 4.

## Required Disposition

Resolve findings 1 through 4 before implementation begins because each affects security, data correctness, or production recoverability. Findings 5 through 10 can be incorporated as narrow invariants, conventions, or readiness gates without changing the selected account-local Cell paradigm.
