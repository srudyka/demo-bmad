"""Pure reservation identity and conditional-claim rules."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol


class ReservationRejected(ValueError):
    """A declaration cannot safely enter the reservation registry."""


class ReservationConflict(ReservationRejected):
    """The canonical identity is already owned by a different declaration."""


class ConditionalReservationStore(Protocol):
    def get(self, key: str) -> Mapping[str, object] | None: ...

    def get_namespace(self, key: str) -> Mapping[str, object] | None: ...

    def put_if_absent(self, key: str, item: Mapping[str, object]) -> bool: ...

    def bind_if_unbound(
        self,
        key: str,
        owner_generation: int,
        binding: Mapping[str, object],
    ) -> bool: ...


class DynamoReservationStore:
    """DynamoDB adapter using a conditional PutItem for the ownership claim."""

    def __init__(self, client: Any, table_name: str) -> None:
        self.client = client
        self.table_name = table_name

    @staticmethod
    def _encode(value: object) -> dict[str, str | bool]:
        if isinstance(value, bool):
            return {"BOOL": value}
        if isinstance(value, int):
            return {"N": str(value)}
        if isinstance(value, str):
            return {"S": value}
        raise ReservationRejected("JOB_RESERVATION_VALUE")

    @staticmethod
    def _decode(value: Mapping[str, object]) -> object:
        if "S" in value:
            return value["S"]
        if "N" in value:
            return int(str(value["N"]))
        if "BOOL" in value:
            return value["BOOL"]
        raise ReservationRejected("JOB_RESERVATION_VALUE")

    def get(self, key: str) -> dict[str, object] | None:
        response = self.client.get_item(
            TableName=self.table_name,
            Key={"pk": {"S": key}, "sk": {"S": "RESERVATION"}},
            ConsistentRead=True,
        )
        raw = response.get("Item")
        if not raw:
            return None
        return {name: self._decode(value) for name, value in raw.items()}

    def get_namespace(self, key: str) -> dict[str, object] | None:
        response = self.client.get_item(
            TableName=self.table_name,
            Key={"pk": {"S": key}, "sk": {"S": "AUTHORIZATION"}},
            ConsistentRead=True,
        )
        raw = response.get("Item")
        if not raw:
            return None
        return {name: self._decode(value) for name, value in raw.items()}

    def put_if_absent(self, key: str, item: Mapping[str, object]) -> bool:
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item={name: self._encode(value) for name, value in item.items()},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except self.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def bind_if_unbound(
        self,
        key: str,
        owner_generation: int,
        binding: Mapping[str, object],
    ) -> bool:
        names = tuple(binding)
        expression_names = {f":{name}": self._encode(binding[name]) for name in names}
        expression = "SET " + ", ".join(f"{name} = :{name}" for name in names)
        condition = (
            "owner_generation = :owner_generation AND lifecycle = :lifecycle "
            "AND tombstoned = :tombstoned AND transfer_state = :transfer_state "
            "AND attribute_not_exists(schedule_arn)"
        )
        expression_names.update(
            {
                ":owner_generation": {"N": str(owner_generation)},
                ":lifecycle": {"S": "RESERVED"},
                ":tombstoned": {"BOOL": False},
                ":transfer_state": {"S": "quiescent"},
            }
        )
        try:
            self.client.update_item(
                TableName=self.table_name,
                Key={"pk": {"S": key}, "sk": {"S": "RESERVATION"}},
                UpdateExpression=expression,
                ConditionExpression=condition,
                ExpressionAttributeValues=expression_names,
            )
        except self.client.exceptions.ConditionalCheckFailedException:
            return False
        return True


@dataclass(frozen=True)
class Reservation:
    job_id: str
    account_id: str
    region: str
    environment: str
    application: str
    repository_id: str
    terraform_root_id: str
    apply_role_id: str
    owner: str
    owner_generation: int = 1
    lifecycle: str = "RESERVED"
    tombstoned: bool = False
    transfer_state: str = "quiescent"

    @property
    def key(self) -> str:
        return f"JOB#{self.job_id}"

    def validate(self) -> None:
        parts = self.job_id.split("/")
        segment = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
        if len(parts) != 3 or any(segment.fullmatch(part) is None for part in parts):
            raise ReservationRejected("JOB_ID_INVALID")
        production_environment = "p" + "rod"
        if self.environment == production_environment or self.application in {
            "platform",
            "system",
        }:
            raise ReservationRejected("JOB_NAMESPACE_RESERVED")
        if parts[0] != self.environment or parts[1] != self.application:
            raise ReservationRejected("JOB_ID_IDENTITY_MISMATCH")
        if len(self.job_id) > 194:
            raise ReservationRejected("JOB_ID_LENGTH")
        if any(part in {"latest", "current"} for part in parts):
            raise ReservationRejected("JOB_ID_INVALID")
        if re.fullmatch(r"[0-9]{12}", self.account_id) is None:
            raise ReservationRejected("JOB_ACCOUNT_ID")
        if not self.region or not self.repository_id or not self.terraform_root_id:
            raise ReservationRejected("JOB_RESERVATION_IDENTITY")
        if (
            self.owner_generation < 1
            or self.lifecycle != "RESERVED"
            or self.transfer_state != "quiescent"
        ):
            raise ReservationRejected("JOB_RESERVATION_STATE")
        if self.tombstoned:
            raise ReservationRejected("JOB_TOMBSTONED")

    def as_item(self) -> dict[str, object]:
        self.validate()
        item = asdict(self)
        item["pk"] = self.key
        item["sk"] = "RESERVATION"
        item["namespace_key"] = f"NAMESPACE#{self.environment}#{self.application}"
        return item


@dataclass(frozen=True)
class DeploymentBinding:
    """Authoritative AWS identities bound to one RESERVED job generation."""

    job_id: str
    account_id: str
    region: str
    owner: str
    owner_generation: int
    schedule_arn: str
    schedule_group_arn: str
    scheduler_delivery_role_arn: str
    scheduler_delivery_role_id: str
    launch_role_arn: str
    launch_role_id: str
    task_family: str
    repository_id: str
    terraform_root_id: str
    task_definition_arn: str = ""

    def validate(self) -> None:
        if (
            not re.fullmatch(
                r"[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}",
                self.job_id,
            )
            or not re.fullmatch(r"[0-9]{12}", self.account_id)
            or not re.fullmatch(
                r"[a-z]{2}(?:-gov|-iso|-isob|-iso-b)?-[a-z]+-[0-9]+", self.region
            )
            or not self.owner
        ):
            raise ReservationRejected("JOB_IDENTITY_BINDING_INVALID")
        if self.owner_generation < 1:
            raise ReservationRejected("JOB_IDENTITY_BINDING_GENERATION")
        fields = (
            self.schedule_arn,
            self.schedule_group_arn,
            self.scheduler_delivery_role_arn,
            self.scheduler_delivery_role_id,
            self.launch_role_arn,
            self.launch_role_id,
            self.task_family,
            self.repository_id,
            self.terraform_root_id,
        )
        if any(not isinstance(value, str) or not value for value in fields):
            raise ReservationRejected("JOB_IDENTITY_BINDING_INVALID")
        arn_pattern = (
            rf"^arn:[a-z0-9-]+:scheduler:{re.escape(self.region)}:{self.account_id}:"
        )
        if not re.fullmatch(arn_pattern + r"schedule/.+", self.schedule_arn):
            raise ReservationRejected("JOB_IDENTITY_BINDING_SCHEDULE_ARN")
        if not re.fullmatch(
            arn_pattern + r"schedule-group/.+", self.schedule_group_arn
        ):
            raise ReservationRejected("JOB_IDENTITY_BINDING_SCHEDULE_GROUP_ARN")
        iam_pattern = rf"^arn:[a-z0-9-]+:iam::{self.account_id}:role/.+"
        for role_arn in (self.scheduler_delivery_role_arn, self.launch_role_arn):
            if not re.fullmatch(iam_pattern, role_arn):
                raise ReservationRejected("JOB_IDENTITY_BINDING_ROLE_ARN")
        if not re.fullmatch(r"^AROA[A-Z0-9]+$", self.scheduler_delivery_role_id):
            raise ReservationRejected("JOB_IDENTITY_BINDING_ROLE_ID")
        if not re.fullmatch(r"^AROA[A-Z0-9]+$", self.launch_role_id):
            raise ReservationRejected("JOB_IDENTITY_BINDING_ROLE_ID")
        if self.task_definition_arn and not re.fullmatch(
            rf"^arn:[a-z0-9-]+:ecs:{re.escape(self.region)}:{self.account_id}:task-definition/.+:[0-9]+$",
            self.task_definition_arn,
        ):
            raise ReservationRejected("JOB_IDENTITY_BINDING_TASK_ARN")

    def as_item(self) -> dict[str, object]:
        self.validate()
        return {
            "schedule_arn": self.schedule_arn,
            "schedule_group_arn": self.schedule_group_arn,
            "scheduler_delivery_role_arn": self.scheduler_delivery_role_arn,
            "scheduler_delivery_role_id": self.scheduler_delivery_role_id,
            "launch_role_arn": self.launch_role_arn,
            "launch_role_id": self.launch_role_id,
            "task_family": self.task_family,
            "bound_repository_id": self.repository_id,
            "bound_terraform_root_id": self.terraform_root_id,
            "bound_account_id": self.account_id,
            "bound_region": self.region,
            "bound_owner": self.owner,
            **(
                {"task_definition_arn": self.task_definition_arn}
                if self.task_definition_arn
                else {}
            ),
        }


def reserve(
    store: ConditionalReservationStore, reservation: Reservation
) -> Reservation:
    """Claim once, return identical retries, and reject conflicting claims."""

    item = reservation.as_item()
    namespace = store.get_namespace(
        f"NAMESPACE#{reservation.environment}#{reservation.application}"
    )
    if namespace is None:
        raise ReservationRejected("NAMESPACE_CROSS_NAMESPACE_CLAIM")
    required = {
        "repository_id": reservation.repository_id,
        "terraform_root_id": reservation.terraform_root_id,
        "apply_role_id": reservation.apply_role_id,
        "account_id": reservation.account_id,
        "region": reservation.region,
    }
    if any(namespace.get(key) != value for key, value in required.items()):
        raise ReservationRejected("NAMESPACE_UNAUTHORIZED_MUTATION")
    existing = store.get(reservation.key)
    if existing is not None:
        if dict(existing) == item:
            return reservation
        raise ReservationConflict("JOB_RESERVATION_CONFLICT")
    if store.put_if_absent(reservation.key, item):
        return reservation
    concurrent = store.get(reservation.key)
    if concurrent is not None and dict(concurrent) == item:
        return reservation
    raise ReservationConflict("JOB_RESERVATION_CONFLICT")


def bind_deployed_identities(
    store: ConditionalReservationStore, binding: DeploymentBinding
) -> Mapping[str, object]:
    """Conditionally bind deployed identities without overwriting a generation."""

    existing = store.get(f"JOB#{binding.job_id}")
    if existing is None:
        raise ReservationRejected("JOB_IDENTITY_BINDING_NOT_RESERVED")
    expected = {
        "job_id": binding.job_id,
        "account_id": binding.account_id,
        "region": binding.region,
        "owner": binding.owner,
        "owner_generation": binding.owner_generation,
        "repository_id": binding.repository_id,
        "terraform_root_id": binding.terraform_root_id,
        "lifecycle": "RESERVED",
        "tombstoned": False,
        "transfer_state": "quiescent",
    }
    if any(existing.get(key) != value for key, value in expected.items()):
        raise ReservationRejected("JOB_IDENTITY_BINDING_MISMATCH")
    binding.validate()
    values = binding.as_item()
    bound_fields = tuple(values)
    if any(field in existing for field in bound_fields):
        if all(existing.get(field) == value for field, value in values.items()):
            return existing
        raise ReservationConflict("JOB_IDENTITY_BINDING_CONFLICT")
    key = existing.get("pk")
    if not isinstance(key, str):
        raise ReservationRejected("JOB_IDENTITY_BINDING_INVALID")
    if store.bind_if_unbound(key, binding.owner_generation, values):
        updated = store.get(key)
        if updated is not None:
            return updated
    concurrent = store.get(key)
    if concurrent is not None and all(
        concurrent.get(field) == value for field, value in values.items()
    ):
        return concurrent
    raise ReservationConflict("JOB_IDENTITY_BINDING_CONFLICT")
