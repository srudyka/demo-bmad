"""Run the credential-free pilot launch evaluator."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scripts.pilot_launch import (
    PilotLaunchError,
    build_launch_authorization,
    evaluate_launch_checklist,
    reviewer_report,
    validate_launch_authorization,
)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PilotLaunchError("PILOT_LAUNCH_DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def _load(path: Path, root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not resolved.is_file()
        or not resolved.is_relative_to(resolved_root)
    ):
        raise PilotLaunchError("PILOT_LAUNCH_ARTIFACT_PATH")
    forbidden = {
        ".git",
        ".terraform",
        "terraform.tfstate",
        "terraform.tfstate.backup",
        "credentials",
        "secrets",
    }
    if any(
        part.casefold() in forbidden
        for part in resolved.relative_to(resolved_root).parts
    ):
        raise PilotLaunchError("PILOT_LAUNCH_ARTIFACT_PATH")
    try:
        value = json.loads(
            resolved.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PilotLaunchError("PILOT_LAUNCH_ARTIFACT_JSON") from error
    if not isinstance(value, dict):
        raise PilotLaunchError("PILOT_LAUNCH_ARTIFACT_SHAPE")
    return value


def _load_approvals(path: Path, root: Path) -> list[dict[str, Any]]:
    value = _load(path, root)
    approvals = value.get("approvals")
    if not isinstance(approvals, list) or any(
        not isinstance(item, dict) for item in approvals
    ):
        raise PilotLaunchError("PILOT_LAUNCH_APPROVAL_SHAPE")
    return approvals


def _write(path: Path, content: str, root: Path) -> None:
    resolved = path.resolve()
    if not resolved.parent.is_relative_to(root.resolve()):
        raise PilotLaunchError("PILOT_LAUNCH_OUTPUT_PATH")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checklist", type=Path, required=True)
    parser.add_argument("--measurement", type=Path)
    parser.add_argument("--approvals", type=Path)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifact_root
    if not root.is_dir() or root.is_symlink():
        raise PilotLaunchError("PILOT_LAUNCH_ARTIFACT_ROOT")
    checklist = _load(args.checklist, root)
    measurement = _load(args.measurement, root) if args.measurement else None
    approvals = _load_approvals(args.approvals, root) if args.approvals else []
    result = evaluate_launch_checklist(
        checklist, measurement=measurement, approvals=approvals
    )
    authorization = build_launch_authorization(checklist, approvals, now=None)
    validate_launch_authorization(authorization)
    destinations = {args.output.resolve(), args.report.resolve()}
    if (
        len(destinations) != 2
        or args.checklist.resolve() in destinations
        or (args.measurement and args.measurement.resolve() in destinations)
        or (args.approvals and args.approvals.resolve() in destinations)
    ):
        raise PilotLaunchError("PILOT_LAUNCH_OUTPUT_COLLISION")
    _write(args.output, json.dumps(authorization, sort_keys=True) + "\n", root)
    _write(args.report, reviewer_report(result), root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PilotLaunchError, TypeError, KeyError) as error:
        raise SystemExit(str(error)) from error
