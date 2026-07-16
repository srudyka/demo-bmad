data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_iam_policy_document" "config_inbox" {
  # Explicit deny statements must use the wildcard principal so they constrain
  # every identity policy, including future job-root principals.
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.config_inbox.arn, "${aws_s3_bucket.config_inbox.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid    = "DenyNonCanonicalConfigObjectKey"
    effect = "Deny"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]

    not_resources = [
      "${aws_s3_bucket.config_inbox.arn}/jobs/*/config/${join("", [for _ in range(64) : "?"])}.json",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }

  statement {
    sid       = "DenyUnencryptedConfigWrites"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/*/config/${join("", [for _ in range(64) : "?"])}.json"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Null"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["true"]
    }
  }

  statement {
    sid       = "DenyWrongConfigEncryptionAlgorithm"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/*/config/${join("", [for _ in range(64) : "?"])}.json"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }

  statement {
    sid       = "DenyWrongConfigEncryptionKey"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/*/config/${join("", [for _ in range(64) : "?"])}.json"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption-aws-kms-key-id"
      values   = [var.kms_key_arn]
    }
  }

  # The Registrar introduced later grants this session tag only after it has
  # bound the job ID, repository root, and apply-role identity.
  statement {
    sid    = "DenyUnregisteredConfigWriter"
    effect = "Deny"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/*/config/${join("", [for _ in range(64) : "?"])}.json"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Null"
      variable = "aws:PrincipalTag/PlatformEcsScheduledJobId"
      values   = ["true"]
    }
  }

  statement {
    sid    = "DenyCrossPrefixConfigObjectAccess"
    effect = "Deny"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
    ]

    not_resources = [
      "${aws_s3_bucket.config_inbox.arn}/jobs/$${aws:PrincipalTag/PlatformEcsScheduledJobId}/config/${join("", [for _ in range(64) : "?"])}.json",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Null"
      variable = "aws:PrincipalTag/PlatformEcsScheduledJobId"
      values   = ["false"]
    }
  }

  statement {
    sid       = "DenyConfigOverwriteWithoutIfNoneMatch"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/*/config/${join("", [for _ in range(64) : "?"])}.json"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    # Multipart initiation and part uploads cannot carry If-None-Match. The
    # completed upload is still denied unless it supplies the precondition.
    condition {
      test     = "Null"
      variable = "s3:if-none-match"
      values   = ["true"]
    }

    condition {
      test     = "Bool"
      variable = "s3:ObjectCreationOperation"
      values   = ["false"]
    }
  }
}

locals {
  name_prefix = "${var.environment}-${var.application}"
  common_tags = merge(
    var.tags,
    {
      Application = var.application
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner
      Service     = var.service
    },
  )

  compatibility_catalog = jsondecode(
    file("${path.module}/../../contracts/v1/catalogs/compatibility.json"),
  )
  supported_ranges = {
    cell                              = local.compatibility_catalog.component_ranges.cell
    config                            = local.compatibility_catalog.component_ranges.config
    ecs_scheduled_job_platform_module = local.compatibility_catalog.component_ranges["ecs-scheduled-job-platform-module"]
  }
  contract_integrations = {
    config_inbox = {
      arn          = aws_s3_bucket.config_inbox.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.config
    }
    configuration_registry = {
      arn          = aws_dynamodb_table.configuration_registry.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.config
    }
    namespace_registry = {
      arn          = aws_dynamodb_table.namespace_registry.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.cell
    }
  }
  cell_contract_body = {
    cell = {
      account_id  = data.aws_caller_identity.current.account_id
      cell_id     = var.cell_id
      environment = var.environment
      region      = data.aws_region.current.region
    }
    contract_version = var.contract_version
    discovery_path   = "/platform/ecs-scheduled-jobs/${var.environment}/${data.aws_region.current.region}/contract"
    encryption = {
      kms_key_arn = var.kms_key_arn
    }
    integrations     = local.contract_integrations
    metric_namespace = var.metric_namespace
    schema_version   = "1.0.0"
    supported_ranges = local.supported_ranges
  }
  cell_contract_string_values = concat(
    [
      data.aws_caller_identity.current.account_id,
      var.cell_id,
      var.environment,
      data.aws_region.current.region,
      var.contract_version,
      local.cell_contract_body.discovery_path,
      var.kms_key_arn,
      var.metric_namespace,
      local.cell_contract_body.schema_version,
    ],
    values(local.supported_ranges),
    flatten([
      for integration in values(local.contract_integrations) : [
        integration.arn,
        integration.owner,
        integration.schema_range,
      ]
    ]),
  )
  # All contract values are ASCII strings and maps with stable literal keys.
  # This restricted profile makes Terraform jsonencode byte-equivalent to JCS.
  cell_contract_json_is_jcs_safe = alltrue([
    for value in local.cell_contract_string_values : can(regex("^[ -~]+$", value))
  ])
  cell_contract_checksum = sha256(jsonencode(local.cell_contract_body))
  cell_contract = merge(
    local.cell_contract_body,
    { checksum = local.cell_contract_checksum },
  )
  cell_contract_json = jsonencode(local.cell_contract)
}

resource "aws_dynamodb_table" "namespace_registry" {
  name                        = "${local.name_prefix}-namespace-registry"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "pk"
  range_key                   = "sk"
  deletion_protection_enabled = var.enable_recovery_protection

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  lifecycle {
    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: kms_key_arn must be in the Cell provider Region."
    }
  }

  tags = local.common_tags
}

resource "aws_s3_bucket" "config_inbox" {
  bucket        = "${local.name_prefix}-cfg-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
  force_destroy = false
  tags          = local.common_tags

  lifecycle {
    precondition {
      condition     = var.access_log_bucket_name != "${local.name_prefix}-cfg-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
      error_message = "ACCESS_LOG_BUCKET_MUST_BE_SEPARATE: access_log_bucket_name must not be the CONFIG inbox bucket."
    }

    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: kms_key_arn must be in the Cell provider Region."
    }
  }
}

resource "aws_s3_bucket_public_access_block" "config_inbox" {
  bucket = aws_s3_bucket.config_inbox.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "config_inbox" {
  bucket = aws_s3_bucket.config_inbox.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config_inbox" {
  bucket = aws_s3_bucket.config_inbox.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "config_inbox" {
  bucket = aws_s3_bucket.config_inbox.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_logging" "config_inbox" {
  bucket        = aws_s3_bucket.config_inbox.id
  target_bucket = var.access_log_bucket_name
  target_prefix = "${local.name_prefix}/config-inbox/"
}

resource "aws_s3_bucket_lifecycle_configuration" "config_inbox" {
  bucket = aws_s3_bucket.config_inbox.id

  rule {
    id     = "abort-incomplete-config-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = var.incomplete_multipart_upload_days
    }
  }
}

resource "aws_s3_bucket_policy" "config_inbox" {
  bucket = aws_s3_bucket.config_inbox.id
  policy = data.aws_iam_policy_document.config_inbox.json

  depends_on = [aws_s3_bucket_public_access_block.config_inbox]
}

resource "aws_dynamodb_table" "configuration_registry" {
  name                        = "${local.name_prefix}-configuration-registry"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "pk"
  range_key                   = "sk"
  deletion_protection_enabled = var.enable_recovery_protection

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  lifecycle {
    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: kms_key_arn must be in the Cell provider Region."
    }
  }

  tags = local.common_tags
}

resource "aws_ssm_parameter" "cell_contract" {
  name   = "/platform/ecs-scheduled-jobs/${var.environment}/${data.aws_region.current.region}/contract"
  type   = "SecureString"
  key_id = var.kms_key_arn
  tier   = "Standard"
  value  = local.cell_contract_json
  tags   = local.common_tags

  lifecycle {
    precondition {
      condition     = local.cell_contract_json_is_jcs_safe
      error_message = "CELL_CONTRACT_JSON_NOT_JCS_SAFE: Cell Contract values must use the module's ASCII-restricted JSON profile."
    }

    precondition {
      condition     = length(local.cell_contract_json) <= 4096
      error_message = "CELL_CONTRACT_STANDARD_TIER_LIMIT: Cell Contract must not exceed the 4 KiB Standard Parameter Store value limit."
    }

    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: kms_key_arn must be in the Cell provider Region."
    }
  }
}
