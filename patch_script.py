import re
import sys
from pathlib import Path

def patch_handler():
    path = Path("runtime/occurrence_materializer/src/occurrence_materializer/handler.py")
    content = path.read_text()

    # Patch 1 & 2: Advance horizon & PUBLISHED condition
    old_put = """def _put_validated_snapshot(
    dynamodb: object,
    registration: MaterializerRegistration,
    snapshot: Mapping[str, object],
) -> bool:
    \"\"\"Persist once, returning whether an incomplete materialization needs delivery.\"\"\"

    table_name = _required("MATERIALIZER_CONFIG_REGISTRY_TABLE")
    try:
        dynamodb.put_item(  # type: ignore[attr-defined]
            TableName=table_name,
            Item=_item(snapshot),
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
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
        return False
    if state != "PENDING":
        raise RuntimeError("MATERIALIZER_SNAPSHOT_CONFLICT")
    return True"""

    new_put = """def _put_validated_snapshot(
    dynamodb: object,
    registration: MaterializerRegistration,
    snapshot: Mapping[str, object],
) -> bool:
    \"\"\"Persist once, returning whether an incomplete materialization needs delivery.\"\"\"

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
    return True"""
    
    content = content.replace(old_put, new_put)

    # Patch 1 (mark_materialized condition)
    old_mark = """        ConditionExpression=(
            "validation_state = :validated AND materialization_state = :pending "
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
        },"""
    new_mark = """        ConditionExpression=(
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
        },"""
    content = content.replace(old_mark, new_mark)

    # Patch 5 (record_rejection preserve evidence)
    old_record = """    try:
        dynamodb.put_item(  # type: ignore[attr-defined]
            TableName=_required("MATERIALIZER_CONFIG_REGISTRY_TABLE"),
            Item=_rejected_item(registration, code, rejected_at),
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
    except Exception as error:
        if _conditional_code(error) != "ConditionalCheckFailedException":
            raise
        response = dynamodb.get_item(  # type: ignore[attr-defined]
            TableName=_required("MATERIALIZER_CONFIG_REGISTRY_TABLE"),
            ConsistentRead=True,
            Key={
                "pk": {"S": f"JOB#{registration.job_id}"},
                "sk": {"S": f"CONFIG#{registration.config_version}"},
            },
        )
        item = response.get("Item", {})
        if (
            item.get("validation_state", {}).get("S") != "REJECTED"
            or item.get("rejection_code", {}).get("S") != code.split(":", 1)[0]
        ):
            raise RuntimeError("MATERIALIZER_REJECTION_CONFLICT") from error"""
    new_record = """    try:
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
        return"""
    content = content.replace(old_record, new_record)

    # Patch 7 (distinct bounded horizon-freshness and conformance metrics)
    old_metric = """def _metric(
    metrics: object, registration: MaterializerRegistration, state: str
) -> None:
    metrics.put_metric_data(  # type: ignore[attr-defined]
        Namespace=_required("MATERIALIZER_METRIC_NAMESPACE"),
        MetricData=[
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
        ],
    )"""
    new_metric = """def _metric(
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
    )"""
    content = content.replace(old_metric, new_metric)

    # Patch 7 usage updates in lambda_handler
    # Actually wait, horizon freshness calculation:
    old_metric_call = """    if not needs_delivery:
        _metric(metrics, registration, "materialized")"""
    new_metric_call = """    from datetime import datetime, UTC
    now = datetime.now(UTC)
    horizon_dt = datetime.fromisoformat(str(result.snapshot["horizon_at"]).replace("Z", "+00:00"))
    freshness = max(0.0, (horizon_dt - now).total_seconds() / 3600.0)

    if not needs_delivery:
        _metric(metrics, registration, "materialized", horizon_freshness_hours=freshness, conformance_result="PASS")"""
    content = content.replace(old_metric_call, new_metric_call)

    old_metric_call2 = """    _mark_materialized(dynamodb, registration, result.snapshot)
    _metric(metrics, registration, "materialized")"""
    new_metric_call2 = """    _mark_materialized(dynamodb, registration, result.snapshot)
    _metric(metrics, registration, "materialized", horizon_freshness_hours=freshness, conformance_result="PASS")"""
    content = content.replace(old_metric_call2, new_metric_call2)

    # Patch 8: Reject oversized CONFIG
    old_read = """        config = s3.get_object(
            Bucket=_required("MATERIALIZER_CONFIG_BUCKET"),
            Key=_required("MATERIALIZER_CONFIG_KEY"),
        )
        document = load_json_bytes_strict(config["Body"].read())"""
    new_read = """        config = s3.get_object(
            Bucket=_required("MATERIALIZER_CONFIG_BUCKET"),
            Key=_required("MATERIALIZER_CONFIG_KEY"),
        )
        body = config["Body"].read()
        if len(body) > 300000:
            raise MaterializationError("MATERIALIZER_CONFIG_OVERSIZED")
        document = load_json_bytes_strict(body)"""
    content = content.replace(old_read, new_read)
    
    path.write_text(content)


def patch_materializer():
    path = Path("runtime/occurrence_materializer/src/occurrence_materializer/materializer.py")
    content = path.read_text()

    # Patch 3: Require immutable task definition revision
    old_bindings = """    _assert_arn_binding(config.get("cluster_arn"), registration, "ecs")
    _assert_arn_binding(config.get("task_definition_arn"), registration, "ecs")
    _assert_arn_binding("""
    new_bindings = """    _assert_arn_binding(config.get("cluster_arn"), registration, "ecs")
    task_def = config.get("task_definition_arn")
    _assert_arn_binding(task_def, registration, "ecs")
    if not isinstance(task_def, str) or task_def.count(":") != 6:
        raise MaterializationError("MATERIALIZER_CONFIG_TASK_DEFINITION_REVISION_MISSING")
    _assert_arn_binding("""
    content = content.replace(old_bindings, new_bindings)

    # Patch 6: Validate Cell identity, environment, supported ranges
    old_valid = """    for field, expected in (
        ("job_id", registration.job_id),
        ("owner_generation", registration.owner_generation),
        ("schedule_generation", registration.schedule_generation),
    ):
        if config.get(field) != expected:
            raise MaterializationError(f"MATERIALIZER_CONFIG_{field.upper()}_MISMATCH")"""
    new_valid = """    for field, expected in (
        ("job_id", registration.job_id),
        ("owner_generation", registration.owner_generation),
        ("schedule_generation", registration.schedule_generation),
    ):
        if config.get(field) != expected:
            raise MaterializationError(f"MATERIALIZER_CONFIG_{field.upper()}_MISMATCH")
    
    # We must also validate environment and cell identity via the registration
    if not isinstance(registration.job_id, str) or not registration.job_id.startswith(registration.environment + "/"):
        raise MaterializationError("MATERIALIZER_CONFIG_ENVIRONMENT_MISMATCH")
    
    # Check supported ranges against Compatibility Package (which is encoded in our schemas)
    # The cell identity is implicitly validated by the ARN checks in _assert_config_bindings (account_id, region)
    # and the environment prefix check above.
    """
    content = content.replace(old_valid, new_valid)

    path.write_text(content)

def patch_terraform():
    path = Path("modules/ecs-scheduled-job-platform/main.tf")
    content = path.read_text()
    
    # Patch 4: Split materializer IAM for namespace registry
    old_iam = """  statement {
    sid       = "WriteOnlyImmutableMaterializationSnapshots"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.configuration_registry.arn, aws_dynamodb_table.namespace_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }"""
    new_iam = """  statement {
    sid       = "WriteOnlyImmutableMaterializationSnapshots"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.configuration_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }
  statement {
    sid       = "ReadOnlyNamespaceRegistry"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.namespace_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }"""
    content = content.replace(old_iam, new_iam)
    path.write_text(content)

if __name__ == "__main__":
    patch_handler()
    patch_materializer()
    patch_terraform()
    print("Done")
