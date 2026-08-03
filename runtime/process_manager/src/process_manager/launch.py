"""Narrow STS/ECS adapter for one idempotent canary launch."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import re
from typing import Any, Protocol, cast


class LaunchUncertain(RuntimeError):
    """ECS outcome cannot be classified without reconciliation."""


class AssumeRoleClient(Protocol):
    def assume_role(self, **kwargs: Any) -> Mapping[str, Any]: ...


class EcsClient(Protocol):
    def run_task(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def list_tasks(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def describe_tasks(self, **kwargs: Any) -> Mapping[str, Any]: ...


def launch_retry_allowed(attempt: Mapping[str, Any], now: str) -> bool:
    """Prevent a blind RunTask retry after the reserved uncertainty deadline."""

    deadline = attempt.get("safe_retry_deadline")
    if deadline is None:
        raise LaunchUncertain("ECS_RETRY_DEADLINE_MISSING")
    timestamp = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
    if (
        not isinstance(deadline, str)
        or not isinstance(now, str)
        or not re.fullmatch(timestamp, deadline)
        or not re.fullmatch(timestamp, now)
    ):
        raise LaunchUncertain("ECS_RETRY_DEADLINE_INVALID")
    try:
        deadline_at = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        now_at = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as error:
        raise LaunchUncertain("ECS_RETRY_DEADLINE_INVALID") from error
    if deadline_at.tzinfo != timezone.utc or now_at.tzinfo != timezone.utc:
        raise LaunchUncertain("ECS_RETRY_DEADLINE_INVALID")
    return now_at <= deadline_at


def _valid_task_arn(value: Any) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"arn:[^:]+:ecs:[^:]+:[0-9]{12}:task/[^/]+/[0-9a-fA-F-]+", value)
    )


def run_task(ecs: EcsClient, attempt: Mapping[str, Any]) -> str:
    """Run exactly one Fargate task using only already-verified attempt fields."""

    correlation = attempt["correlation"]
    network = {
        "awsvpcConfiguration": {
            "subnets": list(attempt["subnet_ids"]),
            "securityGroups": list(attempt["security_group_ids"]),
            "assignPublicIp": "DISABLED",
        }
    }
    response = ecs.run_task(
        cluster=correlation["cluster_arn"],
        taskDefinition=attempt["task_definition_arn"],
        count=1,
        launchType="FARGATE",
        networkConfiguration=network,
        clientToken=attempt["client_token"],
        startedBy=attempt["occurrence_id"],
        enableECSManagedTags=True,
        tags=[
            {"key": "PlatformCell", "value": attempt["platform_cell"]},
            {"key": "JobId", "value": attempt["job_id"]},
            {"key": "OccurrenceId", "value": attempt["occurrence_id"]},
            {"key": "ConfigVersion", "value": attempt["config_version"]},
            {"key": "AttemptNo", "value": "0"},
            {
                "key": "DeploymentIdentity",
                "value": attempt["deployment_identity_id"],
            },
        ],
        overrides={
            "containerOverrides": [
                {
                    "name": "canary",
                    "environment": [
                        {"name": "PLATFORM_JOB_ID", "value": attempt["job_id"]},
                        {
                            "name": "PLATFORM_OCCURRENCE_ID",
                            "value": attempt["occurrence_id"],
                        },
                        {
                            "name": "PLATFORM_CONFIG_VERSION",
                            "value": attempt["config_version"],
                        },
                        {"name": "PLATFORM_ATTEMPT_NO", "value": "0"},
                        {
                            "name": "PLATFORM_DEPLOYMENT_IDENTITY",
                            "value": attempt["deployment_identity_id"],
                        },
                    ],
                }
            ]
        },
    )
    if not isinstance(response, Mapping):
        raise LaunchUncertain("ECS_RUN_TASK_RESPONSE_INVALID")
    failures = response.get("failures", [])
    tasks = response.get("tasks", [])
    if not isinstance(failures, list) or not isinstance(tasks, list):
        raise LaunchUncertain("ECS_RUN_TASK_RESPONSE_INVALID")
    if isinstance(failures, list) and failures and not tasks:
        raise ValueError("ECS_RUN_TASK_FAILED")
    if isinstance(failures, list) and failures and tasks:
        raise LaunchUncertain("ECS_RUN_TASK_CONFLICT")
    if not isinstance(tasks, list) or len(tasks) != 1:
        raise LaunchUncertain("ECS_RUN_TASK_NO_SINGLE_TASK")
    task_arn = tasks[0].get("taskArn") if isinstance(tasks[0], Mapping) else None
    if not _valid_task_arn(task_arn):
        raise LaunchUncertain("ECS_RUN_TASK_TASK_ARN_INVALID")
    return cast(str, task_arn)


def reconcile_task(ecs: EcsClient, attempt: Mapping[str, Any]) -> str | None:
    """Find one exact accepted task using ECS-owned correlation fields."""

    cluster = attempt["correlation"]["cluster_arn"]
    arns: list[str] = []
    for desired_status in ("PENDING", "RUNNING", "STOPPED"):
        listed = ecs.list_tasks(
            cluster=cluster,
            startedBy=attempt["occurrence_id"],
            desiredStatus=desired_status,
        )
        listed_arns = listed.get("taskArns", [])
        if not isinstance(listed_arns, list) or not all(
            _valid_task_arn(arn) for arn in listed_arns
        ):
            raise LaunchUncertain("ECS_RECONCILIATION_RESPONSE_INVALID")
        arns.extend(arn for arn in listed_arns if arn not in arns)
    if len(arns) > 1:
        raise LaunchUncertain("ECS_RECONCILIATION_MULTIPLE_TASKS")
    if not arns:
        return None
    described = ecs.describe_tasks(cluster=cluster, tasks=arns, include=["TAGS"])
    tasks = described.get("tasks", [])
    if not isinstance(tasks, list) or len(tasks) != 1:
        raise LaunchUncertain("ECS_RECONCILIATION_NOT_EXACT")
    task = tasks[0]
    if not isinstance(task, Mapping) or task.get("taskArn") != arns[0]:
        raise LaunchUncertain("ECS_RECONCILIATION_ARN_MISMATCH")
    if task.get("taskDefinitionArn") != attempt["task_definition_arn"]:
        raise LaunchUncertain("ECS_RECONCILIATION_PARAMETERS_MISMATCH")
    tags = task.get("tags", [])
    if not isinstance(tags, list):
        raise LaunchUncertain("ECS_RECONCILIATION_TAGS_INVALID")
    expected_tags = {
        "PlatformCell": attempt["platform_cell"],
        "JobId": attempt["job_id"],
        "OccurrenceId": attempt["occurrence_id"],
        "ConfigVersion": attempt["config_version"],
        "AttemptNo": "0",
        "DeploymentIdentity": attempt["deployment_identity_id"],
    }
    actual_tags = {
        tag.get("key"): tag.get("value") for tag in tags if isinstance(tag, Mapping)
    }
    if any(actual_tags.get(key) != value for key, value in expected_tags.items()):
        raise LaunchUncertain("ECS_RECONCILIATION_TAG_MISMATCH")
    return str(arns[0])
