"""Small self-contained contract/storage primitives for the router artifact."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from typing import Any

import rfc8785


def _profile(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > 9007199254740991:
            raise ValueError("CANONICAL_INTEGER_OUT_OF_RANGE")
        return
    if isinstance(value, float):
        raise ValueError("CANONICAL_FLOAT_FORBIDDEN")
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("CANONICAL_STRING_NOT_NFC")
        return
    if isinstance(value, list):
        for child in value:
            _profile(child)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("CANONICAL_KEY_NOT_STRING")
            _profile(key)
            _profile(child)
        return
    raise ValueError("CANONICAL_TYPE_FORBIDDEN")


def canonical_json_bytes(value: Any) -> bytes:
    _profile(value)
    return rfc8785.dumps(value)


def attribute(value: Any) -> dict[str, Any]:
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, int):
        return {"N": str(value)}
    if isinstance(value, list):
        return {"L": [attribute(item) for item in value]}
    if isinstance(value, Mapping):
        return {"M": {str(key): attribute(child) for key, child in value.items()}}
    return {"S": str(value)}


def dynamodb_item(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    item = {key: attribute(value) for key, value in record.items() if key != "keys"}
    keys = record.get("keys")
    if isinstance(keys, Mapping):
        item["pk"] = attribute(keys["pk"])
        item["sk"] = attribute(keys["sk"])
    return item


def plain_item(item: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in item.items():
        if not isinstance(value, Mapping) or len(value) != 1:
            result[key] = value
            continue
        kind, child = next(iter(value.items()))
        if kind == "S":
            result[key] = child
        elif kind == "N":
            result[key] = int(child) if str(child).isdigit() else float(child)
        elif kind == "BOOL":
            result[key] = child
        elif kind == "NULL":
            result[key] = None
        elif kind == "L" and isinstance(child, list):
            result[key] = [plain_item({"value": item})["value"] for item in child]
        elif kind == "M" and isinstance(child, Mapping):
            result[key] = plain_item(child)
        else:
            result[key] = child
    return result
