from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ValidationEntrypointTest(unittest.TestCase):
    def test_shell_entrypoint_is_executable_and_delegates_to_typed_runner(self) -> None:
        entrypoint = REPOSITORY_ROOT / "scripts" / "validate.sh"
        self.assertTrue(entrypoint.is_file())
        self.assertTrue(entrypoint.stat().st_mode & stat.S_IXUSR)
        contents = entrypoint.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", contents)
        self.assertIn("AWS_EC2_METADATA_DISABLED=true", contents)
        self.assertIn("mktemp -d", contents)
        self.assertIn("uv lock --check", contents)
        self.assertIn("uv run --locked python scripts/validate.py", contents)

    def test_runner_strips_aws_credentials_from_subprocesses(self) -> None:
        from scripts.validate import sanitized_environment

        source = {
            "PATH": os.environ.get("PATH", ""),
            "AWS_ACCESS_KEY_ID": "not-a-real-key",
            "AWS_SECRET_ACCESS_KEY": "not-a-real-secret",
            "AWS_SESSION_TOKEN": "not-a-real-token",
            "AWS_PROFILE": "not-a-real-profile",
            "AWS_EC2_METADATA_DISABLED": "false",
            "PYTEST_ADDOPTS": "--collect-only",
            "TF_CLI_ARGS": "-help",
            "TF_VAR_secret": "not-a-real-secret",
            "PYTHONPATH": "/tmp/untrusted",
        }
        environment = sanitized_environment(source)
        self.assertIn("PATH", environment)
        for credential_name in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_PROFILE",
        ):
            self.assertNotIn(credential_name, environment)
        self.assertEqual(environment["AWS_CONFIG_FILE"], os.devnull)
        self.assertEqual(environment["AWS_SHARED_CREDENTIALS_FILE"], os.devnull)
        self.assertEqual(environment["AWS_EC2_METADATA_DISABLED"], "true")
        for control_name in (
            "PYTEST_ADDOPTS",
            "TF_CLI_ARGS",
            "TF_VAR_secret",
            "PYTHONPATH",
        ):
            self.assertNotIn(control_name, environment)

    def test_failed_stage_names_the_exact_validation_unit(self) -> None:
        from scripts.validate import ValidationFailure, run_stage

        completed = subprocess.CompletedProcess(["false"], returncode=7)
        with patch("scripts.validate.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(
                ValidationFailure, "terraform:modules/example failed with exit code 7"
            ):
                run_stage("terraform:modules/example", ("false",))

    def test_missing_tool_is_reported_as_a_named_validation_failure(self) -> None:
        from scripts.validate import ValidationFailure, run_stage

        with patch(
            "scripts.validate.subprocess.run",
            side_effect=FileNotFoundError("tool is missing"),
        ):
            with self.assertRaisesRegex(
                ValidationFailure, "toolchain:Terraform could not start"
            ):
                run_stage("toolchain:Terraform", ("terraform", "version"))

    def test_provider_seed_reads_the_aws_provider_block(self) -> None:
        from scripts.validate import provider_seed

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module = root / "module"
            module.mkdir()
            (module / ".terraform.lock.hcl").write_text(
                """provider "registry.terraform.io/hashicorp/random" {
  version = "9.9.9"
}
provider "registry.terraform.io/hashicorp/aws" {
  version = "6.54.0"
}
""",
                encoding="utf-8",
            )
            with patch("scripts.validate.REPOSITORY_ROOT", root):
                self.assertEqual(provider_seed((Path("module"),)), "6.54.0")

    def test_runner_fails_when_validation_creates_a_checkout_artifact(self) -> None:
        from scripts.validate import main

        with (
            patch(
                "scripts.validate.checkout_artifacts",
                side_effect=(frozenset(), frozenset({".ruff_cache/result"})),
            ),
            patch("scripts.validate.terraform_roots", return_value=(Path("module"),)),
            patch("scripts.validate.print_toolchain"),
            patch("scripts.validate.run_stage"),
            patch("scripts.validate.validate_terraform"),
        ):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
