# Story 3.6 Blind Hunter Review

Invoke the `bmad-review-adversarial-general` skill. Review the current working-tree changes against baseline commit `9200fb5` in `/Users/srudyka/slower/demo-bmad`, including tracked and untracked Story 3.6 files.

Read the complete diff with:

```bash
git diff 9200fb5 -- .
for f in _bmad-output/implementation-artifacts/3-6-record-deployment-and-rollback-evidence.md contracts/v1/schemas/deployment-evidence.schema.json scripts/deployment_evidence.py; do git diff --no-index /dev/null "$f" || true; done
```

Also read `_bmad-output/project-context.md`, `_bmad/custom/standards/aws-terraform-implementation.md`, and the Story 3.6 story file. Report only actionable findings with file/line evidence, consequence, and severity. Do not modify files.
