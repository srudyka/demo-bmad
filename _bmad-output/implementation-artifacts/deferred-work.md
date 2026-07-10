- source_spec: `_bmad-output/implementation-artifacts/spec-ecs-scheduled-jobs-platform-service.md`
  summary: Add an account-specific Terraform plan workflow once environment roots and GitHub OIDC AWS roles exist.
  evidence: The reusable module CI validates fmt, module/example validation, and Checkov, but the repository standard also calls for Terraform plan; this repo currently has no environment roots, backend, AWS account inputs, or OIDC role to run a meaningful plan without violating the spec's Ask First boundary.
