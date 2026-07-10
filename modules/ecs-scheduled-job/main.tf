data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  name = "${var.environment}-${var.application}-${var.job_name}"

  create_task_roles     = var.execution_role_arn == null && var.task_role_arn == null
  create_scheduler_role = var.scheduler_role_arn == null
  execution_role_arn    = local.create_task_roles ? aws_iam_role.execution[0].arn : var.execution_role_arn
  task_role_arn         = local.create_task_roles ? aws_iam_role.task[0].arn : var.task_role_arn
  scheduler_role_arn    = local.create_scheduler_role ? aws_iam_role.scheduler[0].arn : var.scheduler_role_arn
  schedule_group_name   = var.create_schedule_group ? aws_scheduler_schedule_group.this[0].name : var.schedule_group_name
  schedule_arn          = "arn:${data.aws_partition.current.partition}:scheduler:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:schedule/${local.schedule_group_name}/${local.name}"
  task_failure_rule     = "${substr(local.name, 0, 50)}-task-failure"
  secret_arns           = [for secret in var.container_secrets : secret.value_from]
  secretsmanager_arns   = [for arn in local.secret_arns : replace(arn, "/^(arn:[^:]+:secretsmanager:[^:]+:[0-9]{12}:secret:[^:]+)(:[^:]*){1,3}$/", "$1") if can(regex(":secretsmanager:", arn))]
  ssm_parameter_arns    = [for arn in local.secret_arns : arn if can(regex(":ssm:", arn))]
  container_environment = [
    for key, value in var.environment_variables : {
      name  = key
      value = value
    }
  ]
  container_secrets = [
    for secret in var.container_secrets : {
      name      = secret.name
      valueFrom = secret.value_from
    }
  ]
  valid_cpu_memory_pairs = toset([
    "256:512", "256:1024", "256:2048",
    "512:1024", "512:2048", "512:3072", "512:4096",
    "1024:2048", "1024:3072", "1024:4096", "1024:5120", "1024:6144", "1024:7168", "1024:8192",
    "2048:4096", "2048:5120", "2048:6144", "2048:7168", "2048:8192", "2048:9216", "2048:10240", "2048:11264", "2048:12288", "2048:13312", "2048:14336", "2048:15360", "2048:16384",
    "4096:8192", "4096:9216", "4096:10240", "4096:11264", "4096:12288", "4096:13312", "4096:14336", "4096:15360", "4096:16384", "4096:17408", "4096:18432", "4096:19456", "4096:20480", "4096:21504", "4096:22528", "4096:23552", "4096:24576", "4096:25600", "4096:26624", "4096:27648", "4096:28672", "4096:29696", "4096:30720",
    "8192:16384", "8192:20480", "8192:24576", "8192:28672", "8192:32768", "8192:36864", "8192:40960", "8192:45056", "8192:49152", "8192:53248", "8192:57344", "8192:61440",
    "16384:32768", "16384:40960", "16384:49152", "16384:57344", "16384:65536", "16384:73728", "16384:81920", "16384:90112", "16384:98304", "16384:106496", "16384:114688", "16384:122880"
  ])

  tags = merge(
    var.tags,
    {
      Name        = local.name
      Environment = var.environment
      Application = var.application
      Service     = var.service
      Owner       = var.owner
      ManagedBy   = "Terraform"
    },
    var.cost_center == null ? {} : { CostCenter = var.cost_center },
    var.repository == null ? {} : { Repository = var.repository }
  )

  container_definition = merge(
    {
      name      = var.container_name
      image     = var.container_image
      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = var.container_name
        }
      }
    },
    length(var.container_command) == 0 ? {} : { command = var.container_command },
    length(local.container_environment) == 0 ? {} : { environment = local.container_environment },
    length(local.container_secrets) == 0 ? {} : { secrets = local.container_secrets }
  )
}

resource "aws_cloudwatch_log_group" "this" {
  #checkov:skip=CKV_AWS_158:Account-specific KMS keys are supplied through log_kms_key_id when required.
  #checkov:skip=CKV_AWS_338:Retention is an explicit module input; production callers should set their required retention.
  name              = "/aws/ecs/${local.name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.log_kms_key_id
  tags              = local.tags
}

resource "aws_sqs_queue" "scheduler_dlq" {
  name                      = "${local.name}-scheduler-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = local.tags
}

data "aws_iam_policy_document" "scheduler_dlq" {
  statement {
    sid    = "AllowSchedulerDeliveryFailures"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scheduler_dlq.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [local.schedule_arn]
    }
  }
}

resource "aws_sqs_queue_policy" "scheduler_dlq" {
  queue_url = aws_sqs_queue.scheduler_dlq.id
  policy    = data.aws_iam_policy_document.scheduler_dlq.json
}

resource "aws_scheduler_schedule_group" "this" {
  count = var.create_schedule_group ? 1 : 0

  name = var.schedule_group_name
  tags = local.tags
}

data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_iam_role" "execution" {
  count              = local.create_task_roles ? 1 : 0
  name_prefix        = "${substr(local.name, 0, 32)}-exec-"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
  tags               = local.tags
}

resource "aws_iam_role" "task" {
  count              = local.create_task_roles ? 1 : 0
  name_prefix        = "${substr(local.name, 0, 32)}-task-"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid    = "WriteContainerLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  dynamic "statement" {
    for_each = length(var.ecr_repository_arns) > 0 ? [1] : []
    content {
      sid       = "GetEcrAuthorizationToken"
      effect    = "Allow"
      actions   = ["ecr:GetAuthorizationToken"]
      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = length(var.ecr_repository_arns) > 0 ? [1] : []
    content {
      sid    = "PullPrivateEcrImages"
      effect = "Allow"
      actions = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ]
      resources = var.ecr_repository_arns
    }
  }

  dynamic "statement" {
    for_each = length(local.secretsmanager_arns) > 0 ? [1] : []
    content {
      sid       = "ReadSecretsManagerReferences"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = local.secretsmanager_arns
    }
  }

  dynamic "statement" {
    for_each = length(local.ssm_parameter_arns) > 0 ? [1] : []
    content {
      sid       = "ReadSsmParameterReferences"
      effect    = "Allow"
      actions   = ["ssm:GetParameters"]
      resources = local.ssm_parameter_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.secret_kms_key_arns) > 0 ? [1] : []
    content {
      sid       = "DecryptConfiguredSecrets"
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = var.secret_kms_key_arns
    }
  }
}

resource "aws_iam_role_policy" "execution" {
  count  = local.create_task_roles ? 1 : 0
  name   = "${local.name}-execution"
  role   = aws_iam_role.execution[0].id
  policy = data.aws_iam_policy_document.execution.json
}

resource "aws_iam_role_policy" "task" {
  count  = local.create_task_roles && var.task_policy_json != null ? 1 : 0
  name   = "${local.name}-task"
  role   = aws_iam_role.task[0].id
  policy = var.task_policy_json
}

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [local.schedule_arn]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  count              = local.create_scheduler_role ? 1 : 0
  name_prefix        = "${substr(local.name, 0, 32)}-sched-"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "RunConfiguredTask"
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.this.arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.cluster_arn]
    }
  }

  statement {
    sid    = "PassTaskRoles"
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = compact([
      local.execution_role_arn,
      local.task_role_arn
    ])

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid       = "SendDeliveryFailuresToDlq"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scheduler_dlq.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  count  = local.create_scheduler_role ? 1 : 0
  name   = "${local.name}-scheduler"
  role   = aws_iam_role.scheduler[0].id
  policy = data.aws_iam_policy_document.scheduler.json
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = local.execution_role_arn
  task_role_arn            = local.task_role_arn
  container_definitions    = jsonencode([local.container_definition])
  tags                     = local.tags

  dynamic "ephemeral_storage" {
    for_each = var.ephemeral_storage_gib == null ? [] : [var.ephemeral_storage_gib]
    content {
      size_in_gib = ephemeral_storage.value
    }
  }

  lifecycle {
    precondition {
      condition     = (var.execution_role_arn == null && var.task_role_arn == null) || (var.execution_role_arn != null && var.task_role_arn != null)
      error_message = "execution_role_arn and task_role_arn must either both be null or both be set."
    }

    precondition {
      condition     = !local.create_task_roles || !can(regex("\\.dkr\\.ecr\\.", var.container_image)) || length(var.ecr_repository_arns) > 0
      error_message = "ecr_repository_arns must be set when the module creates the execution role for a private ECR image."
    }

    precondition {
      condition     = can(regex("^arn:${data.aws_partition.current.partition}:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/.+", var.cluster_arn))
      error_message = "cluster_arn must be in the current Terraform AWS provider partition, region, and account."
    }

    precondition {
      condition     = contains(local.valid_cpu_memory_pairs, "${var.cpu}:${var.memory}")
      error_message = "cpu and memory must be a valid Fargate combination."
    }

    precondition {
      condition     = var.flexible_time_window_mode == "FLEXIBLE" || var.maximum_window_in_minutes == null
      error_message = "maximum_window_in_minutes must be null when flexible_time_window_mode is OFF."
    }

    precondition {
      condition     = var.flexible_time_window_mode != "FLEXIBLE" || var.maximum_window_in_minutes != null
      error_message = "maximum_window_in_minutes must be set when flexible_time_window_mode is FLEXIBLE."
    }
  }
}

resource "aws_scheduler_schedule" "this" {
  name                         = local.name
  group_name                   = local.schedule_group_name
  description                  = "Runs ECS Fargate scheduled job ${local.name}"
  kms_key_arn                  = var.scheduler_kms_key_arn
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_timezone
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode                      = var.flexible_time_window_mode
    maximum_window_in_minutes = var.flexible_time_window_mode == "FLEXIBLE" ? var.maximum_window_in_minutes : null
  }

  target {
    arn      = var.cluster_arn
    role_arn = local.scheduler_role_arn

    dead_letter_config {
      arn = aws_sqs_queue.scheduler_dlq.arn
    }

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_in_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.this.arn
      task_count          = var.task_count
      launch_type         = "FARGATE"
      platform_version    = var.platform_version

      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = var.assign_public_ip
      }
    }
  }
}

resource "aws_cloudwatch_event_rule" "task_failure" {
  name        = local.task_failure_rule
  description = "Matches stopped ECS tasks for ${local.name} when a task fails to start or a container exits non-zero"

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    detail = {
      clusterArn = [var.cluster_arn]
      lastStatus = ["STOPPED"]
      taskDefinitionArn = [{
        prefix = "${aws_ecs_task_definition.this.arn_without_revision}:"
      }]
    }
    "$or" = [
      {
        detail = {
          containers = {
            exitCode = [{
              "anything-but" = [0]
            }]
          }
        }
      },
      {
        detail = {
          stopCode = ["TaskFailedToStart"]
        }
      }
    ]
  })

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "task_failure" {
  #checkov:skip=CKV_AWS_319:Alarm actions are caller-supplied through alarm_actions for account-specific notification targets.
  alarm_name          = "${local.name}-task-failure"
  alarm_description   = "ECS scheduled job ${local.name} had one or more stopped tasks with non-zero container exit codes."
  namespace           = "AWS/Events"
  metric_name         = "TriggeredRules"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = var.task_failure_alarm_evaluation_periods
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.task_failure.name
  }
  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "scheduler_dlq_visible_messages" {
  #checkov:skip=CKV_AWS_319:Alarm actions are caller-supplied through alarm_actions for account-specific notification targets.
  alarm_name          = "${local.name}-scheduler-dlq-visible"
  alarm_description   = "EventBridge Scheduler delivery failures for ${local.name} are present in the DLQ."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.dlq_visible_messages_alarm_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  dimensions = {
    QueueName = aws_sqs_queue.scheduler_dlq.name
  }
  tags = local.tags
}
