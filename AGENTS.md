# AGENTS.md

## Repository Instructions

This repository follows DevOps/SRE-first engineering standards.

Before planning, coding, reviewing, or generating infrastructure, read:

`_bmad-output/project-context.md`

That file contains the project rules for:

- AWS design
- Terraform structure
- CI/CD
- security
- IAM
- observability
- reliability
- rollback
- documentation
- definition of done

## Default Expectations

- Prefer small, reviewable changes.
- Do not commit secrets, generated state files, or credentials.
- Follow existing repository structure.
- Use Terraform for infrastructure changes.
- Include validation steps in every final response.
- Include rollback notes for production-impacting changes.
- Update README or runbook documentation when behavior changes.

## Validation

For Terraform changes, run:

```bash
terraform fmt -check
terraform validate

## Networked Validation

When Terraform Registry or PyPI DNS resolution is required, configure the
environment to use nameserver `192.168.1.1` before running validation.
