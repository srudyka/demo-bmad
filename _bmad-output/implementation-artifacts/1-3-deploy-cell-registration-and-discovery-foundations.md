---
baseline_commit: 51bca7d70d384c1fa5052a9abebab261254a5757
---

# Story 1.3: Deploy Cell Registration and Discovery Foundations

Status: done

## Story

As a Platform Engineer,
I want an encrypted account-Region foundation for job ownership, immutable configuration, and Cell discovery,
so that jobs can register safely without accessing platform Terraform state or premature runtime resources.

## Acceptance Criteria

1. **Given** an approved AWS account, Region, Environment, encryption configuration, retention policy, and standard tags
   **When** the Platform Cell module is planned
   **Then** it creates only account- and Region-local registration, CONFIG, and discovery resources with predictable names and protected tags
   **And** account IDs, Regions, Environment names, ARNs, notification targets, and KMS keys are supplied or derived rather than hardcoded.

2. **Given** repositories must not claim arbitrary job identities
   **When** the namespace registry is created
   **Then** its key design and documented conditional-write contract support canonical Environment/Application namespace ownership, full job reservation, immutable repository/root/apply-role binding, owner generation, transfer state, and tombstones
   **And** duplicate, cross-namespace, stale-generation, and unauthorized ownership mutations are represented by deterministic conditional failures.

3. **Given** job roots publish secret-free CONFIG candidates
   **When** the CONFIG inbox is created
   **Then** it is an encrypted, versioned, public-blocked S3 bucket with the canonical job-scoped, content-addressed key `jobs/<job_id>/config/<config_version>.json` and lifecycle behavior compatible with validation, replay, investigation, and rollback horizons
   **And** its policy denies insecure transport, unencrypted writes, noncanonical keys, cross-prefix writes, and writes from principals that have not received registration-derived authorization.

4. **Given** validated CONFIG must be isolated from job Terraform authority
   **When** the configuration registry is created
   **Then** it is physically separate from namespace ownership and future occurrence state, encrypted at rest, protected by production PITR where applicable, and documented for immutable `PK=JOB#<job_id>`, `SK=CONFIG#<config_version>` lookup
   **And** no job, consumer workflow, or application principal receives direct permission to write, overwrite, or delete registry records.

5. **Given** operational metadata has bounded retention and cost requirements
   **When** lifecycle settings are applied
   **Then** inputs require a finite compatible retention policy and protect referenced CONFIG from destructive expiration
   **And** invalid, unbounded, or policy-incompatible retention values fail planning with an actionable message.

6. **Given** consumers must discover the Cell without cross-repository state coupling
   **When** the foundation is applied
   **Then** it publishes a JSON-Schema-valid Cell Contract at `/platform/ecs-scheduled-jobs/<environment>/<region>/contract` with Cell, account, Region, semantic version, available resource identifiers, supported ranges, metric namespace, encryption reference, and a verified checksum
   **And** consumers can validate identity and compatibility without `terraform_remote_state` or direct platform-state access.

7. **Given** later stories add Cell integrations
   **When** the Cell Contract or Terraform implementation evolves
   **Then** its canonical SSM address, schema/version/checksum rules, resource addresses, and backward-compatible discovery behavior are preserved
   **And** a resource-address change includes a reviewed `moved` block or explicit migration procedure.

8. **Given** this foundation changes
   **When** repository validation runs
   **Then** the Cell module and `modules/ecs-scheduled-job-platform/examples/basic` pass formatting, backend-free initialization, validation, contract tests, and security scans for encryption, public access, tags, PITR, retention, policy scope, and state separation
   **And** tests prove that no runtime ledger, alert outbox, notification ledger, or producer queues are created.

9. **Given** a foundation deployment must be rolled back
   **When** the documented rollback is followed
   **Then** the previous compatible module version and Cell Contract can be restored without deleting ownership or CONFIG evidence
   **And** production data resources use deletion protection or equivalent safeguards so rollback does not become destructive cleanup.

## Tasks / Subtasks

**Development entry gate:** Start from reviewed baseline `51bca7d`. Confirm the worktree is clean or identify unrelated user changes before editing. Preserve the Terraform and contract lock/checksum fixes from the prior story; do not regenerate locks casually.

- [x] 1. Replace the platform Cell skeleton with the strictly scoped foundation interface (AC: 1, 5, 7)
  - [x] In `modules/ecs-scheduled-job-platform/{main,variables,outputs}.tf`, add only the inputs, locals, resource declarations, and operational outputs necessary for namespace registration, CONFIG storage/registry, and SSM discovery. Keep `versions.tf` constraints unchanged: Terraform `>= 1.10, < 2.0`, AWS provider `>= 6.0, < 7.0`.
  - [x] Require descriptive, validated inputs for environment, application/service/owner, Cell ID, supplied KMS key ARN, finite CONFIG retention policy, production recovery/deletion safeguards, metric namespace, contract version/ranges, and consumer tags. Derive account ID and Region from AWS provider data only where required for the contract; do not accept or hardcode deployment identity values.
  - [x] Use the existing `<environment>-<application>-<component>` convention for stable names and build protected tags in locals. Require nonempty `Environment`, `Application`, `Service`, `Owner`, and set `ManagedBy = Terraform`; module-required tags override consumer collisions. Include `CostCenter` and `Repository` when supplied.
  - [x] Keep stable, meaningful resource addresses. Record a migration procedure or add `moved` blocks if an address must change while implementing this story.
  - [x] Add useful outputs only: Cell ID, namespace registry table ARN/name, CONFIG inbox bucket ARN/name, configuration registry table ARN/name, SSM contract parameter ARN/name, metric namespace, and contract checksum/version. Do not expose secret values or platform state details.

- [x] 2. Create the namespace registry as a Cell-owned conditional-write substrate, not a Registrar runtime (AC: 1, 2, 4, 8, 9)
  - [x] Provision a dedicated KMS-encrypted DynamoDB namespace registry with predictable name, protected tags, deletion safeguards, and production PITR controlled by an explicit validated policy input rather than an implicit string comparison alone.
  - [x] Define and document the table key/item shapes for namespace authorization and job reservations: canonical Environment/Application namespace, full `job_id`, immutable repository ID, Terraform root ID, apply-role immutable ID, account, Region, owner, owner generation, transfer state, approver evidence, and tombstone state. Do not add a Lambda, API, queue, or direct application writer in this story.
  - [x] Specify the future Registrar's exact DynamoDB conditional expressions/expected error codes for duplicate reservation, cross-namespace claim, stale owner generation, unauthorized principal, transfer, and tombstone reuse. The table foundation must make these checks representable; Story 2.1 owns registration execution.
  - [x] Do not grant job, workflow, or application principals table mutation authority. No IAM role or broad bucket/table policy should be invented merely to simulate future runtime behavior.

- [x] 3. Provision the immutable CONFIG inbox with enforceable, staged authorization (AC: 1, 3, 5, 8, 9)
  - [x] Create a dedicated S3 bucket with supplied KMS SSE, versioning enabled, all four public-access-block settings, bucket-owner-enforced object ownership, no public ACLs/policies, no `force_destroy`, protected tags, and an explicit lifecycle rule for incomplete multipart uploads.
  - [x] Make `jobs/<job_id>/config/<config_version>.json` the one canonical CONFIG publication key. Reconcile the stale `contracts/v1/catalogs/ownership.json` key shape (`jobs/<job-id>/<config-version>.json`) to this convention; update the contract manifest/release snapshot/migration classification as Story 1.2 requires. Do not retain ambiguous aliases.
  - [x] Add a resource policy that explicitly denies non-TLS requests, SSE-KMS writes that omit or use a different supplied key, writes outside the canonical `jobs/` CONFIG shape, and access outside a writer's registered job prefix. Use a viable authorization bridge: the foundation is deny-by-default and later Registrar-issued, prefix-scoped role/session bindings establish authorized writers. Do not claim that an S3 resource policy can query DynamoDB dynamically.
  - [x] Keep content-addressed current CONFIG objects and registry-referenced evidence non-destructively retained. A generic S3 lifecycle rule cannot determine whether CONFIG is referenced; it may only clean incomplete uploads and, if proven safe, noncurrent versions beyond an explicit compatible horizon. Story 1.15 owns registry-aware garbage collection. Reject attempts to configure current-version expiration or unbounded/invalid values.
  - [x] Do not create a bucket access point unless an approved architecture/contract change explicitly introduces it. The adopted discovery interface is SSM, not an S3 Cell Contract access point.

- [x] 4. Create the separate configuration registry with immutable lookup and recovery controls (AC: 1, 4, 5, 8, 9)
  - [x] Provision a second, separately named KMS-encrypted DynamoDB table for validated CONFIG. It must not share a table with namespace ownership or future occurrence state and must use stable key attributes compatible with `PK=JOB#<job_id>` and `SK=CONFIG#<config_version>`.
  - [x] Enable point-in-time recovery and deletion protection/equivalent safeguards when the validated production protection policy requires them. Do not add a TTL that can expire a referenced CONFIG record. Explain the recovery limitation that DynamoDB PITR restores to a new table and requires runbook-controlled reconstruction of safeguards/tags.
  - [x] Ensure the Terraform resource graph and any policies grant no direct job-root, consumer-workflow, or application write/update/delete authority. Later materialization and lifecycle roles are out of scope and must not be created here.

- [x] 5. Publish and verify the canonical SSM Cell Contract (AC: 1, 6, 7, 8, 9)
  - [x] Publish an encrypted `aws_ssm_parameter` at exactly `/platform/ecs-scheduled-jobs/<environment>/<region>/contract`; use the supplied KMS key and a documented compatible parameter tier/size constraint. Its value must contain no secrets and only identifiers for resources introduced in this story.
  - [x] Generate a `cell-contract.schema.json`-valid payload with `schema_version`, `contract_version`, `cell` identity, canonical discovery path, a nonempty `integrations` map of Cell-owned foundation resource ARNs, metric namespace reservation, KMS ARN, supported ranges from `contracts/v1/catalogs/compatibility.json`, and checksum.
  - [x] Establish one normative checksum rule: lowercase SHA-256 over RFC 8785/JCS bytes of the complete Cell Contract with `checksum` omitted. Add a fixture/vector and semantic verifier under the existing `contracts/` test tooling. Terraform must not silently treat arbitrary `jsonencode` output as JCS; constrain and test the generated payload's JSON values or use an approved, reproducible mechanism that yields the exact canonical bytes.
  - [x] Reconcile `contracts/v1/catalogs/ownership.json` so `cell-contract-publication` describes the SSM discovery contract required by AD-15, not the currently stale S3 access-point ARN shape. Update all required manifest hashes/release snapshot and migration documentation according to the Compatibility Package rules.
  - [x] Publish only foundations that exist: namespace registry, CONFIG inbox, and configuration registry. Do not fabricate ledger, queue, processor, alert, ECS, or job-root identifiers just to satisfy a contract field.

- [x] 6. Wire a complete, non-secret basic example and documentation (AC: 1, 5, 6, 7, 9)
  - [x] Update `modules/ecs-scheduled-job-platform/examples/basic/{main,variables,outputs}.tf` to exercise all required inputs with unmistakably fictitious non-secret values and no credentials, provider credentials, state backend, or account-specific deployment settings. Retain an independently valid root and lock file.
  - [x] Update the platform-module README with required providers, all inputs/outputs, ownership boundary, CONFIG path and retention behavior, namespace conditional-write semantics, SSM discovery/compatibility validation, encryption/IAM assumptions, deliberate absence of runtime resources, validation commands, and non-destructive rollback/recovery steps.
  - [x] Update root README and `docs/runbooks/README.md` only as needed to replace the resource-free bootstrap claim with this foundation's scope, validation, operational ownership, and rollback notes. Preserve BMad customization and existing repository safety boundaries.

- [x] 7. Add proof-oriented tests and preserve credential-free CI behavior (AC: 2-8)
  - [x] Replace the all-modules resource-free assertion in `tests/contract/test_repository_structure.py` with a narrow Cell-foundation allowlist and explicit deny-list. Preserve the per-job module's resource-free boundary at this stage and reject `terraform_remote_state`, backends, runtime ledger, alert outbox, notification ledger, queues/DLQs, Lambda/processors, ECS/task/schedule resources, alert/notification integrations, and unexpected IAM resources.
  - [x] Add static/module-contract tests for required tags; KMS encryption; S3 versioning, ownership controls, public-access block, `force_destroy = false`, TLS/KMS/canonical-prefix policy denies; separate registry tables; production PITR/deletion protection; finite retention validations; SSM canonical path; Cell Contract JSON-Schema/semantic checksum/range validation; and no plaintext secret-shaped values.
  - [x] Test namespace schema/conditional-operation definitions for duplicate, cross-namespace, stale-generation, unauthorized, transfer, and tombstone cases without calling AWS. Test generated contract fixtures using the strict local parser and local-only JSON Schema registry from Story 1.2.
  - [x] Update documentation tests so the platform module is allowed to own this specific foundation but continues to state its non-claims. Do not weaken tests into broad string or resource exemptions.
  - [x] Preserve `scripts/validate.py` credential scrubbing, temporary `TF_DATA_DIR`, `-backend=false`, `-lockfile=readonly`, dynamic Terraform-root discovery, Checkov, and checkout hygiene. Add no network/AWS-dependent test path.
  - [x] Run `terraform fmt -check -recursive`, backend-free `terraform init -lockfile=readonly` and `terraform validate` for both modules and both examples, `ruff format --check runtime scripts tests`, `./scripts/validate.sh`, and `git diff --check`. If any provider lock changes are required, regenerate all four lock files with both `darwin_arm64` and `linux_amd64` hashes, then rerun locked validation.

### Review Findings

- [x] [Review][Patch] Remove the out-of-scope EventBridge publication [modules/ecs-scheduled-job-platform/main.tf:319] — removed the S3 EventBridge notification; runtime integration remains deferred.
- [x] [Review][Patch] Preserve immutable and referenced CONFIG evidence [modules/ecs-scheduled-job-platform/main.tf:324] — removed noncurrent expiration and require `If-None-Match: *` for content-addressed CONFIG publication.
- [x] [Review][Patch] Specify the namespace conditional-write protocol [modules/ecs-scheduled-job-platform/README.md:76] — documented canonical item shapes, DynamoDB conditions, and deterministic failure mapping.
- [x] [Review][Patch] Enforce and prove Cell Contract compatibility semantics [modules/ecs-scheduled-job-platform/variables.tf:85] — constrained the Cell contract version and added path/range/checksum semantic validation with an independent foundation fixture.
- [x] [Review][Patch] Bound the Standard-tier SSM contract payload [modules/ecs-scheduled-job-platform/main.tf:389] — added a documented 4 KiB Standard-tier precondition.
- [x] [Review][Patch] Validate that the supplied KMS key is local to the Cell Region [modules/ecs-scheduled-job-platform/variables.tf:51] — added Cell-Region preconditions to every encrypted foundation resource.
- [x] [Review][Patch] Allow authorized multipart aborts without relaxing encryption enforcement [modules/ecs-scheduled-job-platform/main.tf:42] — scope encryption-header denies to `PutObject` only.
- [x] [Review][Patch] Enforce canonical CONFIG object access and key shape [modules/ecs-scheduled-job-platform/main.tf:26] — enforce a fixed-length content-hash filename and registered-prefix access restrictions for reads, writes, and deletes.
- [x] [Review][Patch] Narrow the Checkov replication exception to this Cell bucket [scripts/validate.py:217] — split security scans so only the platform Cell path excludes `CKV_AWS_144`.

## Dev Notes

### Developer Context

This is the first story permitted to create Cell AWS infrastructure. It establishes the account/Region-local registration, immutable CONFIG, and discovery foundations. It does **not** implement a runnable Cell or a scheduled job.

The contract from Story 1.2 is normative. Reuse its schemas, catalogs, strict parser, local `$ref` registry, manifest, release snapshot, migration classification, and RFC 8785 helper rather than duplicating version/range/checksum rules in Terraform tests or documentation. Any contract correction is a compatibility change and must update its inventory/release evidence.

The direct prior baseline is `51bca7d` (`style: format contract conformance tests`). It includes the Linux provider lock checksum repair and formatting correction. Review Story 1.3 separately from Story 1.2; do not fold unrelated contract or CI cleanup into this change.

### Scope Boundary

In scope:

- The Cell-owned namespace registry and its documented conditional-write data contract.
- The KMS-encrypted, versioned, private CONFIG inbox.
- The physically separate KMS-encrypted CONFIG registry.
- SSM Cell Contract publication and its compatibility/checksum verification.
- Foundation example, focused static/contract tests, README/runbook updates, and rollback guidance.

Out of scope:

- Registrar implementation or application/job identity reservation execution (Story 2.1).
- CONFIG validation/materialization and registry writes (Story 2.6).
- Runtime ledger, occurrence state, alert outbox, notification ledger, queues/DLQs, Lambda/processors, EventBridge, ECS tasks, schedules, logs, CloudWatch metrics/alarms, networking, task/IAM roles, alert destinations, or any application principal.
- Registry-aware CONFIG deletion or garbage collection (Story 1.15).
- Terraform remote-state access, an internal UI, secret lifecycle, and automatic remediation.

### Required Design Decisions

- **Ownership:** Platform Engineering's Cell root owns the three foundation resources and Cell Contract. Per-job roots consume the published SSM contract and later write only content-addressed objects in their own authorized CONFIG prefix. Neither root reads or mutates the other's Terraform state/resources.
- **Cell locality:** one Cell per AWS account and Region. Derived account/Region metadata is valid; hardcoded deployment identifiers are not.
- **Registry separation:** namespace reservation and validated CONFIG are two tables. The future occurrence ledger is a third table and must not appear in this story.
- **Namespace authority:** a table alone cannot authenticate a writer. This story defines the storage/key/conditional-failure substrate. The later Registrar owns authenticated evaluation and issuance of prefix-scoped authority.
- **S3 authority:** an S3 bucket policy cannot query DynamoDB. Enforce transport/encryption/canonical-key deny rules now, default unknown writers to deny, and model registration-derived access through later Registrar-managed prefix-scoped roles/session tags. Do not falsely document dynamic DynamoDB policy evaluation.
- **Retention:** architecture gives defaults for logs/occurrences/queues, not a safe destructive CONFIG expiry. CONFIG and its references are append-only while needed for validation, replay, investigation, rollback, or compatibility. Do not expire current CONFIG; only a later registry-aware lifecycle process may remove proven-unreferenced versions.
- **Recovery:** non-destructive rollback means reverting to a compatible module and restoring a compatible SSM contract without deleting S3/DynamoDB evidence. DynamoDB PITR restores to a new table; runbooks must require review/reapplication of tags, policies, PITR, deletion protection, streams/TTL if ever present, then controlled contract cutover.
- **Contract evolution:** retain the exact canonical SSM path and compatible `schema_version`/`contract_version` rules. Use additive `integrations` entries for later Cell capabilities; do not publish fictitious resources. Address changes require `moved` blocks or explicit migration documentation.

### AWS And Terraform Guardrails

- Require an approved external KMS key ARN for S3, both tables, and SecureString SSM publication. Do not create a default or ungoverned key.
- S3 must use `BucketOwnerEnforced`, block all public access, enabled versioning, explicit encryption, and `force_destroy = false`. The policy must use an explicit TLS deny and KMS/key condition. Never use public principals or broad access grants.
- DynamoDB must be on-demand unless a reviewed capacity reason is introduced; it must be encrypted and tagged. Production recovery/deletion safeguards are controlled by explicit validated inputs, never guessed solely from a label.
- Keep all variables and outputs described. Validate identifiers, ARNs, finite retention, compatible protection settings, required tags, metric namespace, and supported SemVer ranges. Do not use `null_resource`, provisioners, provider aliases for a hidden account, plaintext secrets, or Terraform state/data sources that couple roots.
- The module adds data resources only for locally derived provider identity. Static tests must still prohibit `terraform_remote_state` and future runtime data/resources.

### Contract Corrections Required Before Completion

1. The adopted architecture requires SSM discovery, but `contracts/v1/catalogs/ownership.json` currently records `cell-contract-publication` as an S3 access point. Correct it to the SSM contract integration and update manifest/release/migration evidence.
2. The adopted CONFIG path is `jobs/<job_id>/config/<config_version>.json`, while the ownership catalog omits `config/`. Correct the catalog and ensure the resource policy, docs, examples, and tests use only the canonical path.
3. The Cell Contract schema presently validates only a checksum shape. Add a normative checksum exclusion rule, canonical fixture, and recomputation test: SHA-256 over RFC 8785/JCS bytes of the complete contract with `checksum` omitted. Do not accept a decorative checksum.

### Project Structure Notes

```text
modules/
  ecs-scheduled-job-platform/
    main.tf                         # Cell foundation resources only
    variables.tf                    # described and validated foundation inputs
    outputs.tf                      # discovery and operational identifiers
    versions.tf                     # preserve >=1.10,<2 and AWS >=6,<7
    README.md
    examples/basic/
      main.tf
      variables.tf
      outputs.tf
contracts/
  manifest.json                     # update only if normative artifacts change
  releases/1.0.0.json               # update/reclassify only if required by package rules
  migrations/v1.0.0.md
  v1/catalogs/ownership.json        # resolve discovery/path inconsistencies
  v1/fixtures/...                   # Cell Contract checksum vector if added
tests/contract/
  support/contracts.py              # reuse/extend strict contract helpers
  test_repository_structure.py      # Cell allowlist and runtime deny-list
  test_documentation.py             # revise bootstrap-only non-claims
  test_*.py                         # focused foundation/contract static tests
docs/runbooks/README.md
README.md
```

The existing `modules/ecs-scheduled-job` skeleton remains resource-free. Do not introduce an environment root, `.tfvars`, Terraform backend, generated plan/state, credentials, or an alternative module layout.

### Testing Requirements

- Tests must be credential-free, local, deterministic, and independent of a deployed AWS account.
- Validate Cell Contract schema documents and values with `Draft202012Validator` and the package's explicit local reference registry; remote schema retrieval is a failure.
- Prove generated SSM contract identity/path/version/range/checksum semantics against checked-in fixtures. Do not calculate both expected and actual values with the same unverified helper.
- Prove no secret-shaped field/value enters Terraform defaults, examples, contract, policy, or test fixture. Examples may contain unmistakably fake structural ARNs only where Terraform validation needs an ARN shape.
- Test one-below/at/one-above finite retention and protection policy boundaries. Include negative tests for a current-version CONFIG expiration and incompatible production recovery setting.
- Keep Checkov enabled and resolve security checks with resource configuration where possible; a suppression must be narrow, justified inline, and covered by a compensating test.
- Terraform validation must keep all four roots independently initialized with `-backend=false -lockfile=readonly`. The Linux CI provider cache is checksum-sensitive; regenerate provider locks for both macOS ARM and Linux AMD64 if and only if a lock update is required.

### Documentation And Rollback Requirements

- Explain that this foundation creates no scheduler, ECS workload, logs, metrics, alarms, notification target, or job runtime. Those are later stories, not an observability exception.
- Document who supplies KMS/retention/protection values, how consumers read/validate the SSM contract, the CONFIG key convention, how ownership authorization will be established, and the recovery limitations.
- Document a rollback that reverts only to a compatible module/contract version, validates the prior contract before publication, and retains S3/DynamoDB evidence. Never prescribe `terraform destroy`, S3 version deletion, table deletion, or a destructive lifecycle workaround as routine rollback.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-2]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-5]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-15]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-23-to-AD-25]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#AD-28-to-AD-29]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#Security-and-operations-review]
- [Source: contracts/v1/schemas/cell-contract.schema.json]
- [Source: contracts/v1/catalogs/compatibility.json]
- [Source: contracts/v1/catalogs/ownership.json]
- [Source: _bmad-output/implementation-artifacts/1-2-publish-canonical-compatibility-contracts.md]
- [Source: _bmad-output/project-context.md]
- [Source: _bmad/custom/standards/aws-terraform-implementation.md]
- [AWS S3 bucket policy examples](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-bucket-policies.html)
- [AWS S3 lifecycle configuration elements](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intro-lifecycle-rules.html)
- [AWS DynamoDB point-in-time recovery restore](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/pointintimerecovery_restores.html)

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Create-story baseline analysis: `51bca7d`.
- CI for `51bca7d` was confirmed green by the user in GitHub.
- `./scripts/validate.sh` passed after temporarily installing the repository-pinned `uv` 0.11.28 outside the checkout. It validated all four Terraform roots and ran Ruff, mypy, 91 tests, Checkov, and hygiene without AWS credentials.

### Completion Notes List

- Implemented the Cell namespace registry, immutable CONFIG inbox/registry, and encrypted SSM discovery contract without introducing runtime resources.
- Reconciled the ownership catalog to the canonical SSM discovery path and CONFIG key path; added semantic Cell Contract checksum verification and updated package inventory/release evidence.
- Added contract/static tests, backend-free example coverage, Checkov enforcement, documentation, rollback/recovery guidance, and the narrow single-Region replication scan exception.
- Full credential-free validation engine passed with Terraform 1.15.8, AWS provider 6.54.0, Ruff, mypy, 91 pytest tests, Checkov (36 checks), repository hygiene, and `git diff --check`.

### File List

- README.md
- _bmad-output/implementation-artifacts/1-3-deploy-cell-registration-and-discovery-foundations.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- contracts/manifest.json
- contracts/migrations/v1.0.0.md
- contracts/releases/1.0.0.json
- contracts/v1/catalogs/ownership.json
- contracts/v1/fixtures/schemas/valid-instances.json
- contracts/v1/schemas/cell-contract.schema.json
- docs/runbooks/README.md
- modules/ecs-scheduled-job-platform/README.md
- modules/ecs-scheduled-job-platform/examples/basic/main.tf
- modules/ecs-scheduled-job-platform/examples/basic/outputs.tf
- modules/ecs-scheduled-job-platform/examples/basic/variables.tf
- modules/ecs-scheduled-job-platform/main.tf
- modules/ecs-scheduled-job-platform/outputs.tf
- modules/ecs-scheduled-job-platform/variables.tf
- scripts/validate.py
- tests/contract/support/contracts.py
- tests/contract/test_cell_foundation.py
- tests/contract/test_documentation.py
- tests/contract/test_repository_structure.py

### Change Log

- 2026-07-16: Implemented Cell registration, immutable CONFIG storage/registry, SSM discovery, contract corrections, tests, and operational documentation.
