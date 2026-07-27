from __future__ import annotations

import pytest

from occurrence_materializer.handler import (
    _assert_authoritative_aws,
    _assert_namespace,
    _validation_request,
)
from occurrence_materializer.materializer import (
    MaterializationError,
    MaterializerRegistration,
)


AWS_ARN = "arn" + ":aws"
REGION = "".join(("us", "-", "east", "-", "1"))
ACCOUNT = "1" * 12
JOB_ID = "dev/sample/daily"
SCHEDULE = f"{AWS_ARN}:scheduler:{REGION}:{ACCOUNT}:schedule/cell/daily"
GROUP = f"{AWS_ARN}:scheduler:{REGION}:{ACCOUNT}:schedule-group/cell"


def registration(**overrides: object) -> MaterializerRegistration:
    values: dict[str, object] = {
        "account_id": ACCOUNT,
        "config_version": "a" * 64,
        "environment": "dev",
        "job_id": JOB_ID,
        "owner_generation": 1,
        "region": REGION,
        "schedule_arn": SCHEDULE,
        "schedule_generation": "b" * 64,
        "scheduler_delivery_role_id": "AROASCHEDULER",
        "schedule_group_arn": GROUP,
        "scheduler_delivery_role_arn": f"{AWS_ARN}:iam::{ACCOUNT}:role/scheduler",
        "launch_role_id": "AROALAUNCH",
    }
    values.update(overrides)
    return MaterializerRegistration(**values)  # type: ignore[arg-type]


def document(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "cluster_arn": f"{AWS_ARN}:ecs:{REGION}:{ACCOUNT}:cluster/cell",
        "task_definition_arn": f"{AWS_ARN}:ecs:{REGION}:{ACCOUNT}:task-definition/daily:1",
        "network": {
            "assign_public_ip": "DISABLED",
            "subnet_ids": ["subnet-a"],
            "security_group_ids": ["sg-a"],
        },
        "role_arns": {
            "execution": f"{AWS_ARN}:iam::{ACCOUNT}:role/execution",
            "launch": f"{AWS_ARN}:iam::{ACCOUNT}:role/launch",
            "task": f"{AWS_ARN}:iam::{ACCOUNT}:role/task",
        },
        "schedule_arn": SCHEDULE,
    }
    values.update(overrides)
    return {"config": values}


class ECS:
    def describe_task_definition(self, *, taskDefinition: str) -> dict[str, object]:
        return {
            "taskDefinition": {
                "taskDefinitionArn": taskDefinition,
                "family": "daily",
                "executionRoleArn": f"{AWS_ARN}:iam::{ACCOUNT}:role/execution",
                "taskRoleArn": f"{AWS_ARN}:iam::{ACCOUNT}:role/task",
                "containerDefinitions": [{"image": "repo/image@sha256:" + "a" * 64}],
            }
        }

    def describe_clusters(self, *, clusters: list[str]) -> dict[str, object]:
        return {"clusters": [{"clusterArn": clusters[0]}]}


class EC2:
    def describe_subnets(self, *, SubnetIds: list[str]) -> dict[str, object]:
        return {"Subnets": [{"SubnetId": value} for value in SubnetIds]}

    def describe_security_groups(self, *, GroupIds: list[str]) -> dict[str, object]:
        return {"SecurityGroups": [{"GroupId": value} for value in GroupIds]}


class IAM:
    def get_role(self, *, RoleName: str) -> dict[str, object]:
        return {
            "Role": {
                "Arn": f"{AWS_ARN}:iam::{ACCOUNT}:role/{RoleName}",
                "RoleId": "AROALAUNCH",
            }
        }


class Scheduler:
    def get_schedule(self, **_: object) -> dict[str, object]:
        return {
            "Arn": SCHEDULE,
            "State": "DISABLED",
            "Target": {"RoleArn": registration().scheduler_delivery_role_arn},
        }


def test_authoritative_mismatch_rejects_wrong_task_definition() -> None:
    class WrongECS(ECS):
        def describe_task_definition(self, *, taskDefinition: str) -> dict[str, object]:
            result = super().describe_task_definition(taskDefinition=taskDefinition)
            result["taskDefinition"]["taskDefinitionArn"] = taskDefinition + "-other"  # type: ignore[index]
            return result

    with pytest.raises(
        MaterializationError, match="MATERIALIZER_TASK_AUTHORITY_MISMATCH"
    ):
        _assert_authoritative_aws(
            document(),
            registration(),
            ecs=WrongECS(),
            ec2=EC2(),
            iam=IAM(),
            scheduler=Scheduler(),
        )


def test_iam_negative_rejects_wrong_launch_role_id() -> None:
    class WrongIAM(IAM):
        def get_role(self, *, RoleName: str) -> dict[str, object]:
            role_id = "AROAWRONG" if RoleName.endswith("launch") else "AROAOTHER"
            return {
                "Role": {
                    "Arn": f"{AWS_ARN}:iam::{ACCOUNT}:role/{RoleName}",
                    "RoleId": role_id,
                }
            }

    with pytest.raises(
        MaterializationError, match="MATERIALIZER_LAUNCH_ROLE_ID_MISMATCH"
    ):
        _assert_authoritative_aws(
            document(),
            registration(),
            ecs=ECS(),
            ec2=EC2(),
            iam=WrongIAM(),
            scheduler=Scheduler(),
        )


def test_scheduler_negative_rejects_enabled_schedule() -> None:
    class EnabledScheduler(Scheduler):
        def get_schedule(self, **kwargs: object) -> dict[str, object]:
            result = super().get_schedule(**kwargs)
            result["State"] = "ENABLED"
            return result

    with pytest.raises(
        MaterializationError, match="MATERIALIZER_SCHEDULER_AUTHORITY_MISMATCH"
    ):
        _assert_authoritative_aws(
            document(),
            registration(),
            ecs=ECS(),
            ec2=EC2(),
            iam=IAM(),
            scheduler=EnabledScheduler(),
        )


def test_api_rejects_invalid_base64_without_calling_aws() -> None:
    with pytest.raises(RuntimeError, match="MATERIALIZER_REQUEST_INVALID"):
        _validation_request({"body": "not-base64", "isBase64Encoded": True})


def test_api_decodes_base64_json_request() -> None:
    encoded = "eyJyZWdpc3RyYXRpb24iOiB7fX0="
    assert _validation_request({"body": encoded, "isBase64Encoded": True}) == {
        "registration": {}
    }


def test_cross_job_namespace_key_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Namespace:
        def __init__(self) -> None:
            self.key: dict[str, object] | None = None

        def get_item(self, **kwargs: object) -> dict[str, object]:
            self.key = kwargs["Key"]  # type: ignore[assignment]
            return {
                "Item": {
                    "account_id": {"S": ACCOUNT},
                    "region": {"S": REGION},
                    "owner_generation": {"N": "1"},
                    "tombstoned": {"BOOL": False},
                    "lifecycle": {"S": "RESERVED"},
                    "transfer_state": {"S": "quiescent"},
                }
            }

    store = Namespace()
    monkeypatch.setenv("MATERIALIZER_NAMESPACE_REGISTRY_TABLE", "registry")
    with pytest.raises(
        MaterializationError, match="MATERIALIZER_NAMESPACE_UNAUTHORIZED"
    ):
        _assert_namespace(store, registration(job_id="dev/other/daily"))
    assert store.key == {
        "pk": {"S": "JOB#dev/other/daily"},
        "sk": {"S": "RESERVATION"},
    }
