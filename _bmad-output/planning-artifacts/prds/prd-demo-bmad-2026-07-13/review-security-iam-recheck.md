# AWS Security and IAM Closure Review

## Verdict

**CONDITIONAL FAIL - the prior Critical finding is closed, but two High findings remain before the PRD is ready to authorize production implementation.**

The revision materially improves the security contract. It now makes production deployment fail closed when the protected GitHub path cannot be enforced, isolates untrusted PR execution, binds deployment targets through an immutable manifest and runtime identity checks, requires secure per-account/environment Terraform state, analyzes effective application permissions, constrains Scheduler/ECS role trust and `iam:PassRole`, and requires immutable workflow/module references. Those changes close the original critical workflow-bypass gap and most original High findings.

## Closure Against Prior Critical/High Findings

| Prior finding | Recheck status | Evidence |
|---|---|---|
| SEC-01: Deployment credential not bound to production gates | **Closed at Critical/High** | FR-22 requires a protected deployment path after mandatory checks and explicitly denies production authorization when GitHub cannot enforce it (lines 289-297); the addendum records OIDC's reusable-workflow limitation and the required procedural boundary (lines 65-68). |
| SEC-02: No-wildcard check misses broad effective IAM | **Closed at Critical/High** | FR-11 now requires effective-policy analysis for actions, resources, conditions, privilege escalation, and cross-account access, with controlled customer-managed policy use (lines 185-192). |
| SEC-03: `PassRole` and service trust under-specified | **Partially closed; IAM-RECHECK-01 remains High** | Scheduler/ECS trust and runtime `PassRole` conditions are now explicit (FR-10, lines 175-183), but CI deployment-role privilege-escalation boundaries remain unspecified. |
| SEC-04: State and PR plan exposure | **Closed at Critical/High** | FR-20 denies AWS/state credentials to untrusted PR code (line 279); FR-23 requires encrypted, locked, account/environment-isolated state and restricted plan output (lines 299-307). |
| SEC-05: Multi-account target binding | **Closed at Critical/High** | FR-22 requires an immutable target manifest, forbids arbitrary production role input, and verifies account and Region (line 296); FR-23 isolates state by the same target boundary (line 307). |
| SEC-06: Supply-chain pinning incomplete | **Partially closed; IAM-RECHECK-02 remains High** | FR-25 requires full commit SHAs and immutable module references (lines 317-325), but the addendum still supplies a mutable tag example and provider locking is not a production gate. |
| SEC-07: OIDC trust under-specified | **Closed at Critical/High** | FR-22 requires rejection of unauthorized repository/ref/Environment subjects and a protected production path (lines 289-297); the addendum requires audience, subject, and active immutable repository identity handling (lines 65-68). |

## Remaining High Findings

### IAM-RECHECK-01: CI plan/apply roles can still be implemented with privilege-escalation authority

**Severity:** High  
**Locations:** PRD FR-11 (lines 185-192), FR-22 (lines 289-297), FR-23 (lines 299-307), NFR-1 and NFR-4 (lines 362-365).

**Finding:** The revision constrains application task policies and runtime role passing, but it never makes the effective permissions of CI plan/apply roles testable. The apply role must create and update IAM roles and policies; without explicit boundaries, a conforming implementation can grant it permission to modify its own trust or policy, change the GitHub OIDC provider, remove a permissions boundary, pass unrelated roles, or create a new privileged role. "Account- and Environment-scoped" and "minimal AWS permissions" do not prevent this privilege-escalation path. Effective-policy analysis in FR-11 is scoped to the application task role, not CI identities.

**Required closure:** Extend FR-22 or FR-23 to require separate least-privilege plan and apply permission matrices and automated effective-policy validation. The production identities must not modify their own role/trust/policies, the OIDC provider, protected backend controls, approval controls, or permissions boundaries; must pass only exact module-created roles with `iam:PassedToService`; and must create/update IAM roles only under a mandatory platform permissions boundary and approved naming/path scope. Add negative tests for self-policy modification, boundary removal, alternate role passing, unauthorized role creation, and OIDC trust modification.

### IAM-RECHECK-02: The technical addendum still instructs consumers to use a mutable module tag

**Severity:** High  
**Locations:** PRD FR-25 (lines 317-325), NFR-12 (line 379), Rollback Principles (line 464); Addendum Initial Distribution Pattern (lines 31-38) and pinning input (line 70).

**Finding:** FR-25 correctly says human-readable release tags are not trusted as immutable references, and addendum line 70 repeats that position. However, addendum lines 34-38 still call a semantic release version the consumer pin and provide `ref=v1.0.0` as the concrete source example. Git tags can be moved. This is an internal contradiction in the implementation-facing artifact and creates a direct path for downstream code to violate Deployment Identity while appearing to follow the documented example. Provider reproducibility also remains only "documented pinning guidance" plus rollback prose; there is no production-gate requirement to commit and verify `.terraform.lock.hcl` checksums or constrain the tested provider release.

**Required closure:** Replace the mutable tag example with an immutable registry version backed by registry immutability controls or a full Git commit SHA, retaining the release tag only as an annotation. Add a production acceptance consequence requiring reviewed provider constraints and committed, verified dependency lock files/checksums for every supported execution platform. Add fixtures that reject branch refs, movable Git tags, unpinned Actions/workflows, missing lock files, and provider selections outside the tested matrix.

## Recheck Gate

No Critical findings remain. Close IAM-RECHECK-01 and IAM-RECHECK-02, then rerun the security closure check. The previously noted secret-lifecycle, network-egress, exception-registry, state-access-logging, and OIDC session-detail issues remain architecture/implementation review items below the Critical/High threshold; they should stay in the Production Readiness Checklist and threat model.

