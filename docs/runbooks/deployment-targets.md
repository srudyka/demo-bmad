# Trusted deployment targets

Each deployment Environment is selected by a reviewed immutable target manifest.
The manifest binds repository owner/repository IDs, the full-SHA reusable workflow,
Environment, account, Region, Terraform root, separate plan/apply roles, exact
state and native lock paths, Cell Contract checksum, and policy version. Consumer
workflow inputs may select a manifest reference only; they cannot override any
bound value.

Before `terraform init`, the trusted workflow runs the target preflight. It checks
the caller, account, Region, repository IDs, Environment, workflow SHA, manifest
checksum, root, role, state path, policy version, and Cell identity. A mismatch
returns a bounded failure code and must not read state or resources.

The workflow invokes the credential-free command before initialization:

```bash
python scripts/deployment_targets.py \
  --manifest "$REVIEWED_TARGET_MANIFEST" \
  --caller "$TRUSTED_CALLER_BINDING" \
  --authority "$AUTHORITATIVE_PLATFORM_BINDING" \
  --expected-manifest-sha256 "$REVIEWED_MANIFEST_SHA256"
```

The caller and authority binding files are produced by the protected deployment
workflow from the reviewed manifest and AWS/GitHub identity evidence. They must
not be generated from consumer workflow inputs. The root workflow must also
consume the returned backend values in its own `backend "s3"` configuration,
including `use_lockfile = true`; a module output cannot configure a caller's
Terraform backend after initialization.

In trusted mode, preflight additionally validates the GitHub claims, Cell
Contract checksum, and AWS account obtained directly from the runner's STS
`GetCallerIdentity` call. The account is never accepted as a workflow argument
or environment variable.

OIDC trust requires `aud=sts.amazonaws.com` and the complete immutable subject.
Plan and apply use separate short-lived roles with permissions boundaries. The
plan role is read-only; apply is limited to the manifest namespace and cannot
change IAM trust, boundaries, OIDC, backend controls, runtime tables, or unrelated
roles. No long-lived AWS keys are created or documented.

Identity rotation uses a reviewed bounded overlap: `validate_rotation` requires
the same target scope, a verified new manifest, and overlap no longer than 24
hours before the old subject is removed. Publish and verify the new
manifest/trust first, then remove the old subject. Rollback restores the last
reviewed identity; moving tags, wildcards, and destructive trust replacement are
not rollback mechanisms. Protected production Environments require reviewers,
self-review prevention, restricted refs, concurrency, and no administrator bypass.
