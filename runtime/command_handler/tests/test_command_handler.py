from __future__ import annotations

import pytest

from command_handler import CommandRejected
from command_handler.handler import lambda_handler


def test_handler_requires_authenticated_invocation_context() -> None:
    with pytest.raises(CommandRejected, match="COMMAND_CALLER_AUTHORITY"):
        lambda_handler({"request": {}}, object())
