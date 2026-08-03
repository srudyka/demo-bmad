"""Credential-free security-boundary qualification contracts.

The evaluator deliberately models evidence and authorization decisions; it never
assumes AWS credentials or mutates a Cell. A protected workflow may attach live
attestation to the same manifest, but an offline/inconclusive result cannot pass.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
from typing import Any

import rfc8785

from scripts.deployment_targets import TargetViolation

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ACCOUNT = re.compile(r"^[0-9]{12}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$")

SECURITY_CONTROL_IDS = (
    "security-identity",
    "security-namespace",
    "security-least-privilege-iam",
    "security-confused-deputy",
    "security-oidc",
    "security-state",
    "security-networking",
    "security-secrets",
    "security-operator-controls",
)
SECURITY_CATEGORIES = {
    "identity",
    "namespace",
    "least-privilege-iam",
    "confused-deputy",
    "oidc",
    "state",
    "networking",
    "secrets",
    "operator-controls",
}
FIXTURE_EXPECTATIONS = {
    "forged-producer": ("identity", "deny"),
    "cross-job-evidence": ("confused-deputy", "deny"),
    "namespace-squatting": ("namespace", "deny"),
    "direct-ledger-write": ("least-privilege-iam", "deny"),
    "run-task-wildcard": ("least-privilege-iam", "deny"),
    "pass-role-alternate": ("least-privilege-iam", "deny"),
    "oidc-fork": ("oidc", "deny"),
    "oidc-mutable-workflow": ("oidc", "deny"),
    "state-reuse": ("state", "deny"),
    "public-network": ("networking", "deny"),
    "plaintext-secret": ("secrets", "deny"),
    "operator-wrong-scope": ("operator-controls", "deny"),
    "registered-producer": ("identity", "allow"),
    "registered-owner": ("namespace", "allow"),
    "exact-deployment-identity": ("least-privilege-iam", "allow"),
    "approved-oidc": ("oidc", "allow"),
    "private-dependency-path": ("networking", "allow"),
    "approved-secret-reference": ("secrets", "allow"),
    "authorized-operator": ("operator-controls", "allow"),
    "trusted-evidence-source": ("confused-deputy", "allow"),
    "approved-state-recovery": ("state", "allow"),
}
CONTROL_CATEGORIES = dict(
    zip(
        SECURITY_CONTROL_IDS,
        (
            "identity",
            "namespace",
            "least-privilege-iam",
            "confused-deputy",
            "oidc",
            "state",
            "networking",
            "secrets",
            "operator-controls",
        ),
        strict=True,
    )
)
REQUIRED_DELETED_ITEMS = {
    "synthetic-cell",
    "synthetic-job",
    "synthetic-identities",
    "synthetic-policies",
    "synthetic-queues",
    "synthetic-logs",
    "injected-faults",
}
REQUIRED_BINDINGS = (
    "release_version",
    "compatibility_package_sha256",
    "source_commit",
    "workflow_sha",
    "workflow_run_id",
    "account_id",
    "region",
    "environment",
    "cell_identity",
    "policy_catalog_version",
    "deployment_identity_sha256",
    "target_manifest_sha256",
)
SENSITIVE_MARKERS = (
    "-----begin",
    "aws_secret_access_key",
    "secret-value",
    "password=",
    "token=",
    "terraform_state",
    "tfplan",
)


class SecurityQualificationError(TargetViolation):
    """A security qualification input failed closed."""


def _digest(value: Any) -> str:
    return hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _require_string(value: Any, code: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise SecurityQualificationError(code)
    if any(marker in value.lower() for marker in SENSITIVE_MARKERS):
        raise SecurityQualificationError("SECURITY_SENSITIVE_FIELD")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise SecurityQualificationError("SECURITY_TIMESTAMP")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as error:
        raise SecurityQualificationError("SECURITY_TIMESTAMP") from error
    return value


def _digest_field(value: Any, code: str, pattern: re.Pattern[str] = SHA256) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise SecurityQualificationError(code)
    return value


def _validate_bindings(
    bindings: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    if set(bindings) != set(REQUIRED_BINDINGS):
        raise SecurityQualificationError("SECURITY_BINDINGS_SHAPE")
    for key in REQUIRED_BINDINGS:
        value = bindings.get(key)
        if not isinstance(value, str) or not value:
            raise SecurityQualificationError("SECURITY_BINDING_MISSING:" + key)
        if key in {"source_commit", "workflow_sha"}:
            _digest_field(value, "SECURITY_BINDING_FORMAT:" + key, SHA1)
        elif key.endswith("_sha256"):
            _digest_field(value, "SECURITY_BINDING_FORMAT:" + key)
        elif key == "account_id" and not ACCOUNT.fullmatch(value):
            raise SecurityQualificationError("SECURITY_BINDING_FORMAT:account_id")
        if key not in expected or str(value) != str(expected[key]):
            raise SecurityQualificationError("SECURITY_BINDING_MISMATCH:" + key)


def _validate_sanitized(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text not in SECURITY_CONTROL_IDS and any(
                marker in key_text
                for marker in (
                    "secret",
                    "password",
                    "credential",
                    "private_key",
                    "raw_payload",
                    "api_key",
                    "access_key",
                    "authorization",
                    "privatekey",
                    "raw_",
                )
            ):
                raise SecurityQualificationError("SECURITY_SENSITIVE_FIELD")
            _validate_sanitized(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str) and any(
        marker in value.lower() for marker in SENSITIVE_MARKERS
    ):
        raise SecurityQualificationError("SECURITY_SENSITIVE_FIELD")


def validate_security_fixture(
    fixture: Mapping[str, Any],
    expected_bindings: Mapping[str, Any],
    *,
    attestation_key: bytes | None = None,
) -> dict[str, Any]:
    """Validate one paired allow/deny fixture without trusting its claims."""

    required = {
        "fixture_id",
        "category",
        "principal_class",
        "resource_class",
        "action",
        "expected_decision",
        "actual_decision",
        "preventive_boundary",
        "stable_code",
        "tool_version",
        "evaluated_at",
        "bindings",
        "evidence_sha256",
        "mutation_count",
        "attestation",
    }
    if set(fixture) != required:
        raise SecurityQualificationError("SECURITY_FIXTURE_SHAPE")
    fixture_id = _require_string(fixture["fixture_id"], "SECURITY_FIXTURE_ID")
    category = _require_string(fixture["category"], "SECURITY_CATEGORY")
    if fixture_id not in FIXTURE_EXPECTATIONS:
        raise SecurityQualificationError("SECURITY_FIXTURE_UNKNOWN")
    expected_category, expected_decision = FIXTURE_EXPECTATIONS[fixture_id]
    if category not in SECURITY_CATEGORIES or category != expected_category:
        raise SecurityQualificationError("SECURITY_CATEGORY_UNKNOWN")
    for key in (
        "principal_class",
        "resource_class",
        "action",
        "preventive_boundary",
        "stable_code",
        "tool_version",
    ):
        _require_string(fixture[key], "SECURITY_FIXTURE_FIELD")
    _timestamp(fixture["evaluated_at"])
    _validate_bindings(fixture["bindings"], expected_bindings)
    _digest_field(fixture["evidence_sha256"], "SECURITY_EVIDENCE_DIGEST")
    if fixture["expected_decision"] != expected_decision or fixture[
        "actual_decision"
    ] not in {"allow", "deny", "inconclusive"}:
        raise SecurityQualificationError("SECURITY_DECISION")
    if type(fixture["mutation_count"]) is not int or fixture["mutation_count"] < 0:
        raise SecurityQualificationError("SECURITY_MUTATION_COUNT")
    attestation = fixture["attestation"]
    if not isinstance(attestation, Mapping) or set(attestation) != {
        "mode",
        "verified",
        "proof",
        "proof_sha256",
        "source_workflow_run_id",
        "signature_sha256",
    }:
        raise SecurityQualificationError("SECURITY_ATTESTATION")
    if (
        attestation["mode"] not in {"live", "offline"}
        or type(attestation["verified"]) is not bool
    ):
        raise SecurityQualificationError("SECURITY_ATTESTATION")
    _digest_field(attestation["proof_sha256"], "SECURITY_ATTESTATION_PROOF")
    proof = attestation["proof"]
    if not isinstance(proof, Mapping) or set(proof) != {
        "workflow_path",
        "run_conclusion",
        "iam_decision",
        "observed",
    }:
        raise SecurityQualificationError("SECURITY_ATTESTATION_PROOF_SHAPE")
    if (
        proof["workflow_path"]
        != ".github/workflows/security-boundary-qualification.yml"
    ):
        raise SecurityQualificationError("SECURITY_ATTESTATION_PROOF_SOURCE")
    if proof["run_conclusion"] != "success" or proof["observed"] is not True:
        raise SecurityQualificationError("SECURITY_ATTESTATION_PROOF_UNVERIFIED")
    if attestation["proof_sha256"] != _digest(proof):
        raise SecurityQualificationError("SECURITY_ATTESTATION_PROOF_MISMATCH")
    _digest_field(attestation["signature_sha256"], "SECURITY_ATTESTATION_SIGNATURE")
    if attestation["source_workflow_run_id"] != expected_bindings["workflow_run_id"]:
        raise SecurityQualificationError("SECURITY_ATTESTATION_BINDING")
    if fixture["actual_decision"] == "inconclusive":
        raise SecurityQualificationError("SECURITY_INCONCLUSIVE")
    if fixture["expected_decision"] != fixture["actual_decision"]:
        raise SecurityQualificationError("SECURITY_UNEXPECTED_DECISION")
    if fixture["expected_decision"] == "deny" and fixture["mutation_count"] != 0:
        raise SecurityQualificationError("SECURITY_MUTATION_ON_DENY")
    if fixture["expected_decision"] == "allow" and fixture["mutation_count"] != 1:
        raise SecurityQualificationError("SECURITY_ALLOW_MUTATION")
    if attestation["mode"] == "offline" and fixture["expected_decision"] == "allow":
        raise SecurityQualificationError("SECURITY_LIVE_ATTESTATION_REQUIRED")
    if fixture["expected_decision"] == "allow" and attestation["verified"] is not True:
        raise SecurityQualificationError("SECURITY_ATTESTATION_UNVERIFIED")
    if proof["iam_decision"] != fixture["actual_decision"]:
        raise SecurityQualificationError("SECURITY_ATTESTATION_PROOF_MISMATCH")
    unsigned_fixture = dict(fixture)
    unsigned_fixture.pop("evidence_sha256", None)
    unsigned_fixture["attestation"] = dict(attestation)
    unsigned_fixture["attestation"].pop("signature_sha256", None)
    if fixture["evidence_sha256"] != _digest(unsigned_fixture):
        raise SecurityQualificationError("SECURITY_EVIDENCE_DIGEST_MISMATCH")
    if attestation_key is None:
        raise SecurityQualificationError("SECURITY_ATTESTATION_KEY_REQUIRED")
    expected_signature = hmac.new(
        attestation_key,
        fixture["evidence_sha256"].encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(attestation["signature_sha256"], expected_signature):
        raise SecurityQualificationError("SECURITY_ATTESTATION_SIGNATURE_MISMATCH")
    _validate_sanitized(fixture)
    return {
        "fixture_id": fixture_id,
        "category": category,
        "expected_decision": fixture["expected_decision"],
        "actual_decision": fixture["actual_decision"],
        "preventive_boundary": fixture["preventive_boundary"],
        "stable_code": fixture["stable_code"],
        "evidence_sha256": fixture["evidence_sha256"],
    }


def validate_security_evidence(
    evidence: Mapping[str, Any],
    expected_bindings: Mapping[str, Any],
    *,
    now: datetime | None = None,
    attestation_key: bytes | None = None,
) -> dict[str, Any]:
    """Validate a complete, sanitized security evidence package."""

    required = {
        "schema_version",
        "bindings",
        "fixtures",
        "results",
        "cleanup",
        "evidence_sha256",
    }
    if set(evidence) != required or evidence.get("schema_version") != "1.0.0":
        raise SecurityQualificationError("SECURITY_EVIDENCE_SHAPE")
    _validate_bindings(evidence["bindings"], expected_bindings)
    _digest_field(evidence["evidence_sha256"], "SECURITY_EVIDENCE_DIGEST")
    unsigned_evidence = dict(evidence)
    unsigned_evidence.pop("evidence_sha256", None)
    if evidence["evidence_sha256"] != _digest(unsigned_evidence):
        raise SecurityQualificationError("SECURITY_EVIDENCE_DIGEST_MISMATCH")
    reference_time = now or datetime.now(timezone.utc)
    fixtures = evidence["fixtures"]
    if (
        not isinstance(fixtures, Sequence)
        or isinstance(fixtures, (str, bytes))
        or not fixtures
    ):
        raise SecurityQualificationError("SECURITY_FIXTURES_REQUIRED")
    summaries = [
        validate_security_fixture(
            item, expected_bindings, attestation_key=attestation_key
        )
        for item in fixtures
    ]
    for fixture in fixtures:
        evaluated_at = datetime.fromisoformat(
            str(fixture["evaluated_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if evaluated_at > reference_time + timedelta(
            minutes=5
        ) or evaluated_at < reference_time - timedelta(hours=24):
            raise SecurityQualificationError("SECURITY_TIMESTAMP_STALE")
    ids = [item["fixture_id"] for item in summaries]
    if set(ids) != set(FIXTURE_EXPECTATIONS) or len(ids) != len(set(ids)):
        raise SecurityQualificationError("SECURITY_FIXTURE_DUPLICATE")
    categories = {item["category"] for item in summaries}
    if categories != SECURITY_CATEGORIES:
        raise SecurityQualificationError("SECURITY_CATEGORY_COVERAGE")
    decisions_by_category = {
        category: {
            item["expected_decision"]
            for item in summaries
            if item["category"] == category
        }
        for category in SECURITY_CATEGORIES
    }
    if any(
        decisions != {"allow", "deny"} for decisions in decisions_by_category.values()
    ):
        raise SecurityQualificationError("SECURITY_PAIRED_FIXTURE_MISSING")
    results = evidence["results"]
    if not isinstance(results, Mapping) or set(results) != set(SECURITY_CONTROL_IDS):
        raise SecurityQualificationError("SECURITY_RESULTS_SHAPE")
    derived_results = {
        control: "passed" if CONTROL_CATEGORIES[control] in categories else "blocked"
        for control in SECURITY_CONTROL_IDS
    }
    if dict(results) != derived_results or any(
        result != "passed" for result in results.values()
    ):
        raise SecurityQualificationError("SECURITY_RESULTS_NOT_PASSED")
    cleanup = evidence["cleanup"]
    if not isinstance(cleanup, Mapping) or set(cleanup) != {
        "mode",
        "deleted",
        "retained",
        "forbidden_artifacts",
    }:
        raise SecurityQualificationError("SECURITY_CLEANUP_SHAPE")
    if (
        cleanup["mode"] != "disable-first"
        or cleanup["forbidden_artifacts"]
        or not isinstance(cleanup["forbidden_artifacts"], list)
    ):
        raise SecurityQualificationError("SECURITY_CLEANUP_FAILED")
    if not isinstance(cleanup["deleted"], list) or not isinstance(
        cleanup["retained"], list
    ):
        raise SecurityQualificationError("SECURITY_CLEANUP_SHAPE")
    if (
        not REQUIRED_DELETED_ITEMS.issubset(cleanup["deleted"])
        or set(cleanup["retained"]) != {"sanitized-manifest"}
        or any(
            not isinstance(item, str)
            for item in (*cleanup["deleted"], *cleanup["retained"])
        )
    ):
        raise SecurityQualificationError("SECURITY_CLEANUP_SHAPE")
    _validate_sanitized(evidence)
    return {
        "status": "passed",
        "fixture_count": len(summaries),
        "categories": sorted(categories),
        "results": dict(results),
        "cleanup": {
            "deleted": len(cleanup["deleted"]),
            "retained": len(cleanup["retained"]),
        },
        "evidence_sha256": evidence["evidence_sha256"],
    }


def security_readiness_projection(
    summary: Mapping[str, Any], bindings: Mapping[str, Any]
) -> dict[str, Any]:
    """Project only Story 4.7 controls; recovery and unrelated controls stay blocked."""

    if summary.get("status") != "passed" or set(summary.get("results", {})) != set(
        SECURITY_CONTROL_IDS
    ):
        raise SecurityQualificationError("SECURITY_PROJECTION_INPUT")
    if not all(value == "passed" for value in summary["results"].values()):
        raise SecurityQualificationError("SECURITY_PROJECTION_INPUT")
    _validate_bindings(bindings, bindings)
    return {
        "category": "security",
        "controls": {control: "passed" for control in SECURITY_CONTROL_IDS},
        "recovery": "blocked",
        "unrelated_controls": "blocked",
        "bindings_sha256": _digest(bindings),
    }


def seal_security_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical evidence object with its checksum sealed last."""

    unsigned = dict(evidence)
    unsigned.pop("evidence_sha256", None)
    _validate_sanitized(unsigned)
    sealed = {**unsigned, "evidence_sha256": _digest(unsigned)}
    return sealed
