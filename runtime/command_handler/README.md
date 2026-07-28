# Command Handler

The handler is the only entry point for the short-lived operator command path.
For `RERUN`, it validates the Job Owner request and independent Platform
approval, resolves the terminal original occurrence and reviewed Cell CONFIG,
and generates the UUIDv7 command ID plus `occurrence/manual/v1` identity. The
requester cannot provide occurrence IDs, task ARNs, task definitions, roles,
networking, overrides, or evidence.

Rerun requests require bounded duplicate-effects and verification plans plus
compensation acknowledgement. They are non-production only and fail closed on
nonterminal or ambiguous originals, stale bindings, and mismatched Cell or
Deployment Identity. The handler writes the durable authorization record and
publishes the canonical command; it never writes the occurrence ledger or calls
ECS `RunTask`.
