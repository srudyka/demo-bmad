# Operator commands

Operator access is a short-lived, MFA-protected IAM session with the Cell
permissions boundary. The role can invoke only the private command-handler
Lambda. It cannot assume workload roles, pass roles, run tasks, write the
ledger, access configuration objects, or send directly to the command queue.

The private invocation broker must provide the authenticated actor, session,
Cell, account, and Region context. The command handler rejects requests without
that context and resolves occurrence/configuration/deployment identities from
the Cell ledger. For a non-production `RERUN`, callers may submit only the
canonical job ID, original occurrence selector, reason, expected duplicate
effects, verification plan, compensation acknowledgement, and approval
reference. The handler resolves CONFIG, Deployment Identity, task revision,
network, roles, Cell, account, Region, and all command/occurrence identities
from authoritative records. Callers cannot submit IDs, ARNs, task definitions,
network settings, overrides, or evidence.

The Job Owner and independent Platform approver must authorize the same bounded
request through the short-lived path. Reruns are blocked for running,
nonterminal, ambiguous, stale, or production occurrences. A rerun does not
edit the EventBridge schedule and is not an automatic retry; unresolved ECS
launch ambiguity requires a new approved command.

Before requesting one, record the expected duplicate side effects, the
structured success evidence to verify, and the application compensation owner.
Afterward, verify one structured success record and zero essential-container
exit, then retain the synthetic occurrence, original-occurrence link, command,
approval, and Deployment Identity as the audit trail.

Replay, disable, recover, and break-glass actions require explicit compensation
acknowledgement and independent approval. Break-glass sessions are time-bound,
MFA-protected, tagged, alerted, and require a post-incident review. Operators
should quarantine the failed queue record and investigate the sanitized
rejection code before retrying; no rejected request creates evidence or a task
side effect.

Rollback is to disable the operator role and command-handler Lambda function,
leaving the encrypted queue and DLQ retained for investigation. Restore access
only after approval and validation of the runbook steps.
