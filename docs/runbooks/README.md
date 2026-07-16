# Operator Runbooks

This is the stable location for platform and job operator Runbooks. Story 1.3
introduces the Cell foundation recovery boundary: retain CONFIG and namespace
evidence during rollback, validate a restored DynamoDB table before a Cell
Contract cutover, and never use routine destructive cleanup as recovery.

Runtime, alarm, rerun, and incident procedures are introduced with the
capabilities they operate.

## Canary Bootstrap Recovery

The platform-owned canary fixture is a non-production, disabled Scheduler
acceptance path. It must not be enabled, manually invoked, or used to claim an
ECS launch, completion, or alert until the later Cell processors are deployed
and disposable-account evidence is recorded. Its encrypted SQS test queue has
no production subscriptions or customer integrations.

For a failed canary definition change, retain the Cell reservation, CONFIG
object versions, Scheduler queues, log group, and test-notification evidence;
restore the last compatible fixture definition and keep the schedule disabled.
Do not use routine destructive cleanup. The Terraform reservation and CONFIG
object intentionally use `prevent_destroy`; pilot retirement or evidence
deletion needs a separately reviewed procedure after investigation and rollback
requirements have elapsed.
