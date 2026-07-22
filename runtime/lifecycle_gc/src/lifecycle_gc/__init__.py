"""Fail-closed platform version lifecycle primitives."""

from .domain import (
    ArtifactClass,
    ArtifactIdentity,
    CleanupDecision,
    ReferenceEvidence,
    build_retirement_manifest,
    evaluate_candidate,
    manifest_checksum,
)
from .cleanup import (
    DeletionOutcome,
    Tombstone,
    execute_manifest,
    validate_manifest_for_execution,
)
from .adapters import (
    EcsTaskDefinitionAdapter,
    EcsTaskDefinitionDeregister,
    LambdaVersionDelete,
    LambdaVersionDeleteAdapter,
    S3DeleteAdapter,
    S3VersionDelete,
    ecs_task_definition_deregister,
    lambda_version_delete,
    s3_version_delete,
)
from .inventory import InventoryPage, InventorySnapshot, build_inventory

__all__ = [
    "ArtifactClass",
    "ArtifactIdentity",
    "CleanupDecision",
    "ReferenceEvidence",
    "build_retirement_manifest",
    "evaluate_candidate",
    "manifest_checksum",
    "DeletionOutcome",
    "Tombstone",
    "execute_manifest",
    "validate_manifest_for_execution",
    "EcsTaskDefinitionDeregister",
    "EcsTaskDefinitionAdapter",
    "LambdaVersionDelete",
    "LambdaVersionDeleteAdapter",
    "S3VersionDelete",
    "S3DeleteAdapter",
    "ecs_task_definition_deregister",
    "lambda_version_delete",
    "s3_version_delete",
    "InventoryPage",
    "InventorySnapshot",
    "build_inventory",
]
