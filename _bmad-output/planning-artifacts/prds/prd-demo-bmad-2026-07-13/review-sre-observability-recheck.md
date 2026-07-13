# SRE and Observability Closure Review

## Verdict

**PASS with no remaining critical or high SRE/observability findings.** The revised PRD closes the prior production blockers as testable product requirements. Architecture still must select and prove the concrete occurrence tracker and `RunTask` response detector, but those are now explicit implementation obligations with production gates rather than silent gaps in the PRD.

## Closure Matrix

### C-1: Aggregate success count could not prove per-occurrence completion — Closed

**Revised locations:** FR-6 (`prd.md` lines 136-144); FR-14 and FR-17 (`prd.md` lines 215-250); NFR-9 (`prd.md` line 373); MVP scope (`prd.md` line 397); Initial Completion Detection Pattern (`addendum.md` lines 43-49)

The revised contract requires a unique Occurrence ID for every Expected Occurrence, propagates it to the job and observability path, requires durable occurrence state, and explicitly prevents late, duplicate, retry, or adjacent-window signals from silently satisfying the wrong occurrence. It also rejects uncorrelated log markers and time-window counts as production proof. The addendum no longer prescribes metric filters as the sole production mechanism.

The acceptance matrix now covers missing invocation, wrong Occurrence ID, delayed prior-run completion, duplicate completion, retries, consecutive windows, and overdue execution. FR-28 adds a five-minute detection bound and requires zero false alerts over at least 20 accelerated successful windows.

### C-2: `RunTask` response failures had no required detector — Closed

**Revised locations:** FR-16 (`prd.md` lines 231-238); FR-17 (`prd.md` lines 240-250); FR-28 (`prd.md` lines 348-356); Risk table (`prd.md` line 477)

FR-16 now explicitly requires evidence that the platform detects an HTTP-200 `RunTask` response with a non-empty `failures` array when no ECS task exists to emit lifecycle events. FR-17 adds `RunTask` failure to the occurrence-aware pilot matrix, and FR-28 makes response-path failure injection a production-readiness gate with bounded detection time. This is sufficient PRD closure; architecture must still name and validate the actual evidence source before implementation is accepted.

### H-1: Schedule semantics were underspecified — Closed

**Revised location:** FR-6 (`prd.md` lines 136-144)

The job contract now declares supported expression type, flexible-window behavior, time-zone and daylight-saving semantics, canonical occurrence, and completion deadline. Flexible windows are disabled by default, providing a safe baseline for occurrence tracking.

### H-2: Unsafe overlap was documented but not gated — Closed

**Revised location:** FR-8 (`prd.md` lines 154-161)

An overlap-unsafe production job cannot deploy without tested application idempotency or locking, and cadence alone is explicitly rejected as proof of overlap prevention.

### H-3: Alarm quality had no measurable acceptance gate — Closed

**Revised locations:** FR-17 and FR-18 (`prd.md` lines 240-258); FR-28 (`prd.md` lines 348-356)

Alerts are now occurrence-aware and include occurrence state and identity. Failure injection must detect every required failure within five minutes of the observable failure or deadline, while at least 20 accelerated successful windows must produce zero false alerts. These criteria are adequate for the MVP gate.

### H-4: ECS failure telemetry was not sufficiently attributable — Closed

**Revised locations:** FR-14 (`prd.md` lines 215-221); FR-17 and FR-18 (`prd.md` lines 240-258); NFR-9 (`prd.md` line 373)

Signals and alerts now carry Occurrence ID, and the occurrence record requires job, schedule, start, completion, status, exit code, and error reason fields. Durable, idempotent state prevents duplicate signals from silently overwriting terminal outcomes. Together with the existing Deployment Identity requirements, this provides an adequate attribution contract for downstream architecture.

### H-5: Pilot evidence lacked a quantitative reliability matrix — Closed

**Revised locations:** FR-17 (`prd.md` lines 240-250); FR-28 (`prd.md` lines 348-356)

The pilot matrix now spans the critical failure and ambiguity paths, while FR-28 supplies objective false-positive and detection-latency gates. Production readiness cannot be claimed without the evidence.

## Residual Non-Blocking Items

These do not rise to critical or high severity and can be resolved in architecture, the Runbook template, or the Production Readiness Checklist:

- Define alarm severity, repeat escalation, recovery notifications, maintenance suppression, and the response when the observability pipeline itself fails.
- Specify the concrete `RunTask.failures` evidence source and occurrence-state mechanism, including their availability, IAM, retention, cost, and failure behavior.
- Ensure conformance tests include at least one real-time cadence and relevant time-zone/DST boundary in addition to accelerated windows.
- Carry task ARN, task-definition revision, stop code/reason, essential-container identity, and Deployment Identity into the concrete lifecycle-event schema.

## Gate Recommendation

The SRE/observability reviewer gate may close. Preserve FR-16, FR-17, NFR-9, and FR-28 as mandatory architecture and implementation acceptance criteria; do not downgrade occurrence-aware production tracking to the non-production metric-filter fallback.
