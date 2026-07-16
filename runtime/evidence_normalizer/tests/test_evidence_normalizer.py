from __future__ import annotations

import evidence_normalizer
from evidence_normalizer.handler import _canonical_message
from tests.contract.support.contracts import canonical_json_bytes


def test_package_boundary_is_importable() -> None:
    assert "normalize_scheduler_record" in evidence_normalizer.__all__


def test_queue_messages_use_contract_canonical_json_bytes() -> None:
    value = {"message": "caf\u00e9", "z": 1}

    assert _canonical_message(value).encode("utf-8") == canonical_json_bytes(value)
