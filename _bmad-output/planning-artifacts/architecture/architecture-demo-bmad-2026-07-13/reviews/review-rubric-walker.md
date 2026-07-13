# Architecture Spine Rubric Review - ECS Scheduled Jobs Platform Service

## Gate Verdict

**CONDITIONAL FAIL - not ready for build handoff.** The spine is at the correct initiative/platform altitude and is unusually complete across topology, account/environment isolation, state ownership, CI authority, runtime observability, rollback, and production evidence. However, its core retry/attempt model is internally contradictory, and several other rules do not yet prevent the divergence they claim to prevent: occurrence alerts depend on aggregate alarm transitions, immutable configuration has no retention/compatibility lifecycle, the foundational brokered-launch decision remains unratified, the stated Terraform floor cannot implement the mandated backend lock, and security-group egress is explicitly left variable.

## Checklist Summary

| Good-spine dimension | Judgment | Notes |
| --- | --- | --- |
| Platform altitude | Strong | The account-local Cell, shared/per-job module boundary, process manager, ledger, workflow authority, and operator authority are initiative-level decisions rather than component internals. |
| Enforceability of every AD | Thin | Most rules are concrete, but AD-7 through AD-9, AD-14, AD-15, and AD-17 contain gaps or contradictions that allow materially different implementations. |
| Source capability coverage | Adequate | The capability map covers the full declared FR/NFR range, but retry completion, per-occurrence notification, secret delivery, and supported-version lifecycle are not fully bound by enforceable rules. |
| Operational and environmental envelope | Strong | Account/Region cells, state boundaries, OIDC, deployment separation, cell health, retention seeds, rollback, runbooks, and production evidence are addressed. Recovery of the shared ledger remains underspecified. |
| Deferred/open-item safety | Broken | A-1 leaves the defining direct-target versus brokered-launch choice unratified, and Deferred leaves production security-group egress free to diverge. |
| Named technology currency | Strong | The named Terraform, AWS provider, Lambda Python, Fargate, and GitHub OIDC capabilities are current and available as of 2026-07-13. |
| Brownfield/parent-spine consistency | Not applicable | No parent spine or existing runtime implementation is declared. The repository context is a standards source rather than a brownfield architecture to ratify. |

## Deterministic Pass

`lint_spine.py` completed with zero findings: no placeholders, duplicate AD IDs, missing Binds/Prevents/Rule fields, or mechanically unpinned Stack versions were reported.

## Critical Findings

### C-1: The attempt and occurrence reducers cannot represent a successful retry safely

**Locations:** AD-7 (lines 86-105), AD-8 (lines 107-111), AD-9 (lines 113-117), AD-21 (lines 185-189)

**Problem:** AD-7 says conflicting terminal evidence yields `AMBIGUOUS`, while AD-9 says any nonzero exit or launch failure yields `FAILED`. A permitted retry that fails once and then succeeds therefore produces both failed and successful terminal evidence, but the spine never decides whether the occurrence is `SUCCEEDED`, `FAILED`, or `AMBIGUOUS`. This contradicts AD-21's bounded retry contract and fails the source capability that requires retry completion to be testable.

AD-8 compounds the ambiguity by deriving the ECS `clientToken` from `occurrence_id + attempt_id` without defining how `attempt_id` is allocated or persisted. A handler that generates a new attempt ID after crashing between `RunTask` and ledger recording can launch a duplicate task despite the rule claiming crash-window idempotency. Different teams could implement attempt ID per SQS delivery, per application retry, or per operator action and all claim conformance.

**Required closure:** Define a canonical `TASK_ATTEMPT` model and occurrence reducer. Atomically reserve and persist an attempt ID, client token, config version, and launch status before `RunTask`; reuse that token for infrastructure retries; create a new attempt only after an explicit retry-policy decision. State exactly how failed-then-success, success-then-failure, multiple successes, exhausted retries, operator stops, and replay attempts reduce to occurrence state. Add conformance fixtures for the crash window before and after `RunTask`, every retry sequence, and concurrent duplicate evidence.

## High Findings

### H-1: Alarm state changes cannot guarantee an occurrence-specific notification

**Locations:** AD-14 (lines 143-147), AD-19 (lines 173-177), Consistency Conventions metrics row (line 210)

**Problem:** AD-14 routes only per-job CloudWatch alarm state changes to the Alert Router, while metrics intentionally omit `occurrence_id`. If two occurrences fail in one evaluation period, or a second occurrence fails while the alarm remains in `ALARM`, CloudWatch emits no new state transition that identifies the later occurrence. Even on the first transition, “reads the ledger” does not define which occurrence the router enriches when several are eligible. This does not enforce the rule's stated prevention of “alerts without run context” and can miss required Job Owner notifications.

**Required closure:** Separate occurrence notification from aggregate alarm state. Emit an idempotent occurrence-state-change event from the Process Manager to the Alert Router, keyed by occurrence and notification policy, while retaining bounded CloudWatch alarms for job/Cell health; or specify an equivalent mechanism that proves one correctly enriched notification per required occurrence without high-cardinality metrics. Define deduplication, repeated/consecutive failure behavior, recovery, routing, and notification-delivery failure handling.

### H-2: Immutable CONFIG and shared Cell contracts have no enforceable lifecycle

**Locations:** AD-2 (lines 56-60), AD-5 (lines 74-78), AD-15 (lines 149-153), AD-17 (lines 161-165), AD-18 (lines 167-171), DynamoDB conventions (line 207)

**Problem:** AD-5 makes CONFIG items content-addressed and says Terraform owns them, but does not prohibit Terraform from deleting the prior item when a job changes. Queued evidence, retries, rollback, and replay can still reference the old `config_version`; deletion makes the supposedly immutable launch snapshot unavailable. Schedule changes receive a drain rule in AD-18, but image, command, IAM, subnet, secret-reference, and task-definition changes do not.

The shared Cell also serves independently versioned job modules, yet versioned envelopes and semantic versioning do not define which schema/Cell Contract majors remain supported, producer/consumer deployment order, expand-contract behavior, or downgrade rules. One Cell upgrade could reject still-supported jobs even though the architecture claims a reusable platform contract.

**Required closure:** Make CONFIG versions append-only through a stated replay/rollback horizon, block destructive replacement, and define garbage-collection eligibility from occurrence, queue, DLQ, and recovery evidence. Define the supported Cell Contract and event-schema compatibility window, upgrade sequencing, unknown-version behavior, and rollback/downgrade rules; include mixed-version Cell tests. Preserve every referenced task definition and required launch authority for the same horizon or make an explicit non-replayable terminal state.

### H-3: The spine's defining brokered-launch paradigm is still an open assumption

**Locations:** Design Paradigm (lines 21-23), AD-1 through AD-3 (lines 50-66), Open Assumptions A-1 (line 284)

**Problem:** The entire runtime design depends on Scheduler sending evidence to a shared Cell and the Process Manager brokering `RunTask`, but A-1 says this mechanism still needs approval because it supersedes direct-target wording. Until ratified, separate implementation units can legitimately build direct Scheduler-to-ECS tasks or the brokered Cell. That is the largest divergence point in the document and cannot remain open at build handoff.

**Required closure:** Obtain the named Platform and Product approval, record the brokered path as adopted, and reconcile the source wording before finalizing. If approval is not obtained, the spine must be rewritten around direct launch; it cannot treat both paths as conformant alternatives.

### H-4: The Terraform compatibility floor contradicts the required backend

**Locations:** AD-15 (lines 149-153), Stack and compatibility note (lines 217-227), Open Assumption A-5 (line 288)

**Problem:** AD-15 requires every root to use native S3 `use_lockfile = true`, but the spine retains a Terraform compatibility floor of `>= 1.5`. Native S3 lockfiles were introduced after that floor (Terraform 1.11); a consumer running an allowed 1.5-1.10 CLI cannot initialize the mandated backend. This is a deterministic incompatibility, not something the later test matrix might discover.

**Required closure:** Raise the applicable root compatibility floor to a version that supports `use_lockfile`, or distinguish a higher platform/root CLI floor from a lower child-module language-compatibility floor and provide a different lock mechanism for older roots. Enforce the chosen floor in `required_version`, reusable workflows, and compatibility fixtures.

### H-5: Deferred security-group egress permits incompatible production security postures

**Locations:** AD-13 (lines 137-141), Deferred optional security group item (line 279)

**Problem:** AD-13 requires “minimal security groups,” but Deferred leaves the exact egress contract as an implementation seed. One module can allow all IPv4/IPv6 egress through NAT while another restricts endpoints and workload destinations; both can claim “documented egress.” The rule is therefore not enforceable and does not prevent security drift across jobs or accounts.

**Required closure:** Define the standard inbound/egress contract and exception path. At minimum, prohibit inbound rules, validate VPC/account/Region association, declare whether unrestricted Internet egress is blocked or exception-controlled, specify how required AWS endpoints and workload destinations are represented, and require negative policy fixtures. Configurable destinations may vary; the validation schema and default posture may not.

## Medium Findings

### M-1: Secret delivery is represented only as an opaque reference

**Locations:** AD-5 (lines 74-78), AD-12 (lines 131-135), Consistency Conventions configuration and data-protection rows (lines 211 and 215), Capability Map IAM and secrets row (line 267)

The spine prevents plaintext values from entering CONFIG, messages, state, or plans, but does not decide the supported reference types or which role retrieves each secret. ECS-agent injection through the execution role, application retrieval through the task role, cross-account references, KMS permissions, version selection, rotation behavior, and the previously named third-party secrets option can therefore diverge. Define a versioned secret-reference union, role ownership, KMS/resource-policy constraints, and unsupported modes.

### M-2: Shared Cell recovery is a runbook assertion rather than a recovery architecture

**Locations:** AD-11 (lines 125-129), AD-18 (lines 167-171), AD-19 (lines 173-177), Deferred retention and multi-Region items (lines 277-278)

DynamoDB PITR and queue retention are named, but the spine does not define Cell RPO/RTO, restoring the ledger to a new table, redirecting processors atomically, reconciling events received after the restore point, or rebuilding the expectation horizon. Multi-Region failover can remain deferred, but account-local recovery needs an invariant and a tested restore path because every job depends on the Cell.

### M-3: `LATEST` is valid but weakens the immutable-runtime claim

**Locations:** AD-17 (lines 161-165), Stack (lines 217-227), Deployment Identity coverage in AD-14 and AD-22

AWS currently documents `LATEST` as Linux Fargate platform 1.4.0, but AWS can change the selected platform revision for newly started tasks. The spine should explicitly accept this managed drift, record the resolved task platform version in operational evidence, and define compatibility testing when `LATEST` changes; otherwise “Immutable Supply Chain” overstates what is pinned.

### M-4: Retention defaults lack an enforceable deletion and evidence policy

**Locations:** NFR bindings in AD-19 and AD-22, Deferred retention item (line 278)

The spine seeds log, occurrence, PITR, and queue retention but does not specify TTL ownership, whether evidence used by active retries or investigations overrides TTL, or which audit/deployment records follow a separate organizational retention policy. Add a retention matrix and fail-safe deletion rules tied to active occurrence/config references.

### M-5: Optional dashboard consistency is deferred below the standardization boundary

**Locations:** AD-14 (lines 143-147), Deferred optional dashboard item (line 279)

The exact per-job widget schema is deferred even though a standard optional dashboard is a source capability. Leaving widgets entirely to implementation allows each job module to project a different operating model. Define a minimum stable widget/query set for schedule delivery, launch, runtime, completion, and Cell health; allow additive customization outside that baseline.

## Positive Controls to Preserve

- AD-1 and AD-15 establish clean account/Region and Terraform-state isolation without cross-repository remote-state coupling.
- AD-3 and AD-4 correctly separate expectation from launch and give every occurrence a deterministic identity.
- AD-6's single-writer and evidence-reduction model is the right concurrency invariant once attempt reduction is fixed.
- AD-12 and AD-16 create strong IAM and deployment-authority boundaries, including exact OIDC claims and reusable-workflow binding.
- AD-18, AD-19, AD-21, and AD-22 make rollout, health, rerun, compensation, runbook, and production evidence part of the architecture rather than implementation afterthoughts.

## Technology Verification

- Terraform 1.15.8 is a published stable release; 1.16 entries are alpha builds: [HashiCorp Terraform releases](https://releases.hashicorp.com/terraform/).
- AWS provider 6.54.0 is a published HashiCorp release dated 2026-07-08: [HashiCorp AWS provider v6.54.0](https://github.com/hashicorp/terraform-provider-aws/releases/tag/v6.54.0).
- AWS Lambda supports `python3.14` on Amazon Linux 2023: [AWS Lambda runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).
- ECS accepts `LATEST`; AWS currently maps the Linux platform to 1.4.0: [AWS Fargate platform versions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/platform-fargate.html).
- GitHub supports custom OIDC subject templates containing repository identity, Environment context, and `job_workflow_ref`: [GitHub OIDC reference](https://docs.github.com/en/actions/reference/security/oidc).

## Gate Closure

Resolve C-1 and H-1 through H-5 before build handoff. M-1 and M-2 should be closed before production Cell implementation; M-3 through M-5 can be incorporated into the implementation contract and production-readiness evidence without changing the core paradigm. Re-run the deterministic linter and reviewer gate after the spine is revised.
