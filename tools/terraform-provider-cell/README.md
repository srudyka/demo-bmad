# Cell Terraform Provider

This provider exposes `cell_config_publication`. It assumes the explicitly
configured same-account publisher role and signs an `execute-api` request to
the Cell private API. The Cell service performs authorization and the atomic S3
`IfNoneMatch="*"` write; this provider never writes S3 directly.

Configure `endpoint_url`, `region`, and `publisher_role_arn` from the Cell
Contract/provider root. The endpoint must be the registered private API route.

Build the pinned provider with:

```bash
go build -o terraform-provider-cell ./tools/terraform-provider-cell
```

The deployment workflow must install the resulting binary through a reviewed
Terraform provider mirror/dev override before a job root uses it. Do not use a
shell upload or Terraform provisioner as a substitute.
