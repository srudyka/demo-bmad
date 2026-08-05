# Currency and Reality Review

## Scope and Date

- Artifact: `ARCHITECTURE-SPINE.md`
- Review date: 2026-07-13
- Lens: committed technologies, exact versions, live defaults, and asserted AWS/GitHub/Terraform behavior
- Sources: official AWS, GitHub, and HashiCorp documentation and release records

## Verdict

**Changes required.** The named Terraform, AWS provider, and Lambda versions exist and are current, and most low-level AWS claims are accurate. The architecture nevertheless has three service-semantics correctness gaps and one incompatible Terraform floor that can break occurrence detection, alerting, or state locking. Three additional assumptions need explicit compatibility gates rather than adopted status.

## Findings

### 1. Critical: Paired schedules do not provide ordered `EXPECTATION` then `LAUNCH` evidence

**Architecture claim:** AD-3 creates separate `EXPECTATION` and `LAUNCH` schedules with the same expression and sends both to a standard SQS ingress queue. AD-7 models creation through `EXPECTED` before `STARTED`.

**Reality check:** EventBridge Scheduler has 60-second invocation precision, so schedules set for the same minute can invoke anywhere within that minute. Scheduler delivery is at least once. SQS standard queues provide only best-effort ordering and can deliver duplicates. There is no AWS guarantee that the `EXPECTATION` message is sent or processed before `LAUNCH`. See [EventBridge Scheduler schedule precision](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html), [Scheduler delivery behavior](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html), and [SQS standard queue ordering](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues.html).

**Impact:** A valid `LAUNCH` can reach the Process Manager first. The spine does not define whether it creates the occurrence, waits, rejects the event, or launches the task. A one-time scan or retry can therefore miss a run or produce an undefined state even when both AWS services behave correctly.

**Required change:** Make both arrival orders and duplicate arrival explicit state-machine inputs. Either converge `LAUNCH`-first and `EXPECTATION`-first processing to the same occurrence and launch decision, or remove the cross-schedule ordering dependency. Add contract tests for both orders, delayed messages, duplicates, one missing member of the pair, and overlapping retries. Do not treat matched expressions as an ordering guarantee.

### 2. Critical: A minute-cadence GSI query can permanently miss a deadline

**Architecture claim:** AD-10 says a deadline scanner queries a deadline-bucket index every minute and emits `DEADLINE_REACHED` evidence.

**Reality check:** DynamoDB global secondary indexes are updated asynchronously and support eventually consistent reads only. AWS explicitly requires applications to handle stale GSI results and notes that propagation delays can be longer during failures. See [DynamoDB GSI synchronization](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html) and [DynamoDB read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html).

**Impact:** If the scanner queries a bucket before a newly written deadline entry appears in the GSI and never revisits that bucket, the occurrence can remain nonterminal indefinitely. This defeats the platform's missed/overdue guarantee.

**Required change:** Specify an overlap and reconciliation algorithm: rescan a bounded lookback window, retain a durable watermark, verify candidates against the base table, and continue reconciling nonterminal occurrences until safely beyond the maximum lateness horizon. Alarm on scanner lag, throttling, and unreconciled overdue items. Test delayed GSI propagation and scanner interruption.

### 3. Critical: Alarm state changes cannot deliver one alert per failed occurrence

**Architecture claim:** AD-14 says per-job CloudWatch alarm state changes invoke the Alert Router, which enriches the alert with the current occurrence.

**Reality check:** Except for Auto Scaling actions, CloudWatch alarm actions run only on state transitions and are not repeated while the condition persists. EventBridge likewise receives an alarm event when alarm state changes. See [CloudWatch alarm action behavior](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-actions.html) and [CloudWatch alarm events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-and-eventbridge.html).

**Impact:** Two or more consecutive failed occurrences can leave a per-job alarm continuously in `ALARM`. Only the first transition invokes the router, so later failed occurrence IDs may never produce an enriched notification. A low-frequency job can also retain stale alarm context across schedule windows depending on missing-data treatment.

**Required change:** Separate per-occurrence notification from aggregate alarm health. Emit an idempotent alert event from the occurrence-state transition path for every newly accepted `FAILED`, `MISSED`, `OVERDUE`, or `AMBIGUOUS` occurrence, and use CloudWatch alarms for sustained/aggregate conditions or as a secondary route. If alarms remain the primary trigger, prove an explicit OK reset and missing-data policy between every supported schedule window. Test consecutive failures without an intervening success.

### 4. High: The Terraform `>= 1.5` floor cannot support required S3 native locking

**Architecture claim:** AD-15 requires S3 backend `use_lockfile = true`, while Stack and A-5 retain a Terraform compatibility floor of `>= 1.5`.

**Reality check:** S3 native state locking was added in Terraform 1.10.0. Terraform 1.5 through 1.9 cannot parse or use this backend capability. See the [Terraform 1.10 release notes](https://github.com/hashicorp/terraform/releases/tag/v1.10.0) and current [S3 backend locking documentation](https://developer.hashicorp.com/terraform/language/backend/s3).

**Impact:** A consumer satisfying the stated floor can fail at `terraform init` before module validation or planning.

**Required change:** State separate compatibility surfaces if needed: the child module may retain a lower language floor only if proven, but all root modules and automation using native S3 lockfiles require Terraform `>= 1.10`. Otherwise, retain the older DynamoDB lock path for pre-1.10 roots. The tested matrix must include the actual minimum, not only the authoring seed.

### 5. Medium: Exact seeds are current, but managed runtime mutability is missing from the supply-chain model

**Architecture claim:** Stack names Terraform 1.15.8, AWS provider 6.54.0, Lambda Python 3.14, and Fargate `LATEST`; AD-17 describes an immutable supply chain.

**Reality check:** Terraform 1.15.8 is a current stable release, AWS provider 6.54.0 was released July 8, 2026, and Lambda Python 3.14 is supported through June 2029. These are valid today. However, exact CLI/provider patches will age quickly and already belong in lock files and the tested matrix. Fargate `LATEST` currently resolves to Linux platform 1.4.0, but AWS can move the alias, and every new task receives the latest revision of the selected platform version. Lambda managed runtimes also update automatically by default. See [Terraform releases](https://releases.hashicorp.com/terraform/), [AWS provider 6.54.0 release](https://github.com/hashicorp/terraform-provider-aws/releases/tag/v6.54.0), [Lambda Python runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html), [Lambda runtime update behavior](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html), and [Fargate platform versions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/platform-fargate.html).

**Impact:** The spine can become stale even while code and lock files are correct, and rollback cannot reproduce the exact managed Fargate or Lambda runtime revision implied by "immutable."

**Required change:** Replace exact CLI/provider patches in the spine with feature-derived minimums plus a dated "validated with" matrix owned by code/lock files. Keep Python 3.14 only with an upgrade/deprecation policy and packaged, pinned application dependencies. Treat Fargate and Lambda runtime patching as explicit managed-runtime exceptions: record the observed platform/runtime in deployment evidence, test after AWS runtime updates, and document whether `LATEST` is a security-first choice or whether a named platform line is required.

### 6. Medium: GitHub OIDC enforcement is supported only under unverified repository and plan conditions

**Architecture claim:** AD-16 is marked adopted and requires an exact custom `sub` containing immutable repository identity, deployment Environment, and `job_workflow_ref`, plus a protected Environment. A-3 still assumes the organization can configure these features.

**Reality check:** GitHub supports subject customization including `job_workflow_ref`, but AWS does not support arbitrary custom OIDC claims; the required values must be encoded into `sub`. An organization subject template does not affect a repository until that repository explicitly opts in. Protected Environment reviewer and no-bypass behavior depends on repository visibility and GitHub plan. See [GitHub OIDC subject customization](https://docs.github.com/en/actions/reference/security/oidc), [GitHub OIDC for AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws), and [GitHub Environment protection availability](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

**Impact:** A correctly written IAM trust policy can deny all deployments if repositories are not opted into the custom template, while an unsupported GitHub plan can silently invalidate the assumed human approval model.

**Required change:** Keep AD-16 conditional until a live pilot repository proves its token's exact `aud` and `sub`, repository-template opt-in, protected Environment reviewers, self-review prevention, branch/tag restrictions, and disabled admin bypass. Define the fallback approval boundary before production if any feature is unavailable.

### 7. Medium: SQS-to-Lambda settings needed for the asserted replay behavior are unspecified

**Architecture claim:** AD-11 selects SQS standard ingress, Lambda partial-batch responses, and a 14-day redrive DLQ.

**Reality check:** The selected services support this pattern, but Lambda requires the function timeout to be no greater than queue visibility timeout, recommends a visibility timeout of at least six times the function timeout, and recommends `maxReceiveCount` of at least five. SQS/Lambda processing remains at least once. See [Lambda SQS event-source configuration](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html), [Lambda SQS delivery behavior](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html), and [partial-batch behavior](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html).

**Impact:** Without binding these values, slow or throttled processing can create avoidable duplicates, premature DLQ moves, or concurrent processing after visibility expires.

**Required change:** Add an invariant tying Lambda timeout, queue visibility timeout, batch size/window, partial-batch response, concurrency, and `maxReceiveCount` together. Make the exact defaults configurable within tested bounds and cover timeout, throttle, partial failure, and poison-message cases.

## Verified Claims

| Architecture item | Status | Reality check |
| --- | --- | --- |
| Terraform CLI 1.15.8 | Current | Present in the official stable release index on 2026-07-13. |
| Terraform AWS provider 6.54.0 | Current | Official release dated 2026-07-08. |
| Lambda Python 3.14 | Supported | Managed `python3.14` runtime on Amazon Linux 2023; deprecation scheduled for 2029-06-30. |
| Fargate `LATEST` | Supported but moving | Linux `LATEST` is 1.4.0 today; new tasks receive the latest revision. |
| Scheduler `<aws.scheduler.scheduled-time>` | Supported | Official Scheduler context attribute; suitable as canonical scheduled-time input. |
| Scheduler SQS DLQ | Supported | Must be a standard SQS queue; FIFO is not supported as a Scheduler DLQ. |
| Scheduler retry bounds | Supported | Exponential backoff; event age 60–86,400 seconds and retry attempts 0–185. |
| ECS `RunTask` 64-character SHA-256 client token | Supported | Client token supports up to 64 printable ASCII characters; lowercase hex is valid. |
| ECS task-state events described as durable | Correct | Direct ECS service events have durable delivery to EventBridge. |
| SQS 14-day retention | Correct maximum | 1,209,600 seconds is the current maximum retention. |
| DynamoDB PITR 35 days | Correct maximum | Recovery window is configurable from 1 through 35 days. |
| CloudWatch Logs subscription duplicates | Handled by design | Subscriptions are at least once and can duplicate; AD-6/AD-7 idempotency is necessary. |
| Provider lock files and `-lockfile=readonly` | Supported | Correct mechanism for provider selection; it does not pin remote modules. |

## Gate Decision

Do not approve the spine for implementation until findings 1 through 4 are resolved in the architecture itself. Findings 5 through 7 may remain explicit, owned assumptions only if the pilot test matrix and production gates name their resolution evidence.
