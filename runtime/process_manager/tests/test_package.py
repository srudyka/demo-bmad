from __future__ import annotations

import process_manager


def test_package_boundary_is_importable() -> None:
    assert process_manager.__all__ == ()
