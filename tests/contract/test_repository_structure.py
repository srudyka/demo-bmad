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
                self.assertTrue((REPOSITORY_ROOT / "runtime" / package_name).is_dir())

        for path in (
            "contracts/README.md",
            "tests/integration/README.md",
            "docs/runbooks/README.md",
        ):
            with self.subTest(path=path):
                self.assertTrue((REPOSITORY_ROOT / path).is_file())

    def test_terraform_boundaries_allow_only_cell_foundation_resources(self) -> None:
        platform_main = (
            REPOSITORY_ROOT / "modules" / "ecs-scheduled-job-platform" / "main.tf"
        ).read_text(encoding="utf-8")
        allowed_resources = {
            "aws_dynamodb_table",
            "aws_s3_bucket",
            "aws_s3_bucket_lifecycle_configuration",
            "aws_s3_bucket_logging",
            "aws_s3_bucket_ownership_controls",
            "aws_s3_bucket_policy",
            "aws_s3_bucket_public_access_block",
            "aws_s3_bucket_server_side_encryption_configuration",
            "aws_s3_bucket_versioning",
            "aws_ssm_parameter",
        }
        found_resources = set(
            re.findall(r'^\s*resource\s+"([^"]+)"', platform_main, re.MULTILINE)
        )
        self.assertTrue(found_resources)
        self.assertTrue(found_resources.issubset(allowed_resources))

        prohibited_platform_terms = (
            "aws_sqs_queue",
            "aws_lambda_function",
            "aws_ecs_task_definition",
            "aws_scheduler_schedule",
            "aws_cloudwatch_metric_alarm",
            "aws_sns_topic",
            "aws_iam_role",
            "aws_s3_bucket_notification",
            "terraform_remote_state",
            'backend "',
        )
        for term in prohibited_platform_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, platform_main)

        job_files = tuple(
            (REPOSITORY_ROOT / "modules" / "ecs-scheduled-job").glob("**/*.tf")
        )
        prohibited_blocks = re.compile(r'^\s*(resource|data|backend)\s+"', re.MULTILINE)
        for terraform_file in job_files:
            with self.subTest(path=terraform_file.relative_to(REPOSITORY_ROOT)):
                self.assertIsNone(
                    prohibited_blocks.search(terraform_file.read_text(encoding="utf-8"))
                )

    def test_versioned_compatibility_package_boundaries_exist(self) -> None:
        contracts_root = REPOSITORY_ROOT / "contracts"
        for path in (
            "manifest.json",
            "migrations/v1.0.0.md",
            "releases/1.0.0.json",
            "v1/schemas",
            "v1/catalogs",
            "v1/fixtures",
        ):
            with self.subTest(path=path):
                self.assertTrue((contracts_root / path).exists())
        self.assertFalse((contracts_root / "latest").exists())


if __name__ == "__main__":
    unittest.main()
