"""AWS adapter for the authenticated operator-command authorization boundary."""

from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime
from typing import Mapping

from .domain import (
    CallerContext,
    CommandRejected,
    OccurrenceBinding,
    authorize_operator_request,
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"COMMAND_HANDLER_CONFIGURATION_MISSING:{name}")
    return value


def _canonical(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _authenticated_caller(
    event: Mapping[str, object], secret: str, now: datetime
) -> CallerContext:
    value = event.get("authenticated_caller")
    signature = event.get("caller_signature")
    if not isinstance(value, Mapping) or not isinstance(signature, str):
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    issued_at = value.get("issued_at")
    if not isinstance(issued_at, str):
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    try:
        issued = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise CommandRejected("COMMAND_CALLER_AUTHORITY") from error
    if abs((now.astimezone(UTC) - issued.astimezone(UTC)).total_seconds()) > 300:
        raise CommandRejected("COMMAND_CALLER_EXPIRED")
    expected = hmac.new(secret.encode(), _canonical(value), hashlib.sha256).digest()
    try:
        supplied = base64.b64decode(signature, validate=True)
    except ValueError as error:
        raise CommandRejected("COMMAND_CALLER_AUTHORITY") from error
    if not hmac.compare_digest(expected, supplied):
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    required = ("actor", "session_id", "cell_id", "account_id", "region")
    if any(
        not isinstance(value.get(name), str) or not value[name] for name in required
    ):
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    return CallerContext(
        actor=value["actor"],
        session_id=value["session_id"],
        cell_id=value["cell_id"],
        account_id=value["account_id"],
        region=value["region"],
        environment=value.get("environment")
        if isinstance(value.get("environment"), str)
        else None,
        break_glass=value.get("break_glass") is True,
    )


def lambda_handler(event: Mapping[str, object], _context: object) -> dict[str, object]:
    """Authorize one request and enqueue only the handler-created canonical payload.

    ``authenticated_caller`` is supplied by the private invocation broker. It is
    deliberately not inferred from caller-provided command fields or workload
    identity, and direct invocations without it fail closed.
    """
    request = event.get("request")
    if not isinstance(request, Mapping):
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    if not isinstance(event.get("authenticated_caller"), Mapping) or not isinstance(
        event.get("caller_signature"), str
    ):
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    now = datetime.now(UTC)

    # The AWS adapter owns all state reads/writes. The request never supplies
    # occurrence IDs, producer identities, ARNs, or evidence.
    import boto3  # type: ignore[import-untyped]

    table = _required("COMMAND_OCCURRENCE_TABLE_NAME")
    authorization_table = _required("COMMAND_AUTHORIZATION_TABLE_NAME")
    queue_url = _required("COMMAND_QUEUE_URL")
    expected_cell = _required("COMMAND_CELL_ID")
    expected_account = _required("COMMAND_ACCOUNT_ID")
    expected_region = _required("COMMAND_REGION")
    dynamodb = boto3.client("dynamodb")
    sqs = boto3.client("sqs")
    cloudwatch = boto3.client("cloudwatch")
    secrets = boto3.client("secretsmanager")
    secret_value = secrets.get_secret_value(
        SecretId=_required("COMMAND_BROKER_SECRET_ARN")
    )
    broker_secret = secret_value.get("SecretString")
    if not isinstance(broker_secret, str) or not broker_secret:
        raise CommandRejected("COMMAND_CALLER_AUTHORITY")
    caller = _authenticated_caller(event, broker_secret, now)

    def lookup(job_id: str, scheduled_time: str) -> OccurrenceBinding | None:
        response = dynamodb.query(
            TableName=table,
            IndexName="job-scheduled-time",
            KeyConditionExpression="job_id = :job AND scheduled_time = :time",
            ExpressionAttributeValues={
                ":job": {"S": job_id},
                ":time": {"S": scheduled_time},
            },
            Limit=2,
            ConsistentRead=False,
        )
        items = response.get("Items", [])
        if (
            not isinstance(items, list)
            or len(items) != 1
            or not isinstance(items[0], Mapping)
        ):
            return None
        item = items[0]
        try:
            return OccurrenceBinding(
                job_id=item["job_id"]["S"],
                scheduled_time=item["scheduled_time"]["S"],
                original_occurrence_id=item["occurrence_id"]["S"],
                config_version=item["config_version"]["S"],
                deployment_identity_id=item["deployment_identity_id"]["S"],
                terminal=item["terminal"]["BOOL"],
                cell_id=item["cell_id"]["S"],
                account_id=item["account_id"]["S"],
                region=item["region"]["S"],
                schedule_generation=item["schedule_generation"]["S"],
            )
        except KeyError, TypeError:
            return None

    def approve(
        reference: str, actor: str, session_id: str, scope_digest: str = ""
    ) -> bool | str:
        response = dynamodb.get_item(
            TableName=table,
            Key={"pk": {"S": f"APPROVAL#{reference}"}, "sk": {"S": "CURRENT"}},
            ConsistentRead=True,
        )
        item = response.get("Item")
        now_value = (
            item.get("expires_at", {}).get("S") if isinstance(item, Mapping) else None
        )
        try:
            expires = (
                datetime.fromisoformat(now_value.replace("Z", "+00:00"))
                if isinstance(now_value, str)
                else None
            )
        except TypeError, ValueError:
            return False
        valid = (
            isinstance(item, Mapping)
            and item.get("actor", {}).get("S") == actor
            and item.get("session_id", {}).get("S") == session_id
            and item.get("approved", {}).get("BOOL") is True
            and item.get("approver_actor", {}).get("S") != actor
            and item.get("cell_id", {}).get("S") == caller.cell_id
            and item.get("job_id", {}).get("S") == request.get("job_id")
            and (
                not scope_digest
                or item.get("scope_digest", {}).get("S") == scope_digest
            )
            and expires is not None
            and expires.astimezone(UTC) > now
        )
        return (
            expires.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if valid and expires
            else False
        )

    result = authorize_operator_request(
        request,
        caller,
        lookup=lookup,
        approve=approve,
        now=now,
        expected_cell_id=expected_cell,
        expected_account_id=expected_account,
        expected_region=expected_region,
        expected_environment=os.environ.get("COMMAND_ENVIRONMENT"),
    )
    if caller.break_glass:
        cloudwatch.put_metric_data(
            Namespace=_required("COMMAND_METRIC_NAMESPACE"),
            MetricData=[
                {
                    "MetricName": "BreakGlassCommandAccepted",
                    "Unit": "Count",
                    "Value": 1.0,
                }
            ],
        )
    record = {
        "pk": {"S": f"REQUEST#{request['request_id']}"},
        "sk": {"S": "CURRENT"},
        "authorization_record_id": {"S": result.authorization_record_id},
        "command": {"S": json.dumps(result.command, separators=(",", ":"))},
        "audit": {"S": json.dumps(result.audit, separators=(",", ":"))},
        "status": {"S": "PENDING"},
        "request_digest": {"S": hashlib.sha256(_canonical(request)).hexdigest()},
    }
    try:
        dynamodb.put_item(
            TableName=authorization_table,
            Item=record,
            ConditionExpression="attribute_not_exists(pk)",
        )
    except dynamodb.exceptions.ConditionalCheckFailedException:
        existing = dynamodb.get_item(
            TableName=authorization_table,
            Key={
                "pk": {"S": f"REQUEST#{request['request_id']}"},
                "sk": {"S": "CURRENT"},
            },
            ConsistentRead=True,
        ).get("Item")
        if isinstance(existing, Mapping) and isinstance(
            existing.get("authorization_record_id"), Mapping
        ):
            if (
                existing.get("request_digest", {}).get("S")
                != record["request_digest"]["S"]
            ):
                raise CommandRejected("COMMAND_IDEMPOTENCY_CONFLICT")
            return {
                "command_id": json.loads(existing["command"]["S"])["command_id"],
                "authorization_record_id": existing["authorization_record_id"]["S"],
                "duplicate": True,
            }
        raise CommandRejected("COMMAND_IDEMPOTENCY_CONFLICT")
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(
            {
                "command": result.command,
                "authorization_record_id": result.authorization_record_id,
            },
            separators=(",", ":"),
        ),
    )
    dynamodb.update_item(
        TableName=authorization_table,
        Key={"pk": {"S": f"REQUEST#{request['request_id']}"}, "sk": {"S": "CURRENT"}},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": {"S": "ENQUEUED"}},
    )
    return {
        "command_id": result.command["command_id"],
        "authorization_record_id": result.authorization_record_id,
    }
