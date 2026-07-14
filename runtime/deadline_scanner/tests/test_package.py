from __future__ import annotations

import deadline_scanner


def test_package_boundary_is_importable() -> None:
    assert deadline_scanner.__all__ == ()
