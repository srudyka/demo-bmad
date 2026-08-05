"""Exact AWS deletion request builders; callers must execute through the lifecycle role."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .domain import ArtifactIdentity, LifecycleRejected


@dataclass(frozen=True)
class S3VersionDelete:
    bucket: str
    key: str
    version_id: str


@dataclass(frozen=True)
class LambdaVersionDelete:
    function_name: str
    qualifier: str


@dataclass(frozen=True)
class EcsTaskDefinitionDeregister:
    task_definition: str


class _S3Client(Protocol):
    def delete_object(self, *, Bucket: str, Key: str, VersionId: str) -> object: ...


class _LambdaClient(Protocol):
    def delete_function(self, *, FunctionName: str, Qualifier: str) -> object: ...


class _EcsClient(Protocol):
    def deregister_task_definition(self, *, taskDefinition: str) -> object: ...


class S3DeleteAdapter:
    def __init__(self, client: _S3Client) -> None:
        self.client = client

    def delete(self, artifact: ArtifactIdentity) -> str:
        request = s3_version_delete(artifact)
        self.client.delete_object(
            Bucket=request.bucket, Key=request.key, VersionId=request.version_id
        )
        return "DELETED"


class LambdaVersionDeleteAdapter:
    def __init__(self, client: _LambdaClient) -> None:
        self.client = client

    def delete(self, artifact: ArtifactIdentity) -> str:
        request = lambda_version_delete(artifact)
        self.client.delete_function(
            FunctionName=request.function_name, Qualifier=request.qualifier
        )
        return "DELETED"


class EcsTaskDefinitionAdapter:
    def __init__(self, client: _EcsClient) -> None:
        self.client = client

    def delete(self, artifact: ArtifactIdentity) -> str:
        request = ecs_task_definition_deregister(artifact)
        self.client.deregister_task_definition(taskDefinition=request.task_definition)
        return "DELETED"


_S3 = re.compile(r"^s3://([^/]+)/(.+)$")
_LAMBDA_ARN = re.compile(
    r"^arn:(?:aws|aws-us-gov|aws-cn):lambda:[^:]+:[0-9]{12}:function:[A-Za-z0-9-_]+$"
)
_ECS_ARN = re.compile(
    r"^arn:(?:aws|aws-us-gov|aws-cn):ecs:[^:]+:[0-9]{12}:task-definition/[A-Za-z0-9_-]+:[1-9][0-9]*$"
)


def s3_version_delete(artifact: ArtifactIdentity) -> S3VersionDelete:
    if artifact.artifact_class != "config":
        raise LifecycleRejected("LIFECYCLE_ADAPTER_CLASS")
    match = _S3.fullmatch(artifact.resource)
    if match is None or artifact.version == "null":
        raise LifecycleRejected("LIFECYCLE_S3_VERSION_REQUIRED")
    return S3VersionDelete(match.group(1), match.group(2), artifact.version)


def lambda_version_delete(artifact: ArtifactIdentity) -> LambdaVersionDelete:
    if (
        artifact.artifact_class != "runtime"
        or _LAMBDA_ARN.fullmatch(artifact.resource) is None
    ):
        raise LifecycleRejected("LIFECYCLE_LAMBDA_TARGET")
    if not artifact.version.isdecimal() or artifact.version == "0":
        raise LifecycleRejected("LIFECYCLE_LAMBDA_VERSION")
    return LambdaVersionDelete(artifact.resource, artifact.version)


def ecs_task_definition_deregister(
    artifact: ArtifactIdentity,
) -> EcsTaskDefinitionDeregister:
    if (
        artifact.artifact_class != "task-definition"
        or _ECS_ARN.fullmatch(artifact.resource) is None
    ):
        raise LifecycleRejected("LIFECYCLE_ECS_TARGET")
    return EcsTaskDefinitionDeregister(artifact.resource)
