from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODULES = ("ecs-scheduled-job-platform", "ecs-scheduled-job")
RUNTIME_PACKAGES = (
    "evidence_normalizer",
    "occurrence_materializer",
    "process_manager",
    "log_ingestor",
    "deadline_scanner",
    "alert_router",
    "command_handler",
)


class RepositoryStructureTest(unittest.TestCase):
    def test_terraform_module_boundaries_exist(self) -> None:
        for module_name in MODULES:
            module_root = REPOSITORY_ROOT / "modules" / module_name
            with self.subTest(module=module_name):
                for filename in (
                    "main.tf",
                    "variables.tf",
                    "outputs.tf",
                    "versions.tf",
                    "README.md",
                ):
                    self.assertTrue((module_root / filename).is_file(), filename)
                self.assertTrue((module_root / "examples" / "basic").is_dir())

    def test_runtime_and_operator_boundaries_exist(self) -> None:
        for package_name in RUNTIME_PACKAGES:
            with self.subTest(package=package_name):
                self.assertTrue(
                    (REPOSITORY_ROOT / "runtime" / package_name).is_dir()
                )

        for path in (
            "contracts/README.md",
            "tests/integration/README.md",
            "docs/runbooks/README.md",
        ):
            with self.subTest(path=path):
                self.assertTrue((REPOSITORY_ROOT / path).is_file())

    def test_bootstrap_terraform_contains_no_resources_or_backends(self) -> None:
        terraform_files = tuple((REPOSITORY_ROOT / "modules").glob("**/*.tf"))
        self.assertTrue(terraform_files)
        prohibited_blocks = re.compile(r'^\s*(resource|data|backend)\s+"', re.MULTILINE)
        for terraform_file in terraform_files:
            with self.subTest(path=terraform_file.relative_to(REPOSITORY_ROOT)):
                self.assertIsNone(
                    prohibited_blocks.search(terraform_file.read_text(encoding="utf-8"))
                )


if __name__ == "__main__":
    unittest.main()
