"""IAM-authenticated Lambda Function URL adapter for CONFIG publication."""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from typing import Any, Mapping

from .domain import PublisherError, PublishRequest, publish

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _caller_identity(user_arn: str) -> tuple[str, str]:
    match = re.fullmatch(
        r"arn:[^:]+:sts::([0-9]{12}):assumed-role/([^/]+)/[^/]+", user_arn
    )
    if match:
        return match.group(1), match.group(2)
    match = re.fullmatch(r"arn:[^:]+:iam::([0-9]{12}):role/(.+)", user_arn)
    if match:
        return match.group(1), match.group(2)
    raise PublisherError("CALLER_IDENTITY_INVALID")


def _response(status: int, body: Mapping[str, object]) -> dict[str, object]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, separators=(",", ":")),
    }


def _emit_metric(
    client: Any, result_code: str, latency_ms: float | None = None
) -> None:
    try:
        metrics: list[dict[str, object]] = [
            {
                "MetricName": "PublishResult",
                "Dimensions": [{"Name": "ResultCode", "Value": result_code}],
                "Value": 1,
                "Unit": "Count",
            }
        ]
        if latency_ms is not None:
            metrics.append(
                {
                    "MetricName": "PublishLatency",
                    "Value": latency_ms,
                    "Unit": "Milliseconds",
                }
            )
        client.put_metric_data(
            Namespace=os.environ.get("METRIC_NAMESPACE", "Platform/EcsScheduledJobs"),
            MetricData=metrics,
        )
    except Exception:
        LOGGER.warning("publisher_metric_failed", extra={"result_code": result_code})


def lambda_handler(event: Mapping[str, object], _context: object) -> dict[str, object]:
    started = time.monotonic()
    request: PublishRequest | None = None
    cloudwatch: object | None = None
    try:
        import boto3  # type: ignore[import-untyped]

        cloudwatch = boto3.client("cloudwatch")

        auth = event.get("requestContext", {})
        iam = (
            auth.get("authorizer", {}).get("iam", {})
            if isinstance(auth, Mapping)
            else {}
        )
        user_arn = iam.get("userArn") if isinstance(iam, Mapping) else None
        if not isinstance(user_arn, str) and isinstance(auth, Mapping):
            identity = auth.get("identity", {})
            user_arn = (
                identity.get("userArn") if isinstance(identity, Mapping) else None
            )
        if not isinstance(user_arn, str):
            raise PublisherError("CALLER_IDENTITY_MISSING")
        body = event.get("body")
        request_value = json.loads(body) if isinstance(body, str) else body
        if not isinstance(request_value, Mapping):
            raise PublisherError("PUBLISH_REQUEST_INVALID")
        request = PublishRequest.from_mapping(request_value)
        account_id, role_name = _caller_identity(user_arn)
        iam_client = boto3.client("iam")
        tags = iam_client.list_role_tags(RoleName=role_name).get("Tags", [])
        tag_map = {
            item["Key"]: item["Value"]
            for item in tags
            if isinstance(item, Mapping) and "Key" in item and "Value" in item
        }
        if tag_map.get("PlatformEcsScheduledJobId") != request.job_id:
            raise PublisherError("JOB_ID_AUTHORIZATION_FAILED")
        reservation = (
            boto3.client("dynamodb")
            .get_item(
                TableName=os.environ["NAMESPACE_REGISTRY_TABLE_NAME"],
                Key={
                    "pk": {"S": f"JOB#{request.job_id}"},
                    "sk": {"S": "RESERVATION"},
                },
                ConsistentRead=True,
            )
            .get("Item", {})
        )
        try:
            reservation_generation = int(
                reservation.get("owner_generation", {}).get("N", "0")
            )
        except (TypeError, ValueError) as error:
            raise PublisherError("OWNERSHIP_AUTHORIZATION_FAILED") from error
        if (
            reservation.get("account_id", {}).get("S") != account_id
            or reservation.get("region", {}).get("S") != os.environ["AWS_REGION"]
            or reservation.get("lifecycle", {}).get("S") != "RESERVED"
            or reservation.get("tombstoned", {}).get("BOOL") is not False
            or reservation.get("transfer_state", {}).get("S") != "quiescent"
            or reservation_generation != request.ownership_generation
        ):
            raise PublisherError("OWNERSHIP_AUTHORIZATION_FAILED")
        result = publish(
            request,
            store=boto3.client("s3"),
            bucket=os.environ["CONFIG_BUCKET_NAME"],
            kms_key_arn=os.environ["CONFIG_KMS_KEY_ARN"],
            authenticated_job_id=request.job_id,
        )
        _emit_metric(
            cloudwatch, str(result["result"]), (time.monotonic() - started) * 1000
        )
        LOGGER.info(
            "config_publish_complete",
            extra={
                "job_id": request.job_id,
                "config_version": request.config_version,
                "result_code": result["result"],
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )
        return _response(200, result)
    except PublisherError as error:
        if cloudwatch is not None:
            _emit_metric(cloudwatch, error.code, (time.monotonic() - started) * 1000)
        metadata: dict[str, object] = {
            "protocol_version": "config-publisher/1.0.0",
            "error_code": error.code,
        }
        if request is not None:
            metadata.update(
                {
                    "job_id": request.job_id,
                    "config_version": request.config_version,
                    "object_key": request.object_key,
                    "contract_version": request.contract_version,
                    "ownership_generation": request.ownership_generation,
                    "operation_id": f"cfgpub-{uuid.uuid4().hex}",
                }
            )
        return _response(
            409 if error.code == "CONFIG_VERSION_CONFLICT" else 400,
            metadata,
        )
    except Exception:
        if cloudwatch is not None:
            _emit_metric(
                cloudwatch,
                "PUBLISHER_INTERNAL_ERROR",
                (time.monotonic() - started) * 1000,
            )
        LOGGER.exception("publisher_internal_error")
        return _response(
            500,
            {
                "error_code": "PUBLISHER_INTERNAL_ERROR",
                "protocol_version": "config-publisher/1.0.0",
            },
        )
