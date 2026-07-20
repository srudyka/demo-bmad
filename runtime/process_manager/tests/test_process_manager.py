from __future__ import annotations

from process_manager import ContractRejection, prepare_expected
from process_manager.contracts import (
    canonical_json_bytes,
    materializer_event_id,
    occurrence_id,
)


JOB = "dev/demo/job"
GENERATION = "a" * 64
CONFIG_VERSION = "b28a21c680e59f87ead051bb2235b91f461112378b9f73cec2bbeb5e0ebb62f9"


def envelope() -> dict[str, object]:
    payload = {
        "config_validated": True,
        "expectation_horizon": "2027-01-02T00:00:00.000Z",
        "materialized_at": "2027-01-01T00:00:00.000Z",
        "repair": False,
    }
    return {
        "schema_version": "1.0.0",
        "event_type": "occurrence.expected.v1",
        "producer_id": "occurrence-materializer",
        "producer_event_id": materializer_event_id(
            JOB, GENERATION, "2027-01-01T00:00:00.000Z", CONFIG_VERSION, 1
        ),
        "job_id": JOB,
        "config_version": CONFIG_VERSION,
        "schedule_generation": GENERATION,
        "scheduled_time": "2027-01-01T00:00:00.000Z",
        "emitted_at": "2027-01-01T00:00:00.000Z",
        "occurrence_id": occurrence_id(JOB, GENERATION, "29979360"),
        "payload": payload,
        "payload_hash": __import__("hashlib")
        .sha256(canonical_json_bytes(payload))
        .hexdigest(),
    }


def snapshot() -> dict[str, object]:
    config = {
        "job_id": JOB,
        "schedule_generation": GENERATION,
        "owner_generation": 1,
        "completion_window_seconds": 3600,
    }
    config_json = canonical_json_bytes(config).decode()
    return {
        "job_id": JOB,
        "config_version": CONFIG_VERSION,
        "schedule_generation": GENERATION,
        "owner_generation": 1,
        "config_hash": __import__("hashlib").sha256(config_json.encode()).hexdigest(),
        "config_json": config_json,
        "validation_state": "VALIDATED",
        "materialization_state": "MATERIALIZED",
    }


def test_package_boundary_is_importable() -> None:
    assert "prepare_expected" in __import__("process_manager").__all__


def test_expected_builds_immutable_occurrence_and_processed_event() -> None:
    result = prepare_expected(
        envelope(),
        snapshot(),
        processor_identity="release-1",
        now="2027-01-01T00:00:01.000Z",
    )
    assert result.occurrence["state"] == "EXPECTED"
    assert result.occurrence["deadline_at"] == "2027-01-01T01:00:00.000Z"
    assert result.occurrence["keys"] == {
        "pk": f"JOB#{JOB}",
        "sk": f"OCCURRENCE#{result.occurrence['occurrence_id']}",
    }
    assert result.processed_event["pk"] == "EVENT#occurrence-materializer"


def test_forged_identity_and_noncanonical_envelope_are_rejected_before_write() -> None:
    value = envelope()
    value["occurrence_id"] = "0" * 64
    try:
        prepare_expected(
            value,
            snapshot(),
            processor_identity="release-1",
            now="2027-01-01T00:00:01.000Z",
        )
    except ContractRejection as error:
        assert error.code == "OCCURRENCE_ID_MISMATCH"
    else:
        raise AssertionError("forged occurrence identity was accepted")


def test_canonical_envelope_requires_expected_payload_shape() -> None:
    value = envelope()
    value["payload"] = {"config_validated": True}
    try:
        prepare_expected(
            value,
            snapshot(),
            processor_identity="release-1",
            now="2027-01-01T00:00:01.000Z",
        )
    except ContractRejection as error:
        assert error.code == "PAYLOAD_HASH_MISMATCH"
    else:
        raise AssertionError("incomplete expected payload was accepted")
