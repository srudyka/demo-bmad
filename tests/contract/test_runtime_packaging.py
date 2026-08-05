from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PACKAGES = (
    "evidence_normalizer",
    "occurrence_materializer",
    "process_manager",
    "log_ingestor",
    "deadline_scanner",
    "alert_router",
    "command_handler",
    "lifecycle_gc",
    "job_registrar",
)
FORBIDDEN_DEFAULTS = re.compile(
    r"\b(?:us-(?:east|west)-\d|eu-[a-z]+-\d|arn:aws|AKIA[0-9A-Z]{16}|"
    r"prod(?:uction)?|staging)\b",
    re.IGNORECASE,
)


class RuntimePackagingTest(unittest.TestCase):
    def test_project_metadata_and_lock_are_reproducible(self) -> None:
        pyproject_path = REPOSITORY_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.is_file())
        metadata = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        self.assertEqual(metadata["project"]["requires-python"], ">=3.14,<3.15")
        self.assertEqual(metadata["project"]["dependencies"], [])

        tools = metadata["dependency-groups"]["dev"]
        self.assertTrue(tools)
        for requirement in tools:
            with self.subTest(requirement=requirement):
                self.assertRegex(requirement, r"^[a-zA-Z0-9_-]+==[^=]+$")

        self.assertTrue((REPOSITORY_ROOT / "uv.lock").is_file())

    def test_each_runtime_component_has_a_typed_package_and_test(self) -> None:
        for package_name in RUNTIME_PACKAGES:
            package_root = REPOSITORY_ROOT / "runtime" / package_name
            source_package = package_root / "src" / package_name
            with self.subTest(package=package_name):
                self.assertTrue((source_package / "__init__.py").is_file())
                self.assertTrue((source_package / "py.typed").is_file())
                self.assertTrue(
                    (package_root / "tests" / f"test_{package_name}.py").is_file()
                )

    def test_runtime_sources_contain_no_deployment_specific_defaults(self) -> None:
        source_files = tuple((REPOSITORY_ROOT / "runtime").glob("**/*.py"))
        self.assertTrue(source_files)
        for source_file in source_files:
            with self.subTest(path=source_file.relative_to(REPOSITORY_ROOT)):
                self.assertIsNone(
                    FORBIDDEN_DEFAULTS.search(source_file.read_text(encoding="utf-8"))
                )


if __name__ == "__main__":
    unittest.main()
