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

  cell_health_alarm_definitions = {
    scheduler_delivery_failures = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.scheduler_dlq.name }
      statistic  = "Maximum"
    }
    scheduler_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.scheduler_dlq.name }
      statistic  = "Maximum"
    }
    scheduler_attempts = {
      namespace  = "AWS/SQS"
      name       = "NumberOfMessagesSent"
      dimensions = { QueueName = aws_sqs_queue.scheduler_ingress.name }
      statistic  = "Sum"
    }
    source_queue_age = {
      namespace  = "AWS/SQS"
      name       = "ApproximateAgeOfOldestMessage"
      dimensions = { QueueName = aws_sqs_queue.scheduler_ingress.name }
      statistic  = "Maximum"
    }
    ingress_queue_age = {
      namespace  = "AWS/SQS"
      name       = "ApproximateAgeOfOldestMessage"
      dimensions = { QueueName = aws_sqs_queue.process_manager_ingress.name }
      statistic  = "Maximum"
    }
    lambda_errors = {
      namespace  = "AWS/Lambda"
      name       = "Errors"
      dimensions = { FunctionName = aws_lambda_function.alert_router.function_name }
      statistic  = "Sum"
    }
    lambda_throttles = {
      namespace  = "AWS/Lambda"
      name       = "Throttles"
      dimensions = { FunctionName = aws_lambda_function.alert_router.function_name }
      statistic  = "Sum"
    }
    dynamodb_throttles = {
      namespace  = "AWS/DynamoDB"
      name       = "ThrottledRequests"
      dimensions = { TableName = aws_dynamodb_table.occurrence_ledger.name }
      statistic  = "Sum"
    }
    deadline_lag = {
      namespace  = var.metric_namespace
      name       = "DeadlineScannerWatermarkAge"
      dimensions = { component = "deadline-scanner", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Maximum"
    }
    outbox_reconciliation = {
      namespace  = var.metric_namespace
      name       = "ReconciliationFailure"
      dimensions = { component = "alert-router", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
    scheduler_queue_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.scheduler_ingress.name }
      statistic  = "Maximum"
    }
    process_manager_queue_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.process_manager_ingress.name }
      statistic  = "Maximum"
    }
    every_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.deadline_scanner_tick_dlq.name }
      statistic  = "Maximum"
    }
    deadline_source_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.deadline_source_dlq.name }
      statistic  = "Maximum"
    }
    ecs_event_source_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.ecs_event_source_dlq.name }
      statistic  = "Maximum"
    }
    completion_source_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.completion_source_dlq.name }
      statistic  = "Maximum"
    }
    normalizer_ingress_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.normalizer_ingress_dlq.name }
      statistic  = "Maximum"
    }
    process_manager_ingress_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.process_manager_ingress_dlq.name }
      statistic  = "Maximum"
    }
    normalizer_quarantine_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.normalizer_quarantine_dlq.name }
      statistic  = "Maximum"
    }
    materializer_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.materializer_dlq.name }
      statistic  = "Maximum"
    }
    command_handler_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.command_handler_dlq.name }
      statistic  = "Maximum"
    }
    alert_router_dlq_depth = {
      namespace  = "AWS/SQS"
      name       = "ApproximateNumberOfMessagesVisible"
      dimensions = { QueueName = aws_sqs_queue.alert_router_dlq.name }
      statistic  = "Maximum"
    }
    lambda_duration = {
      namespace  = "AWS/Lambda"
      name       = "Duration"
      dimensions = { FunctionName = aws_lambda_function.alert_router.function_name }
      statistic  = "Maximum"
      threshold  = 5000
    }
    lambda_concurrency = {
      namespace  = "AWS/Lambda"
      name       = "ConcurrentExecutions"
      dimensions = { FunctionName = aws_lambda_function.alert_router.function_name }
      statistic  = "Maximum"
    }
    dynamodb_conditional_failures = {
      namespace  = "AWS/DynamoDB"
      name       = "ConditionalCheckFailedRequests"
      dimensions = { TableName = aws_dynamodb_table.occurrence_ledger.name }
      statistic  = "Sum"
    }
    log_subscription_delivery = {
      namespace  = "AWS/Logs"
      name       = "DeliveryErrors"
      dimensions = { LogGroupName = aws_cloudwatch_log_group.alert_router.name }
      statistic  = "Sum"
    }
    notification_delivery = {
      namespace  = var.metric_namespace
      name       = "NotificationDelivered"
      dimensions = { component = "alert-router", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
    expectation_horizon_freshness = {
      namespace  = var.metric_namespace
      name       = "DeadlineScannerWatermarkAge"
      dimensions = { component = "deadline-scanner", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Maximum"
    }
    schedule_conformance = {
      namespace  = var.metric_namespace
      name       = "CanaryProcessedHeartbeat"
      dimensions = { component = "canary", cell_id = var.cell_id, environment = var.environment, state = "SUCCEEDED" }
      statistic  = "Sum"
    }
    recovery_blocked = {
      namespace  = var.metric_namespace
      name       = "RecoveryBlocked"
      dimensions = { component = "recovery-controller", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
    recovery_restore_failure = {
      namespace  = var.metric_namespace
      name       = "RecoveryRestoreFailure"
      dimensions = { component = "recovery-controller", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
    recovery_integrity_failure = {
      namespace  = var.metric_namespace
      name       = "RecoveryIntegrityFailure"
      dimensions = { component = "recovery-controller", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
    recovery_replay_failure = {
      namespace  = var.metric_namespace
      name       = "RecoveryReplayFailure"
      dimensions = { component = "recovery-controller", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
    recovery_verification_failure = {
      namespace  = var.metric_namespace
      name       = "RecoveryVerificationFailure"
      dimensions = { component = "recovery-controller", cell_id = var.cell_id, environment = var.environment }
      statistic  = "Sum"
    }
  }
  cell_health_alarm_policy = {
    for key in keys(local.cell_health_alarm_definitions) : key => {
      threshold          = try(local.cell_health_alarm_definitions[key].threshold, 1)
      evaluation_periods = 5
      period_seconds     = 60
      missing_data       = "breaching"
      owner              = var.owner
      severity           = "critical"
      runbook_uri        = var.alert_router.runbook_uri
    }
  }

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
    task_arn_index = {
      arn          = "${aws_dynamodb_table.occurrence_ledger.arn}/index/task-arn"
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    deadline_index = {
      arn          = "${aws_dynamodb_table.occurrence_ledger.arn}/index/deadlines"
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    deadline_scanner = {
      arn          = aws_lambda_function.deadline_scanner.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    deadline_source = {
      arn          = aws_sqs_queue.deadline_source.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    deadline_checkpoint = {
      arn          = aws_dynamodb_table.deadline_checkpoint.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    occurrence_ledger = {
      arn          = aws_dynamodb_table.occurrence_ledger.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
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
    process_manager_ingress = {
      arn          = aws_sqs_queue.process_manager_ingress.arn
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
    ecs_event_source = {
      arn          = aws_sqs_queue.ecs_event_source.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    completion_source = {
      arn          = aws_sqs_queue.completion_source.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges.evidence
    }
    alert_outbox = {
      arn          = "${aws_dynamodb_table.occurrence_ledger.arn}/index/alert-outbox"
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["alert-router"]
    }
    notification_ledger = {
      arn          = aws_dynamodb_table.notification_ledger.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["alert-router"]
    }
    alert_router = {
      arn          = aws_lambda_function.alert_router.arn
      owner        = "cell-root"
      schema_range = local.compatibility_catalog.component_ranges["alert-router"]
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
    iam = {
      permissions_boundary_arn = var.permissions_boundary_arn
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
      var.permissions_boundary_arn,
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

resource "aws_dynamodb_table" "occurrence_ledger" {
  name                        = "${local.name_prefix}-occurrence-ledger"
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

  attribute {
    name = "task_arn"
    type = "S"
  }

  attribute {
    name = "deadline_key"
    type = "S"
  }

  attribute {
    name = "deadline_sort"
    type = "S"
  }

  attribute {
    name = "record_type"
    type = "S"
  }

  attribute {
    name = "alert_sort"
    type = "S"
  }

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "scheduled_time"
    type = "S"
  }

  global_secondary_index {
    name            = "task-arn"
    hash_key        = "task_arn"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "alert-outbox"
    hash_key        = "record_type"
    range_key       = "alert_sort"
    projection_type = "ALL"
  }

  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  global_secondary_index {
    name            = "deadlines"
    hash_key        = "deadline_key"
    range_key       = "deadline_sort"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "job-scheduled-time"
    hash_key        = "job_id"
    range_key       = "scheduled_time"
    projection_type = "ALL"
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

resource "aws_cloudwatch_log_group" "process_manager" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/process-manager"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.process_manager.log_retention_days
  tags              = local.common_tags
}

resource "aws_dynamodb_table" "deadline_checkpoint" {
  name                        = "${local.name_prefix}-deadline-checkpoint"
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

  tags = local.common_tags
}

resource "aws_sqs_queue" "deadline_source_dlq" {
  name                      = "${local.name_prefix}-deadline-events-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "deadline_source" {
  name                       = "${local.name_prefix}-deadline-events"
  kms_master_key_id          = var.kms_key_arn
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 6 * var.deadline_scanner.timeout_seconds + var.deadline_scanner.batch_window_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.deadline_source_dlq.arn
    maxReceiveCount     = var.deadline_scanner.max_receive_count
  })
  tags = local.common_tags

  lifecycle {
    precondition {
      condition     = 6 * var.deadline_scanner.timeout_seconds + var.deadline_scanner.batch_window_seconds <= 43200
      error_message = "DEADLINE_SOURCE_VISIBILITY_INVALID: deadline source visibility must not exceed the SQS maximum."
    }
  }
}

data "aws_iam_policy_document" "deadline_scanner_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "deadline_scanner" {
  name                 = "${local.name_prefix}-deadline-scanner"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.deadline_scanner_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_cloudwatch_log_group" "deadline_scanner" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/deadline-scanner"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.deadline_scanner.log_retention_days
  tags              = local.common_tags
}

data "aws_iam_policy_document" "deadline_scanner" {
  statement {
    sid       = "ReadOnlyDeadlineProjection"
    effect    = "Allow"
    actions   = ["dynamodb:Query"]
    resources = ["${aws_dynamodb_table.occurrence_ledger.arn}/index/deadlines"]
  }
  statement {
    sid       = "ReadOnlyAuthoritativeOccurrences"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }
  statement {
    sid       = "UpdateOnlyScannerCheckpoint"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.deadline_checkpoint.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["CELL#${var.cell_id}"]
    }
  }
  statement {
    sid       = "SendOnlyDeadlineEvidence"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.deadline_source.arn]
  }
  statement {
    sid       = "WriteOnlyOwnLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.deadline_scanner.arn}:*"]
  }
  statement {
    sid       = "UseOnlyDeadlineQueueKeyContext"
    effect    = "Allow"
    actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
    resources = [var.kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:EncryptionContext:aws:sqs:arn"
      values   = [aws_sqs_queue.deadline_source.arn]
    }
  }
  statement {
    sid       = "PublishOnlyBoundedScannerMetrics"
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

resource "aws_iam_role_policy" "deadline_scanner" {
  name   = "${local.name_prefix}-deadline-scanner"
  role   = aws_iam_role.deadline_scanner.id
  policy = data.aws_iam_policy_document.deadline_scanner.json
}

resource "aws_lambda_function" "deadline_scanner" {
  function_name                  = "${local.name_prefix}-deadline-scanner"
  filename                       = var.deadline_scanner.artifact_path
  source_code_hash               = var.deadline_scanner.artifact_source_hash
  handler                        = "deadline_scanner.handler.lambda_handler"
  role                           = aws_iam_role.deadline_scanner.arn
  runtime                        = "python3.14"
  timeout                        = var.deadline_scanner.timeout_seconds
  reserved_concurrent_executions = var.deadline_scanner.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn

  environment {
    variables = {
      DEADLINE_SCANNER_OCCURRENCE_TABLE_NAME           = aws_dynamodb_table.occurrence_ledger.name
      DEADLINE_SCANNER_RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
      DEADLINE_SCANNER_INDEX_NAME                      = "deadlines"
      DEADLINE_SCANNER_SOURCE_QUEUE_URL                = aws_sqs_queue.deadline_source.url
      DEADLINE_SCANNER_CHECKPOINT_TABLE_NAME           = aws_dynamodb_table.deadline_checkpoint.name
      DEADLINE_SCANNER_CHECKPOINT_PK                   = "CELL#${var.cell_id}"
      DEADLINE_SCANNER_LOOKBACK_SECONDS                = tostring(var.deadline_scanner.lookback_seconds)
      DEADLINE_SCANNER_MAX_LATENESS_SECONDS            = tostring(var.deadline_scanner.maximum_lateness_seconds)
      DEADLINE_SCANNER_PAGE_SIZE                       = tostring(var.deadline_scanner.page_size)
      DEADLINE_SCANNER_SHARD                           = "0"
      DEADLINE_SCANNER_METRIC_NAMESPACE                = var.metric_namespace
      DEADLINE_SCANNER_ENVIRONMENT                     = var.environment
    }
  }

  depends_on = [aws_cloudwatch_log_group.deadline_scanner]
  tags       = local.common_tags
}

resource "aws_cloudwatch_event_rule" "deadline_scanner_tick" {
  name                = "${local.name_prefix}-deadline-scanner-tick"
  description         = "Minute-cadence deadline reconciliation; detection only."
  schedule_expression = "rate(1 minute)"
  tags                = local.common_tags
}

resource "aws_sqs_queue" "deadline_scanner_tick_dlq" {
  name                      = "${local.name_prefix}-deadline-scanner-tick-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

data "aws_iam_policy_document" "deadline_scanner_tick_dlq" {
  statement {
    sid       = "AllowOnlyDeadlineScannerRuleDeadLetterDelivery"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.deadline_scanner_tick_dlq.arn]
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
      values   = [aws_cloudwatch_event_rule.deadline_scanner_tick.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "deadline_scanner_tick_dlq" {
  queue_url = aws_sqs_queue.deadline_scanner_tick_dlq.id
  policy    = data.aws_iam_policy_document.deadline_scanner_tick_dlq.json
}

resource "aws_cloudwatch_event_target" "deadline_scanner_tick" {
  rule = aws_cloudwatch_event_rule.deadline_scanner_tick.name
  arn  = aws_lambda_function.deadline_scanner.arn
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 5
  }
  dead_letter_config {
    arn = aws_sqs_queue.deadline_scanner_tick_dlq.arn
  }
}

resource "aws_lambda_permission" "deadline_scanner_tick" {
  statement_id  = "AllowEventBridgeDeadlineScannerTick"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.deadline_scanner.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.deadline_scanner_tick.arn
}

resource "aws_dynamodb_table" "notification_ledger" {
  name                        = "${local.name_prefix}-notification-ledger"
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

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  lifecycle {
    precondition {
      condition     = split(":", var.kms_key_arn)[3] == data.aws_region.current.region
      error_message = "KMS_KEY_REGION_MISMATCH: notification ledger key must be in the Cell provider Region."
    }
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "alert_router" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/alert-router"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.alert_router.log_retention_days
  tags              = local.common_tags
}

resource "aws_sqs_queue" "alert_router_dlq" {
  name                      = "${local.name_prefix}-alert-router-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

data "aws_iam_policy_document" "alert_router_dlq" {
  statement {
    sid       = "AllowEventBridgeReconciliationDeadLetterDelivery"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.alert_router_dlq.arn]
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
      values   = [aws_cloudwatch_event_rule.alert_router_reconciliation.arn]
    }
  }
  statement {
    sid       = "AllowOnlyAlertRouterStreamDeadLetterDelivery"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.alert_router_dlq.arn]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_dynamodb_table.occurrence_ledger.stream_arn]
    }
  }
}

resource "aws_sqs_queue_policy" "alert_router_dlq" {
  queue_url = aws_sqs_queue.alert_router_dlq.id
  policy    = data.aws_iam_policy_document.alert_router_dlq.json
}

data "aws_iam_policy_document" "alert_router_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "alert_router" {
  statement {
    sid       = "ReadOnlyOccurrenceStream"
    effect    = "Allow"
    actions   = ["dynamodb:DescribeStream", "dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:ListStreams"]
    resources = [aws_dynamodb_table.occurrence_ledger.stream_arn]
  }
  statement {
    sid       = "ReadOnlyAuthoritativeOccurrences"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#*"]
    }
  }
  statement {
    sid       = "ReadOnlyAlertOutbox"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = ["${aws_dynamodb_table.occurrence_ledger.arn}/index/alert-outbox"]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["ALERT_OUTBOX"]
    }
  }
  statement {
    sid       = "UpdateOnlyAlertOutbox"
    effect    = "Allow"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["ALERT_OUTBOX#*"]
    }
  }
  statement {
    sid       = "ReadOnlyRegisteredConfig"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.configuration_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#*"]
    }
  }
  statement {
    sid       = "UpdateOnlyNotificationLedger"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.notification_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["NOTIFICATION#*"]
    }
  }
  statement {
    sid       = "PublishOnlyRegisteredTarget"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [var.alert_router.notification_target_arn]
  }
  statement {
    sid       = "WriteOnlyOwnLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.alert_router.arn}:*"]
  }
  statement {
    sid       = "PublishOnlyBoundedRouterMetrics"
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
    sid       = "UseCellDataKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "kms:EncryptionContext:aws:dynamodb:tableName"
      values   = [aws_dynamodb_table.occurrence_ledger.name, aws_dynamodb_table.configuration_registry.name, aws_dynamodb_table.notification_ledger.name, aws_dynamodb_table.deadline_checkpoint.name]
    }
  }
}

resource "aws_iam_role" "alert_router" {
  name                 = "${local.name_prefix}-alert-router"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.alert_router_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_iam_role_policy" "alert_router" {
  name   = "${local.name_prefix}-alert-router"
  role   = aws_iam_role.alert_router.id
  policy = data.aws_iam_policy_document.alert_router.json
}

resource "aws_lambda_function" "alert_router" {
  function_name                  = "${local.name_prefix}-alert-router"
  filename                       = var.alert_router.artifact_path
  source_code_hash               = var.alert_router.artifact_source_hash
  handler                        = "alert_router.handler.lambda_handler"
  role                           = aws_iam_role.alert_router.arn
  runtime                        = "python3.14"
  timeout                        = var.alert_router.timeout_seconds
  reserved_concurrent_executions = var.alert_router.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn

  environment {
    variables = {
      ALERT_ROUTER_ACCOUNT_ID                      = data.aws_caller_identity.current.account_id
      ALERT_ROUTER_CELL_ID                         = var.cell_id
      ALERT_ROUTER_CELL_TARGET_ARN                 = var.alert_router.notification_target_arn
      ALERT_ROUTER_NOTIFICATIONS_ENABLED           = tostring(var.alert_router.notifications_enabled)
      ALERT_ROUTER_CONFIG_TABLE_NAME               = aws_dynamodb_table.configuration_registry.name
      ALERT_ROUTER_ENVIRONMENT                     = var.environment
      ALERT_ROUTER_NOTIFICATION_TABLE_NAME         = aws_dynamodb_table.notification_ledger.name
      ALERT_ROUTER_OCCURRENCE_TABLE_NAME           = aws_dynamodb_table.occurrence_ledger.name
      ALERT_ROUTER_RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
      ALERT_ROUTER_OWNER                           = var.owner
      ALERT_ROUTER_REGION                          = data.aws_region.current.region
      ALERT_ROUTER_RUNBOOK_URI                     = var.alert_router.runbook_uri
      ALERT_ROUTER_RECONCILIATION_PAGE_SIZE        = tostring(var.alert_router.reconciliation_page_size)
      ALERT_ROUTER_METRIC_NAMESPACE                = var.metric_namespace
    }
  }

  depends_on = [aws_cloudwatch_log_group.alert_router]
  tags       = local.common_tags
}

resource "aws_lambda_event_source_mapping" "alert_router" {
  enabled                            = var.alert_router.stream_enabled
  event_source_arn                   = aws_dynamodb_table.occurrence_ledger.stream_arn
  function_name                      = aws_lambda_function.alert_router.arn
  batch_size                         = var.alert_router.batch_size
  maximum_batching_window_in_seconds = var.alert_router.batch_window_seconds
  maximum_record_age_in_seconds      = var.alert_router.maximum_record_age_seconds
  maximum_retry_attempts             = var.alert_router.maximum_retry_attempts
  bisect_batch_on_function_error     = true
  starting_position                  = "TRIM_HORIZON"
  function_response_types            = ["ReportBatchItemFailures"]

  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName = ["INSERT", "MODIFY"]
        dynamodb = {
          NewImage = {
            record_type = { S = ["ALERT_OUTBOX"] }
          }
        }
      })
    }
  }

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.alert_router_dlq.arn
    }
  }
}

resource "aws_cloudwatch_event_rule" "alert_router_reconciliation" {
  is_enabled          = var.alert_router.reconciliation_enabled
  name                = "${local.name_prefix}-alert-router-reconciliation"
  description         = "Bounded replay of pending occurrence alert obligations."
  schedule_expression = var.alert_router.reconciliation_schedule_expression
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "alert_router_reconciliation" {
  rule = aws_cloudwatch_event_rule.alert_router_reconciliation.name
  arn  = aws_lambda_function.alert_router.arn
  input = jsonencode({
    mode = "reconciliation"
  })
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 5
  }
  dead_letter_config {
    arn = aws_sqs_queue.alert_router_dlq.arn
  }
}

resource "aws_lambda_permission" "alert_router_reconciliation" {
  statement_id  = "AllowEventBridgeAlertRouterReconciliation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_router.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.alert_router_reconciliation.arn
}

resource "aws_cloudwatch_metric_alarm" "canary_processed_freshness" {
  alarm_name          = "${local.name_prefix}-canary-processed-freshness"
  alarm_description   = "Canary end-to-end processing heartbeat is stale; see the Cell runbook."
  namespace           = var.metric_namespace
  metric_name         = "CanaryProcessedHeartbeat"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 5
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = var.alert_router.notifications_enabled ? [aws_lambda_function.alert_router.arn] : []
  ok_actions          = var.alert_router.notifications_enabled ? [aws_lambda_function.alert_router.arn] : []
  dimensions = {
    component   = "canary"
    cell_id     = var.cell_id
    state       = "SUCCEEDED"
    environment = var.environment
  }
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "alert_router_retries" {
  alarm_name          = "${local.name_prefix}-alert-router-retries"
  alarm_description   = "Alert Router retries require Cell runbook investigation."
  namespace           = var.metric_namespace
  metric_name         = "Retry"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 5
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alert_router.notifications_enabled ? [aws_lambda_function.alert_router.arn] : []
  ok_actions          = var.alert_router.notifications_enabled ? [aws_lambda_function.alert_router.arn] : []
  dimensions = {
    component   = "alert-router"
    cell_id     = var.cell_id
    environment = var.environment
  }
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "cell_health" {
  for_each            = local.cell_health_alarm_definitions
  alarm_name          = "${local.name_prefix}-cell-${each.key}"
  alarm_description   = "Cell health signal ${each.key}; owner: ${local.cell_health_alarm_policy[each.key].owner}; severity: ${local.cell_health_alarm_policy[each.key].severity}; threshold: ${local.cell_health_alarm_policy[each.key].threshold}; missing-data: ${local.cell_health_alarm_policy[each.key].missing_data}; runbook: ${local.cell_health_alarm_policy[each.key].runbook_uri}."
  namespace           = each.value.namespace
  metric_name         = each.value.name
  statistic           = each.value.statistic
  period              = local.cell_health_alarm_policy[each.key].period_seconds
  evaluation_periods  = local.cell_health_alarm_policy[each.key].evaluation_periods
  threshold           = local.cell_health_alarm_policy[each.key].threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = local.cell_health_alarm_policy[each.key].missing_data
  alarm_actions       = var.alert_router.notifications_enabled ? [aws_lambda_function.alert_router.arn] : []
  ok_actions          = var.alert_router.notifications_enabled ? [aws_lambda_function.alert_router.arn] : []
  dimensions          = each.value.dimensions
  tags                = merge(local.common_tags, { Severity = "critical", HealthOwner = var.owner, Runbook = var.alert_router.runbook_uri })
}

resource "aws_lambda_permission" "alert_router_cloudwatch_alarms" {
  for_each = merge(
    {
      canary_processed_freshness = aws_cloudwatch_metric_alarm.canary_processed_freshness.arn
      alert_router_retries       = aws_cloudwatch_metric_alarm.alert_router_retries.arn
    },
    { for key, alarm in aws_cloudwatch_metric_alarm.cell_health : "cell_${key}" => alarm.arn }
  )
  statement_id   = "AllowCloudWatchAlarm${replace(each.key, "-", "")}"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.alert_router.function_name
  principal      = "lambda.alarms.cloudwatch.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
  source_arn     = each.value
}

data "aws_iam_policy_document" "process_manager" {
  statement {
    sid       = "ConsumeOnlyCanonicalIngress"
    effect    = "Allow"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.process_manager_ingress.arn]
  }
  statement {
    sid       = "QuarantineOnlyRejectedEvidence"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.normalizer_quarantine.arn]
  }
  statement {
    sid       = "ReadOnlyVerifiedConfig"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.configuration_registry.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }
  statement {
    sid       = "WriteOnlyOccurrenceLedgerRecords"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:TransactWriteItems"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}", "EVENT#occurrence-materializer", "EVENT#scheduler"]
    }
  }
  statement {
    sid       = "UpdateOnlyCanaryHeartbeatCheckpoint"
    effect    = "Allow"
    actions   = ["dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.deadline_checkpoint.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["CELL#${var.cell_id}"]
    }
  }
  statement {
    sid       = "AssumeOnlyRegisteredCanaryLaunchRole"
    effect    = "Allow"
    actions   = ["sts:AssumeRole"]
    resources = [var.canary_normalizer_registration.canary_launch_role_arn]
  }
  statement {
    sid       = "PublishOnlyBoundedMetrics"
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
    resources = ["${aws_cloudwatch_log_group.process_manager.arn}:*"]
  }
  statement {
    sid       = "UseOnlyIngressAndLedgerKeyContexts"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "kms:EncryptionContext:aws:sqs:arn"
      values   = [aws_sqs_queue.process_manager_ingress.arn, aws_sqs_queue.normalizer_quarantine.arn]
    }
  }
}

resource "aws_iam_role_policy" "process_manager" {
  name   = "${local.name_prefix}-process-manager"
  role   = aws_iam_role.process_manager.id
  policy = data.aws_iam_policy_document.process_manager.json
}

resource "aws_lambda_function" "process_manager" {
  function_name                  = "${local.name_prefix}-process-manager"
  filename                       = var.process_manager.artifact_path
  source_code_hash               = var.process_manager.artifact_source_hash
  handler                        = "process_manager.handler.lambda_handler"
  role                           = aws_iam_role.process_manager.arn
  runtime                        = "python3.14"
  timeout                        = var.process_manager.timeout_seconds
  reserved_concurrent_executions = var.process_manager.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn

  environment {
    variables = {
      PROCESS_MANAGER_CONFIG_TABLE_NAME               = aws_dynamodb_table.configuration_registry.name
      PROCESS_MANAGER_DEPLOYMENT_IDENTITY             = "${var.cell_id}:process-manager:v1"
      PROCESS_MANAGER_ENVIRONMENT                     = var.environment
      PROCESS_MANAGER_INGRESS_QUEUE_ARN               = aws_sqs_queue.process_manager_ingress.arn
      PROCESS_MANAGER_QUARANTINE_QUEUE_URL            = aws_sqs_queue.normalizer_quarantine.url
      PROCESS_MANAGER_OWNER_GENERATION                = tostring(var.canary_normalizer_registration.owner_generation)
      PROCESS_MANAGER_METRIC_NAMESPACE                = var.metric_namespace
      PROCESS_MANAGER_CANARY_JOB_ID                   = var.canary_normalizer_registration.job_id
      PROCESS_MANAGER_CELL_ID                         = var.cell_id
      PROCESS_MANAGER_ENVIRONMENT                     = var.environment
      PROCESS_MANAGER_OCCURRENCE_TABLE_NAME           = aws_dynamodb_table.occurrence_ledger.name
      PROCESS_MANAGER_RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
      PROCESS_MANAGER_HEARTBEAT_TABLE_NAME            = aws_dynamodb_table.deadline_checkpoint.name
      PROCESS_MANAGER_CANARY_LAUNCH_ROLE_ARN          = var.canary_normalizer_registration.canary_launch_role_arn
    }
  }
  depends_on = [aws_cloudwatch_log_group.process_manager]
  tags       = local.common_tags
}

resource "aws_lambda_event_source_mapping" "process_manager" {
  event_source_arn                   = aws_sqs_queue.process_manager_ingress.arn
  function_name                      = aws_lambda_function.process_manager.arn
  batch_size                         = var.process_manager.batch_size
  maximum_batching_window_in_seconds = var.process_manager.batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
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

resource "aws_sqs_queue" "ecs_event_source_dlq" {
  name                      = "${local.name_prefix}-ecs-events-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "ecs_event_source" {
  name                       = "${local.name_prefix}-ecs-events"
  kms_master_key_id          = var.kms_key_arn
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 6 * var.normalizer.timeout_seconds + var.normalizer.batch_window_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ecs_event_source_dlq.arn
    maxReceiveCount     = var.normalizer.max_receive_count
  })
  tags = local.common_tags
}

resource "aws_sqs_queue" "completion_source_dlq" {
  name                      = "${local.name_prefix}-completion-events-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "completion_source" {
  name                       = "${local.name_prefix}-completion-events"
  kms_master_key_id          = var.kms_key_arn
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 6 * var.log_ingestor.timeout_seconds + var.log_ingestor.batch_window_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.completion_source_dlq.arn
    maxReceiveCount     = var.normalizer.max_receive_count
  })
  tags = local.common_tags

  lifecycle {
    precondition {
      condition     = 6 * var.log_ingestor.timeout_seconds + var.log_ingestor.batch_window_seconds <= 43200
      error_message = "LOG_INGESTOR_SOURCE_VISIBILITY_INVALID: completion source visibility must not exceed the SQS maximum."
    }
  }
}

resource "aws_cloudwatch_event_rule" "ecs_task_state" {
  name           = "${local.name_prefix}-ecs-task-state"
  event_bus_name = "default"
  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    account       = [data.aws_caller_identity.current.account_id]
    region        = [data.aws_region.current.region]
    detail = {
      clusterArn = [var.ecs_cluster_arn]
    }
  })
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "ecs_task_state" {
  rule      = aws_cloudwatch_event_rule.ecs_task_state.name
  target_id = "ecs-event-source"
  arn       = aws_sqs_queue.ecs_event_source.arn

  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 5
  }

  dead_letter_config {
    arn = aws_sqs_queue.ecs_event_source_dlq.arn
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

resource "aws_sqs_queue" "process_manager_ingress_dlq" {
  name                      = "${local.name_prefix}-process-manager-ingress-dlq"
  kms_master_key_id         = var.kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "process_manager_ingress" {
  name                       = "${local.name_prefix}-process-manager-ingress"
  kms_master_key_id          = var.kms_key_arn
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 6 * var.process_manager.timeout_seconds + var.process_manager.batch_window_seconds
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.process_manager_ingress_dlq.arn
    maxReceiveCount     = 5
  })
  tags = local.common_tags
}

resource "aws_sqs_queue_policy" "process_manager_ingress" {
  queue_url = aws_sqs_queue.process_manager_ingress.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowOnlyCellNormalizer"
      Effect    = "Allow"
      Principal = { AWS = aws_iam_role.evidence_normalizer.arn }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.process_manager_ingress.arn
    }]
  })
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
    resources = [aws_sqs_queue.scheduler_ingress.arn, aws_sqs_queue.materializer_ingress.arn, aws_sqs_queue.ecs_event_source.arn, aws_sqs_queue.deadline_source.arn, aws_sqs_queue.command_handler_queue.arn]
  }
  statement {
    sid       = "WriteOnlyCanonicalEvidenceAndQuarantine"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.normalizer_ingress.arn, aws_sqs_queue.process_manager_ingress.arn, aws_sqs_queue.normalizer_quarantine.arn, aws_sqs_queue.recovery_queue.arn]
  }
  statement {
    sid       = "ReadOnlyOccurrenceTaskIndex"
    effect    = "Allow"
    actions   = ["dynamodb:Query"]
    resources = ["${aws_dynamodb_table.occurrence_ledger.arn}/index/task-arn"]
  }
  statement {
    sid       = "ReadOnlyMappedOccurrence"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
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
        aws_sqs_queue.ecs_event_source.arn,
        aws_sqs_queue.deadline_source.arn,
        aws_sqs_queue.normalizer_ingress.arn,
        aws_sqs_queue.process_manager_ingress.arn,
        aws_sqs_queue.normalizer_quarantine.arn,
        aws_sqs_queue.command_handler_queue.arn,
        aws_sqs_queue.recovery_queue.arn,
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
      NORMALIZER_CONTRACTS_ROOT                  = "/var/task/contracts/v1"
      NORMALIZER_INGRESS_QUEUE_URL               = aws_sqs_queue.normalizer_ingress.url
      NORMALIZER_PROCESS_MANAGER_QUEUE_URL       = aws_sqs_queue.process_manager_ingress.url
      NORMALIZER_RECOVERY_QUEUE_URL              = aws_sqs_queue.recovery_queue.url
      NORMALIZER_METRIC_NAMESPACE                = var.metric_namespace
      NORMALIZER_QUARANTINE_QUEUE_URL            = aws_sqs_queue.normalizer_quarantine.url
      NORMALIZER_OCCURRENCE_TABLE_NAME           = aws_dynamodb_table.occurrence_ledger.name
      NORMALIZER_RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
      NORMALIZER_COMMAND_REGISTRATION = jsonencode({
        account_id          = data.aws_caller_identity.current.account_id
        cell_id             = var.cell_id
        environment         = var.environment
        region              = data.aws_region.current.region
        handler_role_id     = aws_iam_role.command_handler.unique_id
        source_queue_arn    = aws_sqs_queue.command_handler_queue.arn
        schedule_generation = var.canary_normalizer_registration.schedule_generation
      })
      NORMALIZER_ECS_REGISTRATION = jsonencode({
        account_id       = data.aws_caller_identity.current.account_id
        environment      = var.environment
        region           = data.aws_region.current.region
        cluster_arn      = var.ecs_cluster_arn
        source_queue_arn = aws_sqs_queue.ecs_event_source.arn
      })
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
      NORMALIZER_DEADLINE_REGISTRATION = jsonencode({
        account_id              = data.aws_caller_identity.current.account_id
        cell_id                 = var.cell_id
        environment             = var.environment
        region                  = data.aws_region.current.region
        scanner_role_id         = aws_iam_role.deadline_scanner.unique_id
        source_queue_arn        = aws_sqs_queue.deadline_source.arn
        registered_deadline_key = "DEADLINE#0#"
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

resource "aws_lambda_event_source_mapping" "evidence_normalizer_ecs" {
  event_source_arn                   = aws_sqs_queue.ecs_event_source.arn
  function_name                      = aws_lambda_function.evidence_normalizer.arn
  batch_size                         = var.normalizer.batch_size
  maximum_batching_window_in_seconds = var.normalizer.batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_lambda_event_source_mapping" "evidence_normalizer_deadline" {
  event_source_arn                   = aws_sqs_queue.deadline_source.arn
  function_name                      = aws_lambda_function.evidence_normalizer.arn
  batch_size                         = var.normalizer.batch_size
  maximum_batching_window_in_seconds = var.normalizer.batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
}

data "aws_iam_policy_document" "log_ingestor_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "log_ingestor" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/log-ingestor"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.log_ingestor.log_retention_days
  tags              = local.common_tags
}

data "aws_iam_policy_document" "log_ingestor" {
  statement {
    sid       = "ReadOnlyCompletionSource"
    effect    = "Allow"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.completion_source.arn]
  }
  statement {
    sid       = "ReadOnlyTaskIndex"
    effect    = "Allow"
    actions   = ["dynamodb:Query"]
    resources = ["${aws_dynamodb_table.occurrence_ledger.arn}/index/task-arn"]
  }
  statement {
    sid       = "ReadOnlyMappedOccurrence"
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["JOB#${var.canary_normalizer_registration.job_id}"]
    }
  }
  statement {
    sid       = "WriteOnlyCanonicalCompletions"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.process_manager_ingress.arn, aws_sqs_queue.normalizer_quarantine.arn]
  }
  statement {
    sid       = "WriteOnlyOwnLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.log_ingestor.arn}:*"]
  }
  statement {
    sid       = "UseOnlyCompletionAndIngressQueueKeys"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "kms:EncryptionContext:aws:sqs:arn"
      values   = [aws_sqs_queue.completion_source.arn, aws_sqs_queue.process_manager_ingress.arn, aws_sqs_queue.normalizer_quarantine.arn]
    }
  }
}

resource "aws_iam_role" "log_ingestor" {
  name                 = "${local.name_prefix}-log-ingestor"
  path                 = "/platform/ecs-scheduled-jobs/${var.cell_id}/v1/"
  assume_role_policy   = data.aws_iam_policy_document.log_ingestor_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_iam_role_policy" "log_ingestor" {
  name   = "${local.name_prefix}-log-ingestor"
  role   = aws_iam_role.log_ingestor.id
  policy = data.aws_iam_policy_document.log_ingestor.json
}

resource "aws_lambda_function" "log_ingestor" {
  function_name                  = "${local.name_prefix}-log-ingestor"
  filename                       = var.log_ingestor.artifact_path
  source_code_hash               = var.log_ingestor.artifact_source_hash
  handler                        = "log_ingestor.handler.lambda_handler"
  role                           = aws_iam_role.log_ingestor.arn
  runtime                        = "python3.14"
  timeout                        = var.log_ingestor.timeout_seconds
  reserved_concurrent_executions = var.log_ingestor.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn
  environment {
    variables = {
      LOG_INGESTOR_OCCURRENCE_TABLE_NAME           = aws_dynamodb_table.occurrence_ledger.name
      LOG_INGESTOR_RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
      LOG_INGESTOR_PROCESS_MANAGER_QUEUE_URL       = aws_sqs_queue.process_manager_ingress.url
      LOG_INGESTOR_QUARANTINE_QUEUE_URL            = aws_sqs_queue.normalizer_quarantine.url
    }
  }
  depends_on = [aws_cloudwatch_log_group.log_ingestor]
  tags       = local.common_tags
}

resource "aws_lambda_event_source_mapping" "log_ingestor" {
  event_source_arn                   = aws_sqs_queue.completion_source.arn
  function_name                      = aws_lambda_function.log_ingestor.arn
  batch_size                         = var.log_ingestor.batch_size
  maximum_batching_window_in_seconds = var.log_ingestor.batch_window_seconds
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
      test     = "StringEquals"
      variable = "kms:EncryptionContext:aws:s3:arn"
      values = [
        "${aws_s3_bucket.config_inbox.arn}/jobs/${var.canary_normalizer_registration.job_id}/config/${var.canary_normalizer_registration.config_version}.json"
      ]
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
    MATERIALIZER_CONTRACTS_ROOT                  = "/var/task/contracts/v1"
    MATERIALIZER_CONFIG_BUCKET                   = aws_s3_bucket.config_inbox.bucket
    MATERIALIZER_CONFIG_KEY                      = "jobs/${var.canary_normalizer_registration.job_id}/config/${var.canary_normalizer_registration.config_version}.json"
    MATERIALIZER_CONFIG_REGISTRY_TABLE           = aws_dynamodb_table.configuration_registry.name
    MATERIALIZER_RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
    MATERIALIZER_NAMESPACE_REGISTRY_TABLE        = aws_dynamodb_table.namespace_registry.name
    MATERIALIZER_SOURCE_QUEUE_URL                = aws_sqs_queue.materializer_ingress.url
    MATERIALIZER_METRIC_NAMESPACE                = var.metric_namespace
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

data "aws_iam_policy_document" "ecs_event_source" {
  statement {
    sid       = "AllowOnlyThisCellEcsRule"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.ecs_event_source.arn, aws_sqs_queue.ecs_event_source_dlq.arn]
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
      values   = [aws_cloudwatch_event_rule.ecs_task_state.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "ecs_event_source" {
  queue_url = aws_sqs_queue.ecs_event_source.id
  policy    = data.aws_iam_policy_document.ecs_event_source.json
}

resource "aws_sqs_queue_policy" "ecs_event_source_dlq" {
  queue_url = aws_sqs_queue.ecs_event_source_dlq.id
  policy    = data.aws_iam_policy_document.ecs_event_source.json
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

resource "aws_sqs_queue" "command_handler_dlq" {
  name                              = "${local.name_prefix}-commands-dlq"
  message_retention_seconds         = var.command_handler.queue_retention_days * 86400
  kms_master_key_id                 = var.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  tags                              = local.common_tags
}

resource "aws_sqs_queue" "command_handler_queue" {
  name                              = "${local.name_prefix}-commands"
  message_retention_seconds         = var.command_handler.queue_retention_days * 86400
  visibility_timeout_seconds        = var.command_handler.visibility_seconds
  kms_master_key_id                 = var.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  receive_wait_time_seconds         = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.command_handler_dlq.arn
    maxReceiveCount     = var.command_handler.max_receive_count
  })
  tags = local.common_tags
}

resource "aws_sqs_queue" "recovery_dlq" {
  name                      = "${local.name_prefix}-recovery-dlq"
  message_retention_seconds = var.command_handler.queue_retention_days * 86400
  kms_master_key_id         = var.kms_key_arn
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "recovery_queue" {
  name                              = "${local.name_prefix}-recovery"
  message_retention_seconds         = var.command_handler.queue_retention_days * 86400
  visibility_timeout_seconds        = var.command_handler.visibility_seconds
  kms_master_key_id                 = var.kms_key_arn
  kms_data_key_reuse_period_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.recovery_dlq.arn
    maxReceiveCount     = var.command_handler.max_receive_count
  })
  tags = local.common_tags
}

resource "aws_sqs_queue_policy" "recovery_queue" {
  queue_url = aws_sqs_queue.recovery_queue.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowOnlyCellNormalizer"
      Effect    = "Allow"
      Principal = { AWS = aws_iam_role.evidence_normalizer.arn }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.recovery_queue.arn
    }]
  })
}

data "aws_iam_policy_document" "command_handler_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "command_handler" {
  statement {
    effect  = "Allow"
    actions = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = [
      aws_dynamodb_table.occurrence_ledger.arn,
      "${aws_dynamodb_table.occurrence_ledger.arn}/index/job-scheduled-time",
    ]
  }
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
    condition {
      test     = "ForAllValues:StringLike"
      variable = "dynamodb:LeadingKeys"
      values   = ["APPROVAL#*"]
    }
  }
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.command_authorizations.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.command_handler_queue.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.command_handler.broker_secret_arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["dynamodb.${data.aws_region.current.region}.amazonaws.com"]
    }
  }
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.command_handler.arn}:*"]
  }
  statement {
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
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["sqs.${data.aws_region.current.region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "command_handler" {
  name                 = "${local.name_prefix}-command-handler"
  assume_role_policy   = data.aws_iam_policy_document.command_handler_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_dynamodb_table" "command_authorizations" {
  name                        = "${local.name_prefix}-command-authorizations"
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
  tags = local.common_tags
}

resource "aws_dynamodb_table" "recovery_manifests" {
  name                        = "${local.name_prefix}-recovery-manifests"
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
  tags = local.common_tags
}

resource "aws_ssm_parameter" "recovery_generation" {
  name   = "/platform/ecs-scheduled-jobs/${var.environment}/${data.aws_region.current.region}/recovery-generation"
  type   = "SecureString"
  key_id = var.kms_key_arn
  value = jsonencode({
    recovery_generation = "INITIAL"
    deployment_identity = "INITIAL"
    tables = [
      aws_dynamodb_table.namespace_registry.name,
      aws_dynamodb_table.configuration_registry.name,
      aws_dynamodb_table.occurrence_ledger.name,
      aws_dynamodb_table.deadline_checkpoint.name,
      aws_dynamodb_table.notification_ledger.name,
    ]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "command_handler" {
  name   = "${local.name_prefix}-command-handler"
  role   = aws_iam_role.command_handler.id
  policy = data.aws_iam_policy_document.command_handler.json
}

data "aws_iam_policy_document" "recovery_controller_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

data "aws_iam_policy_document" "recovery_controller" {
  statement {
    sid       = "ReadAndRestoreCellTables"
    effect    = "Allow"
    actions   = ["dynamodb:DescribeTable", "dynamodb:DescribeContinuousBackups", "dynamodb:RestoreTableToPointInTime"]
    resources = [aws_dynamodb_table.namespace_registry.arn, aws_dynamodb_table.configuration_registry.arn, aws_dynamodb_table.occurrence_ledger.arn, aws_dynamodb_table.deadline_checkpoint.arn, aws_dynamodb_table.notification_ledger.arn]
  }
  statement {
    sid       = "ConfigureOnlyRecoveryTables"
    effect    = "Allow"
    actions   = ["dynamodb:DescribeTable", "dynamodb:TagResource", "dynamodb:UpdateContinuousBackups", "dynamodb:UpdateTable"]
    resources = ["arn:aws:dynamodb:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:table/${local.name_prefix}-*-recovery-*"]
  }
  statement {
    sid       = "WriteOnlyRecoveryManifest"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem"]
    resources = [aws_dynamodb_table.recovery_manifests.arn]
  }
  statement {
    sid       = "PauseCellSchedules"
    effect    = "Allow"
    actions   = ["scheduler:GetSchedule", "scheduler:UpdateSchedule"]
    resources = ["arn:aws:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule/${aws_scheduler_schedule_group.cell.name}/*"]
  }
  statement {
    sid     = "UpdateCellEventSources"
    effect  = "Allow"
    actions = ["lambda:UpdateEventSourceMapping"]
    resources = [
      for mapping in [
        aws_lambda_event_source_mapping.alert_router,
        aws_lambda_event_source_mapping.process_manager,
        aws_lambda_event_source_mapping.evidence_normalizer,
        aws_lambda_event_source_mapping.evidence_normalizer_ecs,
        aws_lambda_event_source_mapping.evidence_normalizer_deadline,
        aws_lambda_event_source_mapping.materializer_normalizer,
        aws_lambda_event_source_mapping.command_normalizer,
        aws_lambda_event_source_mapping.log_ingestor,
      ] : "arn:aws:lambda:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:event-source-mapping:${mapping.uuid}"
    ]
  }
  statement {
    sid     = "InvokeRecoveryChecks"
    effect  = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [
      aws_lambda_function.alert_router.arn,
      aws_lambda_function.process_manager.arn,
      aws_lambda_function.occurrence_materializer.arn,
      aws_lambda_function.deadline_scanner.arn,
    ]
  }
  statement {
    sid       = "UpdateRecoveryPointer"
    effect    = "Allow"
    actions   = ["ssm:PutParameter", "ssm:GetParameter"]
    resources = [aws_ssm_parameter.recovery_generation.arn]
  }
  statement {
    sid       = "ConsumeRecoveryQueue"
    effect    = "Allow"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.recovery_queue.arn]
  }
  statement {
    sid       = "PublishRecoveryMetrics"
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
    sid       = "UseRecoveryEncryptionKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role" "recovery_controller" {
  name                 = "${local.name_prefix}-recovery-controller"
  assume_role_policy   = data.aws_iam_policy_document.recovery_controller_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_iam_role_policy" "recovery_controller" {
  name   = "${local.name_prefix}-recovery-controller"
  role   = aws_iam_role.recovery_controller.id
  policy = data.aws_iam_policy_document.recovery_controller.json
}

data "aws_iam_policy_document" "recovery_controller_logs" {
  statement {
    sid       = "WriteRecoveryLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.recovery_controller.arn}:*"]
  }
}

resource "aws_iam_role_policy" "recovery_controller_logs" {
  name   = "${local.name_prefix}-recovery-controller-logs"
  role   = aws_iam_role.recovery_controller.id
  policy = data.aws_iam_policy_document.recovery_controller_logs.json
}

data "aws_iam_policy_document" "lifecycle_gc_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:lambda:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:function:${local.name_prefix}-lifecycle-gc"]
    }
  }
}

data "aws_iam_policy_document" "lifecycle_gc" {
  statement {
    sid    = "DenyNonLifecycleMutation"
    effect = "Deny"
    actions = [
      "dynamodb:DeleteItem",
      "dynamodb:DeleteTable",
      join("", ["ecs:Run", "Task"]),
      join("", ["iam:Pass", "Role"]),
      "iam:PutRolePolicy",
      "iam:UpdateAssumeRolePolicy",
      "s3:DeleteObject",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "InventoryCellVersions"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
    ]
    resources = [
      aws_dynamodb_table.namespace_registry.arn,
      aws_dynamodb_table.configuration_registry.arn,
      aws_dynamodb_table.occurrence_ledger.arn,
      aws_dynamodb_table.deadline_checkpoint.arn,
      aws_dynamodb_table.notification_ledger.arn,
      aws_dynamodb_table.recovery_manifests.arn,
    ]
  }

  statement {
    sid    = "ReadConfigInventory"
    effect = "Allow"
    actions = [
      "s3:GetBucketVersioning",
      "s3:ListBucket",
      "s3:ListBucketVersions",
      "s3:GetObject",
      "s3:GetObjectAttributes",
      "s3:GetObjectVersion",
    ]
    resources = [aws_s3_bucket.config_inbox.arn, "${aws_s3_bucket.config_inbox.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:ResourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid     = "ReadLifecyclePointers"
    effect  = "Allow"
    actions = ["ssm:GetParameter", "ssm:GetParameterHistory"]
    resources = [
      aws_ssm_parameter.recovery_generation.arn,
      aws_ssm_parameter.cell_contract.arn,
    ]
  }

  statement {
    sid     = "ReadLifecycleQueues"
    effect  = "Allow"
    actions = ["sqs:GetQueueAttributes", "sqs:ListDeadLetterSourceQueues"]
    resources = [
      aws_sqs_queue.deadline_source.arn,
      aws_sqs_queue.deadline_source_dlq.arn,
      aws_sqs_queue.alert_router_dlq.arn,
      aws_sqs_queue.command_handler_queue.arn,
      aws_sqs_queue.command_handler_dlq.arn,
      aws_sqs_queue.recovery_queue.arn,
      aws_sqs_queue.recovery_dlq.arn,
    ]
  }

  statement {
    sid    = "ReadRuntimeInventory"
    effect = "Allow"
    actions = [
      "lambda:GetFunction",
      "lambda:ListAliases",
      "lambda:ListVersionsByFunction",
    ]
    resources = [
      aws_lambda_function.alert_router.arn,
      aws_lambda_function.command_handler.arn,
      aws_lambda_function.deadline_scanner.arn,
      aws_lambda_function.evidence_normalizer.arn,
      aws_lambda_function.log_ingestor.arn,
      aws_lambda_function.occurrence_materializer.arn,
      aws_lambda_function.process_manager.arn,
      aws_lambda_function.recovery_controller.arn,
    ]
  }

  statement {
    sid     = "ReadEcsTaskInventory"
    effect  = "Allow"
    actions = ["ecs:DescribeTaskDefinition", "ecs:ListTagsForResource"]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.name_prefix}-*"
    ]
  }

  statement {
    sid       = "DeleteExactConfigVersion"
    effect    = "Allow"
    actions   = ["s3:DeleteObjectVersion"]
    resources = ["${aws_s3_bucket.config_inbox.arn}/jobs/*/config/*.json"]
    condition {
      test     = "StringEquals"
      variable = "s3:ResourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid    = "DeleteCellRuntimeVersion"
    effect = "Allow"
    actions = [
      "lambda:DeleteFunction",
    ]
    resources = [
      aws_lambda_function.alert_router.arn,
      aws_lambda_function.command_handler.arn,
      aws_lambda_function.deadline_scanner.arn,
      aws_lambda_function.evidence_normalizer.arn,
      aws_lambda_function.log_ingestor.arn,
      aws_lambda_function.occurrence_materializer.arn,
      aws_lambda_function.process_manager.arn,
      aws_lambda_function.recovery_controller.arn,
    ]
  }

  statement {
    sid       = "WriteLifecycleEvidence"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.recovery_manifests.arn]
    condition {
      test     = "ForAllValues:StringEquals"
      variable = "dynamodb:LeadingKeys"
      values   = ["LIFECYCLE#${var.cell_id}"]
    }
  }

  statement {
    sid       = "PublishLifecycleMetrics"
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

resource "aws_iam_role" "lifecycle_gc" {
  name                 = "${local.name_prefix}-lifecycle-gc"
  assume_role_policy   = data.aws_iam_policy_document.lifecycle_gc_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_iam_role_policy" "lifecycle_gc" {
  name   = "${local.name_prefix}-lifecycle-gc"
  role   = aws_iam_role.lifecycle_gc.id
  policy = data.aws_iam_policy_document.lifecycle_gc.json
}

resource "aws_cloudwatch_log_group" "lifecycle_gc" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/lifecycle-gc"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.command_handler.log_retention_days
  tags              = local.common_tags
}

resource "aws_cloudwatch_event_rule" "lifecycle_gc_schedule" {
  name                = "${local.name_prefix}-lifecycle-gc"
  description         = "Disabled-by-default lifecycle cleanup control-plane trigger."
  schedule_expression = var.lifecycle_cleanup_schedule_expression
  is_enabled          = var.lifecycle_cleanup_enabled
  tags                = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lifecycle_gc_blocked" {
  alarm_name          = "${local.name_prefix}-lifecycle-gc-blocked"
  alarm_description   = "Lifecycle cleanup candidates are being blocked by safety gates."
  namespace           = var.metric_namespace
  metric_name         = "LifecycleCleanupBlocked"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { CellId = var.cell_id }
  tags                = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "lifecycle_gc_failure" {
  alarm_name          = "${local.name_prefix}-lifecycle-gc-failure"
  alarm_description   = "Lifecycle cleanup execution reported a failure."
  namespace           = var.metric_namespace
  metric_name         = "LifecycleCleanupFailure"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { CellId = var.cell_id }
  tags                = local.common_tags
}

data "aws_iam_policy_document" "recovery_pointer_consumers" {
  statement {
    sid       = "ReadCellRecoveryPointer"
    effect    = "Allow"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.recovery_generation.arn]
  }
  statement {
    sid       = "DecryptCellRecoveryPointer"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${data.aws_region.current.region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "recovery_pointer_consumers" {
  for_each = {
    alert_router            = aws_iam_role.alert_router.id
    deadline_scanner        = aws_iam_role.deadline_scanner.id
    evidence_normalizer     = aws_iam_role.evidence_normalizer.id
    log_ingestor            = aws_iam_role.log_ingestor.id
    occurrence_materializer = aws_iam_role.occurrence_materializer.id
    process_manager         = aws_iam_role.process_manager.id
  }
  name   = "${local.name_prefix}-${each.key}-recovery-pointer"
  role   = each.value
  policy = data.aws_iam_policy_document.recovery_pointer_consumers.json
}

resource "aws_cloudwatch_log_group" "recovery_controller" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/recovery-controller"
  kms_key_id        = var.kms_key_arn
  retention_in_days = var.command_handler.log_retention_days
  tags              = local.common_tags
}

resource "aws_lambda_function" "recovery_controller" {
  function_name                  = "${local.name_prefix}-recovery-controller"
  filename                       = var.command_handler.artifact_path
  source_code_hash               = var.command_handler.artifact_source_hash
  handler                        = "command_handler.recovery_handler.lambda_handler"
  role                           = aws_iam_role.recovery_controller.arn
  runtime                        = "python3.14"
  timeout                        = var.command_handler.timeout_seconds
  reserved_concurrent_executions = 1
  kms_key_arn                    = var.kms_key_arn
  environment {
    variables = {
      RECOVERY_CELL_ID                = var.cell_id
      RECOVERY_ACCOUNT_ID             = data.aws_caller_identity.current.account_id
      RECOVERY_REGION                 = data.aws_region.current.region
      RECOVERY_ENVIRONMENT            = var.environment
      RECOVERY_OWNER                  = var.owner
      RECOVERY_KMS_KEY_ARN            = var.kms_key_arn
      RECOVERY_METRIC_NAMESPACE       = var.metric_namespace
      RECOVERY_MANIFEST_TABLE_NAME    = aws_dynamodb_table.recovery_manifests.name
      RECOVERY_POINTER_PARAMETER_NAME = aws_ssm_parameter.recovery_generation.name
      RECOVERY_SOURCE_TABLES          = jsonencode([aws_dynamodb_table.namespace_registry.name, aws_dynamodb_table.configuration_registry.name, aws_dynamodb_table.occurrence_ledger.name, aws_dynamodb_table.deadline_checkpoint.name, aws_dynamodb_table.notification_ledger.name])
      RECOVERY_SCHEDULES              = jsonencode([{ name = "${local.name_prefix}-canary", group_name = aws_scheduler_schedule_group.cell.name }])
      RECOVERY_EVENT_SOURCE_MAPPINGS = jsonencode([
        aws_lambda_event_source_mapping.alert_router.uuid,
        aws_lambda_event_source_mapping.process_manager.uuid,
        aws_lambda_event_source_mapping.evidence_normalizer.uuid,
        aws_lambda_event_source_mapping.evidence_normalizer_ecs.uuid,
        aws_lambda_event_source_mapping.evidence_normalizer_deadline.uuid,
        aws_lambda_event_source_mapping.materializer_normalizer.uuid,
        aws_lambda_event_source_mapping.command_normalizer.uuid,
        aws_lambda_event_source_mapping.log_ingestor.uuid,
      ])
      RECOVERY_REPLAY_MAPPINGS = jsonencode([
        aws_lambda_event_source_mapping.evidence_normalizer.uuid,
        aws_lambda_event_source_mapping.evidence_normalizer_ecs.uuid,
        aws_lambda_event_source_mapping.evidence_normalizer_deadline.uuid,
        aws_lambda_event_source_mapping.process_manager.uuid,
        aws_lambda_event_source_mapping.materializer_normalizer.uuid,
        aws_lambda_event_source_mapping.alert_router.uuid,
      ])
      RECOVERY_RECONCILIATION_FUNCTIONS = jsonencode([
        aws_lambda_function.occurrence_materializer.arn,
        aws_lambda_function.deadline_scanner.arn,
        aws_lambda_function.alert_router.arn,
      ])
    }
  }
  depends_on = [aws_cloudwatch_log_group.recovery_controller]
  tags       = local.common_tags
}

resource "aws_lambda_event_source_mapping" "recovery_controller" {
  event_source_arn                   = aws_sqs_queue.recovery_queue.arn
  function_name                      = aws_lambda_function.recovery_controller.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_cloudwatch_log_group" "command_handler" {
  name              = "/platform/ecs-scheduled-jobs/${var.cell_id}/command-handler"
  retention_in_days = var.command_handler.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = local.common_tags
}

resource "aws_lambda_function" "command_handler" {
  function_name                  = "${local.name_prefix}-command-handler"
  filename                       = var.command_handler.artifact_path
  source_code_hash               = var.command_handler.artifact_source_hash
  handler                        = "command_handler.handler.lambda_handler"
  role                           = aws_iam_role.command_handler.arn
  runtime                        = "python3.14"
  timeout                        = var.command_handler.timeout_seconds
  reserved_concurrent_executions = var.command_handler.reserved_concurrency
  kms_key_arn                    = var.kms_key_arn
  environment {
    variables = {
      COMMAND_OCCURRENCE_TABLE_NAME    = aws_dynamodb_table.occurrence_ledger.name
      COMMAND_AUTHORIZATION_TABLE_NAME = aws_dynamodb_table.command_authorizations.name
      COMMAND_QUEUE_URL                = aws_sqs_queue.command_handler_queue.url
      COMMAND_CELL_ID                  = var.cell_id
      COMMAND_ACCOUNT_ID               = data.aws_caller_identity.current.account_id
      COMMAND_REGION                   = data.aws_region.current.region
      COMMAND_BROKER_SECRET_ARN        = var.command_handler.broker_secret_arn
      COMMAND_METRIC_NAMESPACE         = var.metric_namespace
    }
  }
  depends_on = [aws_cloudwatch_log_group.command_handler]
  tags       = local.common_tags
}

data "aws_iam_policy_document" "command_queue" {
  statement {
    sid       = "HandlerOnlySend"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.command_handler_queue.arn]
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.command_handler.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "command_queue" {
  queue_url = aws_sqs_queue.command_handler_queue.id
  policy    = data.aws_iam_policy_document.command_queue.json
}

resource "aws_lambda_event_source_mapping" "command_normalizer" {
  event_source_arn                   = aws_sqs_queue.command_handler_queue.arn
  function_name                      = aws_lambda_function.evidence_normalizer.arn
  batch_size                         = var.normalizer.batch_size
  maximum_batching_window_in_seconds = var.normalizer.batch_window_seconds
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_cloudwatch_metric_alarm" "command_queue_age" {
  alarm_name          = "${local.name_prefix}-command-queue-age"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  dimensions          = { QueueName = aws_sqs_queue.command_handler_queue.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 5
  threshold           = var.command_handler.visibility_seconds
  comparison_operator = "GreaterThanThreshold"
  alarm_description   = "Authorized command evidence is not being consumed within the bounded visibility window."
  treat_missing_data  = "notBreaching"
  tags                = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "command_dlq_messages" {
  alarm_name          = "${local.name_prefix}-command-dlq-messages"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.command_handler_dlq.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  alarm_description   = "Authorized command evidence is quarantined in the command DLQ."
  treat_missing_data  = "notBreaching"
  tags                = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "command_break_glass" {
  alarm_name          = "${local.name_prefix}-command-break-glass"
  namespace           = var.metric_namespace
  metric_name         = "BreakGlassCommandAccepted"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  alarm_description   = "A break-glass command was accepted and requires immediate review."
  treat_missing_data  = "notBreaching"
  tags                = local.common_tags
}

data "aws_iam_policy_document" "operator_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole", "sts:TagSession"]
    principals {
      type        = "AWS"
      identifiers = var.operator.trusted_principal_arns
    }
    condition {
      test     = "Bool"
      variable = "aws:MultiFactorAuthPresent"
      values   = ["true"]
    }
    condition {
      test     = "StringLike"
      variable = "sts:SourceIdentity"
      values   = ["operator:*"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/PlatformCell"
      values   = [var.cell_id]
    }
    condition {
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"
      values   = ["PlatformCell", "Actor", "ApprovalReference", "BreakGlassApproved"]
    }
  }
}

data "aws_iam_policy_document" "operator" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.command_handler.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.occurrence_ledger.arn]
  }
  statement {
    effect    = "Allow"
    actions   = ["logs:FilterLogEvents"]
    resources = ["${aws_cloudwatch_log_group.command_handler.arn}:*"]
  }
}

resource "aws_iam_role" "operator" {
  name                 = "${local.name_prefix}-operator"
  assume_role_policy   = data.aws_iam_policy_document.operator_assume_role.json
  permissions_boundary = var.operator.permissions_boundary_arn
  max_session_duration = var.operator.max_session_duration
  tags                 = local.common_tags
}

resource "aws_iam_role_policy" "operator" {
  name   = "${local.name_prefix}-operator"
  role   = aws_iam_role.operator.id
  policy = data.aws_iam_policy_document.operator.json
}
