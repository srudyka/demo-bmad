from __future__ import annotations

import unittest

from scripts.validate import (
    classify_changed_paths,
    load_rollout_catalog,
    migration_check,
)


class ValidationTargetTest(unittest.TestCase):
    def test_classifies_all_owned_target_families(self) -> None:
        inventory = classify_changed_paths(
            (
                "modules/ecs-scheduled-job/main.tf",
                "runtime/process_manager/src/process_manager/domain.py",
                "contracts/v1/schemas/common.schema.json",
                "tests/contract/test_contract_iam.py",
                ".github/workflows/validate.yml",
                "pyproject.toml",
                "docs/runbooks/validation.md",
            )
        )
        self.assertEqual(
            inventory["targets"],
            (
                "contracts",
                "dependency",
                "documentation",
                "runtime",
                "terraform",
                "tests",
                "workflow-policy",
            ),
        )
        self.assertEqual(inventory["unknown"], ())

    def test_unknown_path_is_reported_and_selects_conservative_suite(self) -> None:
        inventory = classify_changed_paths(("new-policy-language/example.policy",))
        self.assertEqual(inventory["unknown"], ("new-policy-language/example.policy",))
        self.assertEqual(
            inventory["targets"],
            ("contracts", "runtime", "terraform", "tests", "workflow-policy"),
        )

    def test_empty_inventory_is_reserved_for_full_local_validation(self) -> None:
        self.assertEqual(classify_changed_paths(())["targets"], ())

    def test_each_changed_path_has_an_owner_record(self) -> None:
        inventory = classify_changed_paths(("runtime/example.py", "new.policy"))
        self.assertIn("runtime/example.py=runtime", inventory["owners"])
        self.assertIn("new.policy=unknown", inventory["owners"])

    def test_rollout_catalog_is_versioned_and_production_blocking(self) -> None:
        catalog = load_rollout_catalog()
        self.assertEqual(catalog["version"], "1.0.0")
        self.assertEqual(catalog["findings"]["secret-exposure"]["severity"], "blocking")

    def test_migration_check_accepts_explicit_ci_base_revision(self) -> None:
        migration_check(("README.md",), "base-sha")


if __name__ == "__main__":
    unittest.main()
