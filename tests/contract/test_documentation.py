from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DocumentationContractTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
