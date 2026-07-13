# AWS Security and IAM Review

## Overall Verdict

**CONDITIONAL FAIL - not ready to authorize production implementation.**

The PRD has the right security themes: separate ECS roles, exact `iam:PassRole` resources, private tasks, OIDC, sensitive plan handling, production policy gates, and immutable images. However, several of those controls are stated as outcomes without defining an enforceable trust boundary or acceptance criteria. The most consequential gap is that a consumer repository can potentially change or bypass the reusable workflow and policy checks while the AWS OIDC role still trusts that repository or GitHub Environment. The IAM, state, supply-chain, and multi-account contracts also leave privilege-escalation paths that a compliant-looking implementation could accidentally permit.

Production approval should remain blocked until SEC-01 through SEC-06 are converted into requirements and negative acceptance tests. SEC-07 through SEC-09 should be resolved before the pilot's production-readiness gate.

## Critical Findings

### SEC-01: Production policy enforcement is not bound to the AWS deployment credential

**Severity:** Critical  
**Locations:** PRD FR-20 through FR-23 (§5.5, lines 259-290), FR-25 (lines 300-307), NFR-4 (line 346), Risk "Approval controls depend on GitHub licensing or configuration" (§11, line 460); Addendum "Initial Distribution Pattern" (lines 31-40) and "Research-Backed Architecture Inputs" (lines 65-69).

**Finding:** The document requires a centralized reusable workflow and production gates, but it does not state how AWS proves that an approved workflow and all mandatory gates ran before issuing deployment credentials. An AWS trust policy restricted to repository, ref, and GitHub Environment can still authorize another workflow in that repository. The addendum itself notes that AWS cannot use GitHub custom claims to require a particular reusable workflow. A consumer able to modify the caller workflow could omit scanning, point at a different module, change the role or target, or run arbitrary Terraform while still presenting an allowed OIDC subject. GitHub Environment approval does not by itself attest that the reviewed reusable workflow produced the deployment.

**Required action:** Define a protected deployment control plane and its bypass resistance. At minimum:

- Restrict the production OIDC `sub` to the protected production Environment and accepted repository identity format, and restrict eligible deployment refs through Environment rules and repository/org rulesets.
- Require Platform/Security CODEOWNERS approval for workflow files, Terraform root configuration, production environment mapping, policy exceptions, and module/workflow pins; prevent self-approval and administrator bypass except through the documented emergency path.
- Pin the reusable workflow to a reviewed full commit SHA and make the AWS apply role obtainable only by the protected deployment job. If AWS cannot attest the reusable workflow directly, add a separately controlled broker/deployment repository or equivalent central gate rather than claiming the consumer workflow is unbypassable.
- Separate PR validation, production planning, and production apply identities. The apply identity must not be available to pull-request or arbitrary dispatch jobs.
- Add negative acceptance tests showing that a modified caller workflow, unauthorized workflow file, unapproved ref, fork PR, and skipped policy job cannot obtain production credentials or apply.

GitHub documents that AWS trust should evaluate exact `aud` and `sub` claims, while reusable-workflow enforcement requires deliberate claim/trust design; GitHub also recommends protected Environment rules when Environment subjects are used: [AWS OIDC configuration](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), [OIDC with reusable workflows](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-with-reusable-workflows).

## High Findings

### SEC-02: The IAM contract can pass a no-wildcard check while remaining broadly privileged

**Severity:** High  
**Locations:** PRD FR-10 and FR-11 (§5.3, lines 169-183), FR-21 (lines 267-273), NFR-1 (line 343), stakeholder table (lines 399-405).

**Finding:** FR-11 permits application statements or "approved policy attachments" and FR-21 focuses on wildcard actions/resources. That does not constrain the effective policy. A customer-managed policy can change after review; an AWS-managed policy can be much broader than one job; enumerated IAM, STS, KMS, S3, Secrets Manager, or Organizations actions can still create privilege escalation without using `*`; `NotAction`, broad condition operators, and cross-account resource policies can evade a simple wildcard rule. The PRD also does not establish whether consumers can attach additional policies to module-created roles outside the module.

**Required action:** Make the whole effective permission set the reviewed artifact. Prefer module-owned inline policies or immutable, versioned approved policies; reject mutable external managed-policy attachments by default. Require AWS IAM Access Analyzer policy validation plus platform policy checks for `NotAction`, privilege-management actions, role chaining, resource-policy mutation, KMS grants, and cross-account access. Require a permissions boundary for module-created roles where organizational controls support it, prohibit out-of-band attachments, and test drift. Security approval must be based on effective permissions and conditions, not only wildcard syntax.

### SEC-03: `iam:PassRole` and service trust requirements omit essential condition boundaries

**Severity:** High  
**Locations:** PRD FR-10 (lines 169-175), FR-22 (lines 275-281), NFR-1 (line 343); Addendum Infrastructure Constraints (lines 18-21) and architecture input on roles (line 63).

**Finding:** Exact role ARNs are necessary but insufficient. The PRD does not require `iam:PassedToService` on deployment and Scheduler pass-role permissions, does not define the allowed `ecs:RunTask` cluster/task-definition scope, and does not require service-role trust policies to prevent confused-deputy use. It also does not constrain who may update role trust or attach policies after creation. A conforming implementation could pass the exact task role to an unintended service, let Scheduler run a broader family/revision or cluster target, or create reusable service trust broader than the job.

**Required action:** Add testable IAM matrices for each principal:

- Scheduler execution role: trust only `scheduler.amazonaws.com`, with `aws:SourceAccount` and the narrowest supported `aws:SourceArn`; allow only the intended `ecs:RunTask` task-definition/cluster target and exact task/execution `iam:PassRole` resources with `iam:PassedToService = ecs-tasks.amazonaws.com`.
- ECS task and execution roles: trust only `ecs-tasks.amazonaws.com` with the recommended confused-deputy conditions; keep execution permissions limited to image pull, logs, and exact secret/KMS resources.
- CI plan/apply roles: exact target-account permissions, explicit pass-role resources and `iam:PassedToService`, no ability to alter their own trust, permissions boundary, OIDC provider, or approval controls unless separately approved.

Require negative tests for passing another role, running another task definition or cluster, changing trust, and cross-account role use. AWS recommends resource-scoped `iam:PassRole` and supports the `iam:PassedToService` condition: [Pass a role to an AWS service](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html), [IAM condition keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_iam-condition-keys.html).

### SEC-04: Terraform state and PR plan exposure are outside the required security boundary

**Severity:** High  
**Locations:** PRD FR-12 (lines 185-191), FR-20 (lines 259-265), FR-23 (lines 283-290), NFR-2 and NFR-14 (lines 344 and 362), NFR-15 (line 366), Risk "Saved Terraform Plans expose sensitive data" (line 459).

**Finding:** The PRD protects saved production plan artifacts and prohibits committing state, but never requires a secured remote backend or isolates state by account and Environment. It also says pull requests receive an advisory plan without specifying whether untrusted/fork PR code can access cloud credentials or production state, whether plan output is posted to PR comments, or whether machine-readable plan JSON is retained. Terraform saved plans include prior state and input values; `sensitive = true` only redacts display and does not remove values from plan/state. A malicious Terraform change can also read and exfiltrate provider-visible data during plan.

**Required action:** Require an encrypted, versioned, access-logged remote backend with state locking and separate state/access boundaries per account and Environment. Plan and apply roles must access only their target backend and AWS account. Do not provide cloud/state credentials to fork or otherwise untrusted PR execution; run static validation there and gate trusted plans after approval. Prohibit raw plan/state JSON in PR comments and unrestricted logs, define redaction and artifact ACL/retention/deletion, and add a test containing canary sensitive data. Include state access and recovery in audit and rollback requirements. HashiCorp explicitly treats state and plan files as sensitive and notes that saved plans can contain cleartext sensitive values: [Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data), [`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan).

### SEC-05: Multi-account target selection is consumer-controlled and lacks fail-closed account binding

**Severity:** High  
**Locations:** PRD FR-2 (lines 96-102), FR-22 through FR-24 (lines 275-298), NFR-12 and NFR-13 (lines 360-361), MVP scope (lines 373-381), Risk "Broad IAM or OIDC trust" (line 457).

**Finding:** AWS account, Region, Environment, CI identity, and backend are described as consumer inputs. The PRD does not require a trusted mapping between GitHub Environment, role ARN, backend, expected account ID, Region, and Terraform root. A caller can accidentally or maliciously pair a production approval with the wrong account, reuse non-production state against production, or create cross-account changes not visible in the intended plan. "Account-scoped role" is not an acceptance test.

**Required action:** Store the environment-to-account/Region/role/backend mapping in a protected platform-controlled source rather than ordinary job inputs. Require pre-plan and pre-apply `sts:GetCallerIdentity`/partition/Region checks against immutable expected values, separate OIDC roles and state namespaces per account/Environment, and controlled concurrency keyed by that target. Ensure the saved plan is applied only with the same source revision, backend, workspace, account, Region, provider lock, and role session that were recorded at plan time. Add negative tests for swapped role ARNs, wrong accounts/Regions/backends, and cross-account resource ARNs.

### SEC-06: Supply-chain pinning is advisory and the proposed module pin is mutable

**Severity:** High  
**Locations:** PRD FR-5 (lines 125-131), FR-20 (lines 259-265), FR-24 and FR-25 (lines 292-307), Rollback Principles (lines 441-448); Addendum module source example (lines 31-38) and architecture input on pinning (line 69).

**Finding:** Production image immutability is required, but GitHub Actions, reusable workflows, Terraform providers, and the module source are not production-gated. The example `ref=v1.0.0` is a mutable Git tag, and `AWS provider >= 5.x` is a compatibility constraint rather than a reproducible pin. The phrase "pin release versions" therefore conflicts with the requirement for an exact reviewed deployment identity. Generic "security scanning" does not state image vulnerability/signature policy or action provenance.

**Required action:** Make supply-chain controls part of FR-21/FR-28: pin all third-party actions and reusable workflows to full commit SHAs; restrict allowed actions/workflows at org or repository level; pin the Terraform module to an immutable commit SHA (with a human-readable release annotation); commit and verify provider lock files/checksums for each supported platform; constrain provider versions; and deploy images by digest. Define required dependency/image vulnerability scanning, severity/exception policy, and provenance/signature verification if the organization has an approved signing system. Record every immutable identifier in Deployment Identity. GitHub states that a full commit SHA is the only immutable way to reference an action: [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).

### SEC-07: OIDC trust is not specific enough to be safely implemented

**Severity:** High  
**Locations:** PRD FR-22 (lines 275-281), NFR-4 (line 346), Risk §11 (lines 457 and 460); Addendum OIDC architecture inputs (lines 65-67).

**Finding:** "Restricted trust conditions" and an unauthorized repo/branch test leave key choices open: exact `aud`, exact `sub`, Environment versus ref subject, immutable repository ID format, session duration/name/tagging, fork and pull-request behavior, and prohibition of wildcard subject matching. The addendum recognizes the 2026 immutable subject-format change, but the PRD does not require onboarding to discover and validate the active format. A name-only or wildcard subject can outlive repository transfers or authorize more refs than intended.

**Required action:** Require `aud = sts.amazonaws.com` (or the exact approved audience) and exact production `sub` values tied to protected Environments and the repository's active immutable identity format. Fail onboarding when the claim format is not verified. Prohibit organization-wide/repository-wildcard production subjects; define maximum session duration, attributable session naming, minimal `id-token: write` scope, and no OIDC issuance in untrusted PR jobs. Test repository transfer/rename behavior and rejected branch/tag/environment subjects. GitHub's AWS guidance requires evaluating `sub` and documents the immutable owner/repository ID format introduced for applicable repositories: [Configuring OIDC in AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

## Medium Findings

### SEC-08: Secret references lack a complete authorization, encryption, and rotation contract

**Severity:** Medium  
**Locations:** PRD FR-12 (lines 185-191), NFR-2 (line 344), FR-28 checklist (lines 330-337); Addendum Infrastructure Constraints (line 21).

**Finding:** The module accepts Secrets Manager, SSM, or Infisical references, but it does not distinguish secrets fetched by the ECS agent from secrets fetched by application code, nor define exact KMS permissions, cross-account secret policies, secret version selection, rotation/restart behavior, or validation for ordinary environment inputs that resemble credentials. "Where the provider permits it" is too weak for production. Infisical is named without defining an approved ECS delivery mechanism, which risks plaintext values reaching Terraform.

**Required action:** Define supported reference types and which role reads each one. Require exact secret/parameter ARNs, exact customer-managed KMS key ARNs when used, least-privilege decrypt conditions, and policy checks that reject secret values in ordinary environment variables, command arguments, outputs, logs, and workflow inputs. Document rotation semantics and how tasks receive a new version. Treat third-party secret delivery as unsupported until its mechanism proves that plaintext does not enter GitHub, Terraform configuration, state, or plans. AWS lists the exact Secrets Manager, SSM, and KMS permissions needed by the task execution role: [ECS task execution IAM role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html).

### SEC-09: Private networking checks do not constrain supplied security groups or outbound exfiltration

**Severity:** Medium  
**Locations:** PRD FR-2 (lines 96-102), FR-13 (lines 193-200), FR-21 (lines 267-273), NFR-3 (line 345); Addendum Infrastructure Constraints (lines 16-21).

**Finding:** Disabling a public IP and selecting a "private" subnet do not create a least-privilege network boundary. Consumer-supplied security groups can allow inbound traffic or unrestricted egress, and a private subnet with NAT still permits Internet exfiltration. The production gate blocks "public networking" but does not define route-table, security-group, VPC, or egress validation. The module-created security group promises documented egress but not restricted egress.

**Required action:** Validate that subnets and security groups belong to the expected VPC/account/Region, block inbound rules for scheduled tasks, and define an egress allowlist or recorded exception policy. Require architecture documentation for NAT versus the necessary VPC endpoints, DNS, ECR/S3/logs/secrets access, and workload destinations. Add negative fixtures for mismatched VPCs, public IP assignment, inbound rules, and unrestricted IPv4/IPv6 egress without approval.

## Policy-Exception Observation

FR-21 captures owner, justification, approver, expiry/review date, and audit trail, which is a sound metadata baseline. It does not say where exceptions live or prevent the requester from changing the exception and control in the same PR. The implementation should keep production exceptions in a protected, machine-evaluated registry with Security/control-owner CODEOWNERS, narrow job/account/control scope, compensating controls, hard expiry, and automatic fail-closed behavior. Expired or broadened exceptions need to block planning/apply, and emergency bypass use should generate reviewable evidence and follow-up.

## Required Security Gate Before Production Pilot

1. Resolve SEC-01 through SEC-07 in the PRD/architecture with named controls and negative acceptance tests.
2. Produce principal-by-principal IAM and trust matrices for Scheduler, ECS execution, ECS task, CI plan, and CI apply roles.
3. Threat-model a malicious/compromised consumer repository, action dependency, application image, and job owner; prove the production credential and state boundaries hold.
4. Run bypass tests for workflow modification, policy-gate omission, wrong account/backend, cross-job `RunTask`, alternate role passing, mutable dependency refs, untrusted PR planning, and expired exceptions.
5. Retain review evidence from IAM Access Analyzer/policy scanning, GitHub rules and Environment configuration, OIDC trust evaluation, state/backend controls, image/dependency scans, and CloudTrail deployment events.

