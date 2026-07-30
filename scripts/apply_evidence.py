"""Create bounded post-apply identity and verification projections."""

from __future__ import annotations

from typing import Any, Mapping


def _resources(module: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    found = list(module.get("resources", []))
    for child in module.get("child_modules", []):
        if isinstance(child, Mapping):
            found.extend(_resources(child))
    return [item for item in found if isinstance(item, Mapping)]


def collect_resource_identities(state: Mapping[str, Any]) -> dict[str, str]:
    """Project only stable address/type/provider data; never state values."""
    root = state.get("values", {}).get("root_module", {})
    result: dict[str, str] = {}
    for resource in _resources(root if isinstance(root, Mapping) else {}):
        address = resource.get("address")
        if not isinstance(address, str) or not address:
            continue
        resource_type = resource.get("type", "unknown")
        provider = resource.get("provider_name", "unknown")
        result[address] = f"{provider}:{resource_type}"
    return result


def build_verification(
    *,
    manifest: Mapping[str, Any],
    state: Mapping[str, Any],
    resource_identities: Mapping[str, str],
    required: tuple[str, ...] = ("target_identity", "lifecycle", "task_revision"),
) -> dict[str, Any]:
    """Produce a fail-closed verification record from actual post-apply state."""
    root = state.get("values", {}).get("root_module")
    checks = {
        "target_identity": bool(manifest.get("account_id") and manifest.get("region")),
        "lifecycle": isinstance(root, Mapping),
        "task_revision": any("task_definition" in key for key in resource_identities),
    }
    missing = [name for name in required if checks.get(name) is not True]
    return {
        "schema_version": "1.0.0",
        "status": "passed" if not missing else "blocked",
        "launch_enabled": not missing,
        "missing": missing,
        "checks": {name: checks.get(name) is True for name in required},
        "observed_at": "post-apply-state",
        "evidence_refs": {"terraform_state_projection": "runner-local"},
        "remediation": "Keep launch disabled and execute reviewed recovery."
        if missing
        else "",
        "decision": "blocked" if missing else "resume-eligible",
    }
