from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import TypedDict, cast

from scripts.check_repository import scan_paths


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Case(TypedDict):
    name: str
    path: str
    content: str


class Cases(TypedDict):
    reject: list[Case]
    allow: list[Case]


def load_cases() -> Cases:
    fixture = REPOSITORY_ROOT / "tests/hygiene/fixtures/cases.json"
    return cast(Cases, json.loads(fixture.read_text(encoding="utf-8")))


class RepositoryHygieneTest(unittest.TestCase):
    def test_rejects_every_prohibited_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for case in load_cases()["reject"]:
                path = root / case["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(case["content"], encoding="utf-8")
                with self.subTest(case=case["name"]):
                    self.assertTrue(scan_paths(root, (path,)))

    def test_allows_locks_source_migrations_and_inert_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for case in load_cases()["allow"]:
                path = root / case["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(case["content"], encoding="utf-8")
                with self.subTest(case=case["name"]):
                    self.assertEqual(scan_paths(root, (path,)), [])


if __name__ == "__main__":
    unittest.main()
