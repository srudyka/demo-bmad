# Blocker-Only Final Architecture Review

## Verdict

**FAIL - one Critical cross-job evidence-forgery gap remains.** The launch replay cutoff, single-attempt reducer, occurrence transactional outbox, manual-rerun identity, CONFIG lifecycle, job registration, activation handshake, Terraform floor, and network contract now close the previous blockers. The deterministic spine linter also passes with zero findings. However, authenticated ingress is bound only to producer-class source queues, not to the registered job/resource instance that originated the evidence.

## Critical Finding

### C-1: A registered job can forge another job's launch or completion evidence

**Locations:** AD-5 (lines 81-85), AD-9 (lines 120-124), AD-27 (lines 228-232), AD-28 (lines 234-238), AD-29 (lines 240-244)

**Problem:** AD-27 creates distinct source queues for producer classes such as Scheduler and log ingestion, and AD-5 derives `producer_id` from the source queue ARN. That authenticates the adapter class, but not the job or concrete AWS resource within that class. `job_id`, `schedule_generation`, `occurrence_id`, task ARN, and other correlation fields still arrive in the payload.

All job schedules sharing the Scheduler source queue are sent by the same AWS service principal. A job-owned schedule can therefore submit victim job coordinates unless the Cell binds the exact originating schedule ARN to the registered job independently of caller-controlled target input. Likewise, the shared log ingestor is trusted for every job, but the spine does not require it to derive job/task identity from the CloudWatch log group and stream; an application can place another job's IDs and task ARN in its log text. AD-9 then has enough claimed correlation fields to accept a false business-success marker when the victim task has a zero exit.

AD-28 secures registration, namespace ownership, inbox policy, and IAM generation, but it does not bind each runtime evidence source to that ownership record. A conforming implementation could trust payload identity, trust an unsigned Scheduler context field, allocate a source queue per job, or validate source-resource mappings. Those choices have materially different cross-job isolation.

**Impact:** One application team can launch a future occurrence of another team's task, force an occurrence into `AMBIGUOUS`, or falsely satisfy another job's completion contract. This violates least-privilege isolation and undermines the platform's core occurrence ledger.

**Required closure:** Make job/resource origin Cell-derived and non-forgeable for every evidence type.

- Bind each Scheduler source to the registered `job_id`, ownership generation, exact schedule ARN, and schedule generation through a Cell-controlled mapping. Use a per-job queue/policy or another transport where the normalizer can authenticate the concrete source independently of message-body claims; never trust a schedule to self-report its own ARN or job ID.
- Make the log ingestor derive job and task identity from the subscribed log-group ARN and log-stream/task identity, validate both against CONFIG and the task-ARN ledger index, and treat identifiers in application log text only as assertions to compare, not authority.
- Apply equivalent source-resource derivation to ECS capture, materializer, deadline, replay, and command evidence, with the registered ownership generation in the canonical envelope.
- Add negative Compatibility Package fixtures proving one registered job, schedule, log group, task, replay command, or producer-class queue cannot emit accepted evidence for another job.

## Prior Blocker Closure

- **Launch replay cutoff:** AD-8 prevents `RunTask` after the 24-hour client-token window and fails unresolved launch state to `AMBIGUOUS`.
- **Transactional alerting:** AD-14 commits terminal failure and outbox state atomically and reconciles Stream delivery.
- **Manual identity:** AD-21 makes the command handler generate manual occurrence identity and prohibits user-supplied occurrence IDs.
- **Registration and activation:** AD-28 binds global job ownership; AD-29 requires acknowledged CONFIG and horizon evidence before a separately reviewed enablement plan.

No other Critical or High finding remains in this blocker-only pass.
