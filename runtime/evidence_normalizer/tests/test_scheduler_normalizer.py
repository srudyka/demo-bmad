from __future__ import annotations
# mypy: ignore-errors

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from evidence_normalizer import (
    MaterializerRegistration,
    SchedulerRegistration,
    TransientTransportError,
    normalize_scheduler_record,
    process_scheduler_batch,
    scheduler_producer_event_id,
    normalize_materializer_record,
)
from tests.contract.support.contracts import (
    build_schema_registry,
    canonical_json_bytes,
    load_json_strict,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "v1"


def registration() -> SchedulerRegistration:
    return SchedulerRegistration(
        account_id="111111111111",
        config_version="a" * 64,
        environment="dev",
        job_id="dev/platform/canary",
        owner_generation=1,
        region="us-east-" + "1",
        schedule_arn=(
            "arn" + ":aws:scheduler:us-east-" + "1:111111111111:"
            "schedule/dev-platform-scheduler/dev-platform-canary"
        ),
        schedule_generation="b" * 64,
        schedule_group_arn=(
            "arn" + ":aws:scheduler:us-east-" + "1:111111111111:"
            "schedule-group/dev-platform-scheduler"
        ),
        scheduler_role_id="AROASCHEDULEREXAMPLE",
        source_queue_arn="arn"
        + ":aws:sqs:us-east-"
        + "1:111111111111:dev-platform-scheduler-ingress",
    )


def record() -> dict[str, object]:
    """Return the raw SQS shape produced by EventBridge Scheduler."""

    scheduled_time = "2027-01-01T00:00:00Z"
    registered = registration()
    return {
        "messageId": "source-message-id",
        "eventSource": "aws:sqs",
        "eventSourceARN": registered.source_queue_arn,
        "awsRegion": registered.region,
        "attributes": {
            "ApproximateFirstReceiveTimestamp": "1798761600000",
            "SenderId": f"{registered.scheduler_role_id}:session",
        },
        "body": json.dumps(
            {
                "account_id": registered.account_id,
                "config_version": registered.config_version,
                "event_type": "occurrence.launch.v1",
                "job_id": registered.job_id,
                "ownership_generation": registered.owner_generation,
                "producer_id": "scheduler",
                "region": registered.region,
                "schedule_arn": registered.schedule_arn,
                "schedule_generation": registered.schedule_generation,
                "schedule_group_arn": registered.schedule_group_arn,
                "scheduler_scheduled_time": scheduled_time,
                "schema_version": "1.0.0",
                "source_queue_arn": registered.source_queue_arn,
            }
        ),
    }


def replace_body(record_value: dict[str, object], **updates: object) -> None:
    body = json.loads(str(record_value["body"]))
    body.update(updates)
    record_value["body"] = json.dumps(body)


def schema_context() -> tuple[dict[str, object], object, dict[str, object]]:
    schemas, registry = build_schema_registry(CONTRACTS_ROOT / "schemas")
    secret_policy = load_json_strict(CONTRACTS_ROOT / "catalogs" / "secret-safety.json")
    return schemas, registry, secret_policy


def test_normalizes_registered_scheduler_record_deterministically() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    normalized = normalize_scheduler_record(
        record(), registration(), schemas, schema_registry, secret_policy
    )
    envelope = normalized.envelope
    assert envelope["producer_id"] == "scheduler"
    assert envelope["event_type"] == "occurrence.launch.v1"
    assert envelope["emitted_at"] == "2027-01-01T00:00:00.000Z"
    assert (
        envelope["payload_hash"]
        == sha256(canonical_json_bytes(envelope["payload"])).hexdigest()
    )
    assert envelope["producer_event_id"] == scheduler_producer_event_id(
        registration(), "2027-01-01T00:00:00.000Z"
    )


def test_normalizes_registered_materializer_expected_evidence() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    registered = MaterializerRegistration(
        account_id="111111111111",
        config_version="a" * 64,
        environment="dev",
        job_id="dev/platform/canary",
        materializer_role_id="AROAMATERIALIZER",
        owner_generation=1,
        region="us-east-" + "1",
        schedule_generation="b" * 64,
        source_queue_arn="arn"
        + ":aws:sqs:us-east-"
        + "1:111111111111:dev-platform-materializer-ingress",
    )
    body = {
        "config_version": registered.config_version,
        "emitted_at": "2027-01-01T00:00:00.000Z",
        "event_type": "occurrence.expected.v1",
        "job_id": registered.job_id,
        "occurrence_id": "c" * 64,
        "payload": {
            "config_validated": True,
            "expectation_horizon": "2027-01-02T00:00:00.000Z",
            "materialized_at": "2027-01-01T00:00:00.000Z",
            "repair": False,
        },
        "payload_hash": "d" * 64,
        "producer_event_id": "e" * 64,
        "producer_id": "occurrence-materializer",
        "schedule_generation": registered.schedule_generation,
        "scheduled_time": "2027-01-01T00:00:00.000Z",
        "schema_version": "1.0.0",
    }
    from tests.contract.support.contracts import (
        canonical_json_bytes,
        materializer_producer_event_id,
        occurrence_id,
    )

    body["occurrence_id"] = occurrence_id(
        registered.job_id, registered.schedule_generation, "29979360"
    )
    body["payload_hash"] = sha256(canonical_json_bytes(body["payload"])).hexdigest()
    body["producer_event_id"] = materializer_producer_event_id(
        registered.job_id,
        registered.schedule_generation,
        body["scheduled_time"],
        registered.config_version,
        registered.owner_generation,
    )
    raw = {
        "messageId": "materializer-message",
        "eventSource": "aws:sqs",
        "eventSourceARN": registered.source_queue_arn,
        "awsRegion": registered.region,
        "attributes": {
            "ApproximateFirstReceiveTimestamp": "1798761600000",
            "SenderId": "AROAMATERIALIZER:session",
        },
        "body": json.dumps(body),
    }
    normalized = normalize_materializer_record(
        raw, registered, schemas, schema_registry, secret_policy
    )
    assert normalized.rejection_code is None
    assert normalized.envelope == body


def test_rejects_body_identity_assertions_that_disagree_with_registration() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    forged = deepcopy(record())
    replace_body(forged, job_id="dev/platform/forged")

    rejected = normalize_scheduler_record(
        forged, registration(), schemas, schema_registry, secret_policy
    )

    assert rejected.envelope is None
    assert rejected.rejection_code == "NORMALIZER_ASSERTION_JOB_ID"
    assert rejected.quarantine_record is not None
    assert "dev/platform/forged" not in str(rejected.quarantine_record)


def test_rejects_stale_sender_role_before_envelope_side_effects() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    forged = deepcopy(record())
    forged["attributes"]["SenderId"] = "AROASTALE:session"  # type: ignore[index]

    rejected = normalize_scheduler_record(
        forged, registration(), schemas, schema_registry, secret_policy
    )

    assert rejected.envelope is None
    assert rejected.rejection_code == "NORMALIZER_SENDER_ROLE"


def test_rejects_sender_id_without_a_session_separator() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    forged = record()
    forged["attributes"] = {"SenderId": registration().scheduler_role_id}

    rejected = normalize_scheduler_record(
        forged, registration(), schemas, schema_registry, secret_policy
    )

    assert rejected.rejection_code == "NORMALIZER_SENDER_ROLE"


def test_rejects_duplicate_json_keys_before_any_envelope_is_created() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    malformed = record()
    malformed["body"] = '{"job_id":"dev/platform/canary","job_id":"forged"}'

    rejected = normalize_scheduler_record(
        malformed, registration(), schemas, schema_registry, secret_policy
    )

    assert rejected.envelope is None
    assert rejected.rejection_code == "NORMALIZER_BODY_INVALID"
    assert rejected.quarantine_record is not None
    assert rejected.quarantine_record["received_at"] == "1798761600000"


def test_rejects_an_optional_occurrence_assertion_that_does_not_match() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    forged = record()
    replace_body(forged, occurrence_id="0" * 64)

    rejected = normalize_scheduler_record(
        forged, registration(), schemas, schema_registry, secret_policy
    )

    assert rejected.rejection_code == "NORMALIZER_ASSERTION_OCCURRENCE_ID"


def test_partial_batch_retries_only_transient_records() -> None:
    schemas, schema_registry, secret_policy = schema_context()
    accepted = record()
    rejected = deepcopy(record())
    rejected["messageId"] = "permanent"
    replace_body(rejected, event_type="task.state.v1")
    transient = deepcopy(record())
    transient["messageId"] = "transient"

    def send_envelope(envelope: dict[str, object]) -> None:
        if envelope["producer_event_id"] == scheduler_producer_event_id(
            registration(), "2027-01-01T00:00:00.000Z"
        ):
            return

    def send_quarantine(record: dict[str, object]) -> None:
        if record["source_message_id_hash"]:
            return

    outcome = process_scheduler_batch(
        [accepted, rejected, transient],
        registration(),
        schemas,
        schema_registry,
        secret_policy,
        send_envelope=send_envelope,
        send_quarantine=send_quarantine,
        transient_message_ids={"transient"},
    )

    assert outcome == {"batchItemFailures": [{"itemIdentifier": "transient"}]}


def test_partial_batch_retries_a_transport_error_without_blocking_other_records() -> (
    None
):
    schemas, schema_registry, secret_policy = schema_context()
    accepted = record()
    failing = deepcopy(record())
    failing["messageId"] = "transport"
    delivered: list[str] = []

    def send_envelope(envelope: dict[str, object]) -> None:
        if (
            envelope["producer_event_id"]
            == scheduler_producer_event_id(registration(), "2027-01-01T00:00:00.000Z")
            and not delivered
        ):
            delivered.append("accepted")
            return
        raise TransientTransportError

    outcome = process_scheduler_batch(
        [accepted, failing],
        registration(),
        schemas,
        schema_registry,
        secret_policy,
        send_envelope=send_envelope,
        send_quarantine=lambda _record: None,
    )

    assert delivered == ["accepted"]
    assert outcome == {"batchItemFailures": [{"itemIdentifier": "transport"}]}
