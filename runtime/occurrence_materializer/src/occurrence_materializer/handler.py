"""AWS adapter for the independent occurrence materializer."""

from __future__ import annotations

import json
import os
import re
import base64
from pathlib import Path
from typing import Any, Mapping

from tests.contract.support.contracts import (
    ContractViolation,
    build_schema_registry,
    canonical_json_bytes,
    load_json_bytes_strict,
    load_json_strict,
)

from .materializer import (
    MaterializationError,
    MaterializerRegistration,
    _parse_timestamp,
    _timestamp,
    materialize_config,
)


_EVENTBRIDGE_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"MATERIALIZER_CONFIGURATION_MISSING:{name}")
    return value


def _resolve_recovery_table() -> None:
    parameter = os.environ.get("MATERIALIZER_RECOVERY_POINTER_PARAMETER_NAME")
    if not parameter:
        return
    import boto3  # type: ignore[import-untyped]

    value = json.loads(
        boto3.client("ssm").get_parameter(Name=parameter, WithDecryption=True)[
            "Parameter"
        ]["Value"]
    )
    tables = value.get("tables") if isinstance(value, Mapping) else None
    if (
        not isinstance(tables, list)
        or len(tables) < 2
        or not all(isinstance(item, str) for item in tables)
    ):
        raise RuntimeError("MATERIALIZER_RECOVERY_POINTER_INVALID")
    os.environ["MATERIALIZER_NAMESPACE_REGISTRY_TABLE"] = tables[0]
    os.environ["MATERIALIZER_CONFIG_REGISTRY_TABLE"] = tables[1]


def _registration(
    event: Mapping[str, object] | None = None,
) -> MaterializerRegistration:
    try:
        candidate = event.get("registration") if isinstance(event, Mapping) else None
        value = candidate
        if value is None:
            value = json.loads(_required("MATERIALIZER_REGISTRATION"))
        if not isinstance(value, Mapping):
            raise TypeError("registration must be an object")
        return MaterializerRegistration(**value)
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError("MATERIALIZER_REGISTRATION_INVALID") from error


def _validation_request(event: Mapping[str, object]) -> Mapping[str, object]:
    """Decode the Cell acknowledgement request without retaining caller details."""

    body = event.get("body")
    if isinstance(body, str):
        if event.get("isBase64Encoded") is True:
            try:
                body = base64.b64decode(body, validate=True).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as error:
                raise RuntimeError("MATERIALIZER_REQUEST_INVALID") from error
        try:
            value = json.loads(body)
        except json.JSONDecodeError as error:
            raise RuntimeError("MATERIALIZER_REQUEST_INVALID") from error
        if not isinstance(value, Mapping):
            raise RuntimeError("MATERIALIZER_REQUEST_INVALID")
        return value
    return event


def _safe_error_code(error: Exception) -> str:
    """Return only a stable machine code, never provider or payload text."""

    candidate = str(error).split(":", 1)[0]
    return (
        candidate
        if re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", candidate)
        else "MATERIALIZER_VALIDATION_FAILED"
    )


def _item(snapshot: Mapping[str, object]) -> dict[str, dict[str, object]]:
    item: dict[str, dict[str, object]] = {
        key: {"S": value} for key, value in snapshot.items() if isinstance(value, str)
    }
    occurrence_ids = snapshot.get("expected_occurrence_ids")
    if isinstance(occurrence_ids, list):
        if not all(isinstance(value, str) for value in occurrence_ids):
            raise RuntimeError("MATERIALIZER_SNAPSHOT_INVALID")
        if occurrence_ids:
            item["expected_occurrence_ids"] = {"SS": occurrence_ids}
    return item


def _metric(
    metrics: object,
    registration: MaterializerRegistration,
    state: str,
    horizon_freshness_hours: float | None = None,
    conformance_result: str | None = None,
) -> None:
    metric_data: list[dict[str, object]] = [
        {
            "MetricName": "OccurrenceMaterializerResult",
            "Unit": "Count",
            "Value": 1.0,
            "Dimensions": [
                {"Name": "environment", "Value": registration.environment},
                {
                    "Name": "failure_plane",
                    "Value": "validation"
                    if os.environ.get("MATERIALIZER_MODE") == "validate"
                    else "materialization",
                },
                {"Name": "job_id", "Value": registration.job_id},
                {"Name": "state", "Value": state},
            ],
        }
    ]
    if horizon_freshness_hours is not None:
        metric_data.append(
            {
                "MetricName": "HorizonFreshnessHours",
                "Unit": "Count",
                "Value": horizon_freshness_hours,
                "Dimensions": [
                    {"Name": "environment", "Value": registration.environment},
                    {
                        "Name": "failure_plane",
                        "Value": "validation"
                        if os.environ.get("MATERIALIZER_MODE") == "validate"
                        else "materialization",
                    },
                    {"Name": "job_id", "Value": registration.job_id},
                ],
            }
        )
    if conformance_result is not None:
        metric_data.append(
            {
                "MetricName": "SchedulerConformance",
                "Unit": "Count",
                "Value": 1.0,
                "Dimensions": [
                    {"Name": "environment", "Value": registration.environment},
                    {
                        "Name": "failure_plane",
                        "Value": "validation"
                        if os.environ.get("MATERIALIZER_MODE") == "validate"
                        else "materialization",
                    },
                    {"Name": "job_id", "Value": registration.job_id},
                    {"Name": "result", "Value": conformance_result},
                ],
            }
        )
    if (
        state in {"rejected", "conflict"}
        and os.environ.get("MATERIALIZER_MODE") == "validate"
    ):
        metric_data.append(
            {
                "MetricName": "ValidationRejections"
                if state == "rejected"
                else "ValidationConflicts",
                "Unit": "Count",
                "Value": 1.0,
                "Dimensions": [
                    {"Name": "environment", "Value": registration.environment}
                ],
            }
        )
    metrics.put_metric_data(  # type: ignore[attr-defined]
        Namespace=_required("MATERIALIZER_METRIC_NAMESPACE"),
        MetricData=metric_data,
    )


def _rejected_item(
    registration: MaterializerRegistration, code: str, rejected_at: str
) -> dict[str, dict[str, object]]:
    return {
        "pk": {"S": f"JOB#{registration.job_id}"},
        "sk": {"S": f"CONFIG#{registration.config_version}"},
        "record_type": {"S": "CONFIG_MATERIALIZATION"},
        "job_id": {"S": registration.job_id},
        "config_version": {"S": registration.config_version},
        "owner_generation": {"N": str(registration.owner_generation)},
        "validation_state": {"S": "REJECTED"},
        "rejection_code": {"S": code.split(":", 1)[0]},
        "rejection_reason": {"S": _rejection_reason(code)},
        "rejected_at": {"S": rejected_at},
    }


def _rejection_reason(code: str) -> str:
    safe = code.split(":", 1)[0]
    reasons = {
        "MATERIALIZER_CONFIG_NONCANONICAL": "CONFIG bytes are not canonical",
        "MATERIALIZER_NETWORK_AUTHORITY_MISMATCH": "network identity does not match authoritative AWS metadata",
        "MATERIALIZER_IAM_AUTHORITY_MISMATCH": "IAM role identity does not match authoritative AWS metadata",
        "MATERIALIZER_SCHEDULER_AUTHORITY_MISMATCH": "Scheduler identity or state does not match the registered contract",
        "MATERIALIZER_SNAPSHOT_CONFLICT": "an immutable acknowledgement already exists with different evidence",
    }
    return reasons.get(safe, "CONFIG failed Cell validation")


def _conditional_code(error: Exception) -> str | None:
    """Return the AWS error code without exposing the provider exception text."""

    response = getattr(error, "response", None)
    if not isinstance(response, Mapping):
        return None
    details = response.get("Error")
    return details.get("Code") if isinstance(details, Mapping) else None


def _put_validated_snapshot(
    dynamodb: object,
    registration: MaterializerRegistration,
    snapshot: Mapping[str, object],
) -> bool:
    """Persist once, returning whether an incomplete materialization needs delivery."""

    table_name = _required("MATERIALIZER_CONFIG_REGISTRY_TABLE")
    try:
        dynamodb.put_item(  # type: ignore[attr-defined]
            TableName=table_name,
            Item=_item(snapshot),
            ConditionExpression="attribute_not_exists(pk) OR validation_state = :published",
            ExpressionAttributeValues={":published": {"S": "PUBLISHED"}},
        )
        return True
    except Exception as error:
        if _conditional_code(error) != "ConditionalCheckFailedException":
            raise
    response = dynamodb.get_item(  # type: ignore[attr-defined]
        TableName=table_name,
        ConsistentRead=True,
        Key={
            "pk": {"S": f"JOB#{registration.job_id}"},
            "sk": {"S": f"CONFIG#{registration.config_version}"},
        },
    )
    item = response.get("Item", {})
    if (
        item.get("config_hash", {}).get("S") != registration.config_version
        or item.get("validation_state", {}).get("S") != "VALIDATED"
    ):
        raise RuntimeError("MATERIALIZER_SNAPSHOT_CONFLICT")
    for field in (
        "job_id",
        "config_version",
        "schedule_generation",
        "schedule_arn",
        "schedule_group_arn",
        "scheduler_delivery_role_arn",
        "scheduler_delivery_role_id",
        "launch_role_arn",
        "launch_role_id",
        "task_family",
        "owner_generation",
        "contract_version",
        "contract_checksum",
        "validation_evidence",
    ):
        expected = snapshot.get(field)
        if isinstance(expected, str) and item.get(field, {}).get("S") != expected:
            raise RuntimeError("MATERIALIZER_SNAPSHOT_CONFLICT")
    state = item.get("materialization_state", {}).get("S")
    if state == "MATERIALIZED":
        horizon_at = item.get("horizon_at", {}).get("S")
        if horizon_at and str(horizon_at) >= str(snapshot["horizon_at"]):
            return False
        return True
    if state != "PENDING":
        raise RuntimeError("MATERIALIZER_SNAPSHOT_CONFLICT")
    return True


def _mark_materialized(
    dynamodb: object,
    registration: MaterializerRegistration,
    snapshot: Mapping[str, object],
    completed_at: str,
) -> None:
    """Advance only the status marker after all deterministic sends succeed."""

    dynamodb.update_item(  # type: ignore[attr-defined]
        TableName=_required("MATERIALIZER_CONFIG_REGISTRY_TABLE"),
        Key={
            "pk": {"S": f"JOB#{registration.job_id}"},
            "sk": {"S": f"CONFIG#{registration.config_version}"},
        },
        UpdateExpression=(
            "SET materialization_state = :materialized, materialized_at = :materialized_at, "
            "horizon_at = :horizon_at, horizon_watermark = :horizon_at, "
            "conformance_result = :conformance_result"
        ),
        ConditionExpression=(
            "validation_state = :validated AND materialization_state IN (:pending, :materialized) "
            "AND config_hash = :config_hash AND horizon_at <= :horizon_at"
        ),
        ExpressionAttributeValues={
            ":config_hash": {"S": registration.config_version},
            ":conformance_result": {"S": "PASS"},
            ":horizon_at": {"S": str(snapshot["horizon_at"])},
            ":materialized": {"S": "MATERIALIZED"},
            ":materialized_at": {"S": completed_at},
            ":pending": {"S": "PENDING"},
            ":validated": {"S": "VALIDATED"},
        },
    )


def _record_rejection(
    dynamodb: object,
    registration: MaterializerRegistration,
    code: str,
    rejected_at: str,
) -> None:
    """Persist one sanitized terminal rejection; transient storage failures retry."""

    try:
        dynamodb.put_item(  # type: ignore[attr-defined]
            TableName=_required("MATERIALIZER_CONFIG_REGISTRY_TABLE"),
            Item=_rejected_item(registration, code, rejected_at),
            ConditionExpression="attribute_not_exists(pk) OR validation_state = :published",
            ExpressionAttributeValues={":published": {"S": "PUBLISHED"}},
        )
    except Exception as error:
        if _conditional_code(error) != "ConditionalCheckFailedException":
            raise
        # Preserve sanitized rejection evidence instead of raising
        return


def _validation_handler(event: Mapping[str, object]) -> dict[str, object]:
    """Validate and acknowledge one CONFIG without materializing expectations."""

    from datetime import UTC, datetime

    request = _validation_request(event)
    # The validator is the authority for evidence time. Request timestamps are
    # intentionally ignored so callers cannot backdate or future-date ACKs.
    validated_at = _timestamp(datetime.now(UTC))
    import boto3

    registration = _registration(request)
    contracts_root = Path(_required("MATERIALIZER_CONTRACTS_ROOT"))
    schemas, schema_registry = build_schema_registry(contracts_root / "schemas")
    secret_policy = load_json_strict(contracts_root / "catalogs" / "secret-safety.json")
    compatibility_catalog = load_json_strict(
        contracts_root / "catalogs" / "compatibility.json"
    )
    s3 = boto3.client("s3")
    dynamodb = boto3.client("dynamodb")
    metrics = boto3.client("cloudwatch")
    ecs = boto3.client("ecs", region_name=registration.region)
    ec2 = boto3.client("ec2", region_name=registration.region)
    iam = boto3.client("iam", region_name=registration.region)
    scheduler = boto3.client("scheduler", region_name=registration.region)
    logs = boto3.client("logs", region_name=registration.region)
    try:
        _assert_namespace(dynamodb, registration)
        expected_key = (
            f"jobs/{registration.job_id}/config/{registration.config_version}.json"
        )
        response = s3.get_object(
            Bucket=_required("MATERIALIZER_CONFIG_BUCKET"),
            Key=expected_key,
        )
        metadata = response.get("Metadata", {})
        if (
            not isinstance(metadata, Mapping)
            or metadata.get("job-id") != registration.job_id
            or metadata.get("config-version") != registration.config_version
            or response.get("ServerSideEncryption") != "aws:kms"
            or response.get("SSEKMSKeyId") != _required("MATERIALIZER_KMS_KEY_ARN")
        ):
            raise MaterializationError("MATERIALIZER_OBJECT_METADATA_INVALID")
        body = response["Body"].read()
        if len(body) > 300000:
            raise MaterializationError("MATERIALIZER_CONFIG_OVERSIZED")
        document = load_json_bytes_strict(body)
        if body != canonical_json_bytes(document):
            raise MaterializationError("MATERIALIZER_CONFIG_NONCANONICAL")
        result = materialize_config(
            document,
            registration,
            validated_at,
            schemas,
            schema_registry,
            secret_policy,
            compatibility_catalog,
            materialize=False,
        )
        _assert_authoritative_aws(
            document,
            registration,
            ecs=ecs,
            ec2=ec2,
            iam=iam,
            scheduler=scheduler,
            logs=logs,
        )
    except (MaterializationError, ContractViolation) as error:
        code = _safe_error_code(error)
        _record_rejection(dynamodb, registration, code, validated_at)
        _metric(metrics, registration, "rejected")
        return {
            "rejected": True,
            "error_code": code,
            "error_reason": _rejection_reason(code),
        }
    try:
        _put_validated_snapshot(dynamodb, registration, result.snapshot)
    except RuntimeError as error:
        code = _safe_error_code(error)
        if code != "MATERIALIZER_SNAPSHOT_CONFLICT":
            raise
        _record_rejection(dynamodb, registration, code, validated_at)
        _metric(metrics, registration, "conflict")
        return {
            "rejected": True,
            "error_code": code,
            "error_reason": _rejection_reason(code),
        }
    _metric(metrics, registration, "validated", conformance_result="PASS")
    return {
        "validated": True,
        "lifecycle": "VALIDATED",
        "job_id": registration.job_id,
        "config_version": registration.config_version,
        "ownership_generation": registration.owner_generation,
        "account_id": registration.account_id,
        "environment": registration.environment,
        "schedule_generation": registration.schedule_generation,
        "schedule_arn": registration.schedule_arn,
        "schedule_group_arn": registration.schedule_group_arn,
        "scheduler_delivery_role_arn": registration.scheduler_delivery_role_arn,
        "scheduler_delivery_role_id": registration.scheduler_delivery_role_id,
        "launch_role_arn": registration.launch_role_arn,
        "launch_role_id": registration.launch_role_id,
        "task_family": registration.task_family,
        "task_definition_arn": registration.task_definition_arn,
        "repository_id": registration.repository_id,
        "terraform_root_id": registration.terraform_root_id,
        "contract_version": result.snapshot["contract_version"],
        "contract_checksum": result.snapshot["contract_checksum"],
        "horizon_watermark": result.snapshot["horizon_watermark"],
        "validation_evidence": result.snapshot["validation_evidence"],
        "validated_at": result.snapshot["validated_at"],
    }


def _assert_authoritative_aws(
    document: Mapping[str, object],
    registration: MaterializerRegistration,
    *,
    ecs: Any,
    ec2: Any,
    iam: Any,
    scheduler: Any,
    logs: Any | None = None,
) -> None:
    """Compare CONFIG assertions with current AWS resource metadata."""

    config = document.get("config")
    if not isinstance(config, Mapping):
        raise MaterializationError("MATERIALIZER_CONFIG_INVALID")
    task_definition_arn = config.get("task_definition_arn")
    cluster_arn = config.get("cluster_arn")
    if not isinstance(task_definition_arn, str) or not isinstance(cluster_arn, str):
        raise MaterializationError("MATERIALIZER_AUTHORITY_INVALID")
    task = ecs.describe_task_definition(taskDefinition=task_definition_arn).get(
        "taskDefinition", {}
    )
    if (
        task.get("taskDefinitionArn") != task_definition_arn
        or task.get("family")
        != task_definition_arn.rsplit("/", 1)[-1].rsplit(":", 1)[0]
    ):
        raise MaterializationError("MATERIALIZER_TASK_AUTHORITY_MISMATCH")
    if (
        registration.task_definition_arn
        and registration.task_definition_arn != task_definition_arn
    ):
        raise MaterializationError("MATERIALIZER_TASK_AUTHORITY_MISMATCH")
    roles = config.get("role_arns")
    if not isinstance(roles, Mapping):
        raise MaterializationError("MATERIALIZER_IAM_AUTHORITY_MISMATCH")
    if task.get("executionRoleArn") != roles.get("execution") or task.get(
        "taskRoleArn"
    ) != roles.get("task"):
        raise MaterializationError("MATERIALIZER_TASK_ROLE_MISMATCH")
    containers = task.get("containerDefinitions", [])
    if not isinstance(containers, list) or any(
        not isinstance(container, Mapping)
        or not isinstance(container.get("image"), str)
        or "@sha256:" not in container["image"]
        for container in containers
    ):
        raise MaterializationError("MATERIALIZER_IMAGE_IMMUTABLE_REQUIRED")
    clusters = ecs.describe_clusters(clusters=[cluster_arn]).get("clusters", [])
    if len(clusters) != 1 or clusters[0].get("clusterArn") != cluster_arn:
        raise MaterializationError("MATERIALIZER_CLUSTER_AUTHORITY_MISMATCH")

    network = config.get("network")
    if (
        not isinstance(network, Mapping)
        or network.get("assign_public_ip") != "DISABLED"
    ):
        raise MaterializationError("MATERIALIZER_NETWORK_AUTHORITY_MISMATCH")
    subnet_ids = network.get("subnet_ids", [])
    security_group_ids = network.get("security_group_ids", [])
    if not isinstance(subnet_ids, list) or not isinstance(security_group_ids, list):
        raise MaterializationError("MATERIALIZER_NETWORK_AUTHORITY_MISMATCH")
    subnets = ec2.describe_subnets(SubnetIds=subnet_ids).get("Subnets", [])
    groups = ec2.describe_security_groups(GroupIds=security_group_ids).get(
        "SecurityGroups", []
    )
    if len(subnets) != len(subnet_ids) or len(groups) != len(security_group_ids):
        raise MaterializationError("MATERIALIZER_NETWORK_AUTHORITY_MISMATCH")
    expected_vpc = network.get("vpc_id")
    if expected_vpc is not None and any(
        subnet.get("VpcId") != expected_vpc for subnet in subnets
    ):
        raise MaterializationError("MATERIALIZER_NETWORK_AUTHORITY_MISMATCH")
    if any(subnet.get("MapPublicIpOnLaunch") is True for subnet in subnets):
        raise MaterializationError("MATERIALIZER_PUBLIC_SUBNET")

    log_config = config.get("logs")
    if logs is not None and isinstance(log_config, Mapping):
        log_group_arn = log_config.get("log_group_arn")
        if not isinstance(log_group_arn, str):
            raise MaterializationError("MATERIALIZER_LOG_AUTHORITY_MISMATCH")
        log_groups = logs.describe_log_groups(logGroupNamePrefix=log_group_arn).get(
            "logGroups", []
        )
        if not any(
            group.get("arn", "").rstrip(":*") == log_group_arn for group in log_groups
        ):
            raise MaterializationError("MATERIALIZER_LOG_AUTHORITY_MISMATCH")

    for role_key, role_arn in roles.items():
        if not isinstance(role_arn, str) or ":role/" not in role_arn:
            raise MaterializationError("MATERIALIZER_IAM_AUTHORITY_MISMATCH")
        role_name = role_arn.split(":role/", 1)[1]
        role = iam.get_role(RoleName=role_name).get("Role", {})
        if role.get("Arn") != role_arn:
            raise MaterializationError("MATERIALIZER_IAM_AUTHORITY_MISMATCH")
        if role_key == "launch" and registration.launch_role_id:
            if role.get("RoleId") != registration.launch_role_id:
                raise MaterializationError("MATERIALIZER_LAUNCH_ROLE_ID_MISMATCH")

    schedule_arn = config.get("schedule_arn")
    if not isinstance(schedule_arn, str) or ":schedule/" not in schedule_arn:
        raise MaterializationError("MATERIALIZER_SCHEDULER_AUTHORITY_MISMATCH")
    schedule_name = schedule_arn.rsplit("/", 1)[-1]
    schedule_group = (
        registration.schedule_group_arn.rsplit("/", 1)[-1]
        if registration.schedule_group_arn
        else None
    )
    schedule = scheduler.get_schedule(
        Name=schedule_name, GroupName=schedule_group or "default"
    )
    if schedule.get("State") != "DISABLED" or schedule.get("Arn") != schedule_arn:
        raise MaterializationError("MATERIALIZER_SCHEDULER_AUTHORITY_MISMATCH")
    if registration.scheduler_delivery_role_arn:
        target = schedule.get("Target", {})
        if target.get("RoleArn") != registration.scheduler_delivery_role_arn:
            raise MaterializationError("MATERIALIZER_SCHEDULER_ROLE_ARN_MISMATCH")
    schedule_config = config.get("schedule")
    if isinstance(schedule_config, Mapping):
        if schedule_config.get("flexible_time_window", "OFF") != "OFF":
            raise MaterializationError("MATERIALIZER_SCHEDULE_FLEXIBLE_WINDOW")
        retry = schedule.get("RetryPolicy")
        expected_retry = schedule_config.get("retry_policy")
        if expected_retry is not None and retry != expected_retry:
            raise MaterializationError("MATERIALIZER_SCHEDULE_RETRY_MISMATCH")


def _assert_namespace(dynamodb: object, registration: MaterializerRegistration) -> None:
    response = dynamodb.get_item(  # type: ignore[attr-defined]
        TableName=_required("MATERIALIZER_NAMESPACE_REGISTRY_TABLE"),
        ConsistentRead=True,
        Key={"pk": {"S": f"JOB#{registration.job_id}"}, "sk": {"S": "RESERVATION"}},
    )
    item = response.get("Item", {})
    if (
        item.get("job_id", {}).get("S") != registration.job_id
        or item.get("account_id", {}).get("S") != registration.account_id
        or item.get("region", {}).get("S") != registration.region
        or item.get("owner_generation", {}).get("N")
        != str(registration.owner_generation)
        or item.get("tombstoned", {}).get("BOOL") is not False
        or item.get("lifecycle", {}).get("S") != "RESERVED"
        or item.get("transfer_state", {}).get("S") != "quiescent"
    ):
        raise MaterializationError("MATERIALIZER_NAMESPACE_UNAUTHORIZED")


def lambda_handler(event: Mapping[str, object], _context: object) -> dict[str, object]:
    if os.environ.get("MATERIALIZER_MODE") == "validate":
        try:
            validation_result = _validation_handler(event)
        except RuntimeError as error:
            validation_result = {
                "rejected": True,
                "error_code": _safe_error_code(error),
            }
        if "body" in event:
            return {
                "statusCode": 200 if validation_result.get("validated") else 422,
                "headers": {"content-type": "application/json"},
                "body": json.dumps(validation_result, separators=(",", ":")),
            }
        return validation_result
    _resolve_recovery_table()
    """Materialize expected evidence; all persistence is immutable and conditional."""

    scheduled_at = event.get("time")
    if (
        not isinstance(scheduled_at, str)
        or _EVENTBRIDGE_TIMESTAMP.fullmatch(scheduled_at) is None
    ):
        raise RuntimeError("MATERIALIZER_EVENT_TIME_INVALID")
    _parse_timestamp(scheduled_at)
    import boto3

    registration = _registration()
    contracts_root = Path(_required("MATERIALIZER_CONTRACTS_ROOT"))
    schemas, schema_registry = build_schema_registry(contracts_root / "schemas")
    secret_policy = load_json_strict(contracts_root / "catalogs" / "secret-safety.json")
    compatibility_catalog = load_json_strict(
        contracts_root / "catalogs" / "compatibility.json"
    )
    s3 = boto3.client("s3")
    dynamodb = boto3.client("dynamodb")
    sqs = boto3.client("sqs")
    metrics = boto3.client("cloudwatch")
    try:
        _assert_namespace(dynamodb, registration)
        config = s3.get_object(
            Bucket=_required("MATERIALIZER_CONFIG_BUCKET"),
            Key=_required("MATERIALIZER_CONFIG_KEY"),
        )
        body = config["Body"].read()
        if len(body) > 300000:
            raise MaterializationError("MATERIALIZER_CONFIG_OVERSIZED")
        document = load_json_bytes_strict(body)
        result = materialize_config(
            document,
            registration,
            scheduled_at,
            schemas,
            schema_registry,
            secret_policy,
            compatibility_catalog,
        )
    except (MaterializationError, ContractViolation) as error:
        _record_rejection(dynamodb, registration, str(error), scheduled_at)
        _metric(metrics, registration, "rejected")
        return {"rejected": True}
    needs_delivery = _put_validated_snapshot(dynamodb, registration, result.snapshot)
    from datetime import datetime, UTC

    now = datetime.now(UTC)
    horizon_dt = datetime.fromisoformat(
        str(result.snapshot["horizon_at"]).replace("Z", "+00:00")
    )
    freshness = max(0.0, (horizon_dt - now).total_seconds() / 3600.0)

    if not needs_delivery:
        _metric(
            metrics,
            registration,
            "materialized",
            horizon_freshness_hours=freshness,
            conformance_result="PASS",
        )
        return {
            "materialized": 0,
            "horizon_at": result.snapshot["horizon_at"],
            "reused": True,
        }
    destination = _required("MATERIALIZER_SOURCE_QUEUE_URL")
    # Queue delivery happens before the immutable completion marker. A failed
    # invocation may duplicate messages, but deterministic producer IDs make
    # that safe for the later reducer and never strand a missing occurrence.
    for envelope in result.envelopes:
        sqs.send_message(
            QueueUrl=destination,
            MessageBody=canonical_json_bytes(envelope).decode("utf-8"),
        )
    _mark_materialized(dynamodb, registration, result.snapshot, _timestamp(now))
    _metric(
        metrics,
        registration,
        "materialized",
        horizon_freshness_hours=freshness,
        conformance_result="PASS",
    )
    return {
        "materialized": len(result.envelopes),
        "horizon_at": result.snapshot["horizon_at"],
    }
