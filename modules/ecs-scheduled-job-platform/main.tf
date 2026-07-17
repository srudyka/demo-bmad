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

    condition {
      test     = "ArnNotEquals"
      variable = "aws:PrincipalArn"
      values   = [aws_iam_role.canary_config_publisher.arn]
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
    process_manager = {
      arn          = aws_iam_role.process_manager.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["process-manager"]
    }
    scheduler_ingress = {
      arn          = aws_sqs_queue.scheduler_ingress.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.cell
    }
    scheduler_dlq = {
      arn          = aws_sqs_queue.scheduler_dlq.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.cell
    }
    materializer_ingress = {
      arn          = aws_sqs_queue.materializer_ingress.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    materializer_dlq = {
      arn          = aws_sqs_queue.materializer_dlq.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    occurrence_materializer = {
      arn          = aws_lambda_function.occurrence_materializer.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["occurrence-materializer"]
    }
    materializer_tick = {
      arn          = aws_cloudwatch_event_rule.materializer_tick.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["occurrence-materializer"]
    }
    scheduler_schedule_group = {
      arn          = aws_scheduler_schedule_group.cell.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.cell
    }
    canary_config_publisher = {
      arn          = aws_iam_role.canary_config_publisher.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.config
    }
    normalizer_ingress = {
      arn          = aws_sqs_queue.normalizer_ingress.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    normalizer_quarantine = {
      arn          = aws_sqs_queue.normalizer_quarantine.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    evidence_normalizer = {
      arn          = aws_lambda_function.evidence_normalizer.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["evidence-normalizer"]
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

locals {
  canary_namespace_key = "NAMESPACE#${var.canary_reservation.environment}#${var.canary_reservation.application}"
  canary_namespace_authorization_item = {
    pk                = { S = local.canary_namespace_key }
    sk                = { S = "AUTHORIZATION" }
    account_id        = { S = var.canary_reservation.account_id }
    apply_role_id     = { S = var.canary_reservation.apply_role_id }
    repository_id     = { S = var.canary_reservation.repository_id }
    region            = { S = var.canary_reservation.region }
    terraform_root_id = { S = var.canary_reservation.terraform_root_id }
  }
  canary_job_reservation_item = {
    pk                = { S = "JOB#${var.canary_reservation.job_id}" }
    sk                = { S = "RESERVATION" }
    account_id        = { S = var.canary_reservation.account_id }
    apply_role_id     = { S = var.canary_reservation.apply_role_id }
    namespace_key     = { S = local.canary_namespace_key }
    owner             = { S = var.canary_reservation.owner }
    owner_generation  = { N = tostring(var.canary_reservation.owner_generation) }
    region            = { S = var.canary_reservation.region }
    repository_id     = { S = var.canary_reservation.repository_id }
    terraform_root_id = { S = var.canary_reservation.terraform_root_id }
    tombstoned        = { BOOL = false }
    transfer_state    = { S = "quiescent" }
  }
}

# The general Registrar is intentionally deferred. This Cell-owned declaration
# blocks ordinary Terraform replacement but is not an atomic transaction.
resource "terraform_data" "canary_reservation_identity" {
  input = jsonencode({
    authorization = local.canary_namespace_authorization_item
    reservation   = local.canary_job_reservation_item
  })

  triggers_replace = [jsonencode({
    authorization = local.canary_namespace_authorization_item
    reservation   = local.canary_job_reservation_item
  })]
}

resource "aws_dynamodb_table_item" "canary_namespace_authorization" {
  table_name = aws_dynamodb_table.namespace_registry.name
  hash_key   = "pk"
  range_key  = "sk"
  item       = jsonencode(local.canary_namespace_authorization_item)

  lifecycle {
    prevent_destroy      = true
    replace_triggered_by = [terraform_data.canary_reservation_identity]

    precondition {
      condition = (
        var.canary_reservation.account_id == data.aws_caller_identity.current.account_id &&
        var.canary_reservation.region == data.aws_region.current.region &&
        var.canary_reservation.environment == var.environment &&
        var.canary_reservation.application == var.application &&
        split("/", var.canary_reservation.job_id)[0] == var.environment &&
        split("/", var.canary_reservation.job_id)[1] == var.application &&
        split(":", var.canary_reservation.apply_role_arn)[4] == data.aws_caller_identity.current.account_id
      )
      error_message = "CANARY_RESERVATION_CELL_MISMATCH: canary reservation identity must belong to this Cell and match its environment/application job namespace."
    }
  }
}

resource "aws_dynamodb_table_item" "canary_job_reservation" {
  table_name = aws_dynamodb_table.namespace_registry.name
  hash_key   = "pk"
  range_key  = "sk"
  item       = jsonencode(local.canary_job_reservation_item)

  lifecycle {
    prevent_destroy      = true
    replace_triggered_by = [terraform_data.canary_reservation_identity]
  }
}

data "aws_iam_policy_document" "process_manager_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "process_manager" {
  name                 = "${local.name_prefix}-process-manager-v1"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.process_manager_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

data "aws_iam_policy_document" "canary_config_publisher_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.canary_reservation.apply_role_arn]
    }
  }
}

data "aws_iam_policy_document" "canary_config_publisher" {
  statement {
    sid       = "PublishOnlyTheReservedCanaryConfigPrefix"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/${var.canary_reservation.job_id}/config/*"]
  }

  statement {
    sid       = "UseTheCellConfigKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role" "canary_config_publisher" {
  name                 = "${local.name_prefix}-canary-config-publisher"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.canary_config_publisher_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags = merge(local.common_tags, {
    PlatformEcsScheduledJobCanaryPublication = "true"
    PlatformEcsScheduledJobId                = var.canary_reservation.job_id
  })
}

resource "aws_iam_role_policy" "canary_config_publisher" {
  name   = "${local.name_prefix}-canary-config-publisher"
  role   = aws_iam_role.canary_config_publisher.id
  policy = data.aws_iam_policy_document.canary_config_publisher.json
}

resource "aws_scheduler_schedule_group" "cell" {
  name = "${local.name_prefix}-scheduler"
  tags = local.common_tags
}

resource "aws_sqs_queue" "scheduler_dlq" {
  name                      = "${local.name_prefix}-scheduler-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags

  lifecycle {
    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: kms_key_arn must be in the Cell provider Region."
    }
  }
}

resource "aws_sqs_queue" "scheduler_ingress" {
  name                       = "${local.name_prefix}-scheduler-ingress"
  kms_master_key_id          = var.kms_key_arn
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 6 * var.normalizer.timeout_seconds + var.normalizer.batch_window_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.scheduler_dlq.arn
    maxReceiveCount     = 5
  })
  tags = local.common_tags

  lifecycle {
    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: kms_key_arn must be in the Cell provider Region."
    }

    precondition {
      condition     = 6 * var.normalizer.timeout_seconds + var.normalizer.batch_window_seconds <= 43200
      error_message = "NORMALIZER_SOURCE_VISIBILITY_INVALID: scheduler ingress visibility must not exceed the SQS maximum."
    }
  }
}

resource "aws_sqs_queue" "normalizer_ingress_dlq" {
  name                      = "${local.name_prefix}-evidence-ingress-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "normalizer_ingress" {
  name                      = "${local.name_prefix}-evidence-ingress"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.normalizer_ingress_dlq.arn
    maxReceiveCount     = var.normalizer.max_receive_count
  })
  tags = local.common_tags
}

resource "aws_sqs_queue" "normalizer_quarantine_dlq" {
  name                      = "${local.name_prefix}-evidence-quarantine-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "normalizer_quarantine" {
  name                      = "${local.name_prefix}-evidence-quarantine"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.normalizer_quarantine_dlq.arn
    maxReceiveCount     = var.normalizer.max_receive_count
  })
  tags = local.common_tags
}

data "aws_iam_policy_document" "evidence_normalizer_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "evidence_normalizer" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/evidence-normalizer"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.normalizer.log_retention_days
  tags              = local.common_tags
}

data "aws_iam_policy_document" "evidence_normalizer" {
  statement {
    sid       = "ReadOnlyTheRegisteredSchedulerSource"
    effect    = "Allow"
    actions   = ["sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ReceiveMessage"]
    resources = [aws_sqs_queue.scheduler_ingress.arn, aws_sqs_queue.materializer_ingress.arn]
  }
  statement {
    sid       = "WriteOnlyCanonicalEvidenceAndQuarantine"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.normalizer_ingress.arn, aws_sqs_queue.normalizer_quarantine.arn]
  }
  statement {
    sid       = "WriteOnlyOwnStructuredLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.evidence_normalizer.arn}:*"]
  }
  statement {
    sid       = "UseOnlyCellQueueKeys"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "kms:EncryptionContext:aws:sqs:arn"
      values = [
        aws_sqs_queue.scheduler_ingress.arn,
        aws_sqs_queue.materializer_ingress.arn,
        aws_sqs_queue.normalizer_ingress.arn,
        aws_sqs_queue.normalizer_quarantine.arn,
      ]
    }
  }
  statement {
    sid       = "PublishOnlyBoundedCellMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = [var.metric_namespace]
    }
  }
}

resource "aws_iam_role" "evidence_normalizer" {
  name                 = "${local.name_prefix}-evidence-normalizer"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.evidence_normalizer_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_iam_role_policy" "evidence_normalizer" {
  name   = "${local.name_prefix}-evidence-normalizer"
  role   = aws_iam_role.evidence_normalizer.id
  policy = data.aws_iam_policy_document.evidence_normalizer.json
}

resource "aws_lambda_function" "evidence_normalizer" {
  function_name                  = "${local.name_prefix}-evidence-normalizer"
  filename                       = var.normalizer.artifact_path
  source_code_hash               = var.normalizer.artifact_source_hash
  handler                        = "evidence_normalizer.handler.lambda_handler"
  role                           = aws_iam_role.evidence_normalizer.arn
  runtime                        = "python3.14"
  timeout                        = var.normalizer.timeout_seconds
  reserved_concurrent_executions = var.normalizer.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn

  environment {
    variables = {
      NORMALIZER_CONTRACTS_ROOT       = "/var/task/contracts/v1"
      NORMALIZER_INGRESS_QUEUE_URL    = aws_sqs_queue.normalizer_ingress.url
      NORMALIZER_METRIC_NAMESPACE     = var.metric_namespace
      NORMALIZER_QUARANTINE_QUEUE_URL = aws_sqs_queue.normalizer_quarantine.url
      NORMALIZER_REGISTRATION = jsonencode({
        account_id          = var.canary_normalizer_registration.account_id
        config_version      = var.canary_normalizer_registration.config_version
        environment         = var.canary_normalizer_registration.environment
        job_id              = var.canary_normalizer_registration.job_id
        owner_generation    = var.canary_normalizer_registration.owner_generation
        region              = var.canary_normalizer_registration.region
        schedule_arn        = var.canary_normalizer_registration.schedule_arn
        schedule_generation = var.canary_normalizer_registration.schedule_generation
        schedule_group_arn  = var.canary_normalizer_registration.schedule_group_arn
        scheduler_role_id   = var.canary_normalizer_registration.scheduler_delivery_role_id
        source_queue_arn    = var.canary_normalizer_registration.source_queue_arn
      })
      NORMALIZER_MATERIALIZER_REGISTRATION = jsonencode({
        account_id           = var.canary_normalizer_registration.account_id
        config_version       = var.canary_normalizer_registration.config_version
        environment          = var.canary_normalizer_registration.environment
        job_id               = var.canary_normalizer_registration.job_id
        materializer_role_id = aws_iam_role.occurrence_materializer.unique_id
        owner_generation     = var.canary_normalizer_registration.owner_generation
        region               = var.canary_normalizer_registration.region
        schedule_generation  = var.canary_normalizer_registration.schedule_generation
        source_queue_arn     = aws_sqs_queue.materializer_ingress.arn
      })
    }
  }

  depends_on = [aws_cloudwatch_log_group.evidence_normalizer]
  tags       = local.common_tags

  lifecycle {
    precondition {
      condition = (
        var.canary_normalizer_registration.account_id == data.aws_caller_identity.current.account_id &&
        var.canary_normalizer_registration.region == data.aws_region.current.region &&
        var.canary_normalizer_registration.environment == var.environment &&
        var.canary_normalizer_registration.job_id == var.canary_reservation.job_id &&
        var.canary_normalizer_registration.owner_generation == var.canary_reservation.owner_generation &&
        var.canary_normalizer_registration.source_queue_arn == aws_sqs_queue.scheduler_ingress.arn &&
        var.canary_normalizer_registration.schedule_group_arn == aws_scheduler_schedule_group.cell.arn &&
        var.canary_normalizer_registration.schedule_arn == "arn:aws:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule/${aws_scheduler_schedule_group.cell.name}/${local.name_prefix}-canary"
      )
      error_message = "CANARY_NORMALIZER_REGISTRATION_MISMATCH: registration must bind the exact Cell, reserved canary, Scheduler source queue, and schedule group."
    }
  }
}

resource "aws_lambda_event_source_mapping" "evidence_normalizer" {
  event_source_arn                   = aws_sqs_queue.scheduler_ingress.arn
  function_name                      = aws_lambda_function.evidence_normalizer.arn
  batch_size                         = var.normalizer.batch_size
  maximum_batching_window_in_seconds = var.normalizer.batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
}

# The materializer is intentionally independent of EventBridge Scheduler. Its
# minute tick only advances the CONFIG expectation watermark; it never launches tasks.
resource "aws_sqs_queue" "materializer_dlq" {
  name                      = "${local.name_prefix}-materializer-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "materializer_ingress" {
  name                       = "${local.name_prefix}-materializer-ingress"
  kms_master_key_id          = var.kms_key_arn
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 6 * var.normalizer.timeout_seconds + var.normalizer.batch_window_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.materializer_dlq.arn
    maxReceiveCount     = var.materializer.max_receive_count
  })
  tags = local.common_tags

  lifecycle {
    precondition {
      condition     = 6 * var.normalizer.timeout_seconds + var.normalizer.batch_window_seconds <= 43200
      error_message = "MATERIALIZER_SOURCE_VISIBILITY_INVALID: visibility must not exceed the SQS maximum."
    }
  }
}

resource "aws_cloudwatch_log_group" "occurrence_materializer" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/occurrence-materializer"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.materializer.log_retention_days
  tags              = local.common_tags
}

data "aws_iam_policy_document" "occurrence_materializer_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "occurrence_materializer" {
  name                 = "${local.name_prefix}-occurrence-materializer"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.occurrence_materializer_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

data "aws_iam_policy_document" "occurrence_materializer" {
  statement {
    sid       = "ReadOnlyTheRegisteredCanaryConfig"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/${var.canary_normalizer_registration.job_id}/config/${var.canary_normalizer_registration.config_version}.json"]
  }
  statement {
    sid       = "WriteOnlyImmutableMaterializationSnapshots"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.configuration_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }
  statement {
    sid       = "ReadOnlyNamespaceRegistry"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.namespace_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }
  statement {
    sid       = "SendOnlyMaterializerEvidence"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.materializer_ingress.arn]
  }
  statement {
    sid       = "UseOnlyTheConfigInboxKeyThroughS3"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["s3.${data.aws_region.current.region}.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "kms:EncryptionContext:aws:s3:arn"
      values   = [aws_s3_bucket.config_inbox.arn]
    }
  }
  statement {
    sid       = "PublishOnlyBoundedMaterializerMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = [var.metric_namespace]
    }
  }
  statement {
    sid       = "WriteOnlyOwnLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.occurrence_materializer.arn}:*"]
  }
  statement {
    sid       = "UseOnlyConfigAndSourceQueueKeyContexts"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "kms:EncryptionContext:aws:sqs:arn"
      values   = [aws_sqs_queue.materializer_ingress.arn]
    }
  }
}

resource "aws_iam_role_policy" "occurrence_materializer" {
  name   = "${local.name_prefix}-occurrence-materializer"
  role   = aws_iam_role.occurrence_materializer.id
  policy = data.aws_iam_policy_document.occurrence_materializer.json
}

resource "aws_lambda_function" "occurrence_materializer" {
  function_name                  = "${local.name_prefix}-occurrence-materializer"
  filename                       = var.materializer.artifact_path
  source_code_hash               = var.materializer.artifact_source_hash
  handler                        = "occurrence_materializer.handler.lambda_handler"
  role                           = aws_iam_role.occurrence_materializer.arn
  runtime                        = "python3.14"
  timeout                        = var.materializer.timeout_seconds
  reserved_concurrent_executions = var.materializer.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn
  environment { variables = {
    MATERIALIZER_CONTRACTS_ROOT           = "/var/task/contracts/v1"
    MATERIALIZER_CONFIG_BUCKET            = aws_s3_bucket.config_inbox.bucket
    MATERIALIZER_CONFIG_KEY               = "jobs/${var.canary_normalizer_registration.job_id}/config/${var.canary_normalizer_registration.config_version}.json"
    MATERIALIZER_CONFIG_REGISTRY_TABLE    = aws_dynamodb_table.configuration_registry.name
    MATERIALIZER_NAMESPACE_REGISTRY_TABLE = aws_dynamodb_table.namespace_registry.name
    MATERIALIZER_SOURCE_QUEUE_URL         = aws_sqs_queue.materializer_ingress.url
    MATERIALIZER_METRIC_NAMESPACE         = var.metric_namespace
    MATERIALIZER_REGISTRATION = jsonencode({
      account_id                 = var.canary_normalizer_registration.account_id
      config_version             = var.canary_normalizer_registration.config_version
      environment                = var.canary_normalizer_registration.environment
      job_id                     = var.canary_normalizer_registration.job_id
      owner_generation           = var.canary_normalizer_registration.owner_generation
      region                     = var.canary_normalizer_registration.region
      schedule_arn               = var.canary_normalizer_registration.schedule_arn
      schedule_generation        = var.canary_normalizer_registration.schedule_generation
      scheduler_delivery_role_id = var.canary_normalizer_registration.scheduler_delivery_role_id
    })
  } }
  depends_on = [aws_cloudwatch_log_group.occurrence_materializer]
  tags       = local.common_tags
}

resource "aws_cloudwatch_event_rule" "materializer_tick" {
  name                = "${local.name_prefix}-materializer-tick"
  description         = "Independent UTC materialization tick; never an ECS launch schedule."
  schedule_expression = "rate(1 minute)"
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "materializer_tick" {
  rule = aws_cloudwatch_event_rule.materializer_tick.name
  arn  = aws_lambda_function.occurrence_materializer.arn

  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 5
  }

  dead_letter_config {
    arn = aws_sqs_queue.materializer_dlq.arn
  }
}

data "aws_iam_policy_document" "materializer_queue" {
  statement {
    sid       = "AllowOnlyTheCellMaterializerRole"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.materializer_ingress.arn]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.occurrence_materializer.arn]
    }
  }
}

data "aws_iam_policy_document" "materializer_dlq_queue" {
  statement {
    sid       = "AllowOnlyThisMaterializerRuleDeadLetterDelivery"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.materializer_dlq.arn]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.materializer_tick.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "materializer_ingress" {
  queue_url = aws_sqs_queue.materializer_ingress.id
  policy    = data.aws_iam_policy_document.materializer_queue.json
}

resource "aws_sqs_queue_policy" "materializer_dlq" {
  queue_url = aws_sqs_queue.materializer_dlq.id
  policy    = data.aws_iam_policy_document.materializer_dlq_queue.json
}

resource "aws_lambda_permission" "materializer_tick" {
  statement_id  = "AllowEventBridgeMaterializerTick"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.occurrence_materializer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.materializer_tick.arn
}

resource "aws_lambda_event_source_mapping" "materializer_normalizer" {
  event_source_arn                   = aws_sqs_queue.materializer_ingress.arn
  function_name                      = aws_lambda_function.evidence_normalizer.arn
  batch_size                         = var.normalizer.batch_size
  maximum_batching_window_in_seconds = var.normalizer.batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
}

data "aws_iam_policy_document" "scheduler_queue" {
  statement {
    sid       = "AllowOnlyThisCellSchedulerGroup"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scheduler_ingress.arn, aws_sqs_queue.scheduler_dlq.arn]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_scheduler_schedule_group.cell.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "scheduler_ingress" {
  queue_url = aws_sqs_queue.scheduler_ingress.id
  policy    = data.aws_iam_policy_document.scheduler_queue.json
}

resource "aws_sqs_queue_policy" "scheduler_dlq" {
  queue_url = aws_sqs_queue.scheduler_dlq.id
  policy    = data.aws_iam_policy_document.scheduler_queue.json
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
