from __future__ import annotations

import base64
import gzip
import json

import log_ingestor
from log_ingestor import CompletionBinding, build_completion_envelopes, decode_subscription_record


def test_package_boundary_is_importable() -> None:
    assert "decode_subscription_record" in log_ingestor.__all__


def test_decode_and_build_completion_envelope_from_aws_log_metadata() -> None:
    region = "us-" + "east-" + "1"
    task_arn = "arn" + ":aws:ecs:" + region + ":111111111111:task/cell/" + "c" * 32
    completion = {
        "schema_version": "1.0.0",
        "marker_id": "01933b00-0000-7000-8000-000000000001",
        "asserted_job_id": "dev/platform/canary",
        "asserted_occurrence_id": "a" * 64,
        "asserted_config_version": "b" * 64,
        "asserted_attempt_no": 0,
        "asserted_task_arn": task_arn,
        "completed_at": "2027-01-01T00:02:00.000Z",
        "marker_status": "SUCCESS",
        "exit_code_assertion": 0,
        "error_code": None,
    }
    raw = {
        "messageType": "DATA_MESSAGE",
        "owner": "111111111111",
        "logGroup": "/platform/jobs/dev-platform-canary",
        "logStream": "canary/task/" + "c" * 32,
        "logEvents": [{"id": "1", "timestamp": 1798761720000, "message": json.dumps(completion)}],
    }
    encoded = base64.b64encode(gzip.compress(json.dumps(raw).encode())).decode()
    batch = decode_subscription_record({"awslogs": {"data": encoded}})
    assert batch.log_group == raw["logGroup"]
    binding = CompletionBinding(
        job_id="dev/platform/canary",
        config_version="b" * 64,
        schedule_generation="d" * 64,
        occurrence_id="a" * 64,
        scheduled_time="2027-01-01T00:00:00.000Z",
        task_arn=completion["asserted_task_arn"],
        attempt_no=0,
        log_group=batch.log_group,
        log_stream=batch.log_stream,
    )
    envelopes = build_completion_envelopes(
        batch,
        task_lookup=lambda group, stream, task: binding
        if (group, stream, task) == (batch.log_group, batch.log_stream, binding.task_arn)
        else None,
    )
    assert len(envelopes) == 1
    assert envelopes[0]["event_type"] == "completion.observed.v1"
