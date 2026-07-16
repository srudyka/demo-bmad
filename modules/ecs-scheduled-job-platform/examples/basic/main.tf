module "platform" {
  source = "../.."

  access_log_bucket_name         = var.access_log_bucket_name
  application                    = var.application
  cell_id                        = var.cell_id
  enable_recovery_protection     = var.enable_recovery_protection
  environment                    = var.environment
  kms_key_arn                    = var.kms_key_arn
  metric_namespace               = var.metric_namespace
  owner                          = var.owner
  permissions_boundary_arn       = var.permissions_boundary_arn
  service                        = var.service
  tags                           = var.tags
  canary_reservation             = var.canary_reservation
  canary_normalizer_registration = var.canary_normalizer_registration
  normalizer                     = var.normalizer
}
