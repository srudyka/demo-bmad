# Epic 1–2 Action-Item Closure Record

Date: 2026-08-04  
Scope: Retrospective action items for Epic 1 and Epic 2  
Validation boundary: credential-free repository evidence only; this record does not claim live AWS qualification.

## Closure summary

All eight open action items are closed against the repository evidence listed below. The evidence is intentionally split between story records, contract fixtures/tests, runbooks, and the repository validation gate so that a fixture or static checklist cannot be mistaken for live production evidence.

## Action-item evidence

### 1. Authority-and-boundary checklist for Epic 2

The Epic 2 story records define the authoritative writer/state boundary, IAM ownership, metrics/evidence boundary, rollback behavior, and negative scenarios. The audited story set is:

- `2-1-declare-and-reserve-a-scheduled-job.md`
- `2-2-create-least-privilege-job-iam-roles.md`
- `2-3-enforce-private-task-networking.md`
- `2-4-provision-the-fargate-task-and-structured-logs.md`
- `2-5-publish-phase-one-job-resources-and-config.md`
- `2-5a-cell-owned-conditional-config-publisher.md`
- `2-6-validate-and-acknowledge-job-configuration.md`
- `2-7-activate-the-non-production-schedule-safely.md`
- `2-8-connect-completion-evidence-and-alert-metadata.md`
- `2-9-expose-job-operations-and-optional-views.md`
- `2-10-perform-a-controlled-non-production-rerun.md`

The common boundary is also documented in `docs/runbooks/`, module READMEs, and the project context rules: Cell-owned state is not job-owned state; credential-free evaluators do not authorize AWS; IAM is least-privilege and role responsibilities remain separate; metrics and evidence are derived from authoritative inputs; and rollback is disable-first with retained evidence.

### 2. Review and validation evidence for Epic 2

Each Epic 2 story contains a review-findings section and completion/validation record. The repository retains adversarial review prompts and findings for representative high-risk stories, including Stories 2.10 and 3.4–3.6. The complete repository gate has been run after the latest implementation changes and includes formatting, strict typing, contract/runtime tests, Terraform validation, Checkov, and repository hygiene.

### 3. Credential-free evidence versus live qualification

The separation is explicit in:

- `docs/runbooks/pull-request-validation.md`
- `docs/runbooks/pilot-measurement.md`
- `docs/runbooks/pilot-launch.md`
- `modules/ecs-scheduled-job-platform/README.md`
- Epic 4 story records, especially Stories 4.8–4.10

Credential-free fixtures and evaluators are prohibited from claiming live AWS behavior, production authorization, or successful pilot execution. Protected workflows and disposable-cell qualification remain the live-evidence boundary.

### 4. Executable Epic 2 negative fixtures

The following contract/runtime tests provide executable coverage for IAM denial, retries, pagination/identity handling, duplicate requests, and partial failure paths:

- `tests/contract/test_contract_iam.py`
- `tests/contract/test_contract_queue_lambda.py`
- `tests/contract/test_canary_reservation.py`
- `tests/contract/test_scheduled_job_phase_one.py`
- `tests/contract/test_scheduled_job_operations.py`
- `runtime/config_publisher/tests/test_publisher_domain.py`
- `runtime/job_registrar/tests/test_job_registrar_domain.py`
- `runtime/process_manager/tests/test_launch.py`
- `runtime/evidence_normalizer/tests/test_scheduler_normalizer.py`

The fixture suites are registered through `contracts/manifest.json` and are exercised by the repository validation gate.

### 5. Affected Epic 3 target validation

Credential-free target discovery and affected-target classification are covered by:

- `tests/contract/test_validation_targets.py`
- `tests/contract/test_deployment_targets.py`
- `tests/contract/test_trusted_plan.py`
- `.github/workflows/validate.yml`
- `.github/workflows/production-apply.yml`

These checks bind account, Region, environment, workflow, OIDC subject, target manifest, plan, and apply authority. They fail closed on changed commits, roles, targets, or plan identity.

### 6. Executable Epic 3 negative fixtures

OIDC trust, target binding, exact-plan approval, and untrusted pull-request output coverage is present in:

- `contracts/v1/fixtures/oidc/cases.json`
- `contracts/v1/fixtures/iam/cases.json`
- `contracts/v1/fixtures/production-policy/cases.json`
- `contracts/v1/fixtures/security/cases.json`
- `tests/contract/test_contract_oidc.py`
- `tests/contract/test_contract_iam.py`
- `tests/contract/test_trusted_plan.py`
- `tests/contract/test_ci_workflow.py`

The tests verify both positive bindings and rejection of wrong audiences, branches, roles, accounts, plans, policies, and untrusted workflow outputs.

### 7. Preserved review evidence

Story-level review findings and review prompts are retained under `_bmad-output/implementation-artifacts/`. The review register covers acceptance, adversarial/blind-hunter, and edge-case analysis where those review layers were run; story files retain the resulting findings and patch status. Full validation results are preserved in the relevant story completion notes and the repository’s reproducible `./scripts/validate.sh` gate.

### 8. Terraform provider modernization tracking

The migration is tracked in `modules/ecs-scheduled-job-platform/README.md` and remains a separate reviewed change because it affects a large, shared Terraform surface. The inventory is:

- Replace deprecated `data.aws_region.current.name` with `.region` where the provider interface permits it.
- Replace legacy DynamoDB `hash_key`/`range_key` arguments with explicit `key_schema` blocks while preserving existing resource addresses and key semantics.
- Run `terraform fmt -check`, backend-free validation for every affected root/module example, and Checkov before merging.
- Use reviewed migration guidance and preserve rollback/resource-address stability; do not suppress the warnings or mix this modernization into unrelated feature work.

The current warnings are non-failing and documented; no production-impacting Terraform change is claimed by this closure record.

## Validation record

- Full repository validation: passed.
- Python tests: 426 passed; 373 contract subtests passed.
- Ruff formatting/lint and mypy: passed.
- Terraform validation: passed with the documented provider deprecation warnings.
- Checkov: 1,014 checks passed, 0 failed.
- Repository hygiene and diff checks: passed.

This record closes retrospective follow-up work; it does not replace protected live qualification, a real pilot, or production approval.
