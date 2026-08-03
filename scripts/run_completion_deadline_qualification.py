"""Project sanitized completion/deadline/alert qualification evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.completion_deadline_qualification import (
    completion_deadline_projection,
    validate_completion_qualification_evidence,
)
from scripts.ecs_qualification import (
    build_launch_runtime_manifest,
    seal_launch_runtime_manifest,
    validate_qualification_evidence,
)


def _object(path: Path, root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not resolved.is_relative_to(resolved_root)
        or not resolved.is_file()
    ):
        raise ValueError(f"qualification artifact is outside the allowed root: {path}")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"qualification artifact must be an object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = _object(args.evidence, args.artifact_root)
    bindings = _object(args.bindings, args.artifact_root)
    configuration = _object(args.configuration, args.artifact_root)
    validate_qualification_evidence(evidence, configuration)
    validate_completion_qualification_evidence(evidence, configuration)
    manifest = build_launch_runtime_manifest(
        release_version=str(configuration["release_version"]),
        compatibility_package=str(configuration["compatibility_package"]),
        account_id=str(configuration["account_id"]),
        region=str(configuration["region"]),
        cell_identity=str(configuration["cell_identity"]),
        task_definition_arn=str(configuration["task_definition_arn"]),
        deployment_identity_id=str(configuration["deployment_identity_id"]),
        injected_fault=str(configuration["injected_fault"]),
        expected_result=str(configuration["expected_result"]),
        test_configuration=configuration["test_configuration"],
        policy_versions=configuration["policy_versions"],
        evidence=evidence,
        bindings=bindings,
    )
    controls = completion_deadline_projection(manifest, evidence["results"], bindings)
    sealed = seal_launch_runtime_manifest(manifest, controls)
    args.output.write_text(json.dumps(sealed, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
