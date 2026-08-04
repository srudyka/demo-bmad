"""Validate story records against their filenames and sprint status."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

STORY_FILENAME = re.compile(
    r"^(?P<epic>[0-9]+)-(?P<story>[0-9]+(?:[a-z])?)-(?P<slug>[a-z0-9][a-z0-9-]*)\.md$"
)
STORY_HEADING = re.compile(
    r"^# Story (?P<epic>[0-9]+)\.(?P<story>[0-9]+(?:[a-z])?): (?P<title>.+?)\s*$"
)
STATUS_LINE = re.compile(r"^Status:\s*(?P<status>[^\s]+)\s*$")
STORY_KEY_PREFIX = re.compile(r"^[0-9]+-[0-9]+(?:[a-z])?(?:-|$)")
VALID_STATUSES = frozenset(
    {"backlog", "ready-for-dev", "in-progress", "review", "done"}
)


class StoryMetadataError(ValueError):
    """Raised when story and sprint metadata are inconsistent."""


class _UniqueKeyLoader(yaml.SafeLoader):  # type: ignore[misc]
    """Reject duplicate YAML mapping keys instead of silently overwriting."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise StoryMetadataError(f"duplicate YAML key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True)
class StoryRecord:
    path: Path
    key: str
    epic: str
    story: str
    status: str


def _story_key(epic: str, story: str, slug: str) -> str:
    return f"{epic}-{story}-{slug}"


def _scalar(value: str, path: Path, line_number: int) -> str:
    value = value.strip()
    if not value:
        raise StoryMetadataError(f"{path}:{line_number}: empty metadata value")
    if value[0] in "'\"":
        quote = value[0]
        closing = value.find(quote, 1)
        trailing = value[closing + 1 :].strip() if closing >= 0 else ""
        if closing < 0 or (trailing and not trailing.startswith("#")):
            raise StoryMetadataError(
                f"{path}:{line_number}: unterminated metadata value"
            )
        value = value[1:closing]
    else:
        value = re.sub(r"\s+#.*$", "", value).strip()
        if not value:
            raise StoryMetadataError(f"{path}:{line_number}: empty metadata value")
    return value


def _frontmatter(path: Path, contents: str) -> dict[str, str]:
    lines = contents.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(
            index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"
        )
    except StopIteration as error:
        raise StoryMetadataError(f"{path}:1: unterminated frontmatter") from error
    values: dict[str, str] = {}
    for index, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line or line[0].isspace():
            raise StoryMetadataError(f"{path}:{index}: malformed frontmatter")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", key) or key in values:
            raise StoryMetadataError(f"{path}:{index}: invalid frontmatter key {key!r}")
        values[key] = _scalar(raw_value, path, index)
    return values


def _parse_sprint_status(path: Path) -> dict[str, str]:
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except UnicodeError as error:
        raise StoryMetadataError(f"{path}: invalid UTF-8: {error}") from error
    except (OSError, yaml.YAMLError, StoryMetadataError) as error:
        raise StoryMetadataError(
            f"{path}: invalid sprint status YAML: {error}"
        ) from error
    if not isinstance(document, dict):
        raise StoryMetadataError(f"{path}: invalid sprint status document")
    development_status = document.get("development_status")
    if not isinstance(development_status, dict):
        raise StoryMetadataError(f"{path}: missing development_status")
    entries: dict[str, str] = {}
    for key, value in development_status.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise StoryMetadataError(
                f"{path}: development_status keys and values must be strings"
            )
        entries[key] = value
    return entries


def discover_story_files(story_root: Path) -> tuple[Path, ...]:
    story_files: list[Path] = []
    for path in sorted(story_root.glob("*.md")):
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeError as error:
            raise StoryMetadataError(f"{path}: invalid UTF-8: {error}") from error
        has_story_heading = any(
            STORY_HEADING.fullmatch(line) for line in contents.splitlines()
        )
        if has_story_heading and STORY_FILENAME.fullmatch(path.name) is None:
            raise StoryMetadataError(f"{path}: story heading has invalid filename")
        if STORY_FILENAME.fullmatch(path.name):
            story_files.append(path)
    return tuple(story_files)


def _parse_story(path: Path) -> StoryRecord:
    match = STORY_FILENAME.fullmatch(path.name)
    if match is None:
        raise StoryMetadataError(f"{path}: invalid story filename")
    try:
        contents = path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise StoryMetadataError(f"{path}: invalid UTF-8: {error}") from error
    lines = contents.splitlines()
    headings = [STORY_HEADING.fullmatch(line) for line in lines]
    headings = [heading for heading in headings if heading is not None]
    if len(headings) != 1:
        raise StoryMetadataError(f"{path}: expected exactly one Story E.S heading")
    heading = headings[0]
    assert heading is not None
    epic = match.group("epic")
    story = match.group("story")
    if (heading.group("epic"), heading.group("story")) != (epic, story):
        raise StoryMetadataError(
            f"{path}: heading identity {heading.group('epic')}.{heading.group('story')} "
            f"does not match filename {epic}.{story}"
        )
    statuses = [STATUS_LINE.fullmatch(line) for line in lines]
    statuses = [status for status in statuses if status is not None]
    if len(statuses) != 1 or statuses[0] is None:
        raise StoryMetadataError(f"{path}: expected exactly one body Status line")
    status = statuses[0].group("status")
    if status not in VALID_STATUSES:
        raise StoryMetadataError(f"{path}: invalid body status {status!r}")
    frontmatter = _frontmatter(path, contents)
    metadata_keys = {"epic", "story", "status", "title"}
    if "story_key" in frontmatter:
        expected_key = _story_key(epic, story, match.group("slug"))
        if frontmatter["story_key"] != expected_key:
            raise StoryMetadataError(
                f"{path}: frontmatter story_key {frontmatter['story_key']!r} "
                f"does not match {expected_key!r}"
            )
    if metadata_keys & frontmatter.keys():
        required = {"epic", "story", "status"}
        missing = sorted(required - frontmatter.keys())
        if missing:
            raise StoryMetadataError(
                f"{path}: frontmatter missing {', '.join(missing)}"
            )
        expected_story = f"{epic}.{story}"
        if frontmatter["epic"] != epic or frontmatter["story"] != expected_story:
            raise StoryMetadataError(
                f"{path}: frontmatter identity {frontmatter['epic']}.{frontmatter['story']} "
                f"does not match {expected_story}"
            )
        if frontmatter["status"] != status:
            raise StoryMetadataError(
                f"{path}: frontmatter status {frontmatter['status']!r} does not match body {status!r}"
            )
    return StoryRecord(
        path, _story_key(epic, story, match.group("slug")), epic, story, status
    )


def validate_story_metadata(
    story_root: Path, sprint_status_path: Path
) -> tuple[StoryRecord, ...]:
    records = tuple(_parse_story(path) for path in discover_story_files(story_root))
    sprint_entries = _parse_sprint_status(sprint_status_path)
    malformed_story_keys = sorted(
        key
        for key in sprint_entries
        if STORY_KEY_PREFIX.match(key) and STORY_FILENAME.fullmatch(key + ".md") is None
    )
    if malformed_story_keys:
        raise StoryMetadataError(
            "sprint status has malformed story key(s): "
            + ", ".join(malformed_story_keys)
        )
    story_entries = {
        key: value
        for key, value in sprint_entries.items()
        if STORY_FILENAME.fullmatch(key + ".md") is not None
    }
    record_keys = {record.key for record in records}
    missing = sorted(record_keys - story_entries.keys())
    orphaned = sorted(story_entries.keys() - record_keys)
    if missing:
        raise StoryMetadataError(
            f"sprint status missing story key(s): {', '.join(missing)}"
        )
    if orphaned:
        raise StoryMetadataError(
            f"sprint status orphan story key(s): {', '.join(orphaned)}"
        )
    for record in records:
        sprint_status = story_entries[record.key]
        if sprint_status not in VALID_STATUSES:
            raise StoryMetadataError(
                f"sprint key {record.key} has invalid status {sprint_status!r}"
            )
        if sprint_status != record.status:
            raise StoryMetadataError(
                f"{record.path}: sprint key {record.key} status {sprint_status!r} "
                f"does not match body {record.status!r}"
            )
    return records
