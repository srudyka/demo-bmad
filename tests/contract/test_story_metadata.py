from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.story_metadata import StoryMetadataError, validate_story_metadata


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "story-metadata"


def _fixture_copy(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "stories"
    root.mkdir()
    shutil.copy(FIXTURE_ROOT / "legacy-story.md", root / "1-1-legacy-story.md")
    shutil.copy(
        FIXTURE_ROOT / "frontmatter-story.md", root / "2-2-frontmatter-story.md"
    )
    shutil.copy(FIXTURE_ROOT / "sprint-status.yaml", root / "sprint-status.yaml")
    return root, root / "sprint-status.yaml"


def test_fixture_catalog_is_executable() -> None:
    cases = json.loads((FIXTURE_ROOT / "cases.json").read_text(encoding="utf-8"))
    assert cases == {
        "passing": ["legacy", "frontmatter"],
        "failing": [
            "heading_identity",
            "frontmatter_status",
            "sprint_status",
            "missing_sprint_entry",
            "orphan_sprint_entry",
            "malformed_status",
            "invalid_filename",
            "malformed_sprint_key",
            "duplicate_yaml_key",
            "invalid_utf8",
        ],
    }


def test_consistent_legacy_and_frontmatter_records_pass(tmp_path: Path) -> None:
    story_root, sprint_status = _fixture_copy(tmp_path)

    records = validate_story_metadata(story_root, sprint_status)

    assert [record.key for record in records] == [
        "1-1-legacy-story",
        "2-2-frontmatter-story",
    ]


def test_quoted_sprint_status_is_normalized(tmp_path: Path) -> None:
    story_root, sprint_status = _fixture_copy(tmp_path)
    sprint_status.write_text(
        sprint_status.read_text(encoding="utf-8").replace(
            "2-2-frontmatter-story: review", '2-2-frontmatter-story: "review"'
        ),
        encoding="utf-8",
    )

    validate_story_metadata(story_root, sprint_status)


@pytest.mark.parametrize(
    ("case", "mutation", "expected"),
    [
        (
            "heading_identity",
            lambda root: (root / "1-1-legacy-story.md").write_text(
                (root / "1-1-legacy-story.md")
                .read_text(encoding="utf-8")
                .replace("# Story 1.1:", "# Story 1.2:"),
                encoding="utf-8",
            ),
            "heading identity",
        ),
        (
            "frontmatter_status",
            lambda root: (root / "2-2-frontmatter-story.md").write_text(
                (root / "2-2-frontmatter-story.md")
                .read_text(encoding="utf-8")
                .replace("status: review", "status: done"),
                encoding="utf-8",
            ),
            "frontmatter status",
        ),
        (
            "missing_sprint_entry",
            lambda root: (root / "sprint-status.yaml").write_text(
                "development_status:\n  1-1-legacy-story: done\n",
                encoding="utf-8",
            ),
            "missing story key",
        ),
        (
            "sprint_status",
            lambda root: (root / "sprint-status.yaml").write_text(
                (root / "sprint-status.yaml")
                .read_text(encoding="utf-8")
                .replace(
                    "2-2-frontmatter-story: review", "2-2-frontmatter-story: done"
                ),
                encoding="utf-8",
            ),
            "does not match body",
        ),
        (
            "orphan_sprint_entry",
            lambda root: (root / "sprint-status.yaml").write_text(
                (root / "sprint-status.yaml").read_text(encoding="utf-8")
                + "  9-9-orphan-story: done\n",
                encoding="utf-8",
            ),
            "orphan story key",
        ),
        (
            "malformed_status",
            lambda root: (root / "1-1-legacy-story.md").write_text(
                (root / "1-1-legacy-story.md")
                .read_text(encoding="utf-8")
                .replace("Status: done", "Status: maybe"),
                encoding="utf-8",
            ),
            "invalid body status",
        ),
        (
            "invalid_filename",
            lambda root: (root / "4-3-bad_story.md").write_text(
                "# Story 4.3: Bad filename\n\nStatus: done\n", encoding="utf-8"
            ),
            "story heading has invalid filename",
        ),
        (
            "malformed_sprint_key",
            lambda root: (root / "sprint-status.yaml").write_text(
                (root / "sprint-status.yaml").read_text(encoding="utf-8")
                + "  4-3-bad_story: done\n",
                encoding="utf-8",
            ),
            "malformed story key",
        ),
        (
            "duplicate_yaml_key",
            lambda root: (root / "sprint-status.yaml").write_text(
                (root / "sprint-status.yaml").read_text(encoding="utf-8")
                + "development_status: {}\n",
                encoding="utf-8",
            ),
            "duplicate YAML key",
        ),
        (
            "invalid_utf8",
            lambda root: (root / "1-1-legacy-story.md").write_bytes(b"\xff"),
            "invalid UTF-8",
        ),
    ],
)
def test_negative_metadata_cases_fail_closed(
    tmp_path: Path, case: str, mutation: object, expected: str
) -> None:
    story_root, sprint_status = _fixture_copy(tmp_path)
    assert case
    mutation(story_root)  # type: ignore[operator]

    with pytest.raises(StoryMetadataError, match=expected):
        validate_story_metadata(story_root, sprint_status)
