"""AWS adapter for the independent occurrence materializer."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

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
    materialize_config,
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"MATERIALIZER_CONFIGURATION_MISSING:{name}")
    return value


def _registration() -> MaterializerRegistration:
    try:
        value = json.loads(_required("MATERIALIZER_REGISTRATION"))
        return MaterializerRegistration(**value)
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError("MATERIALIZER_REGISTRATION_INVALID") from error


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
                {"Name": "account_id", "Value": registration.account_id},
                {"Name": "environment", "Value": registration.environment},
                {"Name": "failure_plane", "Value": "materialization"},
                {"Name": "job_id", "Value": registration.job_id},
                {"Name": "region", "Value": registration.region},
                {"Name": "state", "Value": state},
            ],
        }
    ]
    if horizon_freshness_hours is not None:
        metric_data.append({
            "MetricName": "HorizonFreshnessHours",
            "Unit": "Count",
            "Value": horizon_freshness_hours,
            "Dimensions": [
                {"Name": "account_id", "Value": registration.account_id},
                {"Name": "environment", "Value": registration.environment},
                {"Name": "failure_plane", "Value": "materialization"},
                {"Name": "job_id", "Value": registration.job_id},
                {"Name": "region", "Value": registration.region},
            ],
        })
    if conformance_result is not None:
        metric_data.append({
            "MetricName": "SchedulerConformance",
            "Unit": "Count",
            "Value": 1.0,
            "Dimensions": [
                {"Name": "account_id", "Value": registration.account_id},
                {"Name": "environment", "Value": registration.environment},
                {"Name": "failure_plane", "Value": "materialization"},
                {"Name": "job_id", "Value": registration.job_id},
                {"Name": "region", "Value": registration.region},
                {"Name": "result", "Value": conformance_result},
            ],
        })
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
        "validation_state": {"S": "REJECTED"},
        "rejection_code": {"S": code.split(":", 1)[0]},
        "rejected_at": {"S": rejected_at},
    }


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
            "horizon_at = :horizon_at, conformance_result = :conformance_result"
        ),
        ConditionExpression=(
            "validation_state = :validated AND materialization_state IN (:pending, :materialized) "
            "AND config_hash = :config_hash"
        ),
        ExpressionAttributeValues={
            ":config_hash": {"S": registration.config_version},
            ":conformance_result": {"S": "PASS"},
            ":horizon_at": {"S": str(snapshot["horizon_at"])},
            ":materialized": {"S": "MATERIALIZED"},
            ":materialized_at": {"S": str(snapshot["validated_at"])},
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


def _assert_namespace(dynamodb: object, registration: MaterializerRegistration) -> None:
    response = dynamodb.get_item(  # type: ignore[attr-defined]
        TableName=_required("MATERIALIZER_NAMESPACE_REGISTRY_TABLE"),
        ConsistentRead=True,
        Key={"pk": {"S": f"JOB#{registration.job_id}"}, "sk": {"S": "RESERVATION"}},
    )
    item = response.get("Item", {})
    if (
        item.get("account_id", {}).get("S") != registration.account_id
        or item.get("region", {}).get("S") != registration.region
        or item.get("owner_generation", {}).get("N")
        != str(registration.owner_generation)
        or item.get("tombstoned", {}).get("BOOL") is not False
    ):
        raise MaterializationError("MATERIALIZER_NAMESPACE_UNAUTHORIZED")


def lambda_handler(event: Mapping[str, object], _context: object) -> dict[str, object]:
    """Materialize expected evidence; all persistence is immutable and conditional."""

    scheduled_at = event.get("time")
    if not isinstance(scheduled_at, str):
        raise RuntimeError("MATERIALIZER_EVENT_TIME_INVALID")
    import boto3  # type: ignore[import-untyped]

    registration = _registration()
    contracts_root = Path(_required("MATERIALIZER_CONTRACTS_ROOT"))
    schemas, schema_registry = build_schema_registry(contracts_root / "schemas")
    secret_policy = load_json_strict(contracts_root / "catalogs" / "secret-safety.json")
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
        )
    except (MaterializationError, ContractViolation) as error:
        _record_rejection(dynamodb, registration, str(error), scheduled_at)
        _metric(metrics, registration, "rejected")
        return {"rejected": True}
    needs_delivery = _put_validated_snapshot(dynamodb, registration, result.snapshot)
    from datetime import datetime, UTC
    now = datetime.now(UTC)
    horizon_dt = datetime.fromisoformat(str(result.snapshot["horizon_at"]).replace("Z", "+00:00"))
    freshness = max(0.0, (horizon_dt - now).total_seconds() / 3600.0)

    if not needs_delivery:
        _metric(metrics, registration, "materialized", horizon_freshness_hours=freshness, conformance_result="PASS")
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
    _mark_materialized(dynamodb, registration, result.snapshot)
    _metric(metrics, registration, "materialized", horizon_freshness_hours=freshness, conformance_result="PASS")
    return {
        "materialized": len(result.envelopes),
        "horizon_at": result.snapshot["horizon_at"],
    }
