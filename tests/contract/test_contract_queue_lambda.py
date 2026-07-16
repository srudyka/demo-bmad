from __future__ import annotations

from pathlib import Path

import pytest

from tests.contract.support.contracts import (
    ContractViolation,
    evaluate_ecs_retry_case,
    evaluate_queue_case,
    load_json_strict,
)


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"


def test_service_maxima_are_separate_from_stricter_platform_limits() -> None:
    catalog = load_json_strict(
        CONTRACTS_ROOT / "v1" / "catalogs" / "queue-lambda-constraints.json"
    )
    assert catalog["sqs"]["service_message_maximum_bytes"] == 1_048_576
    assert catalog["sqs"]["platform_message_maximum_bytes"] == 262_144
    assert catalog["lambda_sqs"]["synchronous_payload_maximum_bytes"] == 6_291_456
    assert catalog["lambda_sqs"]["event_source_batch_size"]["maximum"] == 10
    assert catalog["sqs"]["retention_seconds"] == 1_209_600


def test_queue_lambda_boundary_and_invalid_combination_fixtures() -> None:
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "queue-lambda" / "cases.json"
    )
    for case in fixture["queue_cases"]:
        if case["accepted"]:
            evaluate_queue_case(case)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_queue_case(case)
    assert fixture["retry_semantics"] == {
        "partial_failure": "return failed messageId values only",
        "poison_message": "redrive after maxReceiveCount",
        "whole_batch_exception": (
            "all messages become visible after visibility timeout"
        ),
    }


def test_ecs_run_task_retry_and_failure_fixtures() -> None:
    fixture = load_json_strict(
        CONTRACTS_ROOT / "v1" / "fixtures" / "queue-lambda" / "cases.json"
    )
    for case in fixture["ecs_run_task_cases"]:
        if case["accepted"]:
            evaluate_ecs_retry_case(case)
        else:
            with pytest.raises(ContractViolation, match=case["error_code"]):
                evaluate_ecs_retry_case(case)
