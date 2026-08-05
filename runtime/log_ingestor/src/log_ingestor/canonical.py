"""Runtime-owned canonical JSON helper for the log-ingestor artifact."""

from __future__ import annotations

from typing import Any

import rfc8785


def canonical_json_bytes(value: Any) -> bytes:
    return rfc8785.dumps(value)
