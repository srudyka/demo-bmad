"""AWS adapter for authoritative scheduled-job identity binding."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from .domain import (
    DeploymentBinding,
    DynamoReservationStore,
    ReservationRejected,
    bind_deployed_identities,
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"REGISTRAR_CONFIGURATION_MISSING:{name}")
    return value


def _registration(event: Mapping[str, object]) -> Mapping[str, object]:
    value: object = event.get("registration", event)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ReservationRejected("JOB_REGISTRATION_INVALID") from error
    if not isinstance(value, Mapping):
        raise ReservationRejected("JOB_REGISTRATION_INVALID")
    return value


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReservationRejected(code)
    return value


def _schedule_parts(schedule_arn: str) -> tuple[str, str]:
    resource = schedule_arn.rsplit(":", 1)[-1]
    parts = resource.split("/")
    if len(parts) != 3 or parts[0] != "schedule" or not parts[1] or not parts[2]:
        raise ReservationRejected("JOB_SCHEDULE_ARN_INVALID")
    return parts[1], parts[2]


def _role_name(role_arn: str) -> str:
    resource = role_arn.rsplit(":role/", 1)
    if len(resource) != 2 or not resource[1]:
        raise ReservationRejected("JOB_ROLE_ARN_INVALID")
    return resource[1]


def _require_ownership_tags(
    tags_response: Mapping[str, object], registration: Mapping[str, object]
) -> None:
    raw_tags = tags_response.get("Tags")
    if not isinstance(raw_tags, list):
        raise ReservationRejected("JOB_OWNERSHIP_TAGS_INVALID")
    tags = {
        item.get("Key"): item.get("Value")
        for item in raw_tags
        if isinstance(item, Mapping)
    }
    parts = _text(registration.get("job_id"), "JOB_REGISTRATION_INVALID").split("/")
    expected = {
        "Environment": parts[0],
        "Application": parts[1],
        "Owner": _text(registration.get("owner"), "JOB_REGISTRATION_INVALID"),
        "Repository": _text(
            registration.get("repository_id"), "JOB_REGISTRATION_INVALID"
        ),
    }
    if any(tags.get(key) != value for key, value in expected.items()):
        raise ReservationRejected("JOB_OWNERSHIP_TAG_MISMATCH")


def _resolve(
    registration: Mapping[str, object], clients: Mapping[str, Any]
) -> dict[str, object]:
    job_id = _text(registration.get("job_id"), "JOB_REGISTRATION_INVALID")
    account_id = _text(registration.get("account_id"), "JOB_REGISTRATION_INVALID")
    region = _text(registration.get("region"), "JOB_REGISTRATION_INVALID")
    schedule_arn = _text(registration.get("schedule_arn"), "JOB_REGISTRATION_INVALID")
    schedule_group_arn = _text(
        registration.get("schedule_group_arn"), "JOB_REGISTRATION_INVALID"
    )
    schedule_group, schedule_name = _schedule_parts(schedule_arn)
    expected_group_arn = (
        ":".join(schedule_arn.split(":")[:5]) + f":schedule-group/{schedule_group}"
    )
    if schedule_group_arn != expected_group_arn:
        raise ReservationRejected("JOB_SCHEDULE_GROUP_MISMATCH")
    schedule = clients["scheduler"].get_schedule(
        Name=schedule_name, GroupName=schedule_group
    )
    if schedule.get("State") != "DISABLED" or schedule.get("Arn") != schedule_arn:
        raise ReservationRejected("JOB_SCHEDULE_NOT_DISABLED")
    target = schedule.get("Target")
    if not isinstance(target, Mapping):
        raise ReservationRejected("JOB_SCHEDULE_TARGET_INVALID")
    scheduler_role_arn = _text(
        registration.get("scheduler_delivery_role_arn") or target.get("RoleArn"),
        "JOB_SCHEDULER_ROLE_INVALID",
    )
    if target.get("RoleArn") != scheduler_role_arn:
        raise ReservationRejected("JOB_SCHEDULER_ROLE_MISMATCH")

    scheduler_role = clients["iam"].get_role(RoleName=_role_name(scheduler_role_arn))
    scheduler_role_data = scheduler_role.get("Role")
    if not isinstance(scheduler_role_data, Mapping):
        raise ReservationRejected("JOB_SCHEDULER_ROLE_INVALID")
    if scheduler_role_data.get("Arn") != scheduler_role_arn:
        raise ReservationRejected("JOB_SCHEDULER_ROLE_MISMATCH")
    scheduler_role_id = _text(
        scheduler_role_data.get("RoleId"), "JOB_SCHEDULER_ROLE_INVALID"
    )
    expected_scheduler_role_id = registration.get("scheduler_delivery_role_id")
    if (
        expected_scheduler_role_id is not None
        and expected_scheduler_role_id != scheduler_role_id
    ):
        raise ReservationRejected("JOB_SCHEDULER_ROLE_ID_MISMATCH")
    _require_ownership_tags(
        clients["iam"].list_role_tags(RoleName=_role_name(scheduler_role_arn)),
        registration,
    )

    launch_role_arn = _text(
        registration.get("launch_role_arn"), "JOB_REGISTRATION_INVALID"
    )
    launch_role = (
        clients["iam"].get_role(RoleName=_role_name(launch_role_arn)).get("Role")
    )
    if (
        not isinstance(launch_role, Mapping)
        or launch_role.get("Arn") != launch_role_arn
    ):
        raise ReservationRejected("JOB_LAUNCH_ROLE_MISMATCH")
    launch_role_id = _text(launch_role.get("RoleId"), "JOB_LAUNCH_ROLE_INVALID")
    _require_ownership_tags(
        clients["iam"].list_role_tags(RoleName=_role_name(launch_role_arn)),
        registration,
    )

    task_definition_arn = _text(
        registration.get("task_definition_arn"), "JOB_REGISTRATION_INVALID"
    )
    task_definition = clients["ecs"].describe_task_definition(
        taskDefinition=task_definition_arn
    )
    task_data = task_definition.get("taskDefinition")
    if (
        not isinstance(task_data, Mapping)
        or task_data.get("taskDefinitionArn") != task_definition_arn
    ):
        raise ReservationRejected("JOB_TASK_DEFINITION_MISMATCH")
    task_family = _text(task_data.get("family"), "JOB_TASK_DEFINITION_MISMATCH")

    return {
        "job_id": job_id,
        "account_id": account_id,
        "region": region,
        "owner": _text(registration.get("owner"), "JOB_REGISTRATION_INVALID"),
        "owner_generation": registration.get("owner_generation"),
        "schedule_arn": schedule_arn,
        "schedule_group_arn": schedule_group_arn,
        "scheduler_delivery_role_arn": scheduler_role_arn,
        "scheduler_delivery_role_id": scheduler_role_id,
        "launch_role_arn": launch_role_arn,
        "launch_role_id": launch_role_id,
        "task_family": task_family,
        "task_definition_arn": task_definition_arn,
        "repository_id": _text(
            registration.get("repository_id"), "JOB_REGISTRATION_INVALID"
        ),
        "terraform_root_id": _text(
            registration.get("terraform_root_id"), "JOB_REGISTRATION_INVALID"
        ),
    }


def handle(
    event: Mapping[str, object], clients: Mapping[str, Any] | None = None
) -> dict[str, object]:
    """Resolve deployed identities and conditionally bind one reservation."""

    import boto3  # type: ignore[import-untyped]

    registration = _registration(event)
    region = _text(registration.get("region"), "JOB_REGISTRATION_INVALID")
    if clients is None:
        session = boto3.session.Session(region_name=region)
        clients = {
            "scheduler": session.client("scheduler"),
            "iam": session.client("iam"),
            "ecs": session.client("ecs"),
            "dynamodb": session.client("dynamodb"),
        }
    resolved = _resolve(registration, clients)
    table = _required("REGISTRAR_NAMESPACE_REGISTRY_TABLE")
    binding = DeploymentBinding(**resolved)  # type: ignore[arg-type]
    receipt = bind_deployed_identities(
        DynamoReservationStore(clients["dynamodb"], table), binding
    )
    return {
        "status": "BOUND",
        "job_id": binding.job_id,
        "owner_generation": binding.owner_generation,
        "schedule_arn": receipt.get("schedule_arn"),
        "scheduler_delivery_role_id": receipt.get("scheduler_delivery_role_id"),
        "launch_role_id": receipt.get("launch_role_id"),
        "task_family": receipt.get("task_family"),
        "task_definition_arn": receipt.get("task_definition_arn"),
    }


def lambda_handler(event: object, context: object) -> dict[str, object]:
    del context
    if not isinstance(event, Mapping):
        return {
            "statusCode": 400,
            "body": json.dumps({"code": "JOB_REGISTRATION_INVALID"}),
        }
    try:
        return handle(event)
    except ReservationRejected as error:
        return {"statusCode": 409, "body": json.dumps({"code": str(error)})}
