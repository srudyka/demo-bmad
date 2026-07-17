provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = local.common_tags
  }
}

provider "aws" {
  alias               = "config_publisher"
  region              = var.region
  allowed_account_ids = [var.account_id]

  assume_role {
    role_arn     = var.cell_config_publisher_role_arn
    session_name = "platform-canary-config-publisher"
  }
}

locals {
  name_prefix  = "${var.environment}-${var.application}-canary"
  schedule_arn = "arn:aws:scheduler:${var.region}:${var.account_id}:schedule/${var.cell_scheduler_group_name}/${local.name_prefix}"
  common_tags = merge(var.tags, {
    Application = var.application
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner
    Repository  = var.repository_id
    Service     = var.service
  })
  schedule_contract = {
    activation_end       = null
    activation_start     = var.activation_start
    evaluator_version    = "schedule-evaluator/1.0.0"
    expression           = var.schedule_expression
    flexible_time_window = "OFF"
    start_anchor         = var.activation_start
    time_zone            = var.schedule_time_zone
    tzdb_version         = "2026b"
  }
  # The schedule contract uses an ASCII-only profile, making Terraform's
  # jsonencode byte-equivalent to the required canonical JSON profile here.
  schedule_generation = sha256("schedule/v1\n${jsonencode(local.schedule_contract)}")
}

data "aws_iam_policy_document" "launch_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.cell_process_manager_role_arn]
    }
  }
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "launch" {
  name                 = "${local.name_prefix}-launch"
  assume_role_policy   = data.aws_iam_policy_document.launch_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

data "aws_iam_policy_document" "launch" {
  statement {
    sid       = "PassOnlyThisTasksRolesToEcs"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.execution.arn, aws_iam_role.task.arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "launch" {
  name   = "${local.name_prefix}-launch-pass-role"
  role   = aws_iam_role.launch.id
  policy = data.aws_iam_policy_document.launch.json
}

resource "aws_iam_role" "execution" {
  name                 = "${local.name_prefix}-execution"
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid       = "PullOnlyTheCanaryImage"
    effect    = "Allow"
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [var.ecr_repository_arn]
  }

  # ECR authorization tokens cannot be scoped to a repository by AWS.
  statement {
    sid       = "GetRequiredEcrAuthorizationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid       = "WriteOnlyTheCanaryLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.canary.arn}:*"]
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "${local.name_prefix}-execution"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

resource "aws_iam_role" "task" {
  name                 = "${local.name_prefix}-task"
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

resource "aws_cloudwatch_log_group" "canary" {
  name              = "/platform/jobs/${replace(var.job_id, "/", "-")}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cell_kms_key_arn
  tags              = local.common_tags
}

resource "aws_ecs_task_definition" "canary" {
  family                   = local.name_prefix
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  tags                     = local.common_tags

  container_definitions = jsonencode([{
    command   = var.command
    essential = true
    environment = [
      { name = "JOB_COMPLETION_LOG_MARKER", value = "JOB_COMPLETED_SUCCESSFULLY" },
      { name = "JOB_ID", value = var.job_id },
    ]
    image = var.image_uri
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.canary.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "canary"
      }
    }
    name = "canary"
  }])

  lifecycle {
    precondition {
      condition = contains([
        "256/512", "256/1024", "256/2048",
        "512/1024", "512/2048", "512/3072", "512/4096",
        "1024/2048", "1024/3072", "1024/4096", "1024/5120", "1024/6144", "1024/7168", "1024/8192",
        "2048/4096", "2048/5120", "2048/6144", "2048/7168", "2048/8192", "2048/9216", "2048/10240", "2048/11264", "2048/12288", "2048/13312", "2048/14336", "2048/15360", "2048/16384",
        "4096/8192", "4096/9216", "4096/10240", "4096/11264", "4096/12288", "4096/13312", "4096/14336", "4096/15360", "4096/16384", "4096/17408", "4096/18432", "4096/19456", "4096/20480", "4096/21504", "4096/22528", "4096/23552", "4096/24576", "4096/25600", "4096/26624", "4096/27648", "4096/28672", "4096/29696", "4096/30720",
        ], "${var.cpu}/${var.memory}") || (
        var.cpu == 8192 && var.memory >= 16384 && var.memory <= 61440 && var.memory % 4096 == 0
        ) || (
        var.cpu == 16384 && var.memory >= 32768 && var.memory <= 122880 && var.memory % 8192 == 0
      )
      error_message = "FARGATE_CPU_MEMORY_INVALID: cpu and memory must be a supported Fargate combination."
    }

    precondition {
      condition = (
        split("/", var.job_id)[0] == var.environment &&
        split("/", var.job_id)[1] == var.application &&
        split(":", var.apply_role_arn)[4] == var.account_id &&
        var.terraform_root_id == "fixtures/canary" &&
        var.cell_contract_parameter_arn == "arn:aws:ssm:${var.region}:${var.account_id}:parameter/platform/ecs-scheduled-jobs/${var.environment}/${var.region}/contract" &&
        can(regex("^arn:[a-z0-9-]+:kms:${var.region}:${var.account_id}:key/[0-9a-fA-F-]+$", var.cell_kms_key_arn)) &&
        can(regex("^arn:[a-z0-9-]+:iam::${var.account_id}:role/.+$", var.cell_process_manager_role_arn)) &&
        can(regex("^arn:[a-z0-9-]+:iam::${var.account_id}:role/.+$", var.cell_config_publisher_role_arn)) &&
        can(regex("^arn:[a-z0-9-]+:sqs:${var.region}:${var.account_id}:.+$", var.cell_scheduler_source_queue_arn)) &&
        can(regex("^arn:[a-z0-9-]+:sqs:${var.region}:${var.account_id}:.+$", var.cell_scheduler_dlq_arn))
      )
      error_message = "CANARY_CELL_INPUT_MISMATCH: fixture identity and Cell resource inputs must belong to the explicit account, Region, and canonical fixture root."
    }

    precondition {
      condition = (
        timecmp(var.activation_start, timestamp()) > 0 &&
        can(regex("^(rate|cron)\\(.+\\)$", var.schedule_expression)) &&
        can(regex("^[A-Za-z_]+/[A-Za-z_]+$|^UTC$", var.schedule_time_zone))
      )
      error_message = "CANARY_SCHEDULE_INVALID: activation_start must be future and schedule expression/time zone must use the supported Scheduler forms."
    }

    precondition {
      condition = (
        can(regex("^arn:[a-z0-9-]+:ecr:${var.region}:${var.account_id}:repository/.+$", var.ecr_repository_arn)) &&
        can(regex("^${var.account_id}\\.dkr\\.ecr\\.${var.region}\\.amazonaws\\.com/.+@sha256:[0-9a-f]{64}$", var.image_uri))
      )
      error_message = "CANARY_ECR_IMAGE_MISMATCH: image_uri and ecr_repository_arn must describe an ECR repository in the explicit account and Region."
    }
  }
}

data "aws_iam_policy_document" "scheduler_delivery_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [local.schedule_arn]
    }
  }
}

resource "aws_iam_role" "scheduler_delivery" {
  name                 = "${local.name_prefix}-scheduler-delivery"
  assume_role_policy   = data.aws_iam_policy_document.scheduler_delivery_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.common_tags
}

data "aws_iam_policy_document" "scheduler_delivery" {
  statement {
    sid       = "SendOnlyToTheCellSchedulerQueues"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [var.cell_scheduler_source_queue_arn, var.cell_scheduler_dlq_arn]
  }
}

resource "aws_iam_role_policy" "scheduler_delivery" {
  name   = "${local.name_prefix}-scheduler-delivery"
  role   = aws_iam_role.scheduler_delivery.id
  policy = data.aws_iam_policy_document.scheduler_delivery.json
}

resource "aws_scheduler_schedule" "canary" {
  name                         = local.name_prefix
  group_name                   = var.cell_scheduler_group_name
  kms_key_arn                  = var.cell_kms_key_arn
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_time_zone
  start_date                   = var.activation_start
  state                        = "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.cell_scheduler_source_queue_arn
    role_arn = aws_iam_role.scheduler_delivery.arn
    input = jsonencode({
      account_id               = var.account_id
      config_version           = local.config_version
      event_type               = "occurrence.launch.v1"
      job_id                   = var.job_id
      ownership_generation     = var.ownership_generation
      producer_id              = "scheduler"
      region                   = var.region
      schedule_arn             = local.schedule_arn
      schedule_generation      = local.schedule_generation
      schedule_group_arn       = "arn:aws:scheduler:${var.region}:${var.account_id}:schedule-group/${var.cell_scheduler_group_name}"
      scheduler_scheduled_time = "<aws.scheduler.scheduled-time>"
      schema_version           = "1.0.0"
      source_queue_arn         = var.cell_scheduler_source_queue_arn
    })

    dead_letter_config {
      arn = var.cell_scheduler_dlq_arn
    }

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }
  }
}

resource "aws_sqs_queue" "test_notification_sink" {
  name                      = "${local.name_prefix}-test-notifications"
  kms_master_key_id         = var.cell_kms_key_arn
  message_retention_seconds = 1209600
  tags                      = local.common_tags
}

locals {
  deployment_identity = {
    account_id = var.account_id
    artifact_checksums = {
      config_schema = "82cfcfaa674238e762ae76e469632da71e81a1c45fd735dbc4e7fc0117a59562"
    }
    contract_version    = "1.0.0"
    environment         = var.environment
    image_digest        = regex("sha256:[0-9a-f]{64}$", var.image_uri)
    module_versions     = { ecs_scheduled_job = "1.0.0" }
    region              = var.region
    resolved_platform   = { fargate = "LATEST", lambda_runtime = "python3.14" }
    source_commit       = var.source_commit
    task_definition_arn = aws_ecs_task_definition.canary.arn
    tool_versions       = { terraform = "1.15.8" }
    workflow = {
      job_workflow_ref = var.workflow_ref
      run_id           = var.workflow_run_id
      workflow_sha     = var.workflow_sha
    }
  }
  deployment_identity_id = sha256(jsonencode(local.deployment_identity))
  config_body = {
    cluster_arn               = var.ecs_cluster_arn
    completion_window_seconds = var.completion_window_seconds
    deployment_identity_id    = local.deployment_identity_id
    job_id                    = var.job_id
    logs = {
      log_group_arn  = aws_cloudwatch_log_group.canary.arn
      retention_days = var.log_retention_days
    }
    network = {
      assign_public_ip   = "DISABLED"
      security_group_ids = sort(tolist(var.security_group_ids))
      subnet_ids         = sort(tolist(var.private_subnet_ids))
    }
    notification_target_arn = aws_sqs_queue.test_notification_sink.arn
    overlap_policy          = var.overlap_policy
    owner_generation        = var.ownership_generation
    role_arns = {
      execution = aws_iam_role.execution.arn
      launch    = aws_iam_role.launch.arn
      task      = aws_iam_role.task.arn
    }
    schedule                   = local.schedule_contract
    schedule_arn               = local.schedule_arn
    schedule_generation        = local.schedule_generation
    scheduler_delivery_role_id = aws_iam_role.scheduler_delivery.unique_id
    secret_references          = []
    task_definition_arn        = aws_ecs_task_definition.canary.arn
  }
  config_version = sha256(jsonencode(local.config_body))
  config_document = {
    config         = local.config_body
    config_version = local.config_version
    schema_version = "1.0.0"
  }
  config_document_json = jsonencode(local.config_document)
}

resource "aws_s3_object" "config_candidate" {
  provider               = aws.config_publisher
  bucket                 = var.cell_config_inbox_bucket
  key                    = "jobs/${var.job_id}/config/${local.config_version}.json"
  content                = local.config_document_json
  content_type           = "application/json"
  kms_key_id             = var.cell_kms_key_arn
  server_side_encryption = "aws:kms"

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = can(regex("^[0-9a-f]{64}$", local.config_version))
      error_message = "CONFIG_VERSION_INVALID: CONFIG must use its canonical SHA-256 content hash."
    }
  }
}
