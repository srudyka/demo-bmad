from __future__ import annotations

from copy import deepcopy

import pytest

from tests.contract.support.contracts import canary_reservation_decision


AUTHORIZATION = {
    "account_id": "111111111111",
    "apply_role_id": "AROACANARY",
    "region": "us-east-1",
    "repository_id": "platform/terraform",
    "terraform_root_id": "fixtures/canary",
}
REQUEST = {
    **AUTHORIZATION,
    "environment": "dev",
    "job_id": "dev/platform/canary",
    "owner": "platform-engineering",
    "owner_generation": 1,
}


def decision(
    request: dict[str, object] = REQUEST,
    existing: dict[str, object] | None = None,
) -> str:
    return canary_reservation_decision(
        cell_account_id="111111111111",
        cell_region="us-east-1",
        authorization=AUTHORIZATION,
        request=request,
        existing_reservation=existing,
    )


def test_canary_reservation_creation_and_identical_retry_are_deterministic() -> None:
    assert decision() == "CREATED"
    assert decision(existing=REQUEST) == "IDEMPOTENT"


@pytest.mark.parametrize(
    ("name", "field", "value", "expected"),
    (
        (
            "duplicate-owner",
            "owner",
            "different-platform-owner",
            "NAMESPACE_DUPLICATE_RESERVATION",
        ),
        (
            "cross-namespace",
            "repository_id",
            "other/repository",
            "NAMESPACE_CROSS_NAMESPACE_CLAIM",
        ),
        (
            "substituted-root",
            "terraform_root_id",
            "other/root",
            "NAMESPACE_CROSS_NAMESPACE_CLAIM",
        ),
        (
            "wrong-account",
            "account_id",
            "999900001111",
            "NAMESPACE_UNAUTHORIZED_MUTATION",
        ),
        (
            "wrong-region",
            "region",
            "us-west-2",
            "NAMESPACE_UNAUTHORIZED_MUTATION",
        ),
    ),
)
def test_canary_reservation_rejects_identity_substitution(
    name: str, field: str, value: object, expected: str
) -> None:
    request = deepcopy(REQUEST)
    request[field] = value
    assert decision(request=request, existing=REQUEST) == expected, name


def test_canary_reservation_rejects_stale_generation_and_tombstone() -> None:
    stale = deepcopy(REQUEST)
    stale["owner_generation"] = 2
    assert (
        decision(request=stale, existing=REQUEST) == "NAMESPACE_STALE_OWNER_GENERATION"
    )

    tombstoned = {**REQUEST, "tombstoned": True}
    assert decision(existing=tombstoned) == "NAMESPACE_TOMBSTONED_JOB_ID"
