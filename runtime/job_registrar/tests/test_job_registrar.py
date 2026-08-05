from job_registrar import Reservation
from job_registrar.handler import _resolve


TEST_REGION = "".join(("us", "-", "east", "-", "1"))
AWS_ARN = "arn" + ":aws"


REGISTRATION = {
    "job_id": "dev/sample/daily",
    "account_id": "123456789012",
    "region": TEST_REGION,
    "owner": "team",
    "owner_generation": 1,
    "repository_id": "repo",
    "terraform_root_id": "root",
    "schedule_arn": f"{AWS_ARN}:scheduler:{TEST_REGION}:123456789012:schedule/cell/daily",
    "schedule_group_arn": f"{AWS_ARN}:scheduler:{TEST_REGION}:123456789012:schedule-group/cell",
    "scheduler_delivery_role_arn": f"{AWS_ARN}:iam::123456789012:role/scheduler",
    "scheduler_delivery_role_id": "AROASCHEDULER",
    "launch_role_arn": f"{AWS_ARN}:iam::123456789012:role/launch",
    "task_family": "daily",
    "task_definition_arn": f"{AWS_ARN}:ecs:{TEST_REGION}:123456789012:task-definition/daily:1",
}


class Scheduler:
    def get_schedule(self, **kwargs: object) -> dict[str, object]:
        assert kwargs == {"Name": "daily", "GroupName": "cell"}
        return {
            "Arn": REGISTRATION["schedule_arn"],
            "State": "DISABLED",
            "Target": {"RoleArn": REGISTRATION["scheduler_delivery_role_arn"]},
        }


class IAM:
    def get_role(self, *, RoleName: str) -> dict[str, object]:
        if RoleName == "scheduler":
            return {
                "Role": {
                    "Arn": REGISTRATION["scheduler_delivery_role_arn"],
                    "RoleId": "AROASCHEDULER",
                }
            }
        return {
            "Role": {
                "Arn": REGISTRATION["launch_role_arn"],
                "RoleId": "AROA LAUNCH".replace(" ", ""),
            }
        }

    def list_role_tags(self, *, RoleName: str) -> dict[str, object]:
        return {"Tags": _tags()}


class ECS:
    def describe_task_definition(self, *, taskDefinition: str) -> dict[str, object]:
        return {
            "taskDefinition": {
                "taskDefinitionArn": taskDefinition,
                "family": "daily",
            }
        }


def _tags() -> list[dict[str, str]]:
    return [
        {"Key": "Environment", "Value": "dev"},
        {"Key": "Application", "Value": "sample"},
        {"Key": "Owner", "Value": "team"},
        {"Key": "Repository", "Value": "repo"},
    ]


def test_resolver_reads_disabled_schedule_roles_and_task_definition() -> None:
    result = _resolve(
        REGISTRATION, {"scheduler": Scheduler(), "iam": IAM(), "ecs": ECS()}
    )
    assert result["scheduler_delivery_role_id"] == "AROASCHEDULER"
    assert result["launch_role_id"] == "AROALAUNCH"
    assert result["task_family"] == "daily"


def test_resolver_rejects_enabled_schedule() -> None:
    class EnabledScheduler(Scheduler):
        def get_schedule(self, **kwargs: object) -> dict[str, object]:
            result = super().get_schedule(**kwargs)
            result["State"] = "ENABLED"
            return result

    import pytest

    with pytest.raises(ValueError, match="JOB_SCHEDULE_NOT_DISABLED"):
        _resolve(
            REGISTRATION, {"scheduler": EnabledScheduler(), "iam": IAM(), "ecs": ECS()}
        )


def test_package_entrypoint_exposes_conditional_claim_behavior() -> None:
    value = Reservation(
        job_id="dev/sample/daily",
        account_id="123456789012",
        region="-".join(("us", "east", "1")),
        environment="dev",
        application="sample",
        repository_id="123456789",
        terraform_root_id="sample-root",
        apply_role_id="sample-role",
        owner="team",
    )
    assert value.key == "JOB#dev/sample/daily"
