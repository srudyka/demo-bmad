from __future__ import annotations

from datetime import datetime
import hashlib
import json

import pytest

from scripts.deployment_targets import TargetViolation
from scripts.readiness_gate import (
    REQUIRED_CATEGORIES,
    REQUIRED_CONTROL_IDS,
    invalidate_if_bindings_changed,
    seal_evidence_envelope,
    validate_evidence_envelope,
)
from scripts.production_apply import validate_readiness_evidence


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _bindings() -> dict[str, str]:
    return {
        "repository": "demo-bmad",
        "source_commit": "a" * 40,
        "workflow_sha": "b" * 40,
        "workflow_run_id": "run-42",
        "plan_sha256": "c" * 64,
        "deployment_identity_sha256": "d" * 64,
        "account_id": "111111111111",
        "region": "us-east-1",
        "environment": "test",
        "job_id": "demo-job",
        "config_sha256": "e" * 64,
        "schedule_generation": "generation-1",
        "cell_contract_sha256": "f" * 64,
        "cell_version": "1.0.0",
        "policy_id": "production-readiness",
        "policy_version": "1.0.0",
        "target_manifest_sha256": "1" * 64,
        "terraform_root": "envs/test",
        "state_key": "test/us-east-1/envs/test/state",
        "provider_lock_path": "envs/test/.terraform.lock.hcl",
        "backend_lock_path": "envs/test/backend.hcl",
    }


def _envelope() -> dict:
    bindings = _bindings()
    category_by_control = {
        control: REQUIRED_CATEGORIES[index % len(REQUIRED_CATEGORIES)]
        for index, control in enumerate(REQUIRED_CONTROL_IDS)
    }
    items = [
        {
            "category": category_by_control[control],
            "control_id": control,
            "producer": "credential-free-validator",
            "tool_version": "validator-1.0.0",
            "evaluated_at": "2026-07-31T10:00:00Z",
            "result": "passed",
            "artifact_sha256": hashlib.sha256(control.encode()).hexdigest(),
            "sensitivity": "internal",
            "reference": f"artifact://readiness/{control}",
            "bindings_sha256": _digest(bindings),
            "claims": {"passed": True},
        }
        for control in REQUIRED_CONTROL_IDS
    ]
    artifacts = {
        f"artifact://readiness/{control}": {
            "sha256": hashlib.sha256(control.encode()).hexdigest(),
            "access": "protected",
        }
        for control in REQUIRED_CONTROL_IDS
    }
    envelope = {
        "schema_version": "1.0.0",
        "status": "passed",
        "evidence_source": "disposable-fixture",
        "bindings": bindings,
        "items": items,
        "attestations": [
            {
                "role": "platform",
                "actor": "platform-reviewer",
                "deployment_identity_sha256": bindings["deployment_identity_sha256"],
                "attested_at": "2026-07-31T09:59:00Z",
                "result": "passed",
            }
        ],
        "findings": [],
        "exceptions": [],
        "artifact_manifest": artifacts,
        "approvals": [
            {
                "role": role,
                "actor": f"{role}-reviewer",
                "source_commit": bindings["source_commit"],
                "workflow_sha": bindings["workflow_sha"],
                "workflow_run_id": bindings["workflow_run_id"],
                "deployment_identity_sha256": bindings["deployment_identity_sha256"],
                "approved_at": "2026-07-31T09:59:00Z",
                "expires_at": "2026-07-31T11:00:00Z",
                "status": "approved",
            }
            for role in ("platform", "job-owner")
        ],
        "reviewer_summary": {
            "status": "passed",
            "reviewer_roles": ["platform", "job-owner"],
            "evidence_links": list(artifacts),
            "generated_at": "2026-07-31T09:59:00Z",
            "access_control": "protected",
        },
        "evaluated_at": "2026-07-31T10:00:00Z",
        "expires_at": "2026-07-31T11:00:00Z",
    }
    envelope["evidence_sha256"] = _digest(envelope)
    return envelope


def test_complete_fixture_is_accepted_and_summarized() -> None:
    envelope = _envelope()
    summary = validate_evidence_envelope(
        envelope,
        _bindings(),
        now=datetime.fromisoformat("2026-07-31T10:30:00+00:00"),
    )
    assert summary["status"] == "passed"
    assert summary["categories"] == sorted(REQUIRED_CATEGORIES)
    assert summary["blocking_findings"] == 0


def test_seal_and_apply_preflight_bind_the_current_evidence_checksum() -> None:
    envelope = _envelope()
    del envelope["evidence_sha256"]
    sealed = seal_evidence_envelope(envelope)
    expected = {**_bindings(), "readiness_evidence_sha256": sealed["evidence_sha256"]}
    summary = validate_readiness_evidence(
        sealed,
        expected,
        now=datetime.fromisoformat("2026-07-31T10:30:00+00:00"),
    )
    assert summary["evidence_sha256"] == expected["readiness_evidence_sha256"]


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda e: e["items"].pop(), "READINESS_CONTROL_MISSING"),
        (
            lambda e: e["bindings"].update(plan_sha256="9" * 64),
            "READINESS_BINDING_MISMATCH",
        ),
        (lambda e: e.update(expires_at="2026-07-31T10:01:00Z"), "READINESS_EXPIRED"),
        (lambda e: e.update(**{"x-secret": "forbidden"}), "READINESS_ENVELOPE_SHAPE"),
    ],
)
def test_invalid_or_stale_evidence_fails_closed(mutation, code: str) -> None:
    envelope = _envelope()
    mutation(envelope)
    with pytest.raises(TargetViolation, match=code):
        validate_evidence_envelope(
            envelope,
            _bindings(),
            now=datetime.fromisoformat("2026-07-31T10:30:00+00:00"),
        )


def test_sensitive_reference_is_rejected() -> None:
    envelope = _envelope()
    envelope["items"][0]["reference"] = "artifact://secret-value"
    with pytest.raises(TargetViolation, match="READINESS_SENSITIVE_FIELD"):
        validate_evidence_envelope(envelope, _bindings())


def test_changed_bound_input_invalidates_previous_decision() -> None:
    envelope = _envelope()
    assert not invalidate_if_bindings_changed(envelope, _bindings())
    changed = {**_bindings(), "schedule_generation": "generation-2"}
    assert invalidate_if_bindings_changed(envelope, changed)


def test_required_approval_and_security_routing_fail_closed() -> None:
    now = datetime.fromisoformat("2026-07-31T10:30:00+00:00")
    envelope = _envelope()
    envelope["approvals"].pop()
    with pytest.raises(TargetViolation, match="READINESS_APPROVAL_MISSING"):
        validate_evidence_envelope(envelope, _bindings(), now=now)
    envelope = _envelope()
    envelope["approvals"][0]["actor"] = "placeholder"
    with pytest.raises(TargetViolation, match="READINESS_APPROVAL_ACTOR"):
        validate_evidence_envelope(envelope, _bindings(), now=now)
    with pytest.raises(TargetViolation, match="READINESS_APPROVAL_MISSING"):
        validate_evidence_envelope(
            _envelope(), {**_bindings(), "security_required": True}, now=now
        )


def test_control_policy_freshness_and_artifact_tampering_fail_closed() -> None:
    now = datetime.fromisoformat("2026-07-31T10:30:00+00:00")
    envelope = _envelope()
    envelope["items"][0]["evaluated_at"] = "2026-08-01T10:00:00Z"
    with pytest.raises(TargetViolation, match="READINESS_ITEM_FRESHNESS"):
        validate_evidence_envelope(
            envelope,
            _bindings(),
            now=now,
        )
    envelope = _envelope()
    envelope["artifact_manifest"][envelope["items"][0]["reference"]]["sha256"] = (
        "0" * 64
    )
    with pytest.raises(TargetViolation, match="READINESS_ARTIFACT_BINDING"):
        validate_evidence_envelope(envelope, _bindings(), now=now)
    envelope = _envelope()
    envelope["bindings"]["policy_version"] = "9.9.9"
    with pytest.raises(TargetViolation, match="READINESS_POLICY_UNKNOWN"):
        validate_evidence_envelope(
            envelope, {**_bindings(), "policy_version": "9.9.9"}, now=now
        )


def test_nonpassed_disposition_and_sealing_shape_fail_closed() -> None:
    now = datetime.fromisoformat("2026-07-31T10:30:00+00:00")
    envelope = _envelope()
    envelope["status"] = "blocked"
    with pytest.raises(TargetViolation, match="READINESS_FINDING_REQUIRED"):
        validate_evidence_envelope(envelope, _bindings(), now=now)
    with pytest.raises(TargetViolation, match="READINESS_ENVELOPE_SHAPE"):
        seal_evidence_envelope({"schema_version": "1.0.0"})
