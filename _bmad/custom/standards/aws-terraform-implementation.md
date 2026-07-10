# AWS Terraform Implementation Standard

Use this standard whenever creating, implementing, reviewing, or validating AWS infrastructure with Terraform.

## Baseline Pattern

- Prefer small, reusable Terraform modules with clear ownership boundaries and stable resource addresses.
- Keep account-specific values in environment root modules, CI variables, Terraform Cloud variables, or uncommitted local files.
- Include a basic module example for reusable modules under `modules/<module-name>/examples/basic`.
- Keep resource naming predictable with `<environment>-<application>-<component>` unless the existing repository convention differs.
- Apply required AWS tags consistently: `Environment`, `Application`, `Service`, `Owner`, `ManagedBy`, and optional `CostCenter`/`Repository`.
- Prefer managed AWS services when they reduce operational burden without weakening security or debuggability.
- Prefer explicit inputs, validations, locals, and outputs over hidden derivation.

## Security And IAM

- Use least-privilege IAM and separate roles by responsibility.
- Scope IAM resources to the narrowest practical ARNs. Any wildcard must be required by AWS or constrained with conditions and documented.
- Add confused-deputy protections to service trust policies when AWS supports `aws:SourceAccount`, `aws:SourceArn`, or equivalent conditions.
- Avoid `Principal = "*"`, public ingress, public storage, and mutable image tags unless explicitly justified and scoped.
- Do not pass secrets through Terraform plaintext variables, README examples, container environment variables, or committed files.
- Use Secrets Manager, SSM Parameter Store, KMS, or CI/CD secret storage for sensitive values.
- Encrypt storage and queues by default where the AWS service supports it.
- Keep security groups minimal and document intended traffic paths.

## Reliability And Observability

- Production-impacting infrastructure must include logs, metrics, alarms, runbook notes, and rollback notes.
- Configure log retention explicitly. Production logs must not rely on infinite retention unless required and documented.
- Define actionable alarms for the primary failure modes of the resource being introduced.
- Use retries with bounded attempts and bounded age where retries are appropriate.
- Use dead-letter queues, failure destinations, or equivalent recovery paths for asynchronous delivery and scheduled workloads.
- Make enable/disable controls explicit for components that may need emergency stop or rollback.
- Prefer private networking for internal workloads and document any public exposure.
- Document idempotency expectations for repeatable jobs, replayable events, migrations, and operational scripts.

## Terraform Interface

- Validate important variables, including names, ARNs, IDs, retention periods, capacity ranges, and mutually exclusive settings.
- Reject mutable image tag `latest`; require immutable tags, digests, commit SHAs, or release versions.
- Keep module outputs operationally useful: resource identifiers, role ARNs, log group names, alarm identifiers, queue/topic identifiers, and endpoint names where applicable.
- Avoid hardcoded account IDs, regions, ARNs, subnet IDs, and environment-specific defaults.
- Do not use provisioners or `null_resource` for normal infrastructure workflows.
- Preserve existing resource addresses unless replacement is intentional and documented with migration or rollback notes.
- For reusable modules, document required providers, assumptions, example usage, inputs, outputs, security notes, and observability notes.

## Scheduled Workloads

- Scheduled workloads should use EventBridge Scheduler or EventBridge rules and run privately unless public access is explicitly required.
- Scheduled workloads must have retry behavior, failure capture, logs, task/job failure alarms, and DLQ or equivalent failed-delivery handling.
- Scheduler or event-invocation roles must be scoped to the configured target and must use confused-deputy protections when supported.
- Containerized scheduled jobs should separate execution role, task/runtime role, and scheduler/invocation role.
- Containerized jobs must validate CPU/memory combinations, log configuration, secrets handling, and immutable image references.

## CI And Documentation

- CI must run format checks, validation for each changed root/module example, and an IaC security scan.
- CI or repository rules must prevent committed Terraform state, committed `.tfvars` files, broad public ingress, mutable `latest` images, and unjustified wildcard IAM.
- Production workflows must include plan review and manual approval before apply unless explicitly approved otherwise.
- Documentation must include validation steps and rollback notes for production-impacting changes.
- For implementation comparisons, prefer the solution that is more observable, easier to debug, more secure by default, and easier to roll back.
- Any deviation from this standard must be explicit in the story, spec, PR notes, or review findings.
