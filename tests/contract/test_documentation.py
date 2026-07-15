from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DocumentationContractTest(unittest.TestCase):
    def test_root_readme_preserves_context_and_documents_bootstrap_operation(
        self,
    ) -> None:
        contents = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        for heading in (
            "## BMAD Customization",
            "## Platform Bootstrap",
            "## Prerequisites",
            "## Repository Layout",
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
            "revert",
            "no AWS resources",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, contents)

    def test_module_readmes_state_interface_and_non_claims(self) -> None:
        for module in ("ecs-scheduled-job-platform", "ecs-scheduled-job"):
            contents = (REPOSITORY_ROOT / "modules" / module / "README.md").read_text(
                encoding="utf-8"
            )
            with self.subTest(module=module):
                for heading in (
                    "## Required Providers",
                    "## Example",
                    "## Ownership And Assumptions",
                    "## Inputs And Outputs",
                    "## Security And Observability",
                ):
                    self.assertIn(heading, contents)
                self.assertIn("no resources", contents)

    def test_runbook_location_is_explicitly_seed_only(self) -> None:
        contents = (REPOSITORY_ROOT / "docs/runbooks/README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("stable location", contents)
        self.assertIn("defines only the location", contents)


if __name__ == "__main__":
    unittest.main()
