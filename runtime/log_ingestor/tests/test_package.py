from __future__ import annotations

import log_ingestor


def test_package_boundary_is_importable() -> None:
    assert log_ingestor.__all__ == ()
