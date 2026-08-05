from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from scripts.security_qualification import (
    FIXTURE_EXPECTATIONS,
    SECURITY_CONTROL_IDS,
    SECURITY_CATEGORIES,
    SecurityQualificationError,
    _digest,
    seal_security_evidence,
    security_readiness_projection,
    validate_security_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
BINDINGS = {
    "release_version": "1.0.0",
    "compatibility_package_sha256": "a" * 64,
    "source_commit": "b" * 40,
    "workflow_sha": "c" * 40,
    "workflow_run_id": "12345",
    "account_id": "111111111111",
    "region": "us-east-1",
    "environment": "qualification",
    "cell_identity": "cell-security-fixture",
    "policy_catalog_version": "1.0.0",
    "deployment_identity_sha256": "d" * 64,
    "target_manifest_sha256": "e" * 64,
}
ATTESTATION_KEY = b"fixture-attestation-key"


def _fixture(index: int, fixture_id: str) -> dict[str, Any]:
    category, decision = FIXTURE_EXPECTATIONS[fixture_id]
    fixture: dict[str, object] = {
        "fixture_id": fixture_id,
        "category": category,
        "principal_class": "untrusted-producer"
        if decision == "deny"
        else "registered-platform-role",
        "resource_class": "cell-control-record",
        "action": "dynamodb:PutItem",
        "expected_decision": decision,
        "actual_decision": decision,
        "preventive_boundary": "iam-policy-and-runtime-binding",
        "stable_code": "SECURITY_DENIED" if decision == "deny" else "SECURITY_ALLOWED",
        "tool_version": "security-evaluator/1.0.0",
        "evaluated_at": "2026-08-03T15:00:00Z",
        "bindings": dict(BINDINGS),
        "evidence_sha256": "0" * 64,
        "mutation_count": 0 if decision == "deny" else 1,
        "attestation": {
            "mode": "offline" if decision == "deny" else "live",
            "verified": decision == "allow",
            "proof": {
                "workflow_path": ".github/workflows/security-boundary-qualification.yml",
                "run_conclusion": "success",
                "iam_decision": decision,
                "observed": True,
            },
            "proof_sha256": "0" * 64,
            "source_workflow_run_id": BINDINGS["workflow_run_id"],
            "signature_sha256": "0" * 64,
        },
    }
    unsigned = dict(fixture)
    unsigned.pop("evidence_sha256")
    attestation = fixture["attestation"]
    assert isinstance(attestation, dict)
    proof = attestation["proof"]
    assert isinstance(proof, dict)
    attestation["proof_sha256"] = _digest(proof)
    attestation_copy = dict(attestation)
    attestation_copy.pop("signature_sha256")
    unsigned["attestation"] = attestation_copy
    evidence_digest = _digest(unsigned)
    fixture["evidence_sha256"] = evidence_digest
    attestation["signature_sha256"] = hmac.new(
        ATTESTATION_KEY,
        evidence_digest.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return fixture


def _evidence() -> dict[str, Any]:
    fixtures = [
        _fixture(i, fixture_id) for i, fixture_id in enumerate(FIXTURE_EXPECTATIONS)
    ]
    return seal_security_evidence(
        {
            "schema_version": "1.0.0",
            "bindings": dict(BINDINGS),
            "fixtures": fixtures,
            "results": {control: "passed" for control in SECURITY_CONTROL_IDS},
            "cleanup": {
                "mode": "disable-first",
                "deleted": [
                    "synthetic-job",
                    "synthetic-cell",
                    "synthetic-identities",
                    "synthetic-policies",
                    "synthetic-queues",
                    "synthetic-logs",
                    "injected-faults",
                ],
                "retained": ["sanitized-manifest"],
                "forbidden_artifacts": [],
            },
        }
    )


def test_fixture_catalog_covers_required_security_matrix() -> None:
    catalog = json.loads(
        (ROOT / "contracts/v1/fixtures/security/cases.json").read_text()
    )
    assert set(catalog["categories"]) == SECURITY_CATEGORIES
    assert len(catalog["required_negative_boundaries"]) >= 12
    assert "exact-deployment-identity" in catalog["required_positive_boundaries"]


def test_complete_sanitized_evidence_projects_security_only() -> None:
    summary = validate_security_evidence(
        _evidence(),
        BINDINGS,
        now=datetime.fromisoformat("2026-08-03T16:00:00+00:00"),
        attestation_key=ATTESTATION_KEY,
    )
    projection = security_readiness_projection(summary, BINDINGS)
    assert summary["status"] == "passed"
    assert projection["category"] == "security"
    assert all(value == "passed" for value in projection["controls"].values())
    assert projection["recovery"] == "blocked"
    assert projection["unrelated_controls"] == "blocked"


def test_digest_and_protected_attestation_are_required() -> None:
    evidence = _evidence()
    tampered = copy.deepcopy(evidence)
    tampered["results"]["security-state"] = "blocked"
    with pytest.raises(
        SecurityQualificationError, match="SECURITY_EVIDENCE_DIGEST_MISMATCH"
    ):
        validate_security_evidence(
            tampered,
            BINDINGS,
            now=datetime.fromisoformat("2026-08-03T16:00:00+00:00"),
            attestation_key=ATTESTATION_KEY,
        )
    with pytest.raises(
        SecurityQualificationError, match="SECURITY_ATTESTATION_KEY_REQUIRED"
    ):
        validate_security_evidence(
            evidence,
            BINDINGS,
            now=datetime.fromisoformat("2026-08-03T16:00:00+00:00"),
        )


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda e: e["fixtures"].pop(), "SECURITY_FIXTURE_DUPLICATE"),
        (
            lambda e: e["fixtures"][0].update(actual_decision="allow"),
            "SECURITY_UNEXPECTED_DECISION",
        ),
        (
            lambda e: e["fixtures"][0].update(mutation_count=1),
            "SECURITY_MUTATION_ON_DENY",
        ),
        (
            lambda e: e["fixtures"][0].update(attestation="inconclusive"),
            "SECURITY_EVIDENCE_DIGEST_MISMATCH",
        ),
        (
            lambda e: e["cleanup"].update(forbidden_artifacts=["terraform.tfstate"]),
            "SECURITY_CLEANUP_FAILED",
        ),
        (
            lambda e: e["fixtures"][0].update(**{"secret_value": "sentinel"}),
            "SECURITY_EVIDENCE_DIGEST_MISMATCH",
        ),
    ],
)
def test_forbidden_or_untrusted_evidence_fails_closed(
    mutation: Callable[[dict[str, Any]], Any], code: str
) -> None:
    evidence = copy.deepcopy(_evidence())
    mutation(evidence)
    if not any("secret_value" in fixture for fixture in evidence["fixtures"]) and all(
        isinstance(fixture.get("attestation"), dict) for fixture in evidence["fixtures"]
    ):
        for fixture in evidence["fixtures"]:
            unsigned = dict(fixture)
            unsigned.pop("evidence_sha256", None)
            unsigned["attestation"] = dict(fixture["attestation"])
            unsigned["attestation"].pop("signature_sha256", None)
            fixture["evidence_sha256"] = _digest(unsigned)
            attestation = fixture["attestation"]
            assert isinstance(attestation, dict)
            attestation["signature_sha256"] = hmac.new(
                ATTESTATION_KEY,
                fixture["evidence_sha256"].encode("ascii"),
                hashlib.sha256,
            ).hexdigest()
        evidence = seal_security_evidence(evidence)
    with pytest.raises(SecurityQualificationError, match=code):
        validate_security_evidence(
            evidence,
            BINDINGS,
            now=datetime.fromisoformat("2026-08-03T16:00:00+00:00"),
            attestation_key=ATTESTATION_KEY,
        )


def test_binding_substitution_and_replay_fail_closed() -> None:
    evidence = _evidence()
    changed = {**BINDINGS, "cell_identity": "other-cell"}
    with pytest.raises(SecurityQualificationError, match="SECURITY_BINDING_MISMATCH"):
        validate_security_evidence(
            evidence,
            changed,
            now=datetime.fromisoformat("2026-08-03T16:00:00+00:00"),
            attestation_key=ATTESTATION_KEY,
        )
    replay = copy.deepcopy(evidence)
    replay["fixtures"][0]["bindings"]["workflow_run_id"] = "99999"
    with pytest.raises(
        SecurityQualificationError, match="SECURITY_EVIDENCE_DIGEST_MISMATCH"
    ):
        validate_security_evidence(
            replay,
            BINDINGS,
            now=datetime.fromisoformat("2026-08-03T16:00:00+00:00"),
            attestation_key=ATTESTATION_KEY,
        )
