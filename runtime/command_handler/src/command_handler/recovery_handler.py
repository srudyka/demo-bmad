"""AWS adapter for the approved, Cell-scoped recovery state machine."""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Iterator, Mapping, cast

from .recovery import (
    RecoveryManifest,
    RecoveryOperations,
    RecoveryPhase,
    execute_recovery,
    recovery_command_fields,
    validate_restore_point,
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"RECOVERY_CONFIGURATION_MISSING:{name}")
    return value


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _elapsed_seconds(start: str, end: str) -> int:
    return max(
        0,
        int(
            (
                datetime.fromisoformat(end.replace("Z", "+00:00"))
                - datetime.fromisoformat(start.replace("Z", "+00:00"))
            ).total_seconds()
        ),
    )


def _json_env(name: str, default: object) -> object:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"RECOVERY_CONFIGURATION_INVALID:{name}") from error


def _json_list_env(name: str) -> list[object]:
    value = _json_env(name, [])
    if not isinstance(value, list):
        raise RuntimeError(f"RECOVERY_CONFIGURATION_INVALID:{name}")
    return value


def _schedule_update(current: Mapping[str, Any], *, state: str) -> dict[str, Any]:
    allowed = (
        "Name",
        "GroupName",
        "ScheduleExpression",
        "StartDate",
        "EndDate",
        "State",
        "Description",
        "FlexibleTimeWindow",
        "Target",
        "KmsKeyArn",
    )
    update = {key: current[key] for key in allowed if key in current}
    update["State"] = state
    if (
        "Name" not in update
        or "ScheduleExpression" not in update
        or "Target" not in update
    ):
        raise RuntimeError("RECOVERY_SCHEDULE_CONFIGURATION_INCOMPLETE")
    return update


def _manifest_item(manifest: RecoveryManifest) -> dict[str, dict[str, object]]:
    values: dict[str, object] = {
        "pk": f"RECOVERY#{manifest.recovery_id}",
        "sk": "CURRENT",
        "record_type": "CELL_RECOVERY",
        "recovery_id": manifest.recovery_id,
        "recovery_generation": manifest.recovery_generation,
        "cell_id": manifest.cell_id,
        "account_id": manifest.account_id,
        "region": manifest.region,
        "actor": manifest.actor,
        "session_id": manifest.session_id,
        "approval_reference": manifest.approval_reference,
        "reason": manifest.reason[:1024],
        "restore_point": manifest.restore_point,
        "expected_rpo_seconds": manifest.expected_rpo_seconds,
        "expected_rto_seconds": manifest.expected_rto_seconds,
        "source_deployment_identity": manifest.source_deployment_identity,
        "phase": manifest.phase.value,
        "phase_started_at": manifest.phase_started_at,
        "source_tables": list(manifest.source_tables),
        "target_tables": list(manifest.target_tables),
    }
    if manifest.failure_code:
        values["failure_code"] = manifest.failure_code
    if manifest.validation_digest:
        values["validation_digest"] = manifest.validation_digest
    if manifest.actual_rpo_seconds is not None:
        values["actual_rpo_seconds"] = manifest.actual_rpo_seconds
    if manifest.actual_rto_seconds is not None:
        values["actual_rto_seconds"] = manifest.actual_rto_seconds

    def attribute(value: object) -> dict[str, object]:
        if isinstance(value, bool):
            return {"BOOL": value}
        if isinstance(value, int):
            return {"N": str(value)}
        if isinstance(value, list):
            return {"L": [attribute(child) for child in value]}
        return {"S": str(value)}

    return {key: attribute(value) for key, value in values.items()}


class AwsRecoveryOperations(RecoveryOperations):
    """Narrow AWS adapter; the recovery role owns only these operations."""

    def __init__(self, clients: Mapping[str, Any]) -> None:
        self.dynamodb = clients["dynamodb"]
        self.scheduler = clients["scheduler"]
        self.lambda_client = clients["lambda"]
        self.ssm = clients["ssm"]

    @contextmanager
    def _pointer_lock(self, recovery_id: str) -> Iterator[None]:
        table = _required("RECOVERY_MANIFEST_TABLE_NAME")
        key = {"pk": {"S": "RECOVERY#POINTER"}, "sk": {"S": "LOCK"}}
        try:
            self.dynamodb.put_item(
                TableName=table,
                Item={
                    **key,
                    "record_type": {"S": "RECOVERY_POINTER_LOCK"},
                    "recovery_id": {"S": recovery_id},
                    "expires_at": {"N": str(int(time.time()) + 300)},
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
        except Exception as error:  # noqa: BLE001 - lock acquisition is fail-closed
            raise RuntimeError("RECOVERY_POINTER_LOCK_UNAVAILABLE") from error
        try:
            yield
        finally:
            self.dynamodb.delete_item(TableName=table, Key=key)

    def contain(self, manifest: RecoveryManifest) -> None:
        for schedule in _json_list_env("RECOVERY_SCHEDULES"):
            if not isinstance(schedule, Mapping):
                raise RuntimeError("RECOVERY_SCHEDULE_CONFIG_INVALID")
            current = self.scheduler.get_schedule(
                Name=str(schedule["name"]),
                GroupName=str(schedule.get("group_name", "default")),
            )
            self.scheduler.update_schedule(
                **_schedule_update(current, state="DISABLED")
            )
        for mapping_uuid in _json_list_env("RECOVERY_EVENT_SOURCE_MAPPINGS"):
            self.lambda_client.update_event_source_mapping(
                UUID=str(mapping_uuid), Enabled=False
            )

    def restore(self, manifest: RecoveryManifest) -> tuple[str, ...]:
        targets: list[str] = []
        for source in manifest.source_tables:
            target = f"{source}-recovery-{manifest.recovery_generation[:16]}"
            self.dynamodb.restore_table_to_point_in_time(
                SourceTableName=source,
                TargetTableName=target,
                RestoreDateTime=datetime.fromisoformat(
                    manifest.restore_point.replace("Z", "+00:00")
                ),
                SSESpecificationOverride={
                    "SSEEnabled": True,
                    "KMSMasterKeyId": _required("RECOVERY_KMS_KEY_ARN"),
                },
            )
            targets.append(target)
        for target in targets:
            deadline = time.monotonic() + float(
                os.environ.get("RECOVERY_RESTORE_TIMEOUT_SECONDS", "900")
            )
            while True:
                description = self.dynamodb.describe_table(TableName=target)["Table"]
                if description.get("TableStatus") == "ACTIVE":
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("RECOVERY_RESTORE_NOT_ACTIVE")
                time.sleep(float(os.environ.get("RECOVERY_RESTORE_POLL_SECONDS", "5")))
            tags = [
                {"Key": "Environment", "Value": _required("RECOVERY_ENVIRONMENT")},
                {"Key": "Application", "Value": "ecs-scheduled-jobs"},
                {"Key": "Service", "Value": "cell-recovery"},
                {"Key": "Owner", "Value": _required("RECOVERY_OWNER")},
                {"Key": "ManagedBy", "Value": "RecoveryController"},
                {"Key": "RecoveryGeneration", "Value": manifest.recovery_generation},
            ]
            for key in ("RECOVERY_REPOSITORY", "RECOVERY_COST_CENTER"):
                if value := os.environ.get(key):
                    tags.append(
                        {"Key": key.removeprefix("RECOVERY_").title(), "Value": value}
                    )
            self.dynamodb.tag_resource(
                ResourceArn=description["TableArn"],
                Tags=tags,
            )
            self.dynamodb.update_continuous_backups(
                TableName=target,
                PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
            )
            self.dynamodb.update_table(TableName=target, DeletionProtectionEnabled=True)
        return tuple(targets)

    def validate(
        self, manifest: RecoveryManifest, target_tables: tuple[str, ...]
    ) -> str:
        snapshots: list[dict[str, object]] = []
        for source, target in zip(manifest.source_tables, target_tables, strict=True):
            source_table = self.dynamodb.describe_table(TableName=source)["Table"]
            target_table = self.dynamodb.describe_table(TableName=target)["Table"]
            source_policy = self.dynamodb.get_resource_policy(
                ResourceArn=source_table["TableArn"]
            ).get("Policy")
            for field in (
                "KeySchema",
                "AttributeDefinitions",
                "GlobalSecondaryIndexes",
                "LocalSecondaryIndexes",
                "StreamSpecification",
                "TimeToLiveDescription",
            ):
                if source_table.get(field) != target_table.get(field):
                    raise RuntimeError(f"RECOVERY_SCHEMA_MISMATCH_{field.upper()}")
            if target_table.get("TableStatus") != "ACTIVE":
                raise RuntimeError("RECOVERY_TARGET_NOT_ACTIVE")
            if target_table.get("DeletionProtectionEnabled") is not True:
                raise RuntimeError("RECOVERY_DELETION_PROTECTION_MISSING")
            if target_table.get("SSEDescription", {}).get(
                "KMSMasterKeyArn"
            ) != _required("RECOVERY_KMS_KEY_ARN"):
                raise RuntimeError("RECOVERY_ENCRYPTION_KEY_MISMATCH")
            backups = self.dynamodb.describe_continuous_backups(TableName=target)[
                "ContinuousBackupsDescription"
            ]
            if (
                not backups.get("PointInTimeRecoveryDescription", {}).get(
                    "PointInTimeRecoveryStatus"
                )
                == "ENABLED"
            ):
                raise RuntimeError("RECOVERY_PITR_NOT_ENABLED")
            target_tags = self.dynamodb.list_tags_of_resource(
                ResourceArn=target_table["TableArn"]
            ).get("Tags", [])
            tag_map = {tag.get("Key"): tag.get("Value") for tag in target_tags}
            for key in (
                "Environment",
                "Application",
                "Service",
                "Owner",
                "ManagedBy",
                "RecoveryGeneration",
            ):
                if not tag_map.get(key):
                    raise RuntimeError(f"RECOVERY_TAG_MISSING_{key.upper()}")
            policy = self.dynamodb.get_resource_policy(
                ResourceArn=target_table["TableArn"]
            ).get("Policy")
            if not policy or policy != source_policy:
                raise RuntimeError("RECOVERY_RESOURCE_POLICY_MISSING")
            if os.environ.get("RECOVERY_COMPATIBILITY_PACKAGE_SHA256") is None:
                raise RuntimeError("RECOVERY_COMPATIBILITY_PACKAGE_MISSING")
            snapshots.append(
                {"source": source, "target": target, "schema": target_table}
            )
        return hashlib.sha256(
            json.dumps(
                snapshots, sort_keys=True, separators=(",", ":"), default=str
            ).encode()
        ).hexdigest()

    def cutover(
        self, manifest: RecoveryManifest, target_tables: tuple[str, ...]
    ) -> None:
        with self._pointer_lock(manifest.recovery_id):
            current = self.ssm.get_parameter(
                Name=_required("RECOVERY_POINTER_PARAMETER_NAME")
            )
            try:
                prior = json.loads(current["Parameter"]["Value"])
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise RuntimeError("RECOVERY_PRIOR_POINTER_INVALID") from error
            if not isinstance(prior, Mapping) or not prior.get("recovery_generation"):
                raise RuntimeError("RECOVERY_PRIOR_POINTER_INVALID")
            expected_prior = os.environ.get("RECOVERY_EXPECTED_POINTER_GENERATION")
            if expected_prior and prior.get("recovery_generation") != expected_prior:
                raise RuntimeError("RECOVERY_POINTER_GENERATION_MISMATCH")
            self.prior_pointer = dict(prior)
            pointer = {
                "recovery_generation": manifest.recovery_generation,
                "deployment_identity": manifest.source_deployment_identity,
                "tables": list(target_tables),
                "prior": self.prior_pointer,
            }
            self.ssm.put_parameter(
                Name=_required("RECOVERY_POINTER_PARAMETER_NAME"),
                Type="SecureString",
                Value=json.dumps(pointer, sort_keys=True, separators=(",", ":")),
                Overwrite=True,
            )

    def replay(self, manifest: RecoveryManifest) -> None:
        payload = json.dumps(
            {
                "mode": "replay",
                "recovery_id": manifest.recovery_id,
                "recovery_generation": manifest.recovery_generation,
                "restore_point": manifest.restore_point,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        for function_arn in _json_list_env("RECOVERY_REPLAY_FUNCTIONS"):
            self.lambda_client.invoke(
                FunctionName=str(function_arn),
                InvocationType="Event",
                Payload=payload,
            )
        for mapping_uuid in _json_list_env("RECOVERY_REPLAY_MAPPINGS"):
            self.lambda_client.update_event_source_mapping(
                UUID=str(mapping_uuid), Enabled=True
            )

    def reconcile(self, manifest: RecoveryManifest) -> None:
        payload = json.dumps(
            {
                "mode": "reconciliation",
                "recovery_id": manifest.recovery_id,
                "recovery_generation": manifest.recovery_generation,
                "deployment_identity": manifest.source_deployment_identity,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        for function_arn in _json_list_env("RECOVERY_RECONCILIATION_FUNCTIONS"):
            self.lambda_client.invoke(
                FunctionName=str(function_arn),
                InvocationType="Event",
                Payload=payload,
            )

    def verify(self, manifest: RecoveryManifest) -> None:
        pointer = self.ssm.get_parameter(
            Name=_required("RECOVERY_POINTER_PARAMETER_NAME")
        )
        try:
            value = json.loads(pointer["Parameter"]["Value"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("RECOVERY_VERIFICATION_INVALID") from error
        if (
            not isinstance(value, Mapping)
            or value.get("recovery_generation") != manifest.recovery_generation
            or tuple(value.get("tables", [])) != manifest.target_tables
        ):
            raise RuntimeError("RECOVERY_VERIFICATION_FAILED")
        for target in manifest.target_tables:
            if (
                self.dynamodb.describe_table(TableName=target)["Table"].get(
                    "TableStatus"
                )
                != "ACTIVE"
            ):
                raise RuntimeError("RECOVERY_VERIFICATION_FAILED")

    def rollback(self, manifest: RecoveryManifest) -> None:
        self.contain(manifest)
        prior = getattr(self, "prior_pointer", None)
        if not isinstance(prior, Mapping):
            raise RuntimeError("RECOVERY_PRIOR_POINTER_INVALID")
        with self._pointer_lock(getattr(manifest, "recovery_id", "unknown")):
            current = self.ssm.get_parameter(
                Name=_required("RECOVERY_POINTER_PARAMETER_NAME")
            )
            try:
                current_value = json.loads(current["Parameter"]["Value"])
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise RuntimeError("RECOVERY_POINTER_GENERATION_MISMATCH") from error
            if (
                not isinstance(current_value, Mapping)
                or current_value.get("recovery_generation")
                != manifest.recovery_generation
            ):
                raise RuntimeError("RECOVERY_POINTER_GENERATION_MISMATCH")
            self.ssm.put_parameter(
                Name=_required("RECOVERY_POINTER_PARAMETER_NAME"),
                Type="SecureString",
                Value=json.dumps(dict(prior), sort_keys=True, separators=(",", ":")),
                Overwrite=True,
            )

    def resume(self, manifest: RecoveryManifest) -> None:
        for schedule in _json_list_env("RECOVERY_SCHEDULES"):
            if not isinstance(schedule, Mapping):
                raise RuntimeError("RECOVERY_SCHEDULE_CONFIG_INVALID")
            current = self.scheduler.get_schedule(
                Name=str(schedule["name"]),
                GroupName=str(schedule.get("group_name", "default")),
            )
            self.scheduler.update_schedule(**_schedule_update(current, state="ENABLED"))
        for mapping_uuid in _json_list_env("RECOVERY_REPLAY_MAPPINGS"):
            self.lambda_client.update_event_source_mapping(
                UUID=str(mapping_uuid), Enabled=True
            )

    def checkpoint(self, manifest: RecoveryManifest) -> None:
        table = _required("RECOVERY_MANIFEST_TABLE_NAME")
        key = {
            "pk": {"S": f"RECOVERY#{manifest.recovery_id}"},
            "sk": {"S": "CURRENT"},
        }
        existing = self.dynamodb.get_item(
            TableName=table, Key=key, ConsistentRead=True
        ).get("Item")
        if (
            existing
            and existing.get("recovery_generation")
            == {"S": manifest.recovery_generation}
            and existing.get("phase") == {"S": manifest.phase.value}
        ):
            if existing.get("phase_started_at") == {"S": manifest.phase_started_at}:
                return
            raise RuntimeError("RECOVERY_CHECKPOINT_CONFLICT")
        try:
            self.dynamodb.put_item(
                TableName=table,
                Item=_manifest_item(manifest),
                ConditionExpression=(
                    "attribute_not_exists(pk) OR "
                    "recovery_generation <> :recovery_generation OR "
                    "phase <> :phase"
                ),
                ExpressionAttributeValues={
                    ":recovery_generation": {"S": manifest.recovery_generation},
                    ":phase": {"S": manifest.phase.value},
                },
            )
        except Exception as error:  # noqa: BLE001 - checkpoint conflicts block recovery
            raise RuntimeError("RECOVERY_CHECKPOINT_CONFLICT") from error


def lambda_handler(event: Mapping[str, object], _context: object) -> dict[str, object]:
    records = event.get("Records")
    if not isinstance(records, list):
        raise RuntimeError("RECOVERY_EVENT_INVALID")
    import boto3  # type: ignore[import-untyped]

    clients = {
        name: boto3.client(name)
        for name in ("cloudwatch", "dynamodb", "scheduler", "lambda", "ssm")
    }
    operations = AwsRecoveryOperations(clients)
    failures: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise RuntimeError("RECOVERY_RECORD_INVALID")
        message_id = record.get("messageId")
        try:
            started_at = _now()
            body = json.loads(str(record.get("body", "")))
            envelope = body if isinstance(body, Mapping) else {}
            payload = envelope.get("payload", envelope)
            command = payload.get("command") if isinstance(payload, Mapping) else None
            if not isinstance(command, Mapping):
                raise RuntimeError("RECOVERY_COMMAND_INVALID")
            restore_point, rpo, rto, deployment = recovery_command_fields(command)
            recovery_watermark = command.get("recovery_watermark")
            if not isinstance(recovery_watermark, str):
                raise RuntimeError("RECOVERY_WATERMARK_REQUIRED")
            source_table_values = _json_list_env("RECOVERY_SOURCE_TABLES")
            if not all(isinstance(item, str) and item for item in source_table_values):
                raise RuntimeError("RECOVERY_SOURCE_TABLES_INVALID")
            source_tables = [cast(str, item) for item in source_table_values]
            recovery_id = str(command["command_id"])
            generation = f"{recovery_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
            manifest = RecoveryManifest(
                recovery_id=recovery_id,
                recovery_generation=generation,
                cell_id=_required("RECOVERY_CELL_ID"),
                account_id=_required("RECOVERY_ACCOUNT_ID"),
                region=_required("RECOVERY_REGION"),
                actor=str(command["actor"]),
                session_id=str(payload.get("session_id", "authenticated")),
                approval_reference=str(command["approval_reference"]),
                reason=str(command["reason"]),
                restore_point=restore_point,
                expected_rpo_seconds=rpo,
                expected_rto_seconds=rto,
                source_deployment_identity=deployment,
                phase_started_at=started_at,
                source_tables=tuple(source_tables),
            )
            if not manifest.source_tables:
                raise RuntimeError("RECOVERY_SOURCE_TABLES_EMPTY")
            # Validate the point against every source table before containment.
            for source in manifest.source_tables:
                recovery = clients["dynamodb"].describe_continuous_backups(
                    TableName=source
                )["ContinuousBackupsDescription"]
                restore_point = validate_restore_point(
                    restore_point,
                    earliest=str(recovery["EarliestRestorableDateTime"]),
                    latest=str(recovery["LatestRestorableDateTime"]),
                )
            manifest = replace(manifest, restore_point=restore_point)
            manifest_table = _required("RECOVERY_MANIFEST_TABLE_NAME")
            existing = (
                clients["dynamodb"]
                .get_item(
                    TableName=manifest_table,
                    Key={
                        "pk": {"S": f"RECOVERY#{recovery_id}"},
                        "sk": {"S": "CURRENT"},
                    },
                    ConsistentRead=True,
                )
                .get("Item")
            )
            if existing:
                continue
            clients["dynamodb"].put_item(
                TableName=manifest_table,
                Item=_manifest_item(manifest),
                ConditionExpression="attribute_not_exists(pk)",
            )
            execution_started_at = _now()
            result = execute_recovery(manifest, operations, now=execution_started_at)
            finished_at = _now()
            result = replace(
                result,
                actual_rpo_seconds=_elapsed_seconds(
                    manifest.restore_point,
                    recovery_watermark,
                ),
                actual_rto_seconds=_elapsed_seconds(started_at, finished_at),
            )
            metric_names = [
                "RecoveryBlocked"
                if result.phase is RecoveryPhase.BLOCKED
                else "RecoveryResumed"
            ]
            if result.failure_code:
                code = result.failure_code
                if "RESTORE" in code:
                    metric_names.append("RecoveryRestoreFailure")
                if (
                    "SCHEMA" in code
                    or "INTEGRITY" in code
                    or "TAG" in code
                    or "ENCRYPTION" in code
                ):
                    metric_names.append("RecoveryIntegrityFailure")
                if "REPLAY" in code:
                    metric_names.append("RecoveryReplayFailure")
                if "VERIFICATION" in code:
                    metric_names.append("RecoveryVerificationFailure")
            clients["cloudwatch"].put_metric_data(
                Namespace=_required("RECOVERY_METRIC_NAMESPACE"),
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Dimensions": [
                            {"Name": "component", "Value": "recovery-controller"},
                            {"Name": "cell_id", "Value": manifest.cell_id},
                            {
                                "Name": "environment",
                                "Value": _required("RECOVERY_ENVIRONMENT"),
                            },
                        ],
                        "Value": 1,
                        "Unit": "Count",
                    }
                    for metric_name in metric_names
                ],
            )
            clients["dynamodb"].put_item(
                TableName=_required("RECOVERY_MANIFEST_TABLE_NAME"),
                Item=_manifest_item(result),
            )
        except Exception:
            if isinstance(message_id, str) and message_id:
                failures.append({"itemIdentifier": message_id})
            else:
                raise
    return {"batchItemFailures": failures}
