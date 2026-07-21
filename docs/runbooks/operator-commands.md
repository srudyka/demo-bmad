# Operator commands

Operator access is a short-lived, MFA-protected IAM session with the Cell
permissions boundary. The role can invoke only the private command-handler
Lambda. It cannot assume workload roles, pass roles, run tasks, write the
ledger, access configuration objects, or send directly to the command queue.

The private invocation broker must provide the authenticated actor, session,
Cell, account, and Region context. The command handler rejects requests without
that context and resolves occurrence/configuration/deployment identities from
the Cell ledger. Callers may submit only a job, scheduled time, reason, approval
reference, and optional command type; all command and occurrence identities are
handler-generated.

Replay, disable, recover, and break-glass actions require explicit compensation
acknowledgement and independent approval. Break-glass sessions are time-bound,
MFA-protected, tagged, alerted, and require a post-incident review. Operators
should quarantine the failed queue record and investigate the sanitized
rejection code before retrying; no rejected request creates evidence or a task
side effect.

Rollback is to disable the operator role and command-handler Lambda function,
leaving the encrypted queue and DLQ retained for investigation. Restore access
only after approval and validation of the runbook steps.
