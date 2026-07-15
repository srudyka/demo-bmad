from __future__ import annotations

import command_handler


def test_package_boundary_is_importable() -> None:
    assert command_handler.__all__ == ()
