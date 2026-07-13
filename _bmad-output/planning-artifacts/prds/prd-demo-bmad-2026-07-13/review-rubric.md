# PRD Quality Review — ECS Scheduled Jobs Platform Service

## Overall verdict

This is a coherent, unusually operational PRD whose product thesis, ownership model, production controls, and MVP boundaries are strong enough to guide architecture and delivery planning. It is not yet an unconditional green light for the production pilot: the core per-job missed-run promise rests on a provisional completion-detection design whose supported schedule semantics and proof threshold are not defined tightly enough, and a few governance and delivery-boundary terms would produce inconsistent stories if left to implementation teams.

## Decision-readiness — adequate

The PRD states real decisions rather than smoothing them away: EventBridge Scheduler is the MVP baseline (§5.2), maximum runtime is detection-only (FR-8), overlap prevention remains an application responsibility (§7.2), and SQS DLQ support is deferred (§7.2). It also names what each decision gives up, especially around duplicate delivery, forced cancellation, and workflow orchestration.

The eight Open Questions are genuine prerequisites with owners and resolution gates rather than disguised undecided scope. However, OQ-3 is central to the product's observability thesis, not merely a pilot configuration detail: the proposed log metric-filter pattern is simultaneously the selected MVP mechanism and still unproven for the supported schedule windows. Architecture may proceed, but pilot acceptance should be explicitly conditional on a bounded completion-detection contract and a documented fallback if that mechanism fails validation.

### Findings

- **high** Core completion-detection decision lacks a bounded contract (§5.4 FR-17, §11 OQ-3, addendum “Initial Completion Detection Pattern”) — The PRD promises detection of “a missing invocation” or late completion for each production job, but does not define supported schedule frequencies, how one success marker is correlated to one scheduled run, how retries or duplicate executions affect the signal, or what false-positive/false-negative threshold constitutes acceptance. The addendum itself notes late logs, retries, duplicates, missing data, and consecutive windows as unresolved. This leaves the product's defining reliability promise open to incompatible implementations. *Fix:* Define an MVP completion-detection support envelope and acceptance contract: minimum schedule spacing, required unique run/window identity or explicitly aggregated semantics, deadline/evaluation-window rules, CloudWatch missing-data treatment, retry/duplicate behavior, measurable false-alarm and missed-detection thresholds, and the fallback scope if the log-metric approach cannot meet them.
- **medium** Security-review trigger is not defined (§5.5 FR-23, §8) — “Qualifying IAM or networking changes require Security review” is repeated, but no rule identifies a qualifying change. Teams cannot implement a deterministic approval gate or know when Security is mandatory. *Fix:* Define the trigger set or assign a named policy artifact as the source of truth, covering at least new wildcard exceptions, OIDC trust changes, cross-account access, public-routing changes, and security-group egress expansion.

## Substance over theater — strong

The document earns its length. The four-plane observability model (§5.4), exact IAM responsibility split (FR-10 through FR-13), deployment identity (Glossary and FR-24), rollback principles (§10), and counter-metrics (§9.3) are specific to scheduled ECS operations rather than generic platform boilerplate. The small role set drives concrete ownership and review requirements, and the document appropriately avoids persona and journey theater for an internal infrastructure capability.

The NFRs mostly reinforce product-specific, verifiable controls instead of repeating generic aspirations. Where the PRD uses terms such as “least privilege” and “actionable,” it generally supplies consequences in the FRs or production gates that make those terms operational.

### Findings

- **low** “Minimally scoped” networking remains partly rhetorical (§5.3 FR-13, §6.1 NFR-3) — Public IP prohibition is concrete, but “minimally scoped security groups” and “documented egress” do not establish whether unrestricted egress is prohibited, exception-controlled, or acceptable. *Fix:* State the egress baseline and exception rule, or explicitly delegate it to an identified networking standard.

## Strategic coherence — strong

The thesis is clear: teams declare job behavior while the Platform Service standardizes the surrounding security, delivery, observability, and operating controls (§1). The feature groups consistently serve that thesis, and the MVP is a platform-pattern MVP rather than an arbitrary collection of AWS resources.

Success metrics validate the thesis through setup time, new-job adoption, control coverage, operability, and drift reduction (§9.1–§9.2). The four counter-metrics directly test whether stronger controls create bypasses, alert fatigue, approval delay, or unstable upgrades (§9.3), which prevents adoption alone from being treated as success.

### Findings

- **medium** Several metrics lack measurement protocols (§9 SM-1, SM-5, SM-C1 through SM-C4) — “Ready inputs,” the measurement cohort and window, review-finding normalization, what counts as an exception, and thresholds for unacceptable alert noise or deployment delay are undefined. This permits success to be reported inconsistently after the pilot. *Fix:* Add metric owner, data source, denominator/cohort, measurement cadence, and pilot acceptance threshold for each primary and counter-metric; OQ-8 should resolve the baseline and measurement method, not only the baseline values.

## Done-ness clarity — thin

The PRD is stronger than most infrastructure PRDs here: every FR has explicit “Consequences (testable),” policy gates require positive and negative fixtures, and pilot failure tests cover multiple lifecycle paths. Most requirements can be decomposed into stories without inventing acceptance criteria.

The dimension is nevertheless thin because the most important reliability requirement, FR-17, is not yet testably bounded, and several downstream controls use terms whose implementation outcome can vary materially. The production-readiness checklist cannot prove “all four failure planes” until the per-job attribution and completion-window semantics are made concrete.

### Findings

- **medium** Schedule-delivery alarms lack a per-job attribution contract (§5.4 FR-15, FR-18; addendum “Research-Backed Architecture Inputs”) — FR-15 requires alarms for target errors, throttling, and dropped invocations and says an alarm identifies the “schedule group or job context,” while the addendum notes native Scheduler metrics are best-effort and grouped by Schedule Group rather than individual schedule. “Or” permits an aggregate alarm that cannot satisfy FR-18's job-specific alert context. *Fix:* Require either per-job metric isolation/correlation, a deterministic mapping from an aggregate alarm to affected jobs, or explicitly limit the per-job guarantee and define the operator workflow for aggregate signals.
- **medium** Supported workflow artifact is ambiguous (§5.5 FR-20, FR-25; §7.1; addendum “Initial Distribution Pattern”) — The PRD alternates between a supported “reusable workflow contract,” a “delivery pattern,” and “reusable or example GitHub Actions workflows.” Those are different products with different versioning, enforcement, and support obligations. *Fix:* Choose the MVP artifact contract: centrally maintained reusable workflow, consumer-owned example/template, or both with a clear normative source and compatibility policy.
- **medium** Environment policy gates are not fully deterministic (§5.5 FR-21, §10 rollout step 5) — “Obvious secret exposure,” “public-subnet configurations detected by policy,” “missing alarms,” and “IAM wildcards” do not identify the scanner/policy contract, supported exceptions, or what happens when static analysis cannot prove compliance from supplied infrastructure. *Fix:* Define the required policy outcomes and evidence interface, including unknown/unverifiable results, rather than requiring a particular tool; connect each outcome to the production-readiness evidence.

## Scope honesty — strong

The MVP and non-goals are explicit and credible (§7). Notably, the PRD does not imply that the platform prevents overlaps, creates secrets, replaces an orchestrator, centrally manages every account, or migrates all existing jobs. Runtime cancellation and DLQ behavior are deferred with reasons, and Existing Infrastructure is clearly separated from module-owned resources.

Assumptions are visibly tagged and indexed, and unresolved prerequisites have owners and “resolve before” gates. The open-item density is acceptable for a draft entering architecture because the items are mostly environment selection, compatibility validation, and pilot onboarding rather than concealed product scope.

### Findings

- **low** Optional security-group creation slightly blurs the dependency boundary (§5.3 FR-13) — Existing Infrastructure defines security groups as consumer-managed, while FR-13 lets the module create one when enabled. The behavior is reasonable, but it expands module ownership into networking lifecycle without stating whether it is an MVP commitment or convenience. *Fix:* List optional security-group creation explicitly in MVP scope and document its lifecycle boundary, or defer it and require supplied groups in version one.

## Downstream usability — adequate

The PRD is explicitly intended to feed architecture and delivery (§0), and its capability-oriented shape, stable FR IDs, Glossary, named roles, testable consequences, risks, and linked success metrics make source extraction practical. FR-1 through FR-28 and NFR-1 through NFR-16 are contiguous and unique; the cross-references inspected resolve.

Architecture can cleanly extract IAM, networking, delivery, observability, and lifecycle concerns. Story creation should wait for the high-severity FR-17 contract issue and the workflow-artifact decision because both affect epic boundaries and acceptance tests.

### Findings

- **medium** “Deployment Identity” mixes module-owned and externally sourced evidence without assigning the assembly boundary (Glossary, FR-4, FR-24) — The identity includes source revision, workflow revision, image digest, account/environment, and task-definition revision, but FR-4 only exposes components “created by the module.” It is unclear which artifact records the complete identity, how runtime task/image evidence is joined to CI metadata, and how on-call retrieves it. *Fix:* Require a canonical deployment record or retrieval contract and assign which component assembles and retains it, while leaving mechanism selection to architecture.

## Shape fit — strong

The capability-spec shape fits a high-stakes internal platform standard. User journeys are deliberately downscaled and replaced by concise operator workflows and jobs-to-be-done (§3), while the requirements emphasize control surfaces, operating evidence, ownership, and release lifecycle. That is the correct shape for a Terraform-plus-delivery product with a small number of operator roles.

The PRD also has the rigor expected of a chain-top artifact: glossary, stable requirements, explicit non-goals, assumptions, risks, measurable outcomes, and operational handoffs. It is detailed without being forced into a consumer-product narrative.

## Mechanical notes

- FR IDs are contiguous and unique from FR-1 through FR-28; NFR IDs are contiguous and unique from NFR-1 through NFR-16.
- Success metric IDs SM-1 through SM-8 and counter-metric IDs SM-C1 through SM-C4 are unique and internally consistent.
- All twelve inline assumptions A1 through A12 appear in the Assumptions Index, and every index entry has an inline source location.
- No `[NOTE FOR PM]` callouts remain. The eight Open Questions all name an owner and a resolution gate.
- Glossary usage is generally stable. “EventBridge Scheduler,” “Scheduled Job,” “Platform Service,” “Terraform Module,” “Deployment Identity,” “Job Owner,” and “Platform Owner” are consistently capitalized as defined terms.
- The addendum's example module source contains placeholder organization and repository names; it is appropriately an implementation example, and OQ-5 prevents it from being mistaken for a final publishing location.
