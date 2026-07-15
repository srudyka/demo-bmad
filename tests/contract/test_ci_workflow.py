from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "validate.yml"


def action_metadata_files() -> tuple[Path, ...]:
    workflows = tuple((REPOSITORY_ROOT / ".github" / "workflows").glob("*.y*ml"))
    composite_actions = tuple(
        path
        for path in (REPOSITORY_ROOT / ".github" / "actions").glob("**/action.y*ml")
        if path.is_file()
    )
    return workflows + composite_actions


class ContinuousIntegrationContractTest(unittest.TestCase):
    def test_workflow_is_unprivileged_pull_request_validation(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        contents = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(contents, r"(?m)^on:\n  pull_request:\s*$")
        self.assertIn("permissions:\n  contents: read", contents)
        for prohibited in (
            "pull_request_target",
            "workflow_run",
            "id-token: write",
            "contents: write",
            "aws-access-key",
            "terraform plan",
            "terraform apply",
            "upload-artifact",
            "download-artifact",
            "write-all",
            "${{ secrets.",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, contents.lower())
        self.assertNotRegex(contents, r"(?m)^\s+environment:\s*")
        self.assertNotRegex(contents, r"(?m)^\s+secrets:\s*")
        self.assertNotRegex(contents, r"(?m)^\s+[a-z-]+:\s*write\s*$")

    def test_all_third_party_actions_are_pinned_to_full_shas(self) -> None:
        metadata_files = action_metadata_files()
        self.assertTrue(metadata_files)
        references_seen = 0
        for metadata_file in metadata_files:
            contents = metadata_file.read_text(encoding="utf-8")
            references = re.findall(r"(?m)^\s+-?\s*uses:\s+([^\s#]+)", contents)
            references_seen += len(references)
            for reference in references:
                with self.subTest(file=metadata_file, reference=reference):
                    if reference.startswith("./"):
                        continue
                    if reference.startswith("docker://"):
                        self.assertRegex(
                            reference, r"^docker://[^@]+@sha256:[0-9a-f]{64}$"
                        )
                        continue
                    owner_action, revision = reference.rsplit("@", 1)
                    self.assertIn("/", owner_action)
                    self.assertRegex(revision, r"^[0-9a-f]{40}$")
        self.assertGreater(references_seen, 0)

    def test_ci_invokes_the_same_validation_entrypoint(self) -> None:
        contents = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(contents.count("./scripts/validate.sh"), 1)
        self.assertIn('terraform_version: "1.15.8"', contents)
        self.assertIn('python-version: "3.14.6"', contents)
        self.assertIn('version: "0.11.28"', contents)


if __name__ == "__main__":
    unittest.main()
