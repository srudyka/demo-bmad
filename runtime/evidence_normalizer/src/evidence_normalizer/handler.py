"""AWS adapter for the deterministic Scheduler evidence normalizer."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Mapping, Protocol

from tests.contract.support.contracts import (
    build_schema_registry,
    canonical_json_bytes,
    load_json_strict,
)

from .normalizer import (
    MaterializerRegistration,
    SchedulerRegistration,
    TransientTransportError,
    process_scheduler_batch,
    process_materializer_batch,
)


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class QueueClient(Protocol):
    """Small SQS boundary retained outside deterministic normalization."""

    def send_message(self, *, QueueUrl: str, MessageBody: str) -> object: ...


class MetricsClient(Protocol):
    """Small CloudWatch boundary with only bounded metric dimensions."""

    def put_metric_data(
        self, *, Namespace: str, MetricData: list[dict[str, object]]
    ) -> object: ...


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"NORMALIZER_CONFIGURATION_MISSING:{name}")
    return value


def _registration() -> SchedulerRegistration:
    try:
        parsed = json.loads(_required_environment("NORMALIZER_REGISTRATION"))
        if not isinstance(parsed, dict):
            raise RuntimeError("NORMALIZER_REGISTRATION_INVALID")
        return SchedulerRegistration(**parsed)
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError("NORMALIZER_REGISTRATION_INVALID") from error


def _materializer_registration() -> MaterializerRegistration:
    try:
        parsed = json.loads(
            _required_environment("NORMALIZER_MATERIALIZER_REGISTRATION")
        )
        return MaterializerRegistration(**parsed)
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError("NORMALIZER_MATERIALIZER_REGISTRATION_INVALID") from error


def _clients() -> tuple[QueueClient, MetricsClient]:
    # boto3 stays inside this adapter so unit tests and parsing need no AWS SDK.
    import boto3  # type: ignore[import-untyped]

    return boto3.client("sqs"), boto3.client("cloudwatch")


def _safe_log(code: str, record: Mapping[str, object]) -> None:
    LOGGER.info(
        "normalizer_record code=%s message_id=%s", code, record.get("messageId", "")
    )


def _canonical_message(value: dict[str, object]) -> str:
    """Encode queue payloads using the same RFC 8785 bytes as the contract."""

    return canonical_json_bytes(value).decode("utf-8")


def lambda_handler(
    event: Mapping[str, object], _context: object
) -> dict[str, list[dict[str, str]]]:
    """Normalize SQS records and retry only failed transport deliveries."""

    records = event.get("Records")
    if not isinstance(records, list) or not all(
        isinstance(item, Mapping) for item in records
    ):
        raise RuntimeError("NORMALIZER_EVENT_INVALID")

    contracts_root = Path(_required_environment("NORMALIZER_CONTRACTS_ROOT"))
    schemas, registry = build_schema_registry(contracts_root / "schemas")
    secret_policy = load_json_strict(contracts_root / "catalogs" / "secret-safety.json")
    registration = _registration()
    materializer_registration = _materializer_registration()
    ingress_url = _required_environment("NORMALIZER_INGRESS_QUEUE_URL")
    process_manager_url = _required_environment("NORMALIZER_PROCESS_MANAGER_QUEUE_URL")
    quarantine_url = _required_environment("NORMALIZER_QUARANTINE_QUEUE_URL")
    namespace = _required_environment("NORMALIZER_METRIC_NAMESPACE")
    queues, metrics = _clients()

    # Keep botocore within the AWS adapter; deterministic unit tests need no SDK.
    from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]

    def send_envelope(envelope: dict[str, object]) -> None:
        try:
            queues.send_message(
                QueueUrl=ingress_url,
                MessageBody=_canonical_message(envelope),
            )
        except (BotoCoreError, ClientError, OSError) as error:
            raise TransientTransportError from error

    def send_quarantine(rejection: dict[str, object]) -> None:
        try:
            queues.send_message(
                QueueUrl=quarantine_url,
                MessageBody=_canonical_message(rejection),
            )
            metrics.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        "MetricName": "EvidenceNormalizerRejected",
                        "Unit": "Count",
                        "Value": 1.0,
                        "Dimensions": [
                            {"Name": "environment", "Value": registration.environment},
                            {"Name": "job_id", "Value": registration.job_id},
                            {"Name": "state", "Value": "rejected"},
                        ],
                    }
                ],
            )
        except (BotoCoreError, ClientError, OSError) as error:
            raise TransientTransportError from error

    def send_process_manager_envelope(envelope: dict[str, object]) -> None:
        try:
            queues.send_message(
                QueueUrl=process_manager_url,
                MessageBody=_canonical_message(envelope),
            )
        except (BotoCoreError, ClientError, OSError) as error:
            raise TransientTransportError from error

    source_arns = {item.get("eventSourceARN") for item in records}
    if source_arns == {materializer_registration.source_queue_arn}:
        response = process_materializer_batch(
            list(records),
            materializer_registration,
            schemas,
            registry,
            secret_policy,
            send_envelope=send_envelope,
            send_process_manager_envelope=send_process_manager_envelope,
            send_quarantine=send_quarantine,
            on_permanent_rejection=_safe_log,
        )
    elif source_arns == {registration.source_queue_arn}:
        response = process_scheduler_batch(
            list(records),
            registration,
            schemas,
            registry,
            secret_policy,
            send_envelope=send_envelope,
            send_quarantine=send_quarantine,
            on_permanent_rejection=_safe_log,
        )
    else:
        raise RuntimeError("NORMALIZER_SOURCE_QUEUE_MIXED_OR_UNKNOWN")
    for failure in response["batchItemFailures"]:
        _safe_log("NORMALIZER_TRANSPORT_RETRY", failure)
    return response
