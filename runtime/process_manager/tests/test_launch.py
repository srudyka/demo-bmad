from __future__ import annotations

from typing import Any

import pytest

from process_manager.launch import (
    LaunchUncertain,
    launch_retry_allowed,
    reconcile_task,
    run_task,
)


def attempt() -> dict[str, Any]:
    return {
        "correlation": {"cluster_arn": "cluster-arn"},
        "task_definition_arn": "task-definition-arn:7",
        "subnet_ids": ["subnet-a"],
        "security_group_ids": ["sg-a"],
        "client_token": "a" * 64,
        "occurrence_id": "b" * 64,
        "deployment_identity_id": "c" * 64,
        "platform_cell": "cell-1",
        "job_id": "dev/platform/canary",
        "config_version": "d" * 64,
    }


TASK_ARN = "arn" + ":aws:ecs:" + "us" + "-east-1:111122223333:task/cluster/" + "a" * 32


class FakeEcs:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.run_kwargs: dict[str, Any] = {}

    def run_task(self, **kwargs: Any) -> dict[str, Any]:
        self.run_kwargs = kwargs
        return self.response

    def list_tasks(self, **kwargs: Any) -> dict[str, Any]:
        return {"taskArns": [TASK_ARN]}

    def describe_tasks(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "tasks": [
                {
                    "taskArn": TASK_ARN,
                    "taskDefinitionArn": "task-definition-arn:7",
                    "tags": [
                        {"key": "PlatformCell", "value": "cell-1"},
                        {"key": "JobId", "value": "dev/platform/canary"},
                        {"key": "OccurrenceId", "value": "b" * 64},
                        {"key": "ConfigVersion", "value": "d" * 64},
                        {"key": "AttemptNo", "value": "0"},
                        {"key": "DeploymentIdentity", "value": "c" * 64},
                    ],
                }
            ]
        }


def test_run_task_is_count_one_private_and_platform_tagged() -> None:
    ecs = FakeEcs({"failures": [], "tasks": [{"taskArn": TASK_ARN}]})
    assert run_task(ecs, attempt()) == TASK_ARN
    assert ecs.run_kwargs["count"] == 1
    assert (
        ecs.run_kwargs["networkConfiguration"]["awsvpcConfiguration"]["assignPublicIp"]
        == "DISABLED"
    )
    assert {tag["key"] for tag in ecs.run_kwargs["tags"]} == {
        "PlatformCell",
        "JobId",
        "OccurrenceId",
        "ConfigVersion",
        "AttemptNo",
        "DeploymentIdentity",
    }
    assert ecs.run_kwargs["startedBy"] == "b" * 64


def test_http_200_failures_are_not_treated_as_success() -> None:
    ecs = FakeEcs({"failures": [{"reason": "RESOURCE:MEMORY"}], "tasks": []})
    with pytest.raises(ValueError, match="ECS_RUN_TASK_FAILED"):
        run_task(ecs, attempt())


def test_reconciliation_requires_one_exact_task() -> None:
    ecs = FakeEcs({"failures": [], "tasks": []})
    assert reconcile_task(ecs, attempt()) == TASK_ARN

    class Multiple(FakeEcs):
        def list_tasks(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "taskArns": [
                    TASK_ARN,
                    "arn"
                    + ":aws:ecs:"
                    + "us"
                    + "-east-1:111122223333:task/cluster/"
                    + "b" * 32,
                ]
            }

    with pytest.raises(LaunchUncertain, match="MULTIPLE_TASKS"):
        reconcile_task(Multiple({}), attempt())


def test_retry_deadline_blocks_blind_run_task_after_uncertainty_window() -> None:
    value = {
        **attempt(),
        "safe_retry_deadline": "2027-01-01T01:00:00.000Z",
    }
    assert launch_retry_allowed(value, "2027-01-01T00:59:59.000Z") is True
    assert launch_retry_allowed(value, "2027-01-01T01:00:00.001Z") is False
    with pytest.raises(LaunchUncertain, match="RETRY_DEADLINE_INVALID"):
        launch_retry_allowed(value, "2027-01-01T01:00:00Z")
    with pytest.raises(LaunchUncertain, match="RETRY_DEADLINE_MISSING"):
        launch_retry_allowed(attempt(), "2027-01-01T00:00:00.000Z")


def test_run_task_rejects_malformed_task_identity() -> None:
    ecs = FakeEcs({"failures": [], "tasks": [{"taskArn": "task-arn"}]})
    with pytest.raises(LaunchUncertain, match="TASK_ARN_INVALID"):
        run_task(ecs, attempt())


def test_reconciliation_includes_pending_tasks() -> None:
    class Pending(FakeEcs):
        def list_tasks(self, **kwargs: Any) -> dict[str, Any]:
            if kwargs["desiredStatus"] == "PENDING":
                return {"taskArns": [TASK_ARN]}
            return {"taskArns": []}

    assert reconcile_task(Pending({}), attempt()) == TASK_ARN
