# Example Environment

This directory shows how one AWS account can consume the `ecs-scheduled-job`
module through an aliased provider and caller-supplied assume-role ARN.

Do not commit real account IDs, role ARNs, subnet IDs, security group IDs,
container image URIs, parameter ARNs, or tfvars files. Supply those values
through your normal secure CI/CD variable mechanism or local uncommitted inputs.

## Validation

```bash
terraform -chdir=envs/example init -backend=false
terraform -chdir=envs/example validate
```

## Production Use

Before adapting this example for production:

- Configure remote state in the environment repository or approved backend.
- Use private subnets and tightly scoped security groups.
- Route alarm actions to the owning team's incident path.
- Review the task role policy statements for least privilege.
