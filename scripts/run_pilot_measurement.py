"""Run the credential-free pilot measurement engine against sanitized artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scripts.pilot_measurement import (
    PilotMeasurementError,
    measure_pilot,
    reviewer_report,
)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PilotMeasurementError("PILOT_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _object(path: Path, root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not resolved.is_file()
        or not resolved.is_relative_to(resolved_root)
    ):
        raise PilotMeasurementError("PILOT_ARTIFACT_PATH")
    try:
        value = json.loads(
            resolved.read_text(encoding="utf-8"), object_pairs_hook=_pairs
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PilotMeasurementError("PILOT_ARTIFACT_JSON") from error
    if not isinstance(value, dict):
        raise PilotMeasurementError("PILOT_ARTIFACT_SHAPE")
    return value


def _validate_root(root: Path) -> None:
    forbidden = (
        ".tfstate",
        ".tfplan",
        ".env",
        "credential",
        "private",
        "secret",
        "raw-log",
        "payload",
    )
    if not root.is_dir() or root.is_symlink():
        raise PilotMeasurementError("PILOT_ARTIFACT_ROOT")
    forbidden_components = {
        "secret",
        "secrets",
        "credential",
        "credentials",
        "private",
        "plans",
        "logs",
        "payloads",
    }
    for path in root.rglob("*"):
        components = {component.lower() for component in path.relative_to(root).parts}
        if (
            path.is_symlink()
            or components & forbidden_components
            or (
                path.is_file()
                and (
                    any(token in path.name.lower() for token in forbidden)
                    or path.suffix.lower()
                    in {".tfstate", ".tfplan", ".log", ".payload"}
                )
            )
        ):
            raise PilotMeasurementError("PILOT_FORBIDDEN_ARTIFACT")


def _verify_source_bytes(root: Path, package: dict[str, Any]) -> None:
    for sample_package in (package,):
        for sample in sample_package.get("samples", []):
            for source in sample.get("source_refs", []):
                locator = source["locator"]
                if locator.startswith("inline://"):
                    continue
                candidate = (root / locator).resolve()
                if (
                    not candidate.is_file()
                    or not candidate.is_relative_to(root.resolve())
                    or candidate.is_symlink()
                ):
                    raise PilotMeasurementError("PILOT_SOURCE_PATH")
                data = candidate.read_bytes()
                lowered = data.lower()
                if any(
                    marker.encode() in lowered
                    for marker in (
                        "password",
                        "secret",
                        "private key",
                        "terraform.tfstate",
                        "raw_payload",
                        "begin rsa",
                    )
                ):
                    raise PilotMeasurementError("PILOT_FORBIDDEN_ARTIFACT")
                digest = hashlib.sha256(data).hexdigest()
                if digest != source["sha256"]:
                    raise PilotMeasurementError("PILOT_SOURCE_DIGEST_MISMATCH")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    _validate_root(args.artifact_root)
    definition = _object(args.definition, args.artifact_root)
    baseline = _object(args.baseline, args.artifact_root)
    pilot = _object(args.pilot, args.artifact_root)
    _verify_source_bytes(args.artifact_root, baseline)
    _verify_source_bytes(args.artifact_root, pilot)
    result = measure_pilot(definition, baseline, pilot)
    input_paths = {
        path.resolve() for path in (args.definition, args.baseline, args.pilot)
    }
    destinations = {path.resolve() for path in (args.output, args.report)}
    if input_paths & destinations or len(destinations) != 2:
        raise PilotMeasurementError("PILOT_OUTPUT_COLLISION")
    for destination in (args.output, args.report):
        resolved = destination.resolve()
        if not resolved.parent.is_relative_to(args.artifact_root.resolve()):
            raise PilotMeasurementError("PILOT_OUTPUT_PATH")
    for destination, content in (
        (args.output, json.dumps(result, sort_keys=True) + "\n"),
        (args.report, reviewer_report(result)),
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, delete=False
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, destination)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PilotMeasurementError) as error:
        raise SystemExit(str(error)) from error
