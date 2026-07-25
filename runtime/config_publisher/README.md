# Config Publisher

The Cell-owned publisher accepts IAM-authenticated Lambda Function URL
requests and creates one encrypted CONFIG object with S3 `IfNoneMatch="*"`.
The caller's `PlatformEcsScheduledJobId` IAM role tag must match the requested
job ID. The runtime never falls back to an unconditional write.
The publisher package includes the checked-in `config.schema.json` and
`common.schema.json` resources under `config_publisher/schemas`. Every request
is validated against that Draft 2020-12 schema before hashing or writing. The
CONFIG version is the RFC 8785 SHA-256 of `config`, matching the job module's
Terraform-compatible canonicalization guard.
