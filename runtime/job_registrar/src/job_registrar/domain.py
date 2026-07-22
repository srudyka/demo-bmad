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
