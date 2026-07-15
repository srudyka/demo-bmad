from __future__ import annotations

import evidence_normalizer


def test_package_boundary_is_importable() -> None:
    assert evidence_normalizer.__all__ == ()
