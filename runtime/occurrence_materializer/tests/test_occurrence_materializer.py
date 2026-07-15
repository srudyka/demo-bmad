from __future__ import annotations

import occurrence_materializer


def test_package_boundary_is_importable() -> None:
    assert occurrence_materializer.__all__ == ()
