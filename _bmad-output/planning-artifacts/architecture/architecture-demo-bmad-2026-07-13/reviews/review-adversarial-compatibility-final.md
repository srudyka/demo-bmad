# Final Adversarial Compatibility Review

## Verdict

**FAIL - the prior compatibility findings are materially closed, but one Critical and four High compliant-incompatibility holes remain.**

The revised spine now provides a real build substrate: occurrence identity is byte-stable and schema-independent; configuration publication is physically separated from the runtime ledger; the Cell Contract and Compatibility Package are normative; producer IDs and task correlation are specified; evidence reduction is commutative; exact task-definition revisions are verified; and Cell upgrades use an explicit expand/migrate/contract protocol. Those changes close the original identity, physical ownership, manifest, deduplication, ordering, task-correlation, and upgrade findings.

The remaining holes concern trust at shared ingress, atomic alert delivery, globally unique job ownership, manual-rerun identity, and asynchronous CONFIG enablement. Each permits two independently built units to obey every current AD while producing unsafe or incompatible behavior.

## Prior Finding Closure

| Prior area | Status | Closure evidence |
|---|---|---|
| Occurrence identity bytes and event-schema independence | **Closed** | AD-4 defines `occurrence/v1`, exact hash inputs, epoch-minute representation, package-owned normalization/test vectors, and Process Manager recomputation (lines 74-78). |
| Physical CONFIG/runtime-ledger ownership | **Closed** | AD-5/AD-6 move job writes to an exact S3 inbox prefix; only the materializer writes the registry and only the Process Manager writes runtime ledger tables (lines 80-90). |
| Cell Contract schema/discovery/compatibility | **Closed** | AD-15 defines canonical SSM path and required identity/resource/version/checksum fields; AD-23 makes schemas and fixtures normative (lines 155-159 and 203-207). |
| Producer namespace and deduplication key | **Closed structurally** | AD-5 requires registered producer ID and producer-unique event ID; AD-23 owns producer registry/key fixtures (lines 80-84 and 203-207). Authenticity of that claimed identity remains open as FINAL-01. |
| Schedule generation and order-independent transitions | **Closed** | AD-5 carries generation; AD-7 requires deterministic commutative reduction; AD-18 defines anchored generation cutover; AD-23 requires reducer/evaluator fixtures (lines 80-96, 173-177, 203-207). |
| Task-to-occurrence correlation and exact revision | **Closed** | AD-5 pins exact revision; AD-8 fixes attempt reservation/tags/environment; AD-9 handles early orphan events with task-ARN index (lines 80-84 and 113-123). |
| Cell/job upgrade and ownership edges | **Closed** | AD-24 defines stable Process Manager principal and expand/migrate/contract lifecycle; AD-25 assigns a single Terraform owner per integration edge (lines 209-219). |

## Remaining Critical Finding

### FINAL-01: Claimed producer identity is not bound to an authenticated ingress principal

**Severity:** Critical  
**Locations:** Diagram ingress paths (lines 35-42), AD-5 (lines 80-84), AD-11 (lines 131-135), AD-12 (lines 137-141), AD-20 (lines 185-195), AD-23 (lines 203-207), processed-event convention (line 239).

**Pair:** Any SQS evidence producer (Scheduler delivery role, Log Ingestor, ECS event capture, Deadline Scanner, replay/operator path) vs Process Manager.

**Compliant implementation A:** The producer registry assigns `producer_id = "ecs-events/v1"` to the ECS event path and `producer_id = "log-ingestor/v1"` to the Log Ingestor. All producers share the Cell ingress queue and emit schema-valid bodies.

**Compliant implementation B:** The Process Manager validates the claimed `producer_id`, `producer_event_id`, event type, and payload against the Compatibility Package. It has no specified cryptographic or transport-authenticated binding between the body claim and the AWS principal/queue path that sent it.

**Conflict:** A compromised or incorrectly implemented producer with `sqs:SendMessage` can claim another registered producer ID and event type. For example, the Log Ingestor can forge ECS zero-exit evidence for a known task ARN, the Deadline Scanner can emit an early deadline under a trusted namespace, or an operator/replay path can synthesize `LAUNCH`/terminal evidence. SQS queue policy authenticates the sender for `SendMessage`, but the architecture does not require the Process Manager to receive and verify that sender against the claimed producer/event-type allowlist. A schema-valid forged pair can satisfy correlated completion or alter state across every job in the Cell.

This is a Cell-wide data-integrity and privilege-boundary failure: registering namespaces solves collision, not authenticity.

**Required closure:** Bind each producer and allowed event types to an unforgeable ingress boundary. Use separate source queues/event buses with source-specific resource policies and Cell-owned normalizers that stamp producer identity, or sign envelopes with producer-specific KMS asymmetric/MAC keys and verify before ledger admission. If relying on SQS system attributes, specify exactly which immutable principal attribute is available through Lambda event-source mapping, its assumed-role/session normalization, and the principal-to-producer/event-type registry. Replay and operator commands must enter through a separate validated command handler that stamps identity and authorizes job/action; humans must not send arbitrary evidence envelopes. Add negative tests proving every producer principal is rejected when it claims another namespace or unauthorized event type.

## Remaining High Findings

### FINAL-02: Terminal state and occurrence-alert delivery lack an atomic outbox contract

**Severity:** High  
**Locations:** Process Manager/Ledger/AlertQueue diagram (lines 42-50), AD-6 and AD-7 (lines 86-96), AD-14 (lines 149-153), AD-19 (lines 179-183).

**Pair:** Process Manager ledger reducer vs occurrence-alert SQS publisher and Alert Router.

**Compliant implementation A:** The Process Manager transaction commits a newly accepted `FAILED`, `MISSED`, `OVERDUE`, or `AMBIGUOUS` state, then calls SQS with the required idempotency key.

**Compliant implementation B:** On retry after a crash, the reducer sees that terminal evidence has already been accepted and performs no new state transition. The Alert Router correctly processes only messages it receives.

**Conflict:** A crash after ledger commit but before `SendMessage` permanently loses the required occurrence alert. Reversing the order produces an alert for a state that may never commit. SQS standard queues also do not provide producer-side deduplication merely because the body contains an idempotency key. AD-14 requires one event but does not specify a transactional outbox, DynamoDB Stream, dispatch marker, reconciliation scan, or router deduplication store.

**Required closure:** Commit terminal state plus a unique `ALERT_OUTBOX#<occurrence>#<policy>` item in the same DynamoDB transaction. A Stream or dispatcher publishes pending outbox items, records delivery state idempotently, and reconciles stranded items. The Alert Router must deduplicate by the durable outbox ID through the notification retry horizon. Failure injection must cover crashes before/after commit and before/after publish, proving no terminal occurrence lacks an alert and duplicate notifications remain bounded.

### FINAL-03: Two application roots can claim the same job ID and shared namespace

**Severity:** High  
**Locations:** AD-1/AD-2 (lines 56-66), AD-5/AD-6 (lines 80-90), AD-15 (lines 155-159), AD-25 (lines 215-219), job-ID and CONFIG conventions (lines 231-244).

**Pair:** Job root in repository/team A vs independent job root in repository/team B within the same account/Region Cell.

**Compliant implementation A:** Team A declares lowercase job ID `prod/reporting/daily`, writes content-addressed CONFIG under `jobs/prod/reporting/daily/...`, and creates the convention-compliant launch schedule/roles/log group.

**Compliant implementation B:** Team B independently chooses the same valid job ID, uses the same deterministic resource namespace and inbox prefix, and presents different owner/repository/task configuration. Both roots satisfy the grammar, required tags, exact-prefix model, and per-job ownership statement.

**Conflict:** The architecture has no Cell-owned conditional registration/lease that makes job identity globally unique and binds it immutably to an owning repository/apply principal. One apply may fail on AWS names, overwrite or add objects in the same S3 prefix, cause the materializer to accept competing CONFIG generations, or let one team's apply role mutate the other team's job namespace. Terraform state separation does not establish resource ownership in AWS.

**Required closure:** Add a Cell-owned job registry with conditional create of `job_id -> owner repository ID, root identity, apply-role principal, environment/account/Region, lifecycle state`. Inbox bucket policy and job IAM must derive from that registered owner, not only the user-supplied job ID. Duplicate or ownership-changing claims must fail before creating schedules, roles, task definitions, or CONFIG. Define controlled transfer/tombstone/reuse procedures and test simultaneous claims and repository transfer.

### FINAL-04: Manual reruns conflict with the only defined Occurrence ID algorithm

**Severity:** High  
**Locations:** AD-4 (lines 74-78), AD-7/AD-8 (lines 92-117), AD-20/AD-21 (lines 185-195), occurrence-ID convention (line 233).

**Pair:** Operator/manual-rerun command producer vs Process Manager occurrence identity validation.

**Compliant implementation A:** The operator creates a separately authorized synthetic occurrence with `replay_of_occurrence_id`, actor, reason, reviewed Deployment Identity, and attempt zero as AD-21 requires.

**Compliant implementation B:** The Process Manager recomputes every occurrence ID using AD-4's only algorithm: identity version, job ID, schedule generation, and epoch minute. It rejects mismatches.

**Conflict:** A rerun of the same job/generation in the original epoch minute hashes to the original occurrence and violates "never overwrites the original." Choosing the current epoch minute can collide with a real scheduled occurrence, and inventing a random/synthetic time violates deterministic schedule coordinates. The architecture defines neither a synthetic-occurrence identity version nor canonical authorization-command bytes, so independent operator and Process Manager implementations cannot agree safely.

**Required closure:** Define a separate identity domain such as `occurrence/manual/v1` with canonical inputs including original occurrence ID, approved command ID, job ID, config version, and a collision-resistant immutable nonce generated by a trusted command handler. Publish test vectors and reducer rules; ensure synthetic IDs cannot collide with scheduled IDs. Bind command ID to CloudTrail-attributed actor/approval and prevent arbitrary user-supplied occurrence IDs.

### FINAL-05: New-job CONFIG acknowledgement and Scheduler enablement have no executable deployment handshake

**Severity:** High  
**Locations:** Diagram S3/materializer path (lines 27-37), AD-3 (lines 68-72), AD-5 (lines 80-84), AD-18 (lines 173-177), AD-25 (lines 215-219), CONFIG publication convention (line 244).

**Pair:** Per-job Terraform module/workflow vs asynchronous Occurrence Materializer/registry.

**Compliant implementation A:** One job module apply uploads content-addressed CONFIG and creates/enables the Scheduler launch resource. Terraform cannot atomically wait for an asynchronous materializer without a separately defined workflow phase; all resources and inputs obey the ADs.

**Compliant implementation B:** The materializer validates CONFIG on S3 notification or its clock, publishes registry acknowledgement later, and only then builds the 24-hour expectation horizon. AD-5/conventions say acknowledgement precedes production enablement, but no resource, status schema, poll API, workflow job, timeout, or second-apply protocol enforces that ordering for initial creation and non-schedule CONFIG changes.

**Conflict:** Independent workflows can enable launch before CONFIG exists in the registry/horizon, or remain disabled indefinitely while waiting on incompatible acknowledgement semantics. AD-18 defines the two-apply protocol for schedule expression/time-zone changes, not initial job creation, image/task-definition/IAM changes, or materializer rejection. A launch during this gap produces no usable CONFIG and can become a false failure or unauthorized fallback.

**Required closure:** Define a machine-enforced publish/ack/materialize/enable state machine for every new or changed CONFIG. The first apply must create CONFIG and a disabled launch; a protected workflow waits on a normative acknowledgement record containing config hash, contract version, generation, validation result, and horizon watermark; only a second reviewed apply or Cell-owned activation API may enable the exact generation. Specify timeout/rejection/rollback behavior and prohibit Scheduler enablement through Terraform preconditions/policy until acknowledgement is verified.

## Gate Result

The requested prior areas are closed at the architecture-contract level: occurrence identity, physical data ownership, Cell Contract, producer namespace structure, task correlation, and Cell upgrades are now specified well enough for independent implementations. The gate remains failed because producer authenticity is still Critical, and alert atomicity, global job ownership, manual-rerun identity, and asynchronous enablement remain High. Close FINAL-01 through FINAL-05 and rerun this adversarial compatibility gate before parallel module/runtime implementation.

