# ECS Scheduled Job Runbook

## Scope

Use this runbook for jobs created by `modules/ecs-scheduled-job`. The module runs one ECS Fargate task on an EventBridge Scheduler expression and publishes outputs for the schedule, task definition, log group, DLQ, roles, and alarms.

## Normal Verification

1. Confirm the schedule is enabled in EventBridge Scheduler.
2. Confirm the task definition revision uses the expected immutable image tag or digest.
3. Inspect the CloudWatch log group from `log_group_name` for successful job completion output.
4. Confirm both alarms are `OK`: `task_failure_alarm_name` and `scheduler_dlq_alarm_name`.
5. Confirm the Scheduler DLQ from `scheduler_dlq_url` has no visible messages.

## Scheduler Delivery Failure

Symptoms: `scheduler_dlq_alarm_name` enters `ALARM`, or messages appear in the Scheduler DLQ.

Checks:

- Inspect the DLQ message body for the failed Scheduler target request.
- Verify the ECS cluster ARN, subnet IDs, security groups, and task definition ARN still exist.
- Verify the scheduler role can call `ecs:RunTask`, pass the task roles, and send to the DLQ.
- Check ECS service quotas and subnet capacity if the task could not be placed.

Recovery:

- Fix the target, role, network, or capacity issue.
- Replay a DLQ message only if the job is idempotent for that scheduled time.
- Delete DLQ messages only after the missed run has been handled or explicitly waived.

## Task Runtime Failure

Symptoms: `task_failure_alarm_name` enters `ALARM`, the ECS task fails to start, or the ECS task stops with a non-zero container exit code.

Checks:

- Open the ECS stopped task and inspect `stoppedReason` plus container `exitCode`.
- Inspect container logs in `log_group_name` around the failed run time.
- Confirm referenced SSM or Secrets Manager ARNs are readable by the execution role.
- Confirm downstream dependencies were reachable from the configured private subnets and security groups.
- Confirm the image reference points to the intended release.
- Confirm the job's own runtime timeout or deadline handling is working as designed.

Recovery:

- Fix the job input, secret reference, dependency, or image.
- Manually rerun only if the job is idempotent for the target period.
- Record whether the failed run was replayed, skipped, or compensated elsewhere.

## Emergency Stop And Rollback

- Set `schedule_enabled = false` and apply to stop future runs while preserving logs and DLQ evidence.
- Roll back a bad release by restoring the previous immutable image reference or previous module version.
- If IAM or network changes caused the issue, restore the previous role policy, subnet, or security group configuration.
- After rollback, verify a controlled manual or next scheduled run, then return alarms to `OK`.

## Idempotency Expectations

Scheduled jobs must tolerate retry or replay for the same logical schedule time. If a job cannot be safely replayed, document the compensating action and require operator approval before redriving DLQ messages or manually starting a replacement task.

Each job should also enforce a bounded runtime in application code or its entrypoint. EventBridge Scheduler starts the task, but it does not provide a generic wall-clock timeout that terminates a long-running Fargate task.
