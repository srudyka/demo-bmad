---
baseline_commit: 86a74a60e20403902674fff57bb44f72b383551b
---

# Story 1.1: Bootstrap the Greenfield Platform Repository

Status: ready-for-dev

## Story

As a Platform Engineering contributor,
I want a reproducible repository seed with credential-free validation,
So that every later platform story starts from the same reviewable structure and toolchain.

## Acceptance Criteria

1. **Given** the repository has no established platform implementation structure
   **When** the bootstrap is created
   **Then** it contains `modules/ecs-scheduled-job-platform/`, `modules/ecs-scheduled-job/`, module-local `examples/basic/`, `runtime/`, `contracts/`, `tests/contract/`, `tests/integration/`, and operator Runbook locations consistent with the architecture seed
   **And** each Terraform module contains documented `main.tf`, `variables.tf`, `outputs.tf`, and `versions.tf` skeletons that validate without creating production resources.

2. **Given** Terraform is the required infrastructure tool
   **When** module and example version constraints are inspected
   **Then** they require Terraform `>= 1.10, < 2.0`, declare the approved AWS provider constraint, and distinguish the dated validation seed from permanent patch constraints
   **And** backend-free initialization and validation can run independently for every module and module-local example.

3. **Given** Python is used for Cell runtime components and validation tooling
   **When** runtime packaging is initialized
   **Then** the repository declares Python 3.14 compatibility, pinned direct dependencies, a reproducible dependency lock, typed package boundaries, and test discovery for each runtime package
   **And** no runtime package contains account-, Region-, Environment-, credential-, or secret-specific defaults.

4. **Given** a contributor needs one repeatable local validation entry point
   **When** the documented command is run from a clean checkout
   **Then** it executes formatting checks, Terraform initialization without backends, validation for each changed module and example, contract tests, runtime tests, and repository hygiene checks
   **And** failures identify the exact module, example, package, or policy that needs correction.

5. **Given** a pull request changes bootstrap-controlled files
   **When** baseline GitHub Actions validation runs
   **Then** it executes the same credential-free checks with minimal read-only `GITHUB_TOKEN` permissions and no AWS credentials, protected state, deployment Environment, or production secret access
   **And** forked or otherwise untrusted pull requests cannot pass data or executable artifacts into a privileged job.

6. **Given** prohibited repository artifacts are introduced
   **When** hygiene validation runs
   **Then** committed `.tfvars`, Terraform state, saved plans, `.terraform/`, credentials, private keys, generated secret material, and unapproved local configuration are rejected
   **And** `.gitignore`, scanning fixtures, and contributor documentation identify the prohibited patterns without containing real secrets.

7. **Given** later Terraform work changes resource addresses or module structure
   **When** contributors follow the bootstrap contribution contract
   **Then** stable Terraform addresses are required and address changes must include reviewed `moved` blocks or explicit migration guidance
   **And** routine provisioners, `null_resource`, mutable production references, and undocumented standards deviations are prohibited.

8. **Given** the bootstrap checks run successfully
   **When** their output is reviewed
   **Then** the repository reports the tested Terraform, provider, and Python toolchain versions and produces no state, saved plan, credential, or deployment artifact
   **And** the documented rollback is removal or reversion of the seed files because this story creates no AWS resources.

## Tasks / Subtasks

- [x] 1. Establish the repository structure and ownership boundaries (AC: 1, 7)
  - [x] Create `modules/ecs-scheduled-job-platform/` and `modules/ecs-scheduled-job/`, each with `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, `README.md`, and `examples/basic/`.
  - [x] Create the seven architecture-seeded runtime package roots: `evidence_normalizer`, `occurrence_materializer`, `process_manager`, `log_ingestor`, `deadline_scanner`, `alert_router`, and `command_handler`.
  - [x] Create `contracts/`, `tests/contract/`, `tests/integration/`, and `docs/runbooks/`; add concise placeholder documentation so Git retains empty structural boundaries.
  - [x] Document that the Cell module owns shared account/Region platform resources and the job module owns per-job resources; neither module may import or mutate the other's resources.
  - [x] Keep all Terraform skeletons resource-free. Do not add backends, provider configurations containing deployment values, environment roots, AWS resources, runtime behavior, or compatibility schemas in this story.

- [x] 2. Seed Terraform compatibility and deterministic provider selection (AC: 1, 2, 8)
  - [x] Set `required_version = ">= 1.10, < 2.0"` in both modules and both module-local examples.
  - [x] Adopt `>= 6.0, < 7.0` as the Story 1.1 AWS provider compatibility constraint in every Terraform root. Record AWS provider `6.54.0` as the dated validation seed, not a permanent exact source constraint.
  - [x] Generate and commit a separate `.terraform.lock.hcl` for every independently initialized module and example; never copy one lock file between roots. Document that reusable-module locks support repository validation but consumers still own their root lock files.
  - [x] Make `terraform init -backend=false -lockfile=readonly` and `terraform validate` succeed independently for each module and example after initial lock generation, without AWS credentials or backend access.
  - [x] Ensure every declared variable and output has a description; add validation only where the skeleton exposes meaningful inputs. Do not invent deployment-specific placeholder inputs merely to populate files.

- [ ] 3. Seed reproducible, typed Python runtime packaging (AC: 3, 8)
  - [ ] Add a root `pyproject.toml` that requires Python 3.14 and defines deterministic test, lint, type-check, and security-tool groups; pin every direct tool/runtime dependency exactly.
  - [ ] Use a checked-in reproducible dependency lock and a documented locked install/run mode. If `uv` is selected, commit `uv.lock`, pin the validated `uv` version, and use `uv lock --check` plus `uv run --locked`; do not present `uv` as a PyPA requirement.
  - [ ] Give every runtime component an independently discoverable package/test boundary using `src/` layout, typed public interfaces, and `py.typed` where applicable. Skeleton tests must prove import and discovery without claiming runtime behavior.
  - [ ] Keep runtime configuration empty and injectable: no account IDs, Regions, Environments, repository IDs, ARNs, credentials, secrets, or deployment-specific defaults.

- [ ] 4. Implement one local validation entry point (AC: 2, 3, 4, 6, 8)
  - [ ] Add a small documented wrapper such as `scripts/validate.sh` using `set -euo pipefail`; keep complex hygiene or policy logic in a typed, tested language rather than growing a large Bash program.
  - [ ] Have the entry point run Terraform formatting, independent backend-free init/validate for all modules and examples, Python formatting/lint/type checks, contract tests, runtime tests, the pinned IaC/security scan, and repository hygiene checks. Validating all roots is acceptable and must include every changed root.
  - [ ] Prefix or summarize failures with the exact Terraform root, example, runtime package, test suite, scanner, or policy that failed.
  - [ ] Print the actual Terraform CLI, resolved AWS provider, Python, package-manager, and scanner versions used by validation.
  - [ ] Use temporary Terraform data directories where practical and verify the command leaves no state, saved plan, credential, deployment, or unrelated generated artifact in the checkout.

- [ ] 5. Enforce repository hygiene with tested positive and negative cases (AC: 6, 7, 8)
  - [ ] Update `.gitignore` for saved Terraform plans, Python virtual environments/caches, local environment files, credentials, private keys, and generated secret material while explicitly allowing committed Terraform and Python lock files.
  - [ ] Add a tracked-file hygiene validator that rejects prohibited paths/content even when `.gitignore` is bypassed; cover `.tfvars`, state, saved plans, `.terraform/`, credentials, private keys, generated secrets, unapproved local config, routine provisioners, `null_resource`, mutable production references, and undocumented deviations.
  - [ ] Store scanner fixtures as inert fixture data or isolated test repositories so prohibited filenames are not accidentally treated as real repository artifacts. Use only unmistakably fake sentinel values and narrowly documented scanner exemptions.
  - [ ] Add negative tests for every prohibited category and positive tests proving `.terraform.lock.hcl`, the Python dependency lock, documented fake fixtures, and legitimate Terraform source remain allowed.

- [ ] 6. Add credential-free baseline GitHub Actions validation (AC: 4, 5, 8)
  - [ ] Add a pull-request workflow that invokes the same local validation entry point instead of duplicating validation logic.
  - [ ] Declare top-level or job-level `permissions: contents: read`; do not grant `id-token: write`, write permissions, AWS credentials, repository secrets, protected Environments, state access, plan/apply capability, or privileged downstream jobs.
  - [ ] Pin every third-party Action to a reviewed full commit SHA and retain the release tag in a comment for maintainability. Pin installed Terraform, Python, package-manager, and scanner versions to the tested seed.
  - [ ] Use the unprivileged `pull_request` event. Do not use `pull_request_target`, execute attacker-controlled context directly in shell, or pass untrusted caches/artifacts into any privileged workflow.

- [ ] 7. Document contribution, validation, security, and rollback contracts (AC: 1, 4, 6, 7, 8)
  - [ ] Preserve the existing BMad customization section in `README.md` and add prerequisites, repository layout, the single validation command, toolchain matrix, lock update procedure, and troubleshooting for actionable validation failures.
  - [ ] Document stable Terraform address expectations, reviewed `moved` blocks or migration guidance, prohibited patterns, immutable references, standards-deviation handling, and the boundary between credential-free bootstrap CI and later trusted delivery workflows.
  - [ ] Add concise module READMEs with purpose, ownership, required providers, assumptions, example usage, future inputs/outputs, and explicit security/observability non-claims for the resource-free skeleton.
  - [ ] Seed `docs/runbooks/README.md` as the stable operator Runbook location without writing the later production Job Runbook contract.
  - [ ] Document rollback as reverting/removing only the Story 1.1 seed files, followed by rerunning validation; no AWS rollback, state operation, or deployment action is permitted because this story creates no AWS resources.

- [ ] 8. Prove the bootstrap from a clean-checkout-equivalent state (AC: 1-8)
  - [ ] Run the documented validation entry point with no AWS environment credentials and confirm all module/example, Python, contract, runtime, security, policy, and hygiene checks pass.
  - [ ] Verify the working tree contains no `.terraform/`, state, saved plans, credentials, deployment artifacts, unexpected lock changes, or generated secrets after validation.
  - [ ] Record the tested tool versions and provide evidence that each module and example initialized and validated independently.
  - [ ] Confirm the change creates zero AWS resources and that rollback is repository-only.

## Dev Notes

### Developer Context

Story 1.1 is the structural prerequisite for every later platform story. The repository currently has no implementation directories, Terraform files, Python package metadata, validation scripts, or GitHub workflows. It contains only repository/BMad documentation and planning artifacts. Build a small, executable seed rather than placeholder infrastructure that implies unapproved behavior.

Epic 1 ultimately proves an account-local Platform Cell with a platform-owned canary, occurrence tracking, alert delivery, operator controls, and recovery. This story implements none of those capabilities. Story 1.2 will populate the normative Compatibility Package, Story 1.3 begins AWS foundations, and Story 1.4 supplies the canary. Do not front-load their resources, schemas, IAM, queues, tables, schedules, runtime algorithms, or alerting into this bootstrap.

Traceability: Story 1.1 primarily supports FR20, FR25, and FR26; its load-bearing constraints are NFR11, NFR12, NFR15 and AR30, AR32, AR40. The acceptance criteria above remain authoritative.

### Architecture Compliance

- `ARCHITECTURE-SPINE.md` is the implementation source of truth. Preserve the one account-local Cell per AWS account/Region and the strict Cell-module/job-module ownership boundary even though this story creates no resources.
- The story's module-local `examples/basic/` requirement and repository standard are more specific than the spine's older top-level example sketch. Create module-local examples only; production examples belong to later adoption work.
- The binding architecture supplies the AWS provider dated seed (`6.54.0`) but not a provider range. This story resolves that bootstrap gap with the major-bounded `>= 6.0, < 7.0` constraint. Any different range is an architecture deviation and must be approved and documented before implementation.
- No backend blocks are needed in this story. The Terraform `>= 1.10` floor exists because later production roots require native S3 lock files; do not scaffold deprecated DynamoDB locking.
- Module skeletons must be empty of AWS resources. Provider download during initialization is acceptable; provider authentication, backend access, plan, and apply are not.
- All future resources must use stable addresses and derived names/tags. Never hardcode account IDs, Regions, ARNs, repository IDs, Environment names, credentials, or secret values.
- Do not introduce direct Scheduler-to-ECS assumptions into placeholders. The adopted architecture sends launch evidence to the Cell and the Process Manager later assumes a job-scoped launch role.

### Library and Framework Requirements

- Terraform CLI contract: `>= 1.10, < 2.0`; dated tested seed: `1.15.8`.
- AWS provider contract for this story: `>= 6.0, < 7.0`; dated tested seed: `6.54.0`.
- Python contract: compatible with Python 3.14; the current dated host seed is `3.14.6`.
- Python packaging is not dictated by the architecture. A root `pyproject.toml` plus one checked-in reproducible lock is required. `uv` is an acceptable implementation choice when its version is pinned and CI uses locked mode.
- Select one pinned Terraform/IaC security scanner that can run in the chosen tool environment. Local and CI validation must use the same scanner and version; do not download an unbounded `latest` tool at runtime.
- Pin GitHub Actions by full commit SHA. Human-readable release tags may appear only as comments.

### File Structure Requirements

**UPDATE - read and preserve before editing**

- `README.md`: currently documents BMad customization. Preserve that section; append platform bootstrap, validation, contribution, toolchain, security, troubleshooting, and rollback guidance.
- `.gitignore`: currently ignores `.terraform/`, Terraform state, `.tfvars`, overrides, and Terraform CLI configuration. Preserve those protections and close the saved-plan, Python, credential/private-key, local-environment, and generated-secret gaps. Do not ignore required lock files.

**NEW - required implementation areas**

```text
.github/workflows/                 # credential-free pull-request validation only
contracts/                         # placeholder boundary; Story 1.2 owns schemas/fixtures
docs/runbooks/                     # stable operator Runbook location
modules/
  ecs-scheduled-job-platform/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
    README.md
    examples/basic/
  ecs-scheduled-job/
    main.tf
    variables.tf
    outputs.tf
    versions.tf
    README.md
    examples/basic/
runtime/
  evidence_normalizer/
  occurrence_materializer/
  process_manager/
  log_ingestor/
  deadline_scanner/
  alert_router/
  command_handler/
scripts/                            # shared local/CI validation entry point
tests/
  contract/
  integration/
  hygiene/                          # recommended validator tests and inert fixtures
pyproject.toml
<checked-in Python lock>
```

Do not edit `_bmad/`, `.agents/`, the PRD, architecture documents, or generated planning artifacts as part of story implementation. `AGENTS.md` is already the repository instruction boundary and needs no Story 1.1 change.

### Security and CI Guardrails

- Baseline validation is deliberately credential-free. It must not request GitHub OIDC, configure AWS credentials, access Terraform state, select a GitHub deployment Environment, create a plan, or apply infrastructure.
- GitHub documents full-length commit SHAs as the only immutable Action reference. Audit each SHA against the upstream Action repository.
- `GITHUB_TOKEN` can be available to Actions even when not passed explicitly, so declare minimal permissions rather than relying on omission.
- Avoid `pull_request_target` and privileged `workflow_run` chains for untrusted validation. Do not check out untrusted code in a privileged context or consume its executable artifacts/caches later.
- The architecture's immutable/custom GitHub OIDC subject is a later delivery concern. Do not add OIDC here; later stories must bind the subject actually emitted by the organization/repository configuration.
- Secret and hygiene checks must inspect tracked content, not merely trust `.gitignore`. Fixtures must never contain valid credentials or realistic private keys.

### Testing Requirements

- Run `terraform fmt -check -recursive` (or an equivalent complete check) and independently initialize/validate both modules and both examples using `-backend=false`.
- Use lock-readonly validation after initial lock generation so CI fails on stale or unexpectedly changed provider selections.
- Test that all seven runtime packages are importable, typed, and individually discoverable. Do not fake runtime behavior tests before the behavior exists.
- Seed contract and integration suites so they are discovered and pass without AWS. AWS-dependent disposable-Cell integration and failure-injection tests belong to later stories.
- Unit-test the hygiene validator with a table of prohibited and allowed cases. Include address/provisioner/`null_resource`/mutable-reference policy checks required by AR40 and the AWS Terraform standard.
- Run the same top-level command locally and in GitHub Actions. CI-specific duplicate command lists are a drift risk.
- A passing result must report tool versions and leave the checkout clean of generated Terraform, secret, credential, plan, state, and deployment artifacts.
- `terraform validate` checks syntax and internal consistency only; do not claim it validates AWS APIs, backend configuration, provider permissions, or deployed behavior.

### Latest Technical Notes (verified 2026-07-14)

- HashiCorp documents `terraform init -backend=false` followed by `terraform validate` for reusable-module validation. Native S3 state locking uses `use_lockfile = true`; DynamoDB locking is deprecated, but backend implementation is outside this story.
- `.terraform.lock.hcl` belongs to each root configuration and locks providers, not remote modules. Each independently validated example needs its own lock; reusable-module validation locks do not remove the consumer's responsibility to commit its root lock.
- Production later uses `terraform init -lockfile=readonly`; `-lockfile=readonly` conflicts with `-upgrade`. Story 1.1 only proves locked, backend-free validation.
- Python 3.14 is stable. Standard project metadata uses `pyproject.toml`; PEP 751 defines tool-neutral `pylock.toml`. A tool-specific `uv.lock` is also acceptable when the repository explicitly chooses and pins `uv`.
- For `uv`, `uv lock --check` detects a missing or stale lock and `uv run --locked` refuses lock updates. `--frozen` is weaker for validation because it trusts the existing lock without checking whether declared dependencies changed.

### Project Structure Notes

- There is no previous story implementation or git pattern to reuse. This story establishes the first implementation convention.
- The only existing implementation-adjacent files to update are `README.md` and `.gitignore`; both were read before story creation. Preserve their current content while extending it.
- The architecture spine lists `alert_router` twice in its structural diagram; create one `runtime/alert_router/` package.
- No UX specification applies. The developer experience is the stable structure, single actionable validation command, executable examples, and clear contribution/rollback documentation.
- Implementation readiness is `READY` with no blockers. Keep the story limited to structural seed, dependency locks, local validation, repository hygiene, and credential-free baseline CI.

### Rollback Notes

This story must create no AWS resource, Terraform state, saved plan, deployment artifact, or credential. Rollback is a normal repository revert/removal of the Story 1.1 seed files plus restoration of the prior `README.md` and `.gitignore`, followed by rerunning the pre-existing repository checks. Do not run `terraform destroy`, mutate a backend, or perform any AWS action.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story-11-Bootstrap-the-Greenfield-Platform-Repository`]
- [Source: `_bmad-output/planning-artifacts/epics.md#Story-Traceability-Matrix`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#Stack`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#Structural-Seed`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/ARCHITECTURE-SPINE.md#Invariants--Rules`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-demo-bmad-2026-07-13/solution-design-review.md#Deployment-State-Release-and-Evolution`]
- [Source: `_bmad-output/project-context.md#Terraform-Rules`]
- [Source: `_bmad-output/project-context.md#CI/CD-Rules`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md#Terraform-Interface`]
- [Source: `_bmad/custom/standards/aws-terraform-implementation.md#CI-And-Documentation`]
- [Source: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-07-14.md#Recommended-Next-Steps`]
- [HashiCorp: Validate command](https://developer.hashicorp.com/terraform/cli/commands/validate)
- [HashiCorp: Init command](https://developer.hashicorp.com/terraform/cli/commands/init)
- [HashiCorp: Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)
- [HashiCorp: S3 backend and native lock file](https://developer.hashicorp.com/terraform/language/backend/s3)
- [GitHub: Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub: `GITHUB_TOKEN` authentication](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [GitHub: Script injection guidance](https://docs.github.com/en/actions/concepts/security/script-injections)
- [PyPA: `pyproject.toml` specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [PyPA: `pylock.toml` specification](https://packaging.python.org/en/latest/specifications/pylock-toml/)
- [uv: Project layout and lock file](https://docs.astral.sh/uv/concepts/projects/layout/)
- [uv: Locked and frozen modes](https://docs.astral.sh/uv/concepts/projects/sync/)

## Dev Agent Record

### Agent Model Used

OpenAI Codex (GPT-5)

### Debug Log References

- RED: `python3 -m unittest tests.contract.test_repository_structure` failed with 13 missing-boundary assertions.
- GREEN: the same contract suite passed after adding the resource-free module, runtime, contract, integration, and Runbook boundaries; `terraform fmt -check -recursive modules` also passed.
- RED: `test_terraform_compatibility` failed because all four independent Terraform roots lacked provider locks.
- GREEN: generated four root-local locks at AWS provider 6.54.0 and validated every root independently with Terraform 1.15.8, no backend, and no AWS credentials.

### Implementation Plan

- Establish and contract-test the zero-resource repository boundaries first.
- Add deterministic Terraform and Python toolchains, then one shared validation command.
- Add tested hygiene policy and unprivileged CI around that command.
- Complete documentation, clean-checkout proof, and final definition-of-done checks.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created
- Task 1 completed: seeded both ownership-separated Terraform modules, seven runtime roots, contract/integration boundaries, and the operator Runbook location without AWS resources.
- Task 2 completed: enforced Terraform/AWS provider ranges, root-local provider locks, and independent backend-free validation for both modules and examples.

### File List
