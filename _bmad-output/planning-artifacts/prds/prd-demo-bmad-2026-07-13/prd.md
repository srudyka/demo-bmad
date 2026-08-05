---
title: ECS Scheduled Jobs Platform Service
status: final
created: 2026-07-13
updated: 2026-08-05
---

# PRD: ECS Scheduled Jobs Platform Service

## 0. Document Purpose

This PRD defines an internal platform capability that standardizes ECS Scheduled Jobs across AWS Accounts and Environments. It is intended for Platform Engineering, DevOps, SRE, Application Teams, Security, and downstream architecture and delivery owners. Implementation constraints and research sources are preserved in [addendum.md](addendum.md).

## 1. Vision

Engineering teams should be able to deploy a production-ready ECS Scheduled Job by declaring job-specific behavior, not by reconstructing the surrounding AWS and delivery controls. The Platform Service provides one supported path for scheduling, task execution, identity, logging, failure detection, deployment governance, and operations across AWS Accounts and Environments.

The product bet is that a transparent, opinionated module and delivery standard will reduce setup time and infrastructure drift while improving security and incident response. The Platform Service is more than a Terraform Module: documentation, review gates, release management, alarms, operational ownership, and rollback are part of the product. The Platform Service should hide repetitive wiring without hiding permissions, failure semantics, or operational responsibilities. A supported non-production deployment path must make the complete Cell-to-ECS flow observable in a real AWS environment before production adoption is considered.

## 2. Problem and Goals

### 2.1 Problem

Teams currently copy or independently design Terraform for ECS task definitions, schedules, IAM Roles, logs, alarms, and GitHub Actions. The resulting variation creates broad permissions, incomplete observability, inconsistent delivery controls, unclear deployed versions, duplicated maintenance, and weak ownership or rollback guidance.

### 2.2 Product Goals

- Reduce the time and specialist ECS knowledge needed to launch a Scheduled Job.
- Make least-privilege permissions, private networking, immutable workload identity, and secret references explicit and reviewable.
- Produce consistent logs and actionable detection for schedule-delivery, task-launch, task-runtime, and job-completion failures.
- Make deployments reproducible and attributable across AWS Accounts and Environments.
- Establish a versioned, supported operational standard that teams can adopt without copy-paste drift.
- Deliver a practical first version suitable for production use without becoming a general workflow orchestrator.

## 3. Target Users and Operating Workflows

### 3.1 Primary Users

- **Platform Engineer / DevOps Engineer:** maintains the Platform Service and reviews platform-impacting changes.
- **Application Engineer:** declares a Scheduled Job and owns its application behavior, permissions, image, success contract, and operational response.
- **SRE / On-call Engineer:** responds to alarms and diagnoses failures using Deployment Identity, logs, task events, and the Runbook.

### 3.2 Secondary Users

- Security and compliance reviewers who evaluate IAM, secret handling, networking, and policy exceptions.
- Engineering managers and Cloud Infrastructure Owners who need adoption, ownership, and production-readiness visibility.

### 3.3 Jobs To Be Done

- Define and deploy a new Scheduled Job through a small, documented configuration surface.
- Review the exact permissions, schedule, networking, alarms, image identity, and production impact before deployment.
- Promote the same job pattern across Environments and AWS Accounts without hardcoded identifiers.
- Determine what version is deployed, whether a run was invoked, whether its ECS Task started, and whether it completed successfully.
- Diagnose and recover from failed, late, duplicate, or missing executions using a standard Runbook.
- Upgrade or roll back the Platform Service without guessing about breaking changes.

### 3.4 Core Workflows

1. An Application Engineer declares a Scheduled Job, supplies Existing Infrastructure and job-specific inputs, and opens a pull request.
2. CI validates formatting, module contracts, examples, security controls, and the proposed Terraform Plan.
3. Platform Engineering and the Application Team review the change; Security joins when IAM or networking policy requires it.
4. An approved workflow deploys an exact reviewed revision to the target Environment and records Deployment Identity.
5. The Platform Service invokes the ECS Task, captures logs and lifecycle outcomes, and routes actionable production failures.
6. An On-call Engineer follows the Runbook to identify the failed plane, rerun safely, or roll back.
7. A Platform Engineer deploys the Platform Cell and one scheduled-job consumer into a disposable non-production Environment, verifies a real occurrence end to end, and destroys only that disposable Environment through a separate protected workflow when the demonstration is complete.

## 4. Glossary

- **AWS Account** — A workload account in which an instance of the Platform Service resources is deployed.
- **Deployment Identity** — The auditable combination of source revision, module version, workflow revision, container image digest, target AWS Account and Environment, and ECS task-definition revision.
- **Environment** — A deployment stage such as dev, staging, or prod, mapped to an AWS Account and Region by the consumer.
- **Existing Infrastructure** — Consumer-managed dependencies supplied to the Terraform Module, including the ECS Cluster, VPC, private subnets, security groups, notification target, CI identity, and secret references.
- **Functional Requirement (FR)** — A stable, testable product capability defined in this PRD.
- **Job Completion Contract** — The occurrence-aware rules by which an Expected Occurrence is correlated with job start and exactly one Completion Result before its deadline.
- **Completion Result** — The occurrence-correlated outcome reported by a Scheduled Job, including timing, status, exit code, and optional error reason.
- **Expected Occurrence** — One planned execution derived from a schedule, with a canonical scheduled time and completion deadline.
- **Occurrence ID** — A unique identifier that binds an Expected Occurrence to its ECS Task start, Completion Result, retries, alarms, and operational evidence.
- **Job Owner** — The Application Team accountable for application behavior, data effects, permissions, idempotency, Runbook specifics, and incident response.
- **Platform Service** — The complete supported product: Terraform Module, reusable delivery pattern, policy gates, documentation, examples, release lifecycle, and operational standards.
- **Platform Owner** — Platform Engineering / DevOps, accountable for the Platform Service and its standards.
- **Production Readiness Checklist** — The mandatory evidence that a Scheduled Job meets production security, delivery, observability, ownership, and rollback requirements.
- **Runbook** — Job-specific operating instructions created from the standard template.
- **Scheduled Job** — A containerized batch or maintenance workload launched on ECS Fargate according to a declared schedule.
- **Terraform Module** — The versioned infrastructure interface through which consumers declare a Scheduled Job.

## 5. Features and Functional Requirements

### 5.1 Declarative Job Contract

**Description:** A consumer declares the behavior and resource needs of one Scheduled Job while reusing Existing Infrastructure. The contract stays portable across AWS Accounts and Environments and exposes important operational settings rather than hiding them.

#### FR-1: Declare a Scheduled Job

An Application Engineer can declare a Scheduled Job using documented inputs for name, container image, schedule, CPU, memory, command or entrypoint overrides, environment variables, secret references, permissions, runtime expectations, tags, and ownership.

**Consequences (testable):**
- A complete example can be configured without modifying the Terraform Module source.
- Every required input has a description, validation where meaningful, and an example.

#### FR-2: Consume Existing Infrastructure

An Application Engineer can supply the AWS Account, Region, Environment, ECS Cluster, VPC, private subnets, security groups, image, notification target, CI identity, and secret references without the Platform Service duplicating those dependencies.

**Consequences (testable):**
- The Terraform Module does not require hardcoded account IDs, Regions, ARNs, or Environment names.
- Missing or invalid required dependency inputs fail during validation or planning with an actionable message.

#### FR-3: Apply Standard Identity and Tags

The Platform Service applies predictable resource names and required Environment, Application, Service, Owner, ManagedBy, and applicable CostCenter and Repository tags.

**Consequences (testable):**
- Resource names follow the documented `<environment>-<application>-<component>` convention unless an AWS service constraint requires a documented transformation.
- Production planning fails when mandatory ownership metadata is absent.
- Tag merging cannot silently override protected platform tags with empty or conflicting values.

#### FR-4: Expose Operational Outputs

The Terraform Module exposes the identifiers needed for operations and integrations, including schedule, ECS task definition, log group, IAM Roles, alarms, and Deployment Identity components created by the module.

**Consequences (testable):**
- Every output is documented and has a description.
- A consumer can locate the deployed job's schedule, logs, task definition, and alarms without inspecting Terraform state directly.

### 5.2 Scheduling and ECS Execution

**Description:** The Platform Service provisions the ECS Fargate execution path and makes delivery, retry, timing, and overlap semantics explicit. [ASSUMPTION A1: EventBridge Scheduler is the version-one scheduling baseline; legacy EventBridge scheduled rules are not created.]

#### FR-5: Provision the ECS Task Definition

The Platform Service creates an ECS Fargate task definition with explicit CPU, memory, network mode, platform compatibility, container image, logging, command settings, environment configuration, and separate execution and task IAM Roles.

**Consequences (testable):**
- Invalid CPU and memory combinations fail validation before apply.
- Production configurations reject mutable image tags such as `latest` and require an immutable tag or digest.

#### FR-6: Provision the Schedule

The Platform Service creates a schedule with a declared expression, optional time zone, enabled state, invocation role, retry behavior, and target ECS Task configuration.

**Consequences (testable):**
- The schedule can be disabled without deleting the task definition or log history.
- The deployed schedule and time zone match the reviewed configuration.
- The job contract declares the supported expression type, flexible-window behavior, time-zone and daylight-saving semantics, and a canonical Expected Occurrence with a completion deadline; flexible windows are disabled by default.
- The Platform Service creates or propagates a unique Occurrence ID for every Expected Occurrence and makes it available to the Scheduled Job and observability path.

#### FR-7: Define Delivery and Retry Semantics

An Application Engineer can configure supported retry attempts and event age and must acknowledge that delivery can occur more than once.

**Consequences (testable):**
- Documentation distinguishes schedule-delivery retries from ECS Task or application retries.
- Each production Scheduled Job declares its idempotency or duplicate-handling expectation in the Runbook.

#### FR-8: Define Runtime and Overlap Semantics

Each Scheduled Job declares its expected maximum runtime and whether overlapping runs are safe; the Job Owner documents any required application locking or idempotency.

**Consequences (testable):**
- A production configuration cannot omit expected runtime or overlap policy.
- Version one treats maximum runtime as a completion deadline used for overdue detection and response, not as a guarantee of forced termination; enforced cancellation is deferred.
- An overlap-unsafe production job cannot deploy without tested application idempotency or locking; schedule cadence alone is not accepted as overlap prevention.

#### FR-9: Support Controlled Manual Reruns

The Platform Service documentation provides a repeatable manual rerun procedure that preserves Deployment Identity and requires the operator to consider duplicate effects.

**Consequences (testable):**
- The Runbook template includes rerun prerequisites, command or workflow steps, authorization, verification, and rollback or compensating action.
- Manual reruns use the reviewed task definition and do not require editing the schedule.

### 5.3 Identity, Secrets, and Networking

**Description:** The Platform Service standardizes least-privilege boundaries while leaving application-specific access explicit. It accepts private networking and approved secret references as Existing Infrastructure.

#### FR-10: Separate IAM Responsibilities

The Platform Service creates or configures separate schedule-invocation, ECS task-execution, and application-task IAM Roles with only the permissions required for each responsibility.

**Consequences (testable):**
- `iam:PassRole` is scoped to the exact roles required for the Scheduled Job.
- Application permissions are not attached to the ECS task execution role.
- Scheduler trust is restricted by service principal, source AWS Account, and schedule-group source ARN; ECS task trust is restricted by service principal and source AWS Account using the narrowest supported source ARN.
- Scheduler `ecs:RunTask` access is restricted to the intended task-definition family and ECS Cluster, and `iam:PassRole` includes the appropriate `iam:PassedToService` condition.

#### FR-11: Declare Application Permissions Explicitly

An Application Engineer can supply reviewable application IAM statements or approved policy attachments for the task IAM Role.

**Consequences (testable):**
- Production checks block wildcard actions or resources unless an exception includes written justification and approval.
- The generated effective policy can be inspected in the Terraform Plan and validated by IAM Access Analyzer or an equivalent policy-analysis gate for actions, resources, conditions, privilege escalation, and cross-account access rather than wildcard syntax alone.
- Application permissions are generated from explicit inline statements by default; customer-managed policy attachments require an approved allowlist, same-account ownership, and policy-version change governance so they cannot drift outside review.

#### FR-12: Reference Secrets Safely

An Application Engineer can reference approved secrets without placing secret values in Git, ordinary Terraform input variables, plan output, or job documentation.

**Consequences (testable):**
- The module accepts secret references rather than plaintext secret values.
- Task execution permissions are scoped to the exact referenced resources where the provider permits it.

#### FR-13: Require Private Task Networking

The Platform Service launches production ECS Tasks in consumer-supplied private subnets and minimally scoped security groups, with public IP assignment disabled.

**Consequences (testable):**
- Production checks block public IP assignment and public-subnet configurations detected by policy.
- By default, consumers supply security group IDs; when explicitly enabled, the Terraform Module can create a dedicated minimally scoped security group with no inbound rules and documented egress.
- Documentation states the required NAT or VPC endpoint reachability for images, logs, secrets, and job dependencies.

### 5.4 Observability and Failure Detection

**Description:** The Platform Service separates four failure planes: schedule delivery, ECS Task launch, ECS Task runtime, and Job Completion Contract. A green schedule invocation is not treated as proof of successful job completion.

#### FR-14: Retain Structured Job Logs

The Platform Service creates a per-job CloudWatch log group with explicit retention and makes it discoverable from module outputs and the Runbook.

**Consequences (testable):**
- Production checks block absent logging or unspecified retention.
- The Job Owner documents recognizable start, successful-completion, and failure log events without exposing secrets. Every signal includes the Occurrence ID; examples use a structured success marker such as `JOB_COMPLETED_SUCCESSFULLY job_name=example-job occurrence_id=2026-07-13T10:00:00Z`.

#### FR-15: Detect Schedule-Delivery Failures

The Platform Service provides alarms or standard integrations for EventBridge Scheduler target errors, throttling, dropped invocations, and supported delivery failure signals.

**Consequences (testable):**
- A simulated or test schedule-delivery failure reaches the configured non-production test destination.
- The alarm identifies the affected schedule group or job context and links to the Runbook.

#### FR-16: Detect ECS Launch and Runtime Failures

The Platform Service detects tasks that fail to launch, stop unexpectedly, or stop with a non-zero essential-container exit code.

**Consequences (testable):**
- Test evidence covers at least task-start failure and non-zero exit scenarios.
- Test evidence proves detection when ECS `RunTask` returns HTTP 200 with a non-empty `failures` array and no ECS Task exists to emit a lifecycle event.
- A normal completion with a zero exit code does not create a failure alarm.

#### FR-17: Detect Missing or Late Completion

Production missed-run detection must be occurrence-aware. The Platform Service correlates each Expected Occurrence with its job start and exactly one Completion Result. A success log marker can be an input signal, but it is not the sole source of truth and must carry the matching Occurrence ID. If no valid Completion Result exists by the configured completion deadline, the Platform Service marks the Expected Occurrence overdue or missed and triggers the configured production alert.

**Consequences (testable):**
- For every Expected Occurrence, the platform can report one of these states: expected; started; completed successfully; failed; overdue or missed; or duplicate or ambiguous completion.
- Each occurrence record includes job name, Occurrence ID, scheduled time, start time when available, completion time when available, status, exit code when available, and optional error reason.
- Late signals, retries, duplicate completions, and signals from adjacent occurrence windows cannot satisfy the wrong Expected Occurrence silently; ambiguity creates an actionable state.
- Production jobs cannot claim missed-run coverage based only on native Scheduler metrics, an uncorrelated log marker, or a time-window count.
- Pilot tests cover a missing invocation, `RunTask` failure, failure before success emission, overdue execution, delayed prior-run completion, duplicate completion, wrong Occurrence ID, successful execution, retry completion, and consecutive schedule windows.
- During MVP, non-production jobs may use best-effort metric-filter alarms without occurrence-aware tracking when clearly labeled as non-production coverage.

#### FR-18: Route Actionable Alerts

An Application Engineer can supply the existing notification target for production failures; alerts include job, Occurrence ID where applicable, Environment, AWS Account, failure plane, occurrence state, detection time, and the Runbook location.

**Consequences (testable):**
- Production deployment is blocked without an alert destination. [ASSUMPTION A2: The destination is an existing organization-standard SNS or incident integration supplied per Environment; Platform Engineering / DevOps on-call receives pilot alerts when no application-specific support policy exists.]
- Dev and staging alarms can be disabled or routed to a low-noise engineering destination.

#### FR-19: Provide Optional Operational Views

An Application Engineer can enable a standard CloudWatch dashboard or equivalent view without making it mandatory for every job.

**Consequences (testable):**
- The view distinguishes schedule delivery, ECS Task outcomes, and completion status.
- Disabling the view does not disable required production alarms.

### 5.5 Delivery, Governance, and Lifecycle

**Description:** The Platform Service supplies a reusable GitHub Actions delivery pattern with explicit review and policy gates. Plans, approvals, applies, releases, and rollbacks remain reproducible and auditable.

#### FR-20: Validate Changes in Pull Requests

The delivery pattern runs Terraform formatting, initialization without a production backend, validation, module and example tests, security scanning, and an advisory Terraform Plan for pull requests.

**Consequences (testable):**
- Terraform formatting and validation failures and obvious secret exposure block merge in every Environment from MVP start.
- The workflow distinguishes Terraform validation from security and policy analysis.
- Untrusted pull-request code never receives AWS credentials or access to protected Terraform state; any cloud-backed plan runs only in an authorized trusted context.

#### FR-21: Enforce Production Policy Gates

Production delivery blocks missing tags, unjustified IAM wildcards, public networking, missing logs or alarms, mutable images, plaintext secret inputs, and missing ownership metadata.

**Consequences (testable):**
- Each blocking policy has a test fixture that proves compliant and noncompliant behavior.
- Exceptions require an owner, a justification, an approver, an expiry or review date, and an audit trail.
- CI role tests prove that plan/apply identities cannot create IAM users or access keys, alter their own trust or policies, modify the GitHub OIDC provider, pass unrelated roles, remove required permissions boundaries, create administrator-equivalent policies, or change protected state-backend controls.

#### FR-22: Authenticate CI Without Long-Lived Credentials

Deployment workflows assume account- and Environment-scoped AWS IAM Roles using GitHub OIDC with restricted trust conditions and minimal workflow permissions.

**Consequences (testable):**
- No long-lived AWS access key is required or documented.
- A workflow from an unauthorized repository, branch, tag, or Environment cannot assume the deployment role.
- An immutable deployment-target manifest binds each Environment to its approved AWS Account, Region, and role; the workflow verifies the assumed account and Region before planning or applying and does not accept an arbitrary production role from consumer input.
- Production credentials are available only to a protected deployment path after mandatory checks: either a dedicated deployment repository or organization/repository rules that require the approved reusable workflow and protected Environment. If GitHub cannot enforce either path, production deployment is not authorized.
- Plan and apply use separate roles. The apply role is constrained by SCPs and/or a required permissions boundary to the platform-managed resource namespace; IAM creation and `iam:PassRole` are limited to module-owned roles with that boundary, and neither role can alter its own authorization path.

#### FR-23: Separate Plan, Approval, and Apply

Production delivery creates a fresh plan from the deployment revision, pauses at an approval gate, and applies that exact saved plan under controlled concurrency.

**Consequences (testable):**
- Approval requires Platform Engineering and the Job Owner; qualifying IAM or networking changes require Security review.
- Saved plans are never committed, are access-restricted, have short retention, and are treated as sensitive artifacts.
- Administrator bypass is disabled for production workflows except through a documented, auditable emergency process.
- Remote state is encrypted, locked where supported, isolated by AWS Account and Environment, and accessible only to the corresponding scoped plan/apply roles; plan content is redacted from unrestricted logs and PR comments.

#### FR-24: Record Deployment Identity and Rollback Evidence

Every deployment records enough Deployment Identity to identify exactly what ran and provides a rollback procedure appropriate to the change.

**Consequences (testable):**
- An On-call Engineer can map an ECS Task to its image digest, task-definition revision, source revision, module version, target, and workflow run.
- A production change cannot proceed without rollback or forward-fix instructions and post-change verification.

#### FR-25: Version and Deprecate the Platform Service

The Platform Owner releases the Terraform Module and reusable workflow contract using semantic versioning and documents deprecation and migration behavior.

**Consequences (testable):**
- Breaking input, output, or behavior changes require a major version and migration notes.
- [ASSUMPTION A3: The current major version and one previous major version receive support; deprecated inputs are documented before removal.]
- [ASSUMPTION A8: The Terraform Module is published from an internal GitHub repository, reusable workflows are published from a centralized platform repository, consumers pin immutable release references, and upgrade notices use GitHub releases plus an internal engineering channel.]
- Production consumers pin third-party Actions and reusable workflows to full commit SHAs and pin the Terraform Module to an immutable registry version or commit; human-readable release tags are recorded but are not trusted as immutable references.
- Consumer root configurations commit a reviewed provider dependency lock file, and production initialization verifies it read-only; unexpected provider selection or checksum changes block deployment.

### 5.6 Documentation and Operations

**Description:** Documentation and operational readiness ship with the product rather than as follow-up work.

#### FR-26: Provide Adoption Documentation and Examples

The Platform Service includes a README, input and output reference, security guidance, architecture prerequisites, and working examples for at least one non-production and one production configuration.

**Consequences (testable):**
- A team unfamiliar with ECS scheduling can deploy the pilot by following the documentation without modifying module internals.
- Examples pass the same format, validation, and security checks as the module.
- `versions.tf` and the README state the tested Terraform, AWS provider, and Fargate compatibility matrix.

#### FR-27: Provide a Job Runbook Template

The Platform Service provides a Runbook template covering ownership, schedule, expected runtime, success contract, alarms, log and task-event queries, common failures, safe reruns, escalation, rollback, and dependency checks.

**Consequences (testable):**
- Every production pilot has a completed Runbook reviewed by Platform Engineering and the Job Owner.
- A reviewer can trace each alarm to a diagnosis and response step.

#### FR-28: Enforce Production Readiness

The Platform Service provides a Production Readiness Checklist that is completed before a Scheduled Job enters production.

**Consequences (testable):**
- The checklist covers IAM, secrets, networking, immutable images, logs, retention, all four failure planes, ownership, deployment approval, rollback, and Runbook evidence.
- Completion evidence includes format and validation results, security-scan results, example validation, representative plan impact, tested alarms, and documented known limitations.
- Failure-injection tests detect every required failure scenario across schedule delivery, `RunTask` response handling, launch, runtime, and completion within five minutes of the observable failure or declared deadline, with zero false alerts across at least 20 accelerated successful schedule windows.
- Incomplete mandatory items block production deployment or require a recorded exception.

#### FR-29: Deploy a Real Non-Production Environment

Platform Engineering can deploy the Platform Cell and one configured ECS Scheduled Job consumer into a real, disposable non-production AWS Environment using the supported Terraform modules and an immutable workload image. [ASSUMPTION A12: The first real deployment is disposable non-production only.]

**Consequences (testable):**
- The deployment path creates or configures all resources owned by the Platform Cell and scheduled-job consumer, while clearly identifying prerequisites and externally owned resources.
- The deployment uses the existing Cell ownership boundary and does not use `terraform_remote_state` or mutate shared Cell state from the consumer root.
- The initial deployment keeps the schedule disabled until the required Cell Contract acknowledgement and non-production readiness evidence are available.
- The deployment records the target Account, Region, source revision, module versions, image digest, Terraform root, workflow run, and resulting resource identifiers as bounded evidence.

#### FR-30: Source Configuration and Secrets Safely

The deployment path sources non-secret configuration from GitHub Actions workflow inputs, variables, and protected GitHub Environment configuration, and sources sensitive values from an approved Infisical integration. [ASSUMPTION A13: Infisical is the approved sensitive-configuration source for this demonstration.]

**Consequences (testable):**
- The PRD and implementation define which values belong in GitHub configuration versus Infisical, including precedence and missing-value behavior.
- GitHub-to-Infisical authentication uses short-lived or otherwise approved machine identity; long-lived credentials are not committed or exposed in logs.
- Secret values never appear in Terraform plans, artifacts, workflow summaries, state, repository files, or unmasked output.
- Secret rotation and revocation can occur without changing committed Terraform or workflow source, subject to the task's documented rollout behavior.

#### FR-31: Provide a Protected Non-Production Deploy Workflow

An authorized operator can manually start a non-production deployment workflow that validates the target, creates a Terraform plan, requires protected approval, applies only the approved plan, and publishes verification evidence. [ASSUMPTION A14: The workflow is manually triggered and protected by GitHub Environment approval.]

**Consequences (testable):**
- The workflow uses GitHub OIDC and account/Environment-scoped AWS roles with least privilege; no long-lived AWS access key is required.
- Formatting, dependency locks, Terraform validation, policy checks, target identity, and immutable image checks run before protected AWS mutation.
- Plan and apply are separate stages with controlled concurrency, explicit timeout, and no automatic mutation retry.
- Verification covers Cell Contract publication, Scheduler configuration, ECS task launch, task completion, logs, retry behavior, alarms, and DLQ behavior.
- The workflow cannot target production through operator-supplied account, Region, role, root, or Environment values.

#### FR-32: Provide a Protected Non-Production Destroy Workflow

An authorized operator can manually destroy a disposable non-production deployment through a separate workflow without destroying production or shared protected Cell resources. [ASSUMPTION A15: Destroy is limited to explicitly labeled disposable non-production targets.]

**Consequences (testable):**
- Destruction requires explicit confirmation, target identity validation, and protected Environment approval.
- The workflow rejects production targets, shared Cell resources, protected state, retained evidence, and resources governed by `prevent_destroy` unless a separate approved lifecycle process exists.
- Required deployment, verification, and failure evidence is preserved before destruction.
- Partial failure produces recovery guidance and never triggers an automatic retry or broad cleanup.

## 6. Cross-Cutting Non-Functional Requirements

### 6.1 Security

- **NFR-1:** Production resources use least-privilege IAM, separate roles, restricted trust policies, and no unjustified wildcard actions or resources.
- **NFR-2:** Secrets never appear in source control, normal Terraform variable values, unrestricted logs, PR comments, saved plans exposed to unauthorized readers, or documentation.
- **NFR-3:** Production ECS Tasks use private networking with public IP assignment disabled.
- **NFR-4:** CI uses short-lived OIDC credentials and minimal `GITHUB_TOKEN` and AWS permissions.

### 6.2 Reliability and Operability

- **NFR-5:** The product documents at-least-once delivery and requires per-job idempotency or duplicate-effect handling.
- **NFR-6:** Alarms must be actionable: they identify failure plane, ownership, Environment, and Runbook, and must be tested before production acceptance.
- **NFR-7:** Platform changes have reproducible deployment and documented rollback or forward-fix procedures.
- **NFR-8:** No production job is considered observable solely because logs exist or the schedule invocation succeeded.
- **NFR-9:** Occurrence state is durable and queryable for the job's operational investigation window, and state transitions are idempotent so duplicate signals cannot overwrite a terminal result silently.

### 6.3 Maintainability and Compatibility

- **NFR-10:** Terraform interfaces are explicit, documented, validated, and backward-compatible within a major version.
- **NFR-11:** The Terraform Module follows the repository's standard module structure and includes executable examples and focused automated tests.
- **NFR-12:** [ASSUMPTION A4: The repository's current tested compatibility seed is Terraform 1.15.8 with Terraform `>= 1.10, < 2.0`, AWS provider 6.54.0 with provider `>= 6.0, < 7.0`, Python 3.14.6, and the repository-approved Fargate platform/runtime values; architecture and implementation must confirm the final matrix.]
- **NFR-13:** The Platform Service avoids account-, Region-, repository-, and Environment-specific hardcoding.
- **NFR-14:** [ASSUMPTION A10: MVP validation covers one to five Scheduled Jobs across one non-production and one production AWS Account in the organization's primary Region; architecture must not prevent later expansion to dozens of jobs.]
- **NFR-15:** The repository never commits Terraform state, saved plans, `.terraform/`, credentials, or generated secret material; normal infrastructure workflows do not use provisioners or `null_resource`.

### 6.4 Auditability and Cost

- **NFR-16:** Production plans, approvals, exceptions, apply operations, Deployment Identity, and rollback evidence are attributable to an actor and retained according to organizational policy.
- **NFR-17:** Optional views and retention defaults must not create unbounded cost; cost-impacting defaults are documented and configurable within platform guardrails.
- **NFR-18:** Non-production deployment and destruction are auditable, repeatable, target-scoped, and fail closed when identity, approval, secret, state, or readiness evidence is missing.
- **NFR-19:** Infisical integration and GitHub Environment configuration use least-privilege access, explicit ownership, rotation guidance, masking, and bounded diagnostic output; secret retrieval failure prevents mutation rather than substituting an unsafe default.

## 7. Scope

### 7.1 MVP In Scope

- One reusable Terraform Module for ECS Fargate Scheduled Jobs.
- EventBridge Scheduler-based invocation with schedule, time zone, retry, and enablement controls.
- ECS task definition, task execution wiring, separate IAM Roles, secret references, and private networking inputs.
- CloudWatch logs with explicit retention and production alarms across the four failure planes.
- Occurrence-aware production tracking that correlates Expected Occurrences, ECS Task starts, Completion Results, retries, deadlines, and ambiguity states without prescribing the storage or reporting mechanism.
- Optional standard CloudWatch dashboard support.
- Reusable or example GitHub Actions workflows for validation, policy scanning, plan, approval, and apply.
- A protected non-production deployment workflow that provisions the Platform Cell and one scheduled-job consumer, plus a separate protected destroy workflow for disposable environments.
- GitHub Environment and Infisical configuration boundaries, authentication, rotation, masking, and audit guidance.
- A real non-production end-to-end demonstration proving Cell publication, scheduled delivery, ECS launch, structured completion, logs, alarms, retries, and DLQ behavior.
- Standard tags, outputs, Deployment Identity, semantic versioning, and compatibility guidance.
- README, examples, security guidance, Runbook template, rollback guidance, and Production Readiness Checklist.
- Multi-account and multi-Environment consumption without centralized cross-account orchestration.

### 7.2 Non-Goals for MVP

- A self-service UI or internal developer portal.
- Kubernetes CronJobs or cross-cloud execution.
- A general workflow orchestrator, real-time scheduler, or enterprise scheduler replacement.
- Complex dependencies between Scheduled Jobs or Step Functions orchestration.
- Creation or lifecycle management of application secrets.
- Centralized approvals outside GitHub.
- Automatic remediation of failed jobs.
- Migration of every existing Scheduled Job during the first release.
- Mandatory centralized dashboards, cost reporting, or external incident integrations.
- SQS dead-letter queue behavior; it remains a future enhancement unless implementation proves trivial and does not complicate the module interface.
- Production activation, production destruction, and a general-purpose multi-Environment destroy capability are excluded from this deployment demonstration.
- Infisical project administration, secret creation, enterprise policy administration, and organization-wide secret migration are excluded; the capability consumes approved secret paths and identities.
- Guaranteed prevention of overlapping runs; the Job Owner retains application-level idempotency or locking responsibility.

## 8. Stakeholders and Approvals

| Decision or artifact | Accountable | Required reviewers |
|---|---|---|
| Platform Service product and standards | Platform Owner | Platform Engineering / DevOps |
| Scheduled Job application behavior and Runbook | Job Owner | Application Team, On-call owner |
| Production deployment | Job Owner and Platform Owner | Platform Engineering plus Application Team |
| Qualifying production IAM or networking change | Platform Owner | Security, Platform Engineering, Application Team |
| Policy exception | Platform Owner | Security or designated control owner, plus Job Owner |
| Breaking Platform Service release | Platform Owner | Platform Engineering and representative consumers |
| Non-production AWS target and state | Cloud Infrastructure Owner | Platform Owner, Security, Job Owner |
| GitHub Environment and OIDC controls | Platform Owner | Security, Cloud Infrastructure Owner |
| Infisical project, identity, and secret paths | Secret Owner | Security, Platform Owner, Job Owner |

## 9. Success Metrics

### 9.1 Primary Metrics

- **SM-1: Basic job setup time** — Median elapsed time from ready inputs to a deployable basic Scheduled Job is under four hours and at least 50% lower than the validated baseline. Validates FR-1, FR-2, FR-20, FR-26. [ASSUMPTION A5: The current baseline is one to three engineering days.]
- **SM-2: New-job adoption** — 100% of new ECS Scheduled Jobs use the Platform Service after pilot acceptance, excluding approved exceptions. Validates FR-1 through FR-28. [ASSUMPTION A6: This becomes policy immediately after pilot acceptance.]
- **SM-3: Production control coverage** — 100% of production jobs deployed through the Platform Service have required tags, immutable images, retained logs, alert destinations, tested failure detection, Deployment Identity, and a completed Runbook. Validates FR-3, FR-5, FR-14 through FR-18, FR-24, FR-27, FR-28.

### 9.2 Secondary Metrics

- **SM-4: Pilot delivery** — One or two low-risk internal jobs reach production within one sprint after MVP completion and pass the Production Readiness Checklist. Validates FR-20 through FR-28. [ASSUMPTION A7: Exact pilot jobs and application owners are not yet selected; Platform Engineering / DevOps owns candidates until owners are assigned before pilot execution.]
- **SM-5: Security review quality** — No pilot or post-pilot production job ships with an unapproved IAM wildcard, plaintext secret, public task networking, or mutable image; repeated IAM and observability review findings trend downward release over release. Validates FR-10 through FR-13, FR-21, NFR-1 through NFR-4.
- **SM-6: Operability coverage** — Every production failure alarm maps to a Runbook response, and every pilot failure test produces enough context to identify its failure plane and Deployment Identity. Validates FR-15 through FR-18, FR-24, FR-27.
- **SM-7: Drift reduction** — New jobs do not copy unmanaged task, schedule, IAM, logging, or alarm Terraform outside the Platform Service without an approved exception. Validates FR-1 through FR-4, FR-25.
- **SM-8: Observability escape rate** — Track incidents or failed runs in which missing logs, alarms, completion signals, or ownership delayed detection or diagnosis; the target is zero for pilot and post-pilot jobs. Validates FR-14 through FR-18, FR-27, FR-28.
- **SM-9: Real-environment demonstration** — One disposable non-production Environment provisions the Platform Cell and one scheduled-job consumer, completes at least one successful occurrence, demonstrates one controlled failure/retry path, and produces bounded evidence for every required verification plane. Validates FR-29 through FR-31.
- **SM-10: Safe teardown** — 100% of demonstration destroy attempts either remove only the approved disposable target or fail before mutation; no production, shared Cell, protected state, or retained evidence is destroyed. Validates FR-32 and NFR-18.

### 9.3 Counter-Metrics

- **SM-C1: Exception rate** — Track approved bypasses and exceptions; adoption is not successful if teams routinely bypass the standard because the contract is too rigid. Counterbalances SM-2 and SM-7.
- **SM-C2: Alert noise** — Track false-positive and unactionable alarms per production job; broader detection must not create ignored alerts. Counterbalances SM-3 and SM-6.
- **SM-C3: Deployment lead time** — Track time waiting on validation and approvals; stronger gates must not turn a basic low-risk deployment into a multi-day process. Counterbalances SM-3 and SM-5.
- **SM-C4: Change failure rate** — Track Platform Service upgrades that require emergency rollback or break consumers; faster adoption must not reduce release stability. Counterbalances SM-1 and SM-2.

## 10. Rollout and Change Management

1. **MVP verification:** Validate the module, examples, policy fixtures, failure simulations, documentation, versioning, and rollback path without credentials, then deploy the Platform Cell and one scheduled-job consumer to a disposable non-production AWS Environment.
2. **Real-environment demonstration:** Use the protected deploy workflow to verify Cell publication, disabled-then-qualified scheduling, ECS launch, structured completion, logs, alarms, retries, and DLQ behavior. Use the separate destroy workflow only after evidence is retained.
3. **Pilot:** [ASSUMPTION A7] Select one or two low-risk, non-customer-facing cleanup, maintenance, reporting, data-sync, or internal batch jobs. Platform Engineering / DevOps owns candidates until a named Job Owner is assigned before execution.
4. **Production acceptance:** Complete the Production Readiness Checklist, execute failure tests, validate alert routing, perform a rollback rehearsal or tabletop, and obtain required approvals. The demonstration workflow does not authorize production activation.
5. **New-job standardization:** [ASSUMPTION A6] Require the Platform Service for all new ECS Scheduled Jobs, with documented time-bound exceptions.
6. **Non-production enforcement:** Terraform formatting and validation failures and obvious secret exposure are blocking from MVP start. [ASSUMPTION A11: Other dev and staging policy findings are advisory during MVP; after pilot acceptance, missing tags become blocking in non-production, and within one or two adoption sprints, staging also blocks IAM wildcards, missing retention or alarms, and mutable images.]
7. **Gradual migration:** Migrate existing jobs when they are materially changed, when a risk is identified, or when the owning team schedules improvement work; do not force wholesale migration in MVP.
8. **Feedback and release:** Measure setup time, review findings, alarm quality, exceptions, and upgrade issues; feed results into minor releases and a documented roadmap.

### Rollback Principles

- Pin module, workflow, provider, and image versions needed to reproduce a known-good deployment.
- Preserve prior task-definition revisions and configuration long enough to restore the known-good job.
- For schedule-only failures, disable or restore the schedule independently of deleting logs or task definitions.
- For application data effects, the Job Owner documents compensating action; infrastructure rollback alone may not reverse job side effects.
- Each production Runbook declares a recovery-time objective appropriate to the job schedule and validates that rollback or forward-fix steps can meet it.
- Verify restored scheduling, execution, logs, alarms, and Deployment Identity after rollback.

## 11. Risks and Mitigations

| Risk | Impact | Mitigation required by this PRD |
|---|---|---|
| Schedule invocation is mistaken for job success | Silent business failure | Separate delivery, launch/runtime, and completion detection; FR-15 through FR-17 |
| Native Scheduler metrics cannot prove an individual missed run | False assurance | Require a per-job Job Completion Contract; FR-17 |
| `RunTask` returns HTTP 200 with failures and creates no task | Launch failure is invisible to task-state monitoring | Require response-path detection and failure injection; FR-16 |
| At-least-once delivery causes duplicate effects or overlap | Data corruption or repeated work | Explicit retry, overlap, idempotency, and rerun requirements; FR-7 through FR-9 |
| Broad IAM or OIDC trust expands access | Cross-job or cross-account compromise | Separate roles, scoped `iam:PassRole`, restricted OIDC trust, blocking policy checks; FR-10, FR-11, FR-21, FR-22 |
| A consumer bypasses the approved reusable workflow while using the same OIDC trust | Mandatory gates are bypassed | Bind production credentials to a protected deployment path and reject production use when controls cannot be enforced; FR-22 |
| Private tasks cannot reach images, logs, secrets, or dependencies | Tasks fail to start or operate | Treat egress/endpoints as documented prerequisites and validate private launch settings; FR-13 |
| Saved Terraform Plans expose sensitive data | Secret or state disclosure | Restricted short-lived artifacts and no repository storage; FR-23, NFR-2 |
| Approval controls depend on GitHub licensing or configuration | Production changes bypass intended review | [ASSUMPTION A9] Use protected Environments where supported; otherwise require PR approval, branch protection, status checks, manual production approval, and an auditable emergency process |
| Module abstraction hides important behavior | Unsafe adoption and difficult diagnosis | Keep permissions, retries, runtime, overlap, success contract, outputs, and Runbook explicit |
| Alerting becomes noisy | On-call ignores real failures | Test alarms, require actionable context, measure SM-C2 |
| Compatibility or upgrades break consumers | Adoption stalls or jobs drift | Semantic versioning, pinned consumption, deprecation, migration notes, and rollback; FR-25 |
| Infisical or GitHub configuration is missing, stale, or over-scoped | Deployment leaks secrets or applies the wrong target | Separate non-secret and secret inputs, short-lived identity, masking, rotation, preflight validation, and fail-closed retrieval; FR-30, NFR-19 |
| Destroy workflow removes shared or protected resources | Loss of platform state, evidence, or other environments | Separate workflow, explicit non-production target binding, confirmation, approval, deny-by-default resource classes, and pre-destroy evidence; FR-32 |
| Real AWS prerequisites are incomplete | Demonstration fails for reasons unrelated to the module | Make Account, Region, state, network, cluster, ECR, Cell, notification, Infisical, and OIDC prerequisites explicit before implementation; FR-29, OQ-8 through OQ-13 |

## 12. Open Questions

1. **OQ-1 — owner: Platform Owner; resolve before pilot execution:** Which one or two low-risk jobs will be used in the pilot, and which named Job Owners will accept operational responsibility?
2. **OQ-2 — owner: Platform Owner; resolve before production pilot:** What exact production notification target and escalation policy will the pilot use?
3. **OQ-3 — owner: Platform Owner; resolve before pilot:** Which exact Terraform, AWS provider, and Fargate platform versions pass compatibility testing and become the documented supported matrix?
4. **OQ-4 — owner: Platform Owner; resolve before consumer release:** What are the exact module repository, reusable-workflow repository, access policy, and engineering announcement channel?
5. **OQ-5 — owner: Platform Owner; resolve before production delivery:** Does the organization's GitHub plan and configuration support the assumed approval controls, or must the equivalent fallback controls be used?
6. **OQ-6 — owner: Cloud Infrastructure Owner; resolve before MVP testing:** What primary AWS Region and account pair will host validation, and do they satisfy the assumed MVP scale?
7. **OQ-7 — owner: Platform Owner; resolve before pilot evaluation:** What measured setup-time and review-finding baseline from two or three recent jobs replaces the initial estimates?
8. **OQ-8 — owner: Cloud Infrastructure Owner; resolve before architecture:** Which non-production AWS Account, Region, Terraform root, backend bucket/key/lock boundary, and state-retention policy will host the demonstration?
9. **OQ-9 — owner: Platform Owner; resolve before implementation:** Will the demonstration deploy the Platform Cell and scheduled-job consumer from one coordinated root or from separate roots with an explicit dependency and promotion order?
10. **OQ-10 — owner: Security and Secret Owner; resolve before implementation:** Which Infisical project/environment, machine identity, authentication method, secret paths, rotation policy, and audit boundary are approved? No values are required in the PRD.
11. **OQ-11 — owner: Platform Owner; resolve before implementation:** Which GitHub Environments, required reviewers, OIDC subjects, workflow repositories, and deployment role manifests are approved for the demonstration?
12. **OQ-12 — owner: Job Owner; resolve before implementation:** What container image digest, command, schedule, test data, expected completion record, controlled failure mode, and idempotency behavior will prove the real task works?
13. **OQ-13 — owner: Platform Owner; resolve before implementation:** Which Cell resources must survive demonstration teardown, and what retained evidence and logs must be preserved before destroy?

## 13. Assumptions Index

- **A1 (§5.2):** EventBridge Scheduler is the version-one baseline; legacy scheduled rules are excluded. **Owner:** Platform Owner. **Revisit:** architecture kickoff.
- **A2 (FR-18):** Consumers supply an organization-standard notification target; Platform Engineering / DevOps on-call receives pilot alerts when no application policy exists. **Owner:** Platform Owner. **Resolve:** before production pilot.
- **A3 (FR-25):** The current major module version and one previous major version receive support. **Owner:** Platform Owner. **Resolve:** before first consumer release.
- **A4 (§6.3):** The repository's current tested compatibility seed is Terraform 1.15.8 with Terraform `>= 1.10, < 2.0`, AWS provider 6.54.0 with provider `>= 6.0, < 7.0`, Python 3.14.6, and repository-approved Fargate platform/runtime values. **Owner:** Platform Owner. **Resolve:** before pilot.
- **A5 (SM-1):** Current setup time is one to three engineering days. **Owner:** Platform Owner. **Replace:** with measured data before pilot evaluation.
- **A6 (SM-2, rollout):** All new ECS Scheduled Jobs must use the Platform Service after pilot acceptance. **Owner:** Platform Owner. **Confirm:** at pilot acceptance.
- **A7 (SM-4, rollout):** One or two low-risk internal jobs enter the pilot within one sprint; Platform Engineering / DevOps owns the pilot candidates until named Job Owners are assigned. **Owner:** Platform Owner. **Resolve:** before pilot execution.
- **A8 (FR-25):** Internal GitHub repositories publish the module and reusable workflows; consumers pin immutable release references and receive GitHub plus internal-channel notices. **Owner:** Platform Owner. **Resolve:** before consumer release.
- **A9 (§11):** GitHub protected-Environment controls are available; equivalent auditable controls apply otherwise. **Owner:** Platform Owner. **Resolve:** before production delivery.
- **A10 (§6.3):** MVP validates one to five jobs in one non-production and one production AWS Account in the primary Region. **Owner:** Cloud Infrastructure Owner. **Resolve:** before MVP environment testing.
- **A11 (§10):** Non-production policy gates beyond always-blocking Terraform validity and obvious secret exposure phase in after pilot acceptance. **Owner:** Platform Owner. **Revisit:** at pilot acceptance and again after one to two adoption sprints.
- **A12 (FR-29):** The first real deployment is disposable non-production only; production activation remains blocked until the existing readiness and protected delivery controls are complete. **Owner:** Platform Owner. **Resolve:** before implementation.
- **A13 (FR-30):** Infisical is the approved sensitive-configuration source for the demonstration, while GitHub Environments provide non-secret configuration and deployment controls. **Owner:** Security and Secret Owner. **Resolve:** before implementation.
- **A14 (FR-31):** The deploy workflow is manually triggered and protected by GitHub Environment approval; it does not grant production access. **Owner:** Platform Owner. **Resolve:** before implementation.
- **A15 (FR-32):** Destroy is limited to explicitly labeled disposable non-production targets and never removes shared Cell foundations or retained evidence by default. **Owner:** Cloud Infrastructure Owner. **Resolve:** before implementation.
