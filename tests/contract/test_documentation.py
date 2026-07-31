from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DocumentationContractTest(unittest.TestCase):
    def test_job_runbooks_are_actionable_and_safe(self) -> None:
        template = (
            REPOSITORY_ROOT / "docs/runbooks/job-runbook-template.md"
        ).read_text(encoding="utf-8")
        canary = (REPOSITORY_ROOT / "docs/runbooks/canary-job-runbook.md").read_text(
            encoding="utf-8"
        )
        for requirement in (
            "Deployment Identity",
            "Cell ID",
            "Cell contract/generation",
            "EXPECTED",
            "SUCCEEDED",
            "FAILED",
            "OVERDUE",
            "MISSED",
            "AMBIGUOUS",
            "schedule-delivery",
            "alert-routing",
            "Cell-health",
            "First query/output",
            "Tested procedure evidence",
            "direct `RunTask`",
            "unresolved",
            "Tabletop",
            "reviewed source revision",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, template)
        for requirement in (
            "terraform output canary",
            "non-production",
            "operator role",
            "`job_id`",
            "`config_hash`",
            "`schedule_arn`",
            "`task_definition_arn`",
            "`log_group_name`",
            "`notification_sink_arn`",
            "`scheduler_dlq_arn`",
            "`ownership_generation`",
            "SUCCEEDED",
            "FAILED",
            "OVERDUE",
            "MISSED",
            "AMBIGUOUS",
            "marker",
            "essential-container exit",
            "source revision",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, canary)

        for forbidden in (
            "TODO",
            "<account",
            "<secret",
            "secret_values",
            "raw CONFIG",
            "terraform show",
            "terraform state",
            "aws ecs run-task",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, canary)

        for relative_path in (
            "runbooks/job-runbook-template.md",
            "runbooks/canary-job-runbook.md",
            "runbooks/operator-commands.md",
            "runbooks/cell-recovery.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((REPOSITORY_ROOT / "docs" / relative_path).is_file())

    def test_root_readme_preserves_context_and_documents_foundation_operation(
        self,
    ) -> None:
        contents = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        for heading in (
            "## BMAD Customization",
            "## Platform Foundation",
            "## Prerequisites",
            "## Repository Layout",
            "## Compatibility Package",
            "## Validation",
            "## Tested Toolchain",
            "## Provider Lock Updates",
            "## Contribution Contract",
            "## Security Boundary",
            "## Troubleshooting",
            "## Rollback",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, contents)

        for requirement in (
            "./scripts/validate.sh",
            "moved",
            "migration guidance",
            "standards deviation",
            "pull_request",
            "credential-free",
            "contracts/manifest.json",
            "revert",
            "Cell foundation",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contents)

    def test_module_readmes_state_interface_and_non_claims(self) -> None:
        platform_contents = (
            REPOSITORY_ROOT / "modules" / "ecs-scheduled-job-platform" / "README.md"
        ).read_text(encoding="utf-8")
        for heading in (
            "## Required Providers",
            "## Example",
            "## Ownership And Assumptions",
            "## Inputs And Outputs",
            "## Security And Observability",
            "## Namespace Reservation Contract",
            "## Rollback And Recovery",
        ):
            with self.subTest(module="ecs-scheduled-job-platform", heading=heading):
                self.assertIn(heading, platform_contents)
        self.assertIn("does not create a general Registrar", platform_contents)
        self.assertIn("no runtime behavior", platform_contents)

        job_contents = (
            REPOSITORY_ROOT / "modules" / "ecs-scheduled-job" / "README.md"
        ).read_text(encoding="utf-8")
        for heading in (
            "## Required Providers",
            "## Example",
            "## Ownership And Assumptions",
            "## Inputs And Outputs",
            "## Security And Observability",
        ):
            with self.subTest(module="ecs-scheduled-job", heading=heading):
                self.assertIn(heading, job_contents)
        self.assertIn("no resources", job_contents)

    def test_runbook_location_and_foundation_recovery_boundary_are_explicit(
        self,
    ) -> None:
        contents = (REPOSITORY_ROOT / "docs/runbooks/README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("stable location", contents)
        self.assertIn("Cell foundation recovery boundary", contents)
        self.assertIn("never use routine destructive cleanup", contents)

    def test_contract_documentation_covers_consumer_security_and_rollback(self) -> None:
        contents = (REPOSITORY_ROOT / "contracts" / "README.md").read_text(
            encoding="utf-8"
        )
        for heading in (
            "## Consumer Workflow",
            "## Versioning And Migration",
            "## Security",
            "## Validation",
            "## Rollback",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, contents)

    def test_adoption_guide_preserves_cell_control_and_safe_operations(self) -> None:
        contents = (
            REPOSITORY_ROOT / "docs" / "scheduled-job-adoption-guide.md"
        ).read_text(encoding="utf-8")
        for requirement in (
            "Scheduler → Cell → ECS",
            "never target ECS directly",
            "occurrence_id",
            "never generates occurrence IDs",
            "accepted Cell marker",
            "zero essential-container exit",
            "direct `RunTask`",
            "two-phase",
            "fail closed",
            "moved` blocks",
            "MATERIALIZED",
            "never create a receipt",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contents)

    def test_adoption_guide_links_and_examples_remain_safe(self) -> None:
        guide = REPOSITORY_ROOT / "docs" / "scheduled-job-adoption-guide.md"
        contents = guide.read_text(encoding="utf-8")
        for relative_path in (
            "runbooks/README.md",
            "runbooks/operator-commands.md",
            "runbooks/cell-recovery.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((guide.parent / relative_path).is_file())
                self.assertIn(relative_path, contents)

        example = (
            REPOSITORY_ROOT
            / "modules"
            / "ecs-scheduled-job"
            / "examples"
            / "basic"
            / "main.tf"
        ).read_text(encoding="utf-8")
        for requirement in (
            "@sha256:",
            'secret_mode = "ecs-agent"',
            "log_retention_days",
            "completion_policy",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, example)
        self.assertNotIn("secret_values", example)

    def test_adoption_guide_has_canonical_completion_and_fail_closed_reference(
        self,
    ) -> None:
        contents = (
            REPOSITORY_ROOT / "docs" / "scheduled-job-adoption-guide.md"
        ).read_text(encoding="utf-8")
        for requirement in (
            '"event":"start"',
            '"event":"success"',
            '"event":"failure"',
            '"task_arn":"<platform-supplied>"',
            '"error_reason":"sanitized_failure_code"',
            "production_launch_checklist",
            "Any unresolved value blocks launch",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contents)


if __name__ == "__main__":
    unittest.main()
