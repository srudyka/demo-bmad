# Story 3.5 Edge Case Review

Invoke the `bmad-review-edge-case-hunter` skill. Review the current working tree changes against baseline commit `11e1cbd` in `/Users/srudyka/slower/demo-bmad`, including tracked and untracked Story 3.5 files.

Inspect the complete tracked and untracked diff, especially `.github/workflows/production-apply.yml`, `scripts/production_apply.py`, the two new schemas, contract manifest/release updates, tests, and runbooks. Read the project context, AWS Terraform standard, and Story 3.5 file. Walk every approval, readiness, checksum, artifact, caller, lock, concurrency, runner-loss, phase, and emergency branch. Report only unhandled actionable edge cases with file/line evidence, consequence, and severity. Do not modify files.
