"""Pure validation and conditional-publication logic for CONFIG."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Protocol, cast

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from referencing import Registry, Resource
import rfc8785


JOB_ID = re.compile(
    r"^[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}/[a-z0-9][a-z0-9-]{0,62}$"
)
VERSION = re.compile(r"^[0-9a-f]{64}$")
PROTOCOL = "config-publisher/1.0.0"
DOCUMENT_KEYS = {"schema_version", "config_version", "config"}
SECRET_KEY = re.compile(
    r"(?:password|secret|token|private[_-]?key|credential|api[_-]?key)", re.IGNORECASE
)
SAFE_SECRET_REFERENCE_KEYS = {"secret_references"}
CONFIG_SCHEMA_ID = "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:config"
COMMON_SCHEMA_ID = "urn:demo-bmad:ecs-scheduled-jobs:contract:1.0.0:schema:common"


class PublisherError(ValueError):
    """Stable, operator-safe publisher rejection."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ObjectStore(Protocol):
    def put_object(self, **kwargs: object) -> Mapping[str, object]: ...

    def get_object(self, **kwargs: object) -> Mapping[str, object]: ...


@lru_cache(maxsize=1)
def _config_validator() -> Draft202012Validator:
    package = files("config_publisher").joinpath("schemas")
    config_schema = json.loads(
        package.joinpath("config.schema.json").read_text(encoding="utf-8")
    )
    common_schema = json.loads(
        package.joinpath("common.schema.json").read_text(encoding="utf-8")
    )
    registry = Registry().with_resources(
        [
            (CONFIG_SCHEMA_ID, Resource.from_contents(config_schema)),
            (COMMON_SCHEMA_ID, Resource.from_contents(common_schema)),
        ]
    )
    return Draft202012Validator(config_schema, registry=registry)


def _validate_config_schema(document: Mapping[str, object]) -> None:
    if any(_config_validator().iter_errors(document)):
        raise PublisherError("CONFIG_DOCUMENT_INVALID")


@dataclass(frozen=True)
class PublishRequest:
    job_id: str
    config_version: str
    object_key: str
    config_document: Mapping[str, object]
    contract_version: str
    ownership_generation: int
    protocol_version: str = PROTOCOL

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "PublishRequest":
        required = (
            "job_id",
            "config_version",
            "object_key",
            "config_document",
            "contract_version",
            "ownership_generation",
        )
        if any(key not in value for key in required):
            raise PublisherError("PUBLISH_REQUEST_INVALID")
        job_id = value["job_id"]
        version = value["config_version"]
        key = value["object_key"]
        document = value["config_document"]
        generation = value["ownership_generation"]
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            raise PublisherError("JOB_ID_INVALID")
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise PublisherError("CONFIG_VERSION_INVALID")
        if not isinstance(key, str) or key != f"jobs/{job_id}/config/{version}.json":
            raise PublisherError("CONFIG_KEY_INVALID")
        if (
            not isinstance(document, Mapping)
            or set(document) != DOCUMENT_KEYS
            or document.get("schema_version") != "1.0.0"
            or document.get("config_version") != version
            or not isinstance(document.get("config"), Mapping)
        ):
            raise PublisherError("CONFIG_DOCUMENT_INVALID")
        if any(SECRET_KEY.search(key) is not None for key in _unsafe_keys(document)):
            raise PublisherError("CONFIG_SECRET_VALUE_FORBIDDEN")
        _validate_config_schema(document)
        if (
            not isinstance(generation, int)
            or isinstance(generation, bool)
            or generation < 1
        ):
            raise PublisherError("OWNERSHIP_GENERATION_INVALID")
        protocol = value.get("protocol_version", PROTOCOL)
        contract = value["contract_version"]
        if (
            protocol != PROTOCOL
            or not isinstance(contract, str)
            or not re.fullmatch(r"1\.[0-9]+\.[0-9]+", contract)
        ):
            raise PublisherError("PUBLISH_PROTOCOL_UNSUPPORTED")
        body = rfc8785.dumps(cast(Any, document["config"]))
        if hashlib.sha256(body).hexdigest() != version:
            raise PublisherError("CONFIG_HASH_MISMATCH")
        return cls(job_id, version, key, document, contract, generation, protocol)


def _keys(value: object) -> list[str]:
    if isinstance(value, Mapping):
        return [key for key in value if isinstance(key, str)] + [
            nested for item in value.values() for nested in _keys(item)
        ]
    if isinstance(value, list):
        return [nested for item in value for nested in _keys(item)]
    return []


def _unsafe_keys(value: object) -> list[str]:
    return [key for key in _keys(value) if key not in SAFE_SECRET_REFERENCE_KEYS]


def publish(
    request: PublishRequest,
    *,
    store: ObjectStore,
    bucket: str,
    kms_key_arn: str,
    authenticated_job_id: str,
) -> dict[str, object]:
    """Create one CONFIG object, treating only an identical retry as success."""

    if authenticated_job_id != request.job_id:
        raise PublisherError("JOB_ID_AUTHORIZATION_FAILED")
    body = rfc8785.dumps(cast(Any, request.config_document))
    try:
        store.put_object(
            Bucket=bucket,
            Key=request.object_key,
            Body=body,
            ContentType="application/json",
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=kms_key_arn,
            IfNoneMatch="*",
            Metadata={
                "job-id": request.job_id,
                "config-version": request.config_version,
            },
        )
        result = "PUBLISHED"
    except (
        Exception
    ) as error:  # boto3 ClientError is intentionally duck-typed for tests.
        response = getattr(error, "response", None)
        details = response.get("Error", {}) if isinstance(response, Mapping) else {}
        code = details.get("Code") if isinstance(details, Mapping) else None
        if code not in {"PreconditionFailed", "412"}:
            raise PublisherError("CONFIG_PUBLISH_FAILED") from error
        existing = store.get_object(Bucket=bucket, Key=request.object_key)
        existing_value = existing.get("Body")
        existing_body = (
            existing_value.read() if hasattr(existing_value, "read") else existing_value
        )
        if existing_body != body:
            raise PublisherError("CONFIG_VERSION_CONFLICT") from error
        result = "ALREADY_PUBLISHED"
    return {
        "protocol_version": request.protocol_version,
        "lifecycle": "PUBLISHED",
        "result": result,
        "job_id": request.job_id,
        "config_version": request.config_version,
        "object_key": request.object_key,
        "contract_version": request.contract_version,
        "ownership_generation": request.ownership_generation,
        "operation_id": f"cfgpub-{uuid.uuid4().hex}",
    }
