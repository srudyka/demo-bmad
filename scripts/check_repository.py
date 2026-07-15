from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_PATHS = (
    re.compile(r"(^|/)\.terraform(/|$)"),
    re.compile(r"\.tfvars(?:\.json)?$", re.IGNORECASE),
    re.compile(r"\.tfstate(?:\.|$)", re.IGNORECASE),
    re.compile(
        r"(^|/)(?:tfplan|planout|[^/]+\.(?:tfplan|plan))(?:\..*)?$",
        re.IGNORECASE,
    ),
    re.compile(r"\.(?:pem|key|p12|pfx)$", re.IGNORECASE),
    re.compile(r"(^|/)(?:id_rsa|id_dsa|id_ecdsa|id_ed25519)(?:\..*)?$", re.IGNORECASE),
    re.compile(r"(^|/)\.env(?:\.|$)"),
    re.compile(r"(^|/)\.terraformrc$"),
    re.compile(r"(^|/)terraform\.rc$"),
    re.compile(r"(?:^|/)(?:\.aws/)?credentials?(?:\..*)?$", re.IGNORECASE),
    re.compile(r"(?:^|/)secrets?\.generated(?:\..*)?$", re.IGNORECASE),
    re.compile(r"(?:^|/)(?:[^/]+\.)?local\.tf$"),
    re.compile(r"(?:^|/)(?:override|[^/]+_override)\.tf(?:\.json)?$"),
)
PROHIBITED_TERRAFORM = (
    ("null_resource", re.compile(r'\bresource\s+"null_resource"\s+"')),
    ("provisioner", re.compile(r'\bprovisioner\s+"(?:local-exec|remote-exec|file)"')),
    (
        "mutable latest reference",
        re.compile(r'(?i)\b[\w-]+\s*=\s*"[^"\n]*:latest"'),
    ),
    (
        "cross-root terraform_remote_state",
        re.compile(r'\bdata\s+"terraform_remote_state"\s+"'),
    ),
    ("ungoverned Checkov suppression", re.compile(r"(?i)#\s*checkov:skip")),
)
GIT_MODULE_SOURCE = re.compile(r'(?i)\bsource\s*=\s*"(git::[^"\n]+)"')
IMMUTABLE_GIT_REF = re.compile(r"^(?:v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?|[0-9a-f]{40})$")
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)\b(?:aws_access_key_id|aws_secret_access_key|aws_session_token|client_secret)"
    r"\b[\"']?\s*[:=]\s*[\"']?([^\s\"',}\]]+)"
)
SAFE_CREDENTIAL_VALUE = re.compile(
    r"(?i)^(?:not-a-real|none|null|os\.environ|var\.|\$\{|getenv)"
)
HIGH_CONFIDENCE_SECRET = (
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    (
        "GitHub token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "private key marker",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
)
PRIVATE_KEY_MARKER = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
USES_REFERENCE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
IMMUTABLE_ACTION = re.compile(r"^[0-9a-f]{40}$")
IMMUTABLE_CONTAINER = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")
CONTENT_EXEMPT_PATHS = frozenset({"tests/hygiene/fixtures/cases.json"})


def repository_files(root: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"),
        cwd=root,
        check=True,
        capture_output=True,
    )
    return tuple(
        root / Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw
    )


def action_metadata(relative: str) -> bool:
    return relative.startswith(".github/workflows/") or (
        relative.startswith(".github/actions/")
        and Path(relative).name in {"action.yml", "action.yaml"}
    )


def scan_action_references(relative: str, contents: str) -> list[str]:
    violations: list[str] = []
    for reference in USES_REFERENCE.findall(contents):
        if reference.startswith("./"):
            continue
        if reference.startswith("docker://"):
            if not IMMUTABLE_CONTAINER.fullmatch(reference):
                violations.append(f"mutable container action {reference}: {relative}")
            continue
        if "@" not in reference:
            violations.append(f"unversioned action reference {reference}: {relative}")
            continue
        revision = reference.rsplit("@", 1)[1]
        if not IMMUTABLE_ACTION.fullmatch(revision):
            violations.append(f"mutable action reference @{revision}: {relative}")
    return violations


def git_source_is_immutable(source: str) -> bool:
    match = re.search(r"[?&]ref=([^&]+)", source)
    return match is not None and IMMUTABLE_GIT_REF.fullmatch(match.group(1)) is not None


def scan_terraform_json(value: Any) -> set[str]:
    violations: set[str] = set()
    if isinstance(value, dict):
        resource = value.get("resource")
        if isinstance(resource, dict) and "null_resource" in resource:
            violations.add("null_resource")
        data = value.get("data")
        if isinstance(data, dict) and "terraform_remote_state" in data:
            violations.add("cross-root terraform_remote_state")
        provisioner = value.get("provisioner")
        if isinstance(provisioner, dict) and any(
            name in provisioner for name in ("file", "local-exec", "remote-exec")
        ):
            violations.add("provisioner")
        for key, nested in value.items():
            if (
                key == "source"
                and isinstance(nested, str)
                and nested.startswith("git::")
            ):
                if not git_source_is_immutable(nested):
                    violations.add("mutable Git module source")
            violations.update(scan_terraform_json(nested))
    elif isinstance(value, list):
        for nested in value:
            violations.update(scan_terraform_json(nested))
    elif isinstance(value, str):
        if value.lower().endswith(":latest"):
            violations.add("mutable latest reference")
        if "checkov:skip" in value.lower():
            violations.add("ungoverned Checkov suppression")
    return violations


def scan_terraform(relative: str, path: Path, contents: str) -> list[str]:
    violations: list[str] = []
    if relative.lower().endswith(".tf.json"):
        try:
            parsed = json.loads(contents)
        except json.JSONDecodeError:
            return violations
        for policy_name in sorted(scan_terraform_json(parsed)):
            violations.append(f"{policy_name}: {relative}")
        return violations

    if path.suffix.lower() != ".tf":
        return violations
    for policy_name, pattern in PROHIBITED_TERRAFORM:
        if pattern.search(contents):
            violations.append(f"{policy_name}: {relative}")
    for source in GIT_MODULE_SOURCE.findall(contents):
        if not git_source_is_immutable(source):
            violations.append(f"mutable Git module source: {relative}")
    return violations


def scan_content(relative: str, contents: str) -> list[str]:
    violations: list[str] = []
    for policy_name, pattern in HIGH_CONFIDENCE_SECRET:
        if pattern.search(contents):
            violations.append(f"{policy_name}: {relative}")
    if relative in CONTENT_EXEMPT_PATHS:
        return violations
    for match in CREDENTIAL_ASSIGNMENT.finditer(contents):
        if not SAFE_CREDENTIAL_VALUE.match(match.group(1)):
            violations.append(f"credential assignment: {relative}")
            break
    if PRIVATE_KEY_MARKER.search(contents):
        violations.append(f"private key marker: {relative}")
    return violations


def scan_paths(root: Path, paths: tuple[Path, ...]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        for pattern in PROHIBITED_PATHS:
            if pattern.search(relative):
                violations.append(f"prohibited path: {relative}")
                break

        if not path.is_file():
            continue
        try:
            contents = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        violations.extend(scan_terraform(relative, path, contents))
        violations.extend(scan_content(relative, contents))
        if action_metadata(relative):
            violations.extend(scan_action_references(relative, contents))
    return violations


def main() -> int:
    violations = scan_paths(REPOSITORY_ROOT, repository_files(REPOSITORY_ROOT))
    if violations:
        for violation in violations:
            print(f"repository hygiene: {violation}", file=sys.stderr)
        return 1
    print("repository hygiene: tracked and candidate files passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
