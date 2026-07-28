# Trusted deployment target

Creates separate short-lived GitHub OIDC plan and apply roles. Both roles
require the exact audience and immutable subject supplied by the reviewed target
manifest, use the supplied permissions boundary, and are restricted to the
manifest-bound S3 state and native `.tflock` objects. This module does not create
users, access keys, OIDC providers, or administrator permissions.
