from __future__ import annotations

import unittest
from pathlib import Path

from scripts.validate import terraform_roots


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class TerraformCompatibilityTest(unittest.TestCase):
    def test_root_discovery_covers_every_terraform_directory(self) -> None:
        expected = {
            path.parent.relative_to(REPOSITORY_ROOT)
            for path in REPOSITORY_ROOT.rglob("*.tf")
            if ".terraform" not in path.relative_to(REPOSITORY_ROOT).parts
        }
        self.assertEqual(set(terraform_roots()), expected)

    def test_every_root_declares_approved_constraints(self) -> None:
        for relative_root in terraform_roots():
            versions = (REPOSITORY_ROOT / relative_root / "versions.tf").read_text(
                encoding="utf-8"
            )
            with self.subTest(root=relative_root):
                self.assertIn('required_version = ">= 1.10, < 2.0"', versions)
                self.assertIn('source  = "hashicorp/aws"', versions)
                self.assertIn('version = ">= 6.0, < 7.0"', versions)

    def test_every_root_owns_a_provider_lock(self) -> None:
        for relative_root in terraform_roots():
            lock_path = REPOSITORY_ROOT / relative_root / ".terraform.lock.hcl"
            with self.subTest(root=relative_root):
                self.assertTrue(lock_path.is_file())
                contents = lock_path.read_bytes()
                self.assertIn(b'version     = "6.54.0"', contents)


if __name__ == "__main__":
    unittest.main()
