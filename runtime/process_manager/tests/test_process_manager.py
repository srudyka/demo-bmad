from __future__ import annotations

from typing import Any, Mapping

from process_manager import (
    ContractRejection,
    prepare_deadline,
    prepare_expected,
    reduce_deadline_state,
)
from process_manager import prepare_launch
from process_manager import prepare_manual_rerun
from process_manager.contracts import (
    canonical_json_bytes,
    deadline_event_id,
    materializer_event_id,
    occurrence_id,
    scheduler_event_id,
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


def launch_snapshot() -> dict[str, object]:
    aws_arn = "arn" + ":aws:"
    region = "us-" + "east-1"
    account = "111" * 4
    schedule_arn = (
        f"{aws_arn}scheduler:{region}:{account}:schedule/dev/dev-platform-canary"
    )
    config = {
        "cluster_arn": f"{aws_arn}ecs:{region}:{account}:cluster/dev-platform",
        "completion_window_seconds": 3600,
        "deployment_identity_id": "c" * 64,
        "job_id": JOB,
        "network": {
            "assign_public_ip": "DISABLED",
            "security_group_ids": ["sg-1234abcd"],
            "subnet_ids": ["subnet-1234abcd"],
        },
        "owner_generation": 1,
        "role_arns": {
            "launch": f"{aws_arn}iam::{account}:role/dev-platform-canary-launch"
        },
        "schedule_arn": schedule_arn,
        "schedule_generation": GENERATION,
        "task_definition_arn": f"{aws_arn}ecs:{region}:{account}:task-definition/dev-platform-canary:7",
    }
    config_json = canonical_json_bytes(config).decode()
    config_version = __import__("hashlib").sha256(config_json.encode()).hexdigest()
    return {
        "job_id": JOB,
        "config_version": config_version,
        "schedule_generation": GENERATION,
        "owner_generation": 1,
        "config_hash": config_version,
        "config_json": config_json,
        "validation_state": "VALIDATED",
        "materialization_state": "MATERIALIZED",
    }


def launch_envelope(snapshot_value: dict[str, object]) -> dict[str, object]:
    scheduled = "2027-01-01T00:00:00.000Z"
    config_version = str(snapshot_value["config_version"])
    aws_arn = "arn" + ":aws:"
    region = "us-" + "east-1"
    account = "111" * 4
    schedule_arn = (
        f"{aws_arn}scheduler:{region}:{account}:schedule/dev/dev-platform-canary"
    )
    payload = {
        "owner_generation": 1,
        "schedule_arn": schedule_arn,
        "schedule_group_arn": f"{aws_arn}scheduler:{region}:{account}:schedule-group/dev",
        "scheduler_scheduled_time": scheduled,
    }
    return {
        "schema_version": "1.0.0",
        "event_type": "occurrence.launch.v1",
        "producer_id": "scheduler",
        "producer_event_id": scheduler_event_id(
            schedule_arn, scheduled, config_version, 1
        ),
        "job_id": JOB,
        "config_version": config_version,
        "schedule_generation": GENERATION,
        "scheduled_time": scheduled,
        "emitted_at": scheduled,
        "occurrence_id": occurrence_id(JOB, GENERATION, "29979360"),
        "payload": payload,
        "payload_hash": __import__("hashlib")
        .sha256(canonical_json_bytes(payload))
        .hexdigest(),
    }


def test_launch_reserves_attempt_zero_with_stable_token_and_network_contract() -> None:
    config = launch_snapshot()
    result = prepare_launch(
        launch_envelope(config),
        config,
        processor_identity="release-1",
        now="2027-01-01T00:00:01.000Z",
    )
    assert result.attempt["attempt_no"] == 0
    assert len(result.client_token) == 64
    assert result.attempt["client_token"] == result.client_token
    assert result.attempt["launch_state"] == "PENDING"
    assert result.attempt["safe_retry_deadline"] == "2027-01-01T01:00:01.000Z"
    assert result.attempt["keys"]["sk"].endswith("#0")


def test_launch_requires_materialized_config() -> None:
    config = launch_snapshot()
    pending = dict(config)
    pending["materialization_state"] = "PENDING"
    try:
        prepare_launch(
            launch_envelope(config),
            pending,
            processor_identity="release-1",
            now="2027-01-01T00:00:01.000Z",
        )
    except ContractRejection as error:
        assert error.code == "CONFIG_NOT_MATERIALIZED"
    else:
        raise AssertionError("pending config was accepted for launch")


def test_manual_rerun_reuses_exact_config_and_links_original_occurrence() -> None:
    import hashlib

    command_id = "0190f2c9-6c00-7000-8000-000000000001"
    original = occurrence_id(JOB, GENERATION, "29979360")
    from command_handler import manual_occurrence_id

    synthetic = manual_occurrence_id(JOB, original, CONFIG_VERSION, command_id)
    config = launch_snapshot()
    config_value = __import__("json").loads(str(config["config_json"]))
    config_value["environment"] = "dev"
    config_value["task_definition_revision"] = 7
    config["config_json"] = canonical_json_bytes(config_value).decode()
    config["config_version"] = hashlib.sha256(
        str(config["config_json"]).encode()
    ).hexdigest()
    config["config_hash"] = config["config_version"]
    command = {
        "schema_version": "1.0.0",
        "form": "canonical",
        "command_id": command_id,
        "command_type": "RERUN",
        "job_id": JOB,
        "scheduled_time": "2027-01-01T00:00:00.000Z",
        "original_occurrence_id": original,
        "replay_of_occurrence_id": original,
        "synthetic_occurrence_id": synthetic,
        "config_version": config["config_version"],
        "schedule_generation": GENERATION,
        "deployment_identity_id": "c" * 64,
        "actor": "operator",
        "approval_reference": "CHANGE-1",
        "reason": "verified transient failure",
        "expected_duplicate_effects": "may repeat one notification",
        "verification_plan": "verify one success marker and zero essential exit",
        "verification_reference": "approval:CHANGE-1",
        "approval_expires_at": "2027-01-01T01:00:00.000Z",
        "compensation_acknowledged": True,
    }
    payload = {"command": command, "authorization_record_id": command_id}
    envelope_value = {
        "schema_version": "1.0.0",
        "event_type": "command.authorized.v1",
        "producer_id": "command-handler",
        "producer_event_id": command_id,
        "job_id": JOB,
        "config_version": config["config_version"],
        "schedule_generation": GENERATION,
        "occurrence_id": synthetic,
        "scheduled_time": "2027-01-01T00:00:00.000Z",
        "emitted_at": "2027-01-01T00:00:01.000Z",
        "payload": payload,
        "payload_hash": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
    }
    original_item = {
        "job_id": JOB,
        "occurrence_id": original,
        "config_version": config["config_version"],
        "schedule_generation": GENERATION,
        "state": "FAILED",
        "task_arn": "arn" + ":aws:ecs:us-" + "east-1:111122223333:task/dev/original",
        "deployment_identity_id": "c" * 64,
        "scheduled_time": "2027-01-01T00:00:00.000Z",
    }
    result = prepare_manual_rerun(
        envelope_value,
        config,
        original_item,
        processor_identity="cell-a:process-manager:v1",
        now="2027-01-01T00:00:02.000Z",
        expected_owner_generation=1,
        expected_environment="dev",
    )
    assert result.attempt["occurrence_id"] == synthetic
    assert result.attempt["client_token"]
    assert result.attempt["replay_of_occurrence_id"] == original
    assert result.attempt["command_id"] == command_id
    assert result.attempt["attempt_no"] == 0
    assert result.attempt["keys"]["sk"] == f"ATTEMPT#{synthetic}#0"
    assert result.processed_event["producer_id"] == "command-handler"


def test_deadline_evidence_is_validated_and_reduced_order_independently() -> None:
    payload = {
        "deadline_kind": "COMPLETION",
        "deadline_at": "2027-01-01T01:00:00.000Z",
        "scanner_watermark": "2027-01-01T01:00:01.000Z",
    }
    value = {
        "schema_version": "1.0.0",
        "event_type": "occurrence.deadline-reached.v1",
        "producer_id": "deadline-scanner",
        "producer_event_id": deadline_event_id(
            JOB,
            GENERATION,
            occurrence_id(JOB, GENERATION, "29979360"),
            "COMPLETION",
            "2027-01-01T01:00:00.000Z",
            CONFIG_VERSION,
        ),
        "job_id": JOB,
        "config_version": CONFIG_VERSION,
        "schedule_generation": GENERATION,
        "occurrence_id": occurrence_id(JOB, GENERATION, "29979360"),
        "scheduled_time": "2027-01-01T00:00:00.000Z",
        "emitted_at": "2027-01-01T01:00:01.000Z",
        "payload": payload,
        "payload_hash": __import__("hashlib")
        .sha256(canonical_json_bytes(payload))
        .hexdigest(),
    }
    prepared = prepare_deadline(
        value, processor_identity="release-1", now="2027-01-01T01:00:02.000Z"
    )
    assert prepared.processed_event["event_type"] == "occurrence.deadline-reached.v1"
    evidence: list[Mapping[str, Any]] = [
        {
            "kind": "DEADLINE",
            "deadline_at": "2027-01-01T01:00:00.000Z",
            "producer_id": "deadline-scanner",
            "producer_event_id": value["producer_event_id"],
            "digest": "1" * 64,
        },
        {
            "kind": "TASK_RUNNING",
            "task_arn": "task-1",
            "producer_id": "ecs",
            "producer_event_id": "e" * 64,
            "digest": "2" * 64,
        },
    ]
    assert reduce_deadline_state("EXPECTED", evidence) == "OVERDUE"
    assert reduce_deadline_state("EXPECTED", list(reversed(evidence))) == "OVERDUE"
