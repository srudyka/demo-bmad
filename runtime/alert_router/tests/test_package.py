from __future__ import annotations

import alert_router


def test_package_boundary_is_importable() -> None:
    assert alert_router.__all__ == ()
