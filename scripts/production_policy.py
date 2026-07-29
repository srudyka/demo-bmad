"""Credential-free, bounded production policy decisions for trusted plans."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import hashlib
import hmac
import os
from pathlib import Path
import re
from typing import Any, Mapping, cast

from scripts.deployment_targets import TargetViolation

POLICY_ID = "production-readiness"
POLICY_VERSION = "1.0.0"
SEVERITIES = {"advisory", "blocking"}
NON_EXEMPTIBLE = {
    "TARGET_BINDING",
    "PLAINTEXT_SECRET",
    "PRIVILEGE_ESCALATION",
    "MUTABLE_DEPLOYMENT_IDENTITY",
    "OCCURRENCE_TRACKING_MISSING",
}
CATALOG_PATH = Path(__file__).resolve().parents[1] / "contracts/v1/catalogs/production-policy.json"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_policy_catalog() -> dict[str, Any]:
    """Load the normative catalog and fail closed on missing/ambiguous data."""
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TargetViolation("POLICY_CATALOG_UNREADABLE") from error
    if not isinstance(catalog, dict):
        raise TargetViolation("POLICY_CATALOG_SHAPE")
    if (
        catalog.get("schema_version") != "1.0.0"
        or catalog.get("policy_id") != POLICY_ID
        or catalog.get("policy_version") != POLICY_VERSION
        or catalog.get("production_disposition") != "BLOCK"
        or catalog.get("unknown_policy_disposition") != "BLOCK"
        or not isinstance(catalog.get("qualifying_change_categories"), list)
        or not isinstance(catalog.get("non_exemptible"), list)
        or set(catalog.get("non_exemptible", [])) != NON_EXEMPTIBLE
        or not isinstance(catalog.get("required_production_controls"), Mapping)
        or not isinstance(catalog.get("rules"), Mapping)
        or not isinstance(catalog.get("exception_required_fields"), list)
        or not isinstance(catalog.get("qualifying_change_policy"), Mapping)
        or not isinstance(catalog.get("exception_owner"), str)
    ):
        raise TargetViolation("POLICY_CATALOG_INVALID")
    return catalog


def _parse_utc(value: str, code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TargetViolation(code) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TargetViolation(code)
    return parsed.astimezone(timezone.utc)


def _strings(value: Any) -> set[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {value}
        return _strings(decoded) if decoded != value else {value}
    if isinstance(value, Mapping):
        result: set[str] = set()
        for key, child in value.items():
            if str(key).lower() in {"action", "actions", "resource", "resources"}:
                result.update(_strings(child))
            else:
                result.update(_strings(child))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(_strings(child))
        return result
    return set()


def _policy_statements(after: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    statements: list[Mapping[str, Any]] = []
    for _, value in _walk(after):
        if isinstance(value, Mapping) and "Statement" in value:
            raw = value["Statement"]
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    continue
            if isinstance(raw, Mapping):
                raw = [raw]
            if isinstance(raw, list):
                statements.extend(item for item in raw if isinstance(item, Mapping))
    return statements


def _image_values(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if "image" in str(key).lower() and isinstance(child, str):
                result.append(child)
            result.extend(_image_values(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_image_values(child))
    return result


def _control_findings(changes: list[Mapping[str, Any]], catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Require explicit, attributable control evidence for every non-empty production plan."""
    controls = catalog["required_production_controls"]
    assert isinstance(controls, Mapping)
    text = json.dumps(changes, sort_keys=True, separators=(",", ":")).lower()
    checks = {
        "tags": all(str(tag).lower() in text for tag in controls["tags"]),
        "logs": "log" in text,
        "retention": "retention" in text,
        "alarms": "alarm" in text,
        "notifications": any(token in text for token in ("notification", "sns", "topic")),
        "acknowledgement": any(token in text for token in ("acknowledg", "enabled")),
        "cell_contract": any(token in text for token in ("cell_contract", "cell-contract", "cellcontract")),
    }
    missing = [name for name, present in checks.items() if not present]
    if not missing:
        return []
    return [_finding("MISSING_PRODUCTION_CONTROLS", "plan", "required production controls must have explicit evidence", "missing=" + ",".join(missing), "add bounded evidence for tags, observability, lifecycle and Cell contract", exemptible=False)]


def _finding(
    code: str,
    address: str,
    requirement: str,
    evidence: str,
    remediation: str,
    *,
    exemptible: bool = True,
) -> dict[str, Any]:
    return {
        "policy_id": f"{POLICY_ID}.{code.lower()}",
        "policy_version": POLICY_VERSION,
        "address": address[:200],
        "requirement": requirement[:240],
        "evidence": evidence[:160],
        "severity": "blocking",
        "remediation": remediation[:240],
        "exemptible": exemptible and code not in NON_EXEMPTIBLE,
    }


def _walk(value: Any) -> list[tuple[str, Any]]:
    result: list[tuple[str, Any]] = []
    def visit(node: Any, path: str) -> None:
        result.append((path, node))
        if isinstance(node, Mapping):
            for key, child in node.items():
                visit(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{path}[{index}]")
    visit(value, "after")
    return result


def _changes(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise TargetViolation("POLICY_PLAN_SHAPE")
    if any(not isinstance(item, Mapping) for item in changes):
        raise TargetViolation("POLICY_PLAN_CHANGE")
    result: list[Mapping[str, Any]] = []
    for item in changes:
        if not isinstance(item, Mapping) or not isinstance(item.get("address"), str):
            raise TargetViolation("POLICY_PLAN_CHANGE")
        change = item.get("change")
        if not isinstance(change, Mapping) or not isinstance(change.get("actions"), list):
            raise TargetViolation("POLICY_PLAN_CHANGE")
        result.append(item)
    return result


def classify_qualifying_changes(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Return a stable catalog classification; unknown shapes fail closed."""
    catalog = load_policy_catalog()
    changes = _changes(plan)
    categories: set[str] = set()
    for item in changes:
        address = str(item.get("address", ""))
        if not address or ".." in address:
            raise TargetViolation("POLICY_CHANGE_ADDRESS")
        lower = address.lower()
        if any(token in lower for token in ("iam", "role", "policy", "oidc")):
            categories.add("iam")
        elif any(
            token in lower
            for token in ("vpc", "subnet", "security_group", "route", "network")
        ):
            categories.add("network")
        elif any(
            token in lower
            for token in ("scheduler", "schedule", "task_definition", "ecs")
        ):
            categories.add("launch")
        elif any(
            token in lower
            for token in ("ecr", "github", "workflow", "module", "provider")
        ):
            categories.add("supply-chain")
        else:
            categories.add("other")
            other_scope = str(catalog["qualifying_change_policy"]["other"]["scope"])
            if not any(token in lower for token in other_scope.split("|")):
                raise TargetViolation("POLICY_CATEGORY_UNKNOWN")
    allowed = set(catalog["qualifying_change_categories"])
    if not categories.issubset(allowed):
        raise TargetViolation("POLICY_CATEGORY_UNKNOWN")
    return {
        "catalog_id": POLICY_ID,
        "catalog_version": POLICY_VERSION,
        "categories": sorted(categories),
        "security_review_required": bool(
            categories & {"iam", "network", "launch", "supply-chain"}
        ),
    }


def evaluate_production_plan(
    plan: Mapping[str, Any],
    *,
    target: Mapping[str, Any],
    source_commit: str,
    plan_sha256: str,
    now: str,
    hygiene_violations: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate only safe plan metadata and return a retained, non-secret decision."""
    catalog = load_policy_catalog()
    if target.get("environment") != "production":
        raise TargetViolation("POLICY_TARGET_ENVIRONMENT")
    if not SHA1.fullmatch(source_commit) or not SHA256.fullmatch(plan_sha256):
        raise TargetViolation("POLICY_BINDING_CHECKSUM")
    _parse_utc(now, "POLICY_TIMESTAMP")
    findings: list[dict[str, Any]] = []
    for violation in hygiene_violations or []:
        findings.append(_finding("SUPPLY_CHAIN_HYGIENE", "repository", "repository hygiene must pass", violation[:160], "remove the prohibited or mutable repository content", exemptible=False))
    changes = _changes(plan)
    if not changes:
        findings.append(_finding(
            "MISSING_PRODUCTION_CONTROLS", "plan",
            "production plans must provide control evidence",
            "empty-plan-no-control-evidence",
            "provide logs, retention, alarms, notifications, ownership and lifecycle evidence",
            exemptible=False,
        ))
    else:
        findings.extend(_control_findings(changes, catalog))
    for item in changes:
        address = str(item.get("address", ""))
        change: Mapping[str, Any] = (
            cast(Mapping[str, Any], item.get("change"))
            if isinstance(item.get("change"), Mapping)
            else {}
        )
        after = change.get("after") if isinstance(change.get("after"), Mapping) else {}
        actions = change["actions"]
        if any(
            action not in {"create", "update", "delete", "no-op"} for action in actions
        ):
            raise TargetViolation("POLICY_ACTION_UNKNOWN")
        lower = address.lower()
        if "iam" in lower or "role" in lower or "policy" in lower or "oidc" in lower:
            actions_found = _strings(after)
            resources_found = _strings(after)
            if "*" in actions_found or "*" in resources_found or any("iam:" in value and value.endswith("*") for value in actions_found):
                findings.append(_finding("IAM_WILDCARD", address, "IAM actions and resources must be least privilege", "wildcard-policy-document", "scope actions, resources and conditions", exemptible=False))
            statements = _policy_statements(after)
            delegated = [statement for statement in statements if any("passrole" in action.lower() or "assumerole" in action.lower() for action in _strings(statement.get("Action", statement.get("actions", []))))]
            if delegated and any(not isinstance(statement.get("Condition"), Mapping) for statement in delegated):
                findings.append(_finding("IAM_UNCONDITIONED_DELEGATION", address, "delegation must be condition-bound", "unconditioned-delegation", "add exact PassedToService and resource conditions", exemptible=False))
            if delegated and any(not {"iam:PassedToService", "aws:SourceAccount", "aws:SourceArn"}.intersection({str(k) for k in statement.get("Condition", {})}) for statement in delegated):
                findings.append(_finding("CONFUSED_DEPUTY_BINDING", address, "delegation must use exact source and service conditions", "missing-exact-confused-deputy-condition", "bind source account, source ARN and PassedToService exactly", exemptible=False))
        if any(
            token in lower for token in ("apply", "passrole", "assume_role", "admin")
        ):
            findings.append(
                _finding(
                    "PRIVILEGE_ESCALATION",
                    address,
                    "policy evaluation must not grant apply or escalation authority",
                    "authority-shaped-address",
                    "remove the authority path",
                    exemptible=False,
                )
            )
        if "iam_user" in lower or "access_key" in lower:
            findings.append(
                _finding(
                    "IAM_USER_OR_KEY",
                    address,
                    "production uses federated roles, not IAM users or keys",
                    "long-lived-credential-resource",
                    "use the approved OIDC role",
                    exemptible=False,
                )
            )
        if "security_group" in lower and (
            "0.0.0.0/0" in str(after) or "::/0" in str(after)
        ):
            findings.append(
                _finding(
                    "UNSAFE_EGRESS",
                    address,
                    "security groups must not allow unrestricted ingress or egress",
                    "unrestricted-cidr",
                    "use approved private references",
                    exemptible=False,
                )
            )
        if ("public" in lower and "ip" in lower) or after.get("assign_public_ip") is True:
            findings.append(
                _finding(
                    "PUBLIC_NETWORK",
                    address,
                    "production tasks use private networking",
                    "public-ip-attribute",
                    "disable public IP assignment",
                    exemptible=False,
                )
            )
        if any(
            key in str(after).lower()
            for key in ("password", "token", "api_key", "secret_value", "private_key")
        ):
            findings.append(
                _finding(
                    "PLAINTEXT_SECRET",
                    address,
                    "secrets must use approved references",
                    "sensitive-field-detected",
                    "use Secrets Manager, SSM, or KMS reference",
                    exemptible=False,
                )
            )
        image_values = _image_values(after)
        if ("ecr" in lower or "image" in lower or "task_definition" in lower) and any(
            ":" in value and "@sha256:" not in value for value in image_values
        ):
            findings.append(
                _finding(
                    "MUTABLE_IMAGE",
                    address,
                    "images must be immutable digests or release versions",
                    "mutable-image-tag",
                    "pin an image digest",
                    exemptible=True,
                )
            )
        if "scheduler" in lower and "ecs" in str(after).lower():
            findings.append(
                _finding(
                    "DIRECT_SCHEDULER_LAUNCH",
                    address,
                    "launches must pass through the Process Manager",
                    "direct-scheduler-target",
                    "target the canonical ingress",
                    exemptible=False,
                )
            )
        if any(token in lower for token in ("scheduler", "schedule", "task_definition")):
            required_launch = ("role_id", "generation", "registered_job", "expectation_horizon", "acknowledgement", "overlap_policy")
            missing_launch = [field for field in required_launch if field not in after]
            if missing_launch:
                findings.append(_finding("SCHEDULE_GOVERNANCE", address, "launch evidence must bind lifecycle, role, generation and occurrence controls", "missing=" + ",".join(missing_launch), "provide exact registered launch evidence", exemptible=False))
        if any(key in after for key in ("lifecycle_state", "generation", "config_mutable", "registered_job")):
            lifecycle = after.get("lifecycle_state")
            if lifecycle is not None and lifecycle not in {"RESERVED", "PUBLISHED", "VALIDATED", "MATERIALIZED", "ENABLED"}:
                findings.append(_finding("SCHEDULE_LIFECYCLE", address, "launch lifecycle must use the approved sequence", "unknown-lifecycle-state", "use RESERVED to ENABLED handshake", exemptible=False))
            if after.get("config_mutable") is True or after.get("registered_job") is False:
                findings.append(_finding("SCHEDULE_GOVERNANCE", address, "scheduled jobs require immutable registered configuration", "mutable-or-unregistered-job", "bind immutable CONFIG and registered job identity", exemptible=False))
        if "null_resource" in lower or "provisioner" in lower:
            findings.append(
                _finding(
                    "UNSAFE_TERRAFORM_MECHANISM",
                    address,
                    "normal infrastructure must not use provisioners or null_resource",
                    "unsupported-mechanism",
                    "use a managed resource",
                    exemptible=True,
                )
            )
    classification = classify_qualifying_changes(plan)
    return {
        "schema_version": "1.0.0",
        "policy_id": POLICY_ID,
        "policy_version": POLICY_VERSION,
        "status": "failed" if findings else "passed",
        "environment": "production",
        "source_commit": source_commit,
        "plan_sha256": plan_sha256,
        "target": {
            key: str(target[key])[:200]
            for key in ("account_id", "region", "root", "environment")
            if key in target
        },
        "classification": classification,
        "findings": findings[:200],
        "catalog_version": str(catalog["policy_version"]),
        "evaluated_at": now,
    }


def validate_exception(
    exception: Mapping[str, Any], decision: Mapping[str, Any], *, now: str,
    consumed_exception_ids: set[str] | None = None,
    signing_key: bytes | None = None,
) -> None:
    required = {
        "policy_id",
        "policy_version",
        "address",
        "environment",
        "source_commit",
        "plan_sha256",
        "owner",
        "justification",
        "approver",
        "compensating_control",
        "expires_at",
        "review_at",
        "signature",
    }
    if set(exception) != required or any(
        not isinstance(exception[key], str) or not exception[key] for key in required
    ):
        raise TargetViolation("POLICY_EXCEPTION_SHAPE")
    if "*" in exception["address"]:
        raise TargetViolation("POLICY_EXCEPTION_SCOPE")
    if exception["policy_id"] != decision.get("policy_id") or exception[
        "policy_version"
    ] != decision.get("policy_version"):
        raise TargetViolation("POLICY_EXCEPTION_POLICY")
    for key in ("environment", "source_commit", "plan_sha256"):
        if exception[key] != str(decision.get(key, "")):
            raise TargetViolation("POLICY_EXCEPTION_BINDING")
    if exception["approver"] == exception["owner"]:
        raise TargetViolation("POLICY_EXCEPTION_APPROVAL")
    matching = [
        item for item in decision.get("findings", [])
        if isinstance(item, Mapping) and item.get("address") == exception["address"]
    ]
    if any(item.get("exemptible") is False for item in matching):
        raise TargetViolation("POLICY_EXCEPTION_NON_EXEMPTIBLE")
    if len(matching) != 1 or matching[0].get("exemptible") is not True:
        raise TargetViolation("POLICY_EXCEPTION_FINDING")
    signing_key_bytes = signing_key or os.environ.get("TRUSTED_EXCEPTION_SIGNING_KEY", "").encode()
    if not signing_key_bytes:
        raise TargetViolation("POLICY_EXCEPTION_SIGNING_KEY")
    unsigned = {field: exception[field] for field in sorted(exception) if field != "signature"}
    payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    expected = hmac.new(signing_key_bytes, payload, hashlib.sha256).hexdigest()
    supplied = exception["signature"].removeprefix("hmac-sha256:")
    if not hmac.compare_digest(supplied, expected):
        raise TargetViolation("POLICY_EXCEPTION_SIGNATURE")
    exception_id = hashlib.sha256(payload).hexdigest()
    if consumed_exception_ids is not None:
        if exception_id in consumed_exception_ids:
            raise TargetViolation("POLICY_EXCEPTION_REUSE")
        consumed_exception_ids.add(exception_id)
    expiry = _parse_utc(exception["expires_at"], "POLICY_EXCEPTION_TIMESTAMP")
    review = _parse_utc(exception["review_at"], "POLICY_EXCEPTION_TIMESTAMP")
    current = _parse_utc(now, "POLICY_EXCEPTION_TIMESTAMP")
    if not current <= review < expiry or expiry <= current:
        raise TargetViolation("POLICY_EXCEPTION_EXPIRED")


def consume_exception_once(exception_id: str, ledger: Path) -> None:
    """Atomically consume an exception ID; the ledger stores no sensitive exception data."""
    ledger.parent.mkdir(parents=True, exist_ok=True)
    marker = ledger / exception_id
    try:
        marker.touch(exist_ok=False)
    except FileExistsError as error:
        raise TargetViolation("POLICY_EXCEPTION_REUSE") from error


def apply_exceptions(
    decision: Mapping[str, Any], exceptions: list[Mapping[str, Any]], *, now: str,
    ledger: Path | None = None,
) -> dict[str, Any]:
    """Validate exact exceptions and remove only their matching findings."""
    findings = list(decision.get("findings", []))
    waived: list[dict[str, str]] = []
    consumed: set[str] = set()
    for exception in exceptions:
        validate_exception(exception, decision, now=now, consumed_exception_ids=consumed)
        unsigned = {field: exception[field] for field in sorted(exception) if field != "signature"}
        exception_id = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if ledger is not None:
            consume_exception_once(exception_id, ledger)
        address = str(exception["address"])
        findings = [item for item in findings if item.get("address") != address]
        waived.append({"exception_id": exception_id, "address": address, "policy_id": str(exception["policy_id"])})
    result = dict(decision)
    result["findings"] = findings[:200]
    result["status"] = "passed" if not findings else "failed"
    result["exceptions"] = waived
    return result
