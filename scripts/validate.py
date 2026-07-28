from __future__ import annotations

import os
import json
import platform
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from scripts.deployment_targets import TargetViolation, validate_target_manifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AMBIENT_CONTROL_PREFIXES = (
    "CHECKOV_",
    "MYPY_",
    "PYTEST_",
    "RUFF_",
    "TF_CLI_ARGS",
    "TF_VAR_",
)
AMBIENT_CONTROL_NAMES = frozenset({"PYTHONPATH", "VIRTUAL_ENV"})
GENERATED_DIRECTORY_NAMES = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".terraform",
        ".venv",
        "__pycache__",
    }
)
GENERATED_FILE = re.compile(
    r"(?:\.py[co]$|\.tfstate(?:\.|$)|\.tfplan(?:\.|$)|(?:^|\.)(?:tfplan|planout)(?:\.|$))"
)


class ValidationFailure(RuntimeError):
    """Raised when a named validation stage fails."""


TARGET_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("terraform", (".tf", ".tf.json", ".terraform.lock.hcl")),
    ("runtime", ("runtime/",)),
    ("contracts", ("contracts/",)),
    ("tests", ("tests/",)),
    ("workflow-policy", (".github/", "scripts/check_repository.py")),
    ("dependency", ("pyproject.toml", "uv.lock")),
    ("documentation", ("docs/", "README.md", "_bmad-output/")),
)
ROLLOUT_CATALOG = REPOSITORY_ROOT / "scripts" / "validation-rollout.json"


def classify_changed_paths(paths: Sequence[str]) -> dict[str, tuple[str, ...]]:
    """Map changed repository paths to owned validation targets.

    The mapping is deliberately conservative: shared manifests, lock files,
    scripts, and unknown paths cause the full validation target set to run.
    """
    normalized = tuple(
        sorted(
            path.replace("\\", "/")[2:]
            if path.replace("\\", "/").startswith("./")
            else path.replace("\\", "/")
            for path in paths
        )
    )
    targets: set[str] = set()
    unknown: list[str] = []
    owners: dict[str, tuple[str, ...]] = {}
    for path in normalized:
        matched = False
        for target, patterns in TARGET_RULES:
            if any(
                path == pattern
                or path.startswith(pattern)
                or (pattern.startswith(".") and path.endswith(pattern))
                for pattern in patterns
            ):
                targets.add(target)
                matched = True
        if not matched:
            unknown.append(path)
        owners[path] = tuple(
            sorted(
                target
                for target, patterns in TARGET_RULES
                if any(
                    path == pattern
                    or path.startswith(pattern)
                    or (pattern.startswith(".") and path.endswith(pattern))
                    for pattern in patterns
                )
            )
        )
    if unknown:
        targets.update(
            {"terraform", "runtime", "contracts", "tests", "workflow-policy"}
        )
    return {
        "targets": tuple(sorted(targets)),
        "unknown": tuple(unknown),
        "paths": normalized,
        "owners": tuple(
            f"{path}={','.join(owners[path]) or 'unknown'}" for path in normalized
        ),
        "terraform_roots": tuple(
            sorted(
                {
                    path.rsplit("/", 1)[0]
                    for path in normalized
                    if path.endswith((".tf", ".tf.json", ".terraform.lock.hcl"))
                }
            )
        ),
    }


def load_rollout_catalog() -> dict[str, object]:
    try:
        catalog = json.loads(ROLLOUT_CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(
            f"policy:rollout-catalog unreadable: {error}"
        ) from error
    if catalog.get("version") != "1.0.0" or not isinstance(
        catalog.get("findings"), dict
    ):
        raise ValidationFailure("policy:rollout-catalog invalid version or findings")
    for code, finding in catalog["findings"].items():
        if not isinstance(finding, dict) or finding.get("severity") not in {
            "blocking",
            "advisory",
        }:
            raise ValidationFailure(f"policy:rollout-catalog invalid severity: {code}")
        if (
            finding.get("environment") == "production"
            and finding.get("severity") != "blocking"
        ):
            raise ValidationFailure(
                f"policy:rollout-catalog production finding is not blocking: {code}"
            )
    return cast(dict[str, object], catalog)


def migration_check(changed_paths: Sequence[str], base: str | None) -> None:
    terraform_changes = tuple(
        path for path in changed_paths if path.endswith((".tf", ".tf.json"))
    )
    if not terraform_changes or not base:
        return
    diff = subprocess.run(
        ("git", "diff", "--unified=0", f"{base}...HEAD", "--", *terraform_changes),
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    block_pattern = re.compile(
        r'^([-+])\s*(resource|data|module|output|variable)\s+"([^"]+)"(?:\s+"([^"]+)")?',
        re.MULTILINE,
    )
    removed_addresses = {
        (kind, name, label or "")
        for sign, kind, name, label in block_pattern.findall(diff)
        if sign == "-"
    }
    added_addresses = {
        (kind, name, label or "")
        for sign, kind, name, label in block_pattern.findall(diff)
        if sign == "+"
    }
    if removed_addresses and added_addresses and not re.search(r"\bmoved\s*\{", diff):
        guidance = any(
            "migration" in Path(path).name.lower()
            or Path(path).parts[:1] == ("migrations",)
            for path in changed_paths
        )
        if not guidance:
            pairs = ", ".join(
                f"{kind}.{name}{('.' + label) if label else ''}"
                for kind, name, label in sorted(removed_addresses | added_addresses)
            )
            raise ValidationFailure(
                "terraform:migration: resource address churn requires a moved block or consumer migration guidance: "
                + pairs
            )


def workflow_security_violations(contents: str) -> tuple[str, ...]:
    checks = {
        "privileged trigger": r"pull_request_target|workflow_run",
        "write permission": r"(?im)(?:id-token|contents|pull-requests|actions):\s*write",
        "secret or environment": r"(?im)secrets\.|^\s+environment:\s*",
        "cache or artifact": r"upload-artifact|download-artifact|actions/cache",
        "credential or environment dump": r"github\.token|printenv|env \|",
        "plan or raw config": r"terraform plan|terraform show|raw_config|config_body",
        "variable file": r"\.tfvars(?:\.json)?",
    }
    return tuple(
        name for name, pattern in checks.items() if re.search(pattern, contents)
    )


def evaluate_workflow_security_case(contents: str) -> dict[str, object]:
    """Derive trust outcomes from the same scanner used by repository policy."""
    violations = workflow_security_violations(contents)
    return {
        "violations": violations,
        "privileged_execution": not bool(violations),
        "satisfies_required_status": not bool(violations),
    }


def artifact_policy_check() -> None:
    """Keep untrusted validation outputs free of trust-crossing artifacts."""
    workflow_root = REPOSITORY_ROOT / ".github" / "workflows"
    metadata_files = list(workflow_root.glob("*.y*ml")) + list(
        (REPOSITORY_ROOT / ".github" / "actions").glob("**/action.y*ml")
    )
    for workflow in metadata_files:
        contents = workflow.read_text(encoding="utf-8")
        trusted_plan = workflow.name == "trusted-plan.yml"
        violations = workflow_security_violations(contents)
        if trusted_plan:
            violations = tuple(
                violation
                for violation in violations
                if violation
                not in {
                    "write permission",
                    "secret or environment",
                    "cache or artifact",
                    "plan or raw config",
                }
            )
            if (
                "workflow_call" not in contents
                or "pull_request_target" in contents
                or "workflow_run" in contents
            ):
                violations += ("trusted workflow boundary",)
        if violations:
            raise ValidationFailure(
                f"policy:artifact-safety prohibited trust-crossing output in {workflow.relative_to(REPOSITORY_ROOT)}"
            )
        if not trusted_plan and re.search(r"(?m)^\s+environment:\s*", contents):
            raise ValidationFailure(
                f"policy:artifact-safety protected Environment in PR workflow {workflow.relative_to(REPOSITORY_ROOT)}"
            )


def changed_paths_from_git(base: str | None) -> tuple[str, ...]:
    """Return changed paths for a PR base, or empty for full local validation."""
    if not base:
        return ()
    try:
        result = subprocess.run(
            ("git", "diff", "--name-only", f"{base}...HEAD"),
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValidationFailure(
            f"changed-target discovery failed for base {base!r}; reproduce with "
            f"git diff --name-only {base}...HEAD"
        ) from error
    return tuple(line for line in result.stdout.splitlines() if line)


def report_changed_targets(paths: Sequence[str]) -> None:
    inventory = classify_changed_paths(paths)
    if not inventory["paths"]:
        print("Changed-target inventory: full repository validation", flush=True)
        return
    print("Changed-target inventory:", flush=True)
    print("  paths: " + ", ".join(inventory["paths"]), flush=True)
    print("  validation targets: " + ", ".join(inventory["targets"]), flush=True)
    if inventory["terraform_roots"]:
        print(
            "  Terraform roots: " + ", ".join(inventory["terraform_roots"]),
            flush=True,
        )
    print("  owners: " + "; ".join(inventory["owners"]), flush=True)
    if inventory["unknown"]:
        print(
            "  unknown paths: "
            + ", ".join(inventory["unknown"])
            + " (conservative full safety suite selected)",
            flush=True,
        )


def sanitized_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ if source is None else source)
    sanitized = {
        key: value
        for key, value in environment.items()
        if not key.startswith("AWS_")
        and key not in AMBIENT_CONTROL_NAMES
        and not key.startswith(AMBIENT_CONTROL_PREFIXES)
    }
    sanitized.update(
        {
            "AWS_CONFIG_FILE": os.devnull,
            "AWS_EC2_METADATA_DISABLED": "true",
            "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
        }
    )
    return sanitized


def terraform_roots() -> tuple[Path, ...]:
    roots: set[Path] = set()
    for terraform_file in REPOSITORY_ROOT.rglob("*.tf"):
        relative = terraform_file.relative_to(REPOSITORY_ROOT)
        if ".git" in relative.parts or ".terraform" in relative.parts:
            continue
        roots.add(relative.parent)
    if not roots:
        raise ValidationFailure("terraform discovery found no roots")
    return tuple(sorted(roots, key=Path.as_posix))


def checkout_artifacts() -> frozenset[str]:
    artifacts: set[str] = set()
    for path in REPOSITORY_ROOT.rglob("*"):
        relative = path.relative_to(REPOSITORY_ROOT)
        if ".git" in relative.parts:
            continue
        if any(part in GENERATED_DIRECTORY_NAMES for part in relative.parts) or (
            path.is_file() and GENERATED_FILE.search(relative.name)
        ):
            artifacts.add(relative.as_posix())
    return frozenset(artifacts)


def run_stage(
    label: str,
    command: Sequence[str],
    *,
    cwd: Path = REPOSITORY_ROOT,
    environment: Mapping[str, str] | None = None,
) -> None:
    print(f"\n==> {label}", flush=True)
    try:
        result = subprocess.run(
            tuple(command),
            cwd=cwd,
            env=dict(environment)
            if environment is not None
            else sanitized_environment(),
            check=False,
        )
    except OSError as error:
        raise ValidationFailure(f"{label} could not start: {error}") from error
    if result.returncode != 0:
        raise ValidationFailure(f"{label} failed with exit code {result.returncode}")


def provider_seed(roots: Sequence[Path]) -> str:
    versions: dict[Path, str] = {}
    pattern = re.compile(
        r'provider\s+"registry\.terraform\.io/hashicorp/aws"\s*\{'
        r'.*?^\s*version\s+=\s+"([^"]+)"$',
        re.MULTILINE | re.DOTALL,
    )
    for root in roots:
        lock_path = REPOSITORY_ROOT / root / ".terraform.lock.hcl"
        try:
            contents = lock_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValidationFailure(
                f"terraform:{root}: cannot read provider lock: {error}"
            ) from error
        match = pattern.search(contents)
        if match is None:
            raise ValidationFailure(
                f"terraform:{root}: lock has no hashicorp/aws version"
            )
        versions[root] = match.group(1)
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        detail = ", ".join(f"{root}={version}" for root, version in versions.items())
        raise ValidationFailure(
            f"terraform locks disagree on hashicorp/aws provider versions: {detail}"
        )
    return unique_versions.pop()


def print_toolchain(roots: Sequence[Path]) -> None:
    print("Toolchain:")
    print(f"  Python {sys.version.split()[0]}")
    print(f"  AWS provider {provider_seed(roots)} (resolved lock seed)")
    for label, command in (
        ("Terraform", ("terraform", "version")),
        ("uv", ("uv", "--version")),
        ("Ruff", ("ruff", "--version")),
        ("mypy", ("mypy", "--version")),
        ("pytest", ("pytest", "--version")),
        ("Checkov", ("checkov", "--version")),
    ):
        run_stage(f"toolchain:{label}", command)


def validate_terraform(roots: Sequence[Path]) -> None:
    base_environment = sanitized_environment()
    lock_snapshots = {
        REPOSITORY_ROOT / root / ".terraform.lock.hcl": (
            REPOSITORY_ROOT / root / ".terraform.lock.hcl"
        ).read_bytes()
        for root in roots
    }
    with tempfile.TemporaryDirectory(prefix="ecs-jobs-terraform-") as temporary:
        temporary_root = Path(temporary)
        plugin_cache = temporary_root / "plugin-cache"
        plugin_cache.mkdir()
        provider_mirror = (
            temporary_root
            / "provider-mirror"
            / "registry.terraform.io"
            / "demo-bmad"
            / "cell"
            / "0.1.0"
            / f"{platform.system().lower()}_{platform.machine().lower().replace('x86_64', 'amd64').replace('aarch64', 'arm64')}"
        )
        provider_mirror.mkdir(parents=True)
        provider_binary = provider_mirror / "terraform-provider-cell_v0.1.0"
        run_stage(
            "terraform:cell-provider:build",
            (
                "go",
                "build",
                "-o",
                str(provider_binary),
                ".",
            ),
            cwd=REPOSITORY_ROOT / "tools" / "terraform-provider-cell",
            environment=base_environment,
        )
        cli_config = temporary_root / "terraform.tfrc"
        cli_config.write_text(
            "provider_installation {\n"
            "  dev_overrides {\n"
            f'    "demo-bmad/cell" = "{provider_binary.parent}"\n'
            "  }\n"
            "  filesystem_mirror {\n"
            f'    path = "{provider_binary.parents[5]}"\n'
            "  }\n"
            "  direct {}\n"
            "}\n",
            encoding="utf-8",
        )
        for root in roots:
            data_dir = temporary_root / root.as_posix().replace("/", "-")
            environment = base_environment | {
                "TF_DATA_DIR": str(data_dir),
                "TF_PLUGIN_CACHE_DIR": str(plugin_cache),
                "TF_CLI_CONFIG_FILE": str(cli_config),
            }
            label = f"terraform:{root}"
            try:
                run_stage(
                    f"{label}:init",
                    (
                        "terraform",
                        "init",
                        "-backend=false",
                        "-input=false",
                        "-no-color",
                    ),
                    cwd=REPOSITORY_ROOT / root,
                    environment=environment,
                )
            finally:
                lock_path = REPOSITORY_ROOT / root / ".terraform.lock.hcl"
                lock_path.write_bytes(lock_snapshots[lock_path])
            # Reusable modules that declare provider configuration aliases are
            # validated through a real caller (the basic example below). A
            # standalone validate of such a child module has no provider
            # configuration to bind to the alias and Terraform reports the
            # misleading "provider configuration not present" state error.
            versions_path = REPOSITORY_ROOT / root / "versions.tf"
            if "configuration_aliases" in versions_path.read_text(encoding="utf-8"):
                print(
                    f"{label}:validate skipped; provider aliases are validated by a caller",
                    flush=True,
                )
                continue
            run_stage(
                f"{label}:validate",
                ("terraform", "validate", "-no-color"),
                cwd=REPOSITORY_ROOT / root,
                environment=environment,
            )


def validate_terraform_security() -> None:
    base_command = ("checkov", "--framework", "terraform", "--quiet", "--compact")
    network_module = (
        REPOSITORY_ROOT / "modules" / "ecs-scheduled-job" / "network.tf"
    ).read_text(encoding="utf-8")
    if (
        len(
            re.findall(
                r'^resource\s+"aws_security_group"\s+', network_module, re.MULTILINE
            )
        )
        != 1
    ):
        raise ValidationFailure(
            "security:terraform:job-module: CKV2_AWS_5 exception is only valid for the single optional job security group"
        )
    run_stage(
        "security:terraform:job-module",
        # Story 2.3 deliberately creates an optional SG before Story 2.4
        # attaches it to the Fargate task definition. Keep this exception
        # centralized and auditable instead of embedding an inline skip.
        (
            *base_command,
            "-d",
            "modules/ecs-scheduled-job",
            "--skip-check",
            "CKV2_AWS_5",
        ),
    )
    # MVP Cells are account/Region-local (AD-1), so an unmanaged replication
    # destination would weaken rollback and recovery. The inbox also has no
    # event consumer until the later Cell processor exists. The normalizer is
    # intentionally regional/no-VPC, uses source-queue redrive instead of a
    # Lambda async DLQ, and relies on a reviewed artifact hash rather than a
    # code-signing profile. The publisher Function URL is IAM-authenticated
    # and account-scoped; CKV_AWS_301 treats all Function URLs as public even
    # when AWS_IAM is required, so keep that exception limited to this Cell
    # module.
    run_stage(
        "security:terraform:platform-cell",
        (
            *base_command,
            "-d",
            "modules/ecs-scheduled-job-platform",
            "--skip-check",
            "CKV_AWS_50,CKV_AWS_116,CKV_AWS_117,CKV_AWS_144,CKV_AWS_272,CKV_AWS_301,CKV_AWS_356,CKV2_AWS_51,CKV2_AWS_62",
        ),
    )
    run_stage(
        "security:terraform:canary-fixture",
        (*base_command, "-d", "fixtures/canary"),
    )


def validate_trusted_target_contract() -> None:
    """Run target binding validation as a required repository gate."""
    import json

    path = REPOSITORY_ROOT / "tests" / "contract" / "fixtures" / "target-manifest.json"
    try:
        validate_target_manifest(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TargetViolation) as error:
        raise ValidationFailure(f"trusted-target-contract: {error}") from error


def validate_trusted_plan_contract() -> None:
    """Keep trusted-plan reporting and artifact boundaries executable and pure."""
    from scripts.trusted_plan import summarize_plan

    try:
        summary = summarize_plan({"resource_changes": []}, policy_status="passed")
        if not summary["no_op"] or summary["policy_status"] != "passed":
            raise ValidationFailure("trusted-plan-contract: unexpected no-op summary")
    except TargetViolation as error:
        raise ValidationFailure(f"trusted-plan-contract: {error}") from error


def main() -> int:
    print("AWS credentials are not passed to validation subprocesses.")
    artifacts_before = checkout_artifacts()
    validation_root = Path(
        os.environ.get("VALIDATION_TEMP_ROOT", tempfile.gettempdir())
    )
    mypy_cache = validation_root / "mypy-cache"
    stages: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("terraform:format", ("terraform", "fmt", "-check", "-recursive", ".")),
        (
            "python:format",
            ("ruff", "format", "--check", "--no-cache", "runtime", "scripts", "tests"),
        ),
        ("python:lint", ("ruff", "check", "--no-cache", "runtime", "scripts", "tests")),
        (
            "python:type",
            (
                "mypy",
                "--cache-dir",
                str(mypy_cache),
                "runtime",
                "scripts",
                "tests/contract/support",
            ),
        ),
        (
            "tests:contract-runtime-integration-hygiene",
            ("pytest", "tests", "runtime", "-q", "-p", "no:cacheprovider"),
        ),
        (
            "repository:hygiene",
            (sys.executable, "scripts/check_repository.py"),
        ),
    )
    try:
        changed_paths = changed_paths_from_git(os.environ.get("VALIDATION_BASE_SHA"))
        report_changed_targets(changed_paths)
        load_rollout_catalog()
        migration_check(changed_paths, os.environ.get("VALIDATION_BASE_SHA"))
        artifact_policy_check()
        validate_trusted_target_contract()
        validate_trusted_plan_contract()
        roots = terraform_roots()
        print_toolchain(roots)
        for label, command in stages[:1]:
            run_stage(label, command)
        validate_terraform(roots)
        for label, command in stages[1:-1]:
            run_stage(label, command)
        validate_terraform_security()
        for label, command in stages[-1:]:
            run_stage(label, command)
        new_artifacts = checkout_artifacts() - artifacts_before
        if new_artifacts:
            raise ValidationFailure(
                "checkout cleanliness found generated artifacts: "
                + ", ".join(sorted(new_artifacts))
            )
    except ValidationFailure as error:
        print(f"validation failed: {error}", file=sys.stderr)
        return 1
    print(
        "\nValidation passed: no AWS plan, state, credential, or deployment artifact created."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
