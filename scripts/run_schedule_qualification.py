"""Run a sanitized schedule qualification evidence projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.schedule_qualification import (
    build_qualification_manifest,
    readiness_projection,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
    configuration = json.loads(args.configuration.read_text(encoding="utf-8"))
    manifest = build_qualification_manifest(
        release_version=str(configuration["release_version"]),
        compatibility_package=str(configuration["compatibility_package"]),
        account_id=str(configuration["account_id"]),
        region=str(configuration["region"]),
        cell_identity=str(configuration["cell_identity"]),
        test_configuration=configuration["test_configuration"],
        policy_versions=configuration["policy_versions"],
        evidence=evidence,
        bindings=bindings,
    )
    manifest["controls"] = readiness_projection(manifest, evidence["results"], bindings)
    args.output.write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
