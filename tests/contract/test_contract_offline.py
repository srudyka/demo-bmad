from __future__ import annotations

import socket
from pathlib import Path

import pytest

from tests.contract.support.contracts import build_schema_registry, load_json_strict


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_contract_loading_and_schema_registry_are_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def network_forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("contract validation attempted network access")

    monkeypatch.setattr(socket, "socket", network_forbidden)
    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    manifest = load_json_strict(CONTRACTS_ROOT / "manifest.json")
    schemas, registry = build_schema_registry(CONTRACTS_ROOT / "v1" / "schemas")
    assert set(manifest["schemas"]) == set(schemas)
    assert registry is not None


def test_contract_tooling_does_not_read_aws_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
    ):
        monkeypatch.setenv(name, "forbidden-fixture-value")
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "catalogs" / "compatibility.json"
    )
    assert fixture["current_major"] == 1
