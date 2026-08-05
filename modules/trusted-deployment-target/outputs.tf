output "plan_role_arn" { value = aws_iam_role.plan.arn }
output "apply_role_arn" { value = aws_iam_role.apply.arn }
output "permissions_boundary_arn" { value = aws_iam_policy.boundary.arn }
output "state_bucket_arn" { value = aws_s3_bucket.state.arn }
output "backend_config" {
  value = {
    bucket       = aws_s3_bucket.state.bucket
    key          = var.state_key
    use_lockfile = true
    encrypt      = true
  }
}
