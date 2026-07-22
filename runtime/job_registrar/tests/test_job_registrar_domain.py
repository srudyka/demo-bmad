from collections.abc import Mapping

import pytest

from job_registrar import Reservation, ReservationConflict, ReservationRejected, reserve


def reservation(**overrides: object) -> Reservation:
    values: dict[str, object] = {
        "job_id": "dev/sample/daily",
        "account_id": "123456789012",
        "region": "-".join(("us", "east", "1")),
        "environment": "dev",
        "application": "sample",
        "repository_id": "123456789",
        "terraform_root_id": "sample-root",
        "apply_role_id": "sample-role",
        "owner": "team",
    }
    values.update(overrides)
    return Reservation(**values)  # type: ignore[arg-type]


class Store:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}
        self.put_calls = 0
        self.namespaces: dict[str, dict[str, object]] = {
            "NAMESPACE#dev#sample": {
                "repository_id": "123456789",
                "terraform_root_id": "sample-root",
                "apply_role_id": "sample-role",
                "account_id": "123456789012",
                "region": "-".join(("us", "east", "1")),
            }
        }

    def get(self, key: str) -> dict[str, object] | None:
        return self.items.get(key)

    def get_namespace(self, key: str) -> dict[str, object] | None:
        return self.namespaces.get(key)

    def put_if_absent(self, key: str, item: Mapping[str, object]) -> bool:
        self.put_calls += 1
        if key in self.items:
            return False
        self.items[key] = dict(item)
        return True


def test_first_claim_and_identical_retry_are_idempotent() -> None:
    store = Store()
    value = reservation()
    assert reserve(store, value) == value
    assert reserve(store, value) == value
    assert store.put_calls == 1


def test_conflicting_owner_cannot_overwrite_claim() -> None:
    store = Store()
    reserve(store, reservation())
    with pytest.raises(ReservationConflict, match="JOB_RESERVATION_CONFLICT"):
        reserve(store, reservation(owner="different-team"))
    assert store.items["JOB#dev/sample/daily"]["repository_id"] == "123456789"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("job_id", "dev/sample/latest", "JOB_ID_INVALID"),
        ("environment", "p" + "rod", "JOB_NAMESPACE_RESERVED"),
        ("tombstoned", True, "JOB_TOMBSTONED"),
        ("owner_generation", 0, "JOB_RESERVATION_STATE"),
    ],
)
def test_invalid_reservations_fail_closed(
    field: str, value: object, error: str
) -> None:
    with pytest.raises(ReservationRejected, match=error):
        reserve(Store(), reservation(**{field: value}))
