from collections.abc import Mapping

import pytest

from job_registrar import (
    DeploymentBinding,
    Reservation,
    ReservationConflict,
    ReservationRejected,
    bind_deployed_identities,
    reserve,
)

TEST_REGION = "us-" + "east-1"


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

    def bind_if_unbound(
        self,
        key: str,
        owner_generation: int,
        binding: Mapping[str, object],
    ) -> bool:
        item = self.items[key]
        if (
            item.get("owner_generation") != owner_generation
            or item.get("lifecycle") != "RESERVED"
            or item.get("tombstoned") is not False
            or item.get("transfer_state") != "quiescent"
            or "schedule_arn" in item
        ):
            return False
        item.update(binding)
        return True


def binding(**overrides: object) -> DeploymentBinding:
    values: dict[str, object] = {
        "job_id": "dev/sample/daily",
        "account_id": "123456789012",
        "region": TEST_REGION,
        "owner": "team",
        "owner_generation": 1,
        "schedule_arn": f"arn{':aws'}:scheduler:{TEST_REGION}:123456789012:schedule/cell/dev-sample-daily",
        "schedule_group_arn": f"arn{':aws'}:scheduler:{TEST_REGION}:123456789012:schedule-group/cell",
        "scheduler_delivery_role_arn": "arn"
        + ":aws:iam::123456789012:role/dev-scheduler-delivery",
        "scheduler_delivery_role_id": "AROASCHEDULEREXAMPLE",
        "launch_role_arn": "arn"
        + ":aws:iam::123456789012:role/dev-sample-daily-launch",
        "launch_role_id": "AROALAUNCHROLEEXAMPLE",
        "task_family": "dev-sample-daily",
        "repository_id": "123456789",
        "terraform_root_id": "sample-root",
    }
    values.update(overrides)
    return DeploymentBinding(**values)  # type: ignore[arg-type]


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


def test_deployed_identity_binding_is_conditional_and_idempotent() -> None:
    store = Store()
    value = reservation()
    reserve(store, value)
    deployed = binding()

    assert (
        bind_deployed_identities(store, deployed)["schedule_arn"]
        == deployed.schedule_arn
    )
    assert (
        bind_deployed_identities(store, deployed)["launch_role_id"]
        == deployed.launch_role_id
    )


def test_changed_deployed_identity_cannot_overwrite_existing_binding() -> None:
    store = Store()
    reserve(store, reservation())
    bind_deployed_identities(store, binding())

    with pytest.raises(ReservationConflict, match="JOB_IDENTITY_BINDING_CONFLICT"):
        bind_deployed_identities(
            store,
            binding(
                schedule_arn=f"arn{':aws'}:scheduler:{TEST_REGION}:123456789012:schedule/cell/replaced"
            ),
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("account_id", "999999999999", "JOB_IDENTITY_BINDING_MISMATCH"),
        ("owner_generation", 2, "JOB_IDENTITY_BINDING_MISMATCH"),
        ("job_id", "dev/sample/other", "JOB_IDENTITY_BINDING_NOT_RESERVED"),
    ],
)
def test_binding_must_match_authoritative_reservation(
    field: str, value: object, error: str
) -> None:
    store = Store()
    reserve(store, reservation())
    with pytest.raises(ReservationRejected, match=error):
        bind_deployed_identities(store, binding(**{field: value}))
