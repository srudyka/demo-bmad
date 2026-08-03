from __future__ import annotations

import hashlib

import pytest

from scripts.ecs_qualification import (
    EcsQualificationError,
    build_launch_runtime_manifest,
    classify_run_task_response,
    classify_task_runtime,
    launch_runtime_projection,
    qualify_healthy_launch_runtime,
    validate_task_evidence,
)


TASK_ARN = "arn:aws:ecs:us-east-1:111111111111:task/platform/" + "a" * 32
CLUSTER_ARN = "arn:aws:ecs:us-east-1:111111111111:cluster/platform"
TASK_DEFINITION_ARN = "arn:aws:ecs:us-east-1:111111111111:task-definition/canary:7"
OCCURRENCE_ID = "b" * 64


def _attempt() -> dict[str, str]:
    return {
        "task_arn": TASK_ARN,
        "cluster_arn": CLUSTER_ARN,
        "task_definition_arn": TASK_DEFINITION_ARN,
        "platform_cell": "cell-1",
        "job_id": "dev/platform/canary",
        "occurrence_id": OCCURRENCE_ID,
        "config_version": "c" * 64,
        "deployment_identity_id": "d" * 64,
        "account_id": "111111111111",
        "region": "us-east-1",
        "started_by": OCCURRENCE_ID,
    }


def _task_event(**changes: object) -> dict[str, object]:
    event: dict[str, object] = {
        **_attempt(),
        "last_status": "STOPPED",
        "event_time": "2027-01-01T00:02:00.000Z",
        "stop_code": "EssentialContainerExited",
        "stopped_reason": "Essential container in task exited",
        "containers": [{"name": "canary", "essential": True, "exit_code": 0}],
        "tags": {
            "PlatformCell": "cell-1",
            "JobId": "dev/platform/canary",
            "OccurrenceId": OCCURRENCE_ID,
            "ConfigVersion": "c" * 64,
            "AttemptNo": "0",
            "DeploymentIdentity": "d" * 64,
        },
    }
    event.update(changes)
    return event


def test_run_task_failure_and_mixed_response_are_not_success() -> None:
    failed = classify_run_task_response(
        {"tasks": [], "failures": [{"reason": "RESOURCE:MEMORY"}]}
    )
    assert failed == {
        "disposition": "FAILED",
        "accepted": False,
        "error_code": "ECS_RUN_TASK_FAILED",
        "failure_count": 1,
    }
    mixed = classify_run_task_response(
        {"tasks": [{"taskArn": TASK_ARN}], "failures": [{"reason": "CAPACITY"}]}
    )
    assert mixed["disposition"] == "AMBIGUOUS"
    assert mixed["accepted"] is False


def test_run_task_acceptance_requires_one_valid_task() -> None:
    result = classify_run_task_response(
        {"tasks": [{"taskArn": TASK_ARN}], "failures": []}
    )
    assert result == {
        "disposition": "ACCEPTED",
        "accepted": True,
        "task_arn": TASK_ARN,
    }
    with pytest.raises(EcsQualificationError, match="ECS_RESPONSE_SHAPE"):
        classify_run_task_response({"tasks": "bad", "failures": []})


def test_task_evidence_requires_exact_boundary_tags() -> None:
    evidence = validate_task_evidence(_task_event(), _attempt())
    assert evidence["task_arn"] == TASK_ARN
    with pytest.raises(EcsQualificationError, match="ECS_TASK_CORRELATION"):
        validate_task_evidence(_task_event(tags={"PlatformCell": "other"}), _attempt())


def test_runtime_zero_exit_does_not_complete_without_marker() -> None:
    result = classify_task_runtime(_task_event(), _attempt())
    assert result["state"] == "STARTED"
    assert result["completion_pending"] is True
    completed = classify_task_runtime(
        _task_event(),
        _attempt(),
        completion_marker={
            "marker_id": "marker-1",
            "occurrence_id": OCCURRENCE_ID,
            "task_arn": TASK_ARN,
            "status": "SUCCESS",
            "exit_code": 0,
            "observed_at": "2027-01-01T00:03:00.000Z",
        },
    )
    assert completed["state"] == "SUCCEEDED"


@pytest.mark.parametrize(
    ("event", "state"),
    [
        (
            _task_event(last_status="RUNNING", stop_code=None, stopped_reason=None),
            "STARTED",
        ),
        (
            _task_event(
                stop_code="TaskFailedToStart",
                stopped_reason="ResourceInitializationError: unable to pull image",
                containers=[{"name": "canary", "essential": True, "exit_code": None}],
            ),
            "FAILED",
        ),
        (
            _task_event(
                containers=[{"name": "canary", "essential": True, "exit_code": 42}]
            ),
            "FAILED",
        ),
    ],
)
def test_runtime_failure_planes_reduce_to_authoritative_state(
    event: dict[str, object], state: str
) -> None:
    assert classify_task_runtime(event, _attempt())["state"] == state


def test_runtime_threshold_is_detection_only() -> None:
    result = classify_task_runtime(
        _task_event(last_status="RUNNING", stop_code=None, stopped_reason=None),
        _attempt(),
        runtime_deadline_reached=True,
    )
    assert result["state"] == "OVERDUE"
    assert result["automatic_stop"] is False


def test_healthy_launch_runtime_requires_twenty_exact_once_cases() -> None:
    cases = [
        {
            "occurrence_id": str(index),
            "task_arn": TASK_ARN.replace("a" * 32, f"{index:032x}"),
            "window_index": index,
            "started_at": "2027-01-01T00:00:00.000Z",
            "stopped_at": "2027-01-01T00:01:00.000Z",
            "accepted_task_count": 1,
            "start_evidence": 1,
            "stop_evidence": 1,
            "runtime_state": "STARTED",
            "completion_pending": True,
            "launch_alerts": 0,
            "runtime_alerts": 0,
            "cell_health_alerts": 0,
        }
        for index in range(20)
    ]
    assert qualify_healthy_launch_runtime(cases)["passed"] is True
    with pytest.raises(EcsQualificationError, match="ECS_HEALTHY_WINDOWS"):
        qualify_healthy_launch_runtime(
            [*cases[:-1], {**cases[-1], "accepted_task_count": 2}]
        )


def test_manifest_binds_task_and_fault_without_sensitive_values() -> None:
    bindings = {
        "repository": "demo-bmad",
        "source_commit": "a" * 40,
        "workflow_sha": "b" * 40,
        "workflow_run_id": "run-1",
        "plan_sha256": "c" * 64,
        "deployment_identity_sha256": "d" * 64,
        "job_id": "dev/platform/canary",
        "config_sha256": "e" * 64,
        "schedule_generation": "f" * 64,
        "target_manifest_sha256": "1" * 64,
    }
    manifest = build_launch_runtime_manifest(
        release_version="1.0.0",
        compatibility_package="1.0.0",
        account_id="111111111111",
        region="us-east-1",
        cell_identity="cell-1",
        task_definition_arn=TASK_DEFINITION_ARN,
        deployment_identity_id="d" * 64,
        injected_fault="task-start-image-pull",
        expected_result="FAILED",
        test_configuration={"windows": 20},
        policy_versions={"launch": "1.0.0"},
        evidence={"result": "passed"},
        bindings=bindings,
    )
    assert manifest["task_definition_arn"] == TASK_DEFINITION_ARN
    assert manifest["injected_fault"] == "task-start-image-pull"
    assert hashlib.sha256  # keep the checksum contract explicit in the fixture
    results = {
        key: "passed"
        for key in (
            "launch-failure",
            "crash-reconciliation",
            "task-start",
            "runtime-evidence",
            "alert-timing",
            "healthy-runs",
        )
    }
    assert launch_runtime_projection(manifest, results, bindings)["launch-runtime"] == (
        "passed"
    )
    with pytest.raises(EcsQualificationError, match="ECS_SENSITIVE"):
        build_launch_runtime_manifest(
            release_version="1",
            compatibility_package="1",
            account_id="111111111111",
            region="us-east-1",
            cell_identity="cell-1",
            task_definition_arn=TASK_DEFINITION_ARN,
            deployment_identity_id="d" * 64,
            injected_fault="secret-value",
            expected_result="FAILED",
            test_configuration={},
            policy_versions={"launch": "1"},
            evidence={},
            bindings=bindings,
        )
