data "aws_region" "current" {}

locals {
  name_prefix    = "${var.environment}-${var.application}-${var.service}"
  log_group_name = "/ecs/${local.name_prefix}"
  event_log_name = "/aws/events/${local.name_prefix}-task-state"

  valid_memory_by_cpu = {
    256   = [512, 1024, 2048]
    512   = [1024, 2048, 3072, 4096]
    1024  = range(2048, 8193, 1024)
    2048  = range(4096, 16385, 1024)
    4096  = range(8192, 30721, 1024)
    8192  = range(16384, 61441, 4096)
    16384 = range(32768, 122881, 8192)
    32768 = [61440, 122880, 249856]
  }

  required_tags = {
    Environment = var.environment
    Application = var.application
    Service     = var.service
    Owner       = var.owner
    ManagedBy   = "Terraform"
    CostCenter  = var.cost_center
    Repository  = var.repository
  }

  tags = merge(var.tags, {
    for key, value in local.required_tags : key => value
    if value != ""
  })

  container_definition = merge(
    {
      name      = var.container_name
      image     = var.container_image
      essential = true
      environment = [
        for name, value in var.container_environment : {
          name  = name
          value = value
        }
      ]
      secrets = [
        for name, value_from in var.container_secrets : {
          name      = name
          valueFrom = value_from
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.job.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = var.container_name
        }
      }
    },
    length(var.container_command) > 0 ? { command = var.container_command } : {},
    length(var.container_entrypoint) > 0 ? { entryPoint = var.container_entrypoint } : {}
  )

  secret_resource_arns = distinct(concat(
    var.execution_secret_arns,
    [for value_from in values(var.container_secrets) : value_from if startswith(value_from, "arn:")]
  ))
}

resource "aws_cloudwatch_log_group" "job" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "task_state_events" {
  name              = local.event_log_name
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    sid     = "AllowEcsTasksAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name_prefix}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid    = "WriteTaskLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.job.arn}:*"]
  }

  dynamic "statement" {
    for_each = var.enable_ecr_pull_permissions ? [1] : []

    content {
      sid       = "GetEcrAuthorizationToken"
      effect    = "Allow"
      actions   = ["ecr:GetAuthorizationToken"]
      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = var.enable_ecr_pull_permissions && length(var.ecr_repository_arns) > 0 ? [1] : []

    content {
      sid    = "PullEcrImages"
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
    for_each = length(local.secret_resource_arns) > 0 ? [1] : []

    content {
      sid    = "ReadConfiguredContainerSecrets"
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
        "ssm:GetParameters"
      ]
      resources = local.secret_resource_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.kms_key_arns) > 0 ? [1] : []

    content {
      sid       = "DecryptConfiguredSecrets"
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = var.kms_key_arns
    }
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "${local.name_prefix}-execution"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

resource "aws_iam_role" "task" {
  name               = "${local.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "task" {
  count = length(var.task_policy_statements) > 0 ? 1 : 0

  dynamic "statement" {
    for_each = var.task_policy_statements

    content {
      sid       = statement.value.sid
      effect    = statement.value.effect
      actions   = statement.value.actions
      resources = statement.value.resources

      dynamic "condition" {
        for_each = statement.value.conditions

        content {
          test     = condition.value.test
          variable = condition.value.variable
          values   = condition.value.values
        }
      }
    }
  }
}

resource "aws_iam_role_policy" "task" {
  count  = length(var.task_policy_statements) > 0 ? 1 : 0
  name   = "${local.name_prefix}-task"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task[0].json
}

resource "aws_iam_role_policy_attachment" "task_managed" {
  for_each   = toset(var.task_managed_policy_arns)
  role       = aws_iam_role.task.name
  policy_arn = each.value
}

resource "aws_ecs_task_definition" "job" {
  family                   = local.name_prefix
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.container_definition])
  tags                     = local.tags

  lifecycle {
    precondition {
      condition     = contains(local.valid_memory_by_cpu[var.cpu], var.memory)
      error_message = "memory must be a valid AWS Fargate value for the selected cpu."
    }

    precondition {
      condition     = !can(regex("\\.dkr\\.ecr\\.", var.container_image)) || (var.enable_ecr_pull_permissions && length(var.ecr_repository_arns) > 0)
      error_message = "private ECR images require enable_ecr_pull_permissions = true and at least one ecr_repository_arn."
    }
  }
}

resource "aws_sqs_queue" "dlq" {
  name                       = "${local.name_prefix}-dlq"
  message_retention_seconds  = var.dlq_message_retention_seconds
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 300
  tags                       = local.tags
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    sid     = "AllowSchedulerAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name_prefix}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "RunConfiguredTask"
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.job.arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.cluster_arn]
    }
  }

  statement {
    sid     = "PassConfiguredTaskRoles"
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.execution.arn,
      aws_iam_role.task.arn
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  statement {
    sid       = "SendFailuresToDlq"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.dlq.arn]
  }

  statement {
    sid       = "TagTasksCreatedByRunTask"
    effect    = "Allow"
    actions   = ["ecs:TagResource"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "ecs:CreateAction"
      values   = ["RunTask"]
    }
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${local.name_prefix}-scheduler"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

data "aws_iam_policy_document" "events_logs" {
  statement {
    sid    = "AllowEventBridgeWriteTaskStateEvents"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.task_state_events.arn}:*"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "events_logs" {
  policy_name     = "${local.name_prefix}-events-logs"
  policy_document = data.aws_iam_policy_document.events_logs.json
}

resource "aws_cloudwatch_event_rule" "task_stopped" {
  name        = "${local.name_prefix}-task-stopped"
  description = "Captures stopped ECS tasks for ${local.name_prefix}"
  tags        = local.tags

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    detail = {
      clusterArn = [var.cluster_arn]
      group      = [local.name_prefix]
      lastStatus = ["STOPPED"]
    }
  })
}

resource "aws_cloudwatch_event_target" "task_state_events" {
  rule = aws_cloudwatch_event_rule.task_stopped.name
  arn  = aws_cloudwatch_log_group.task_state_events.arn

  depends_on = [aws_cloudwatch_log_resource_policy.events_logs]
}

resource "aws_cloudwatch_log_metric_filter" "task_nonzero_exit" {
  name           = "${local.name_prefix}-task-nonzero-exit"
  log_group_name = aws_cloudwatch_log_group.task_state_events.name
  pattern        = "{ $.detail.containers[0].exitCode != 0 }"

  metric_transformation {
    name          = "${local.name_prefix}-task-failures"
    namespace     = "ECS/ScheduledJobs"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_scheduler_schedule" "job" {
  name                         = local.name_prefix
  group_name                   = var.schedule_group_name
  description                  = "Runs ${local.name_prefix} ECS scheduled job"
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_expression_timezone
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode                      = var.flexible_time_window_mode
    maximum_window_in_minutes = var.flexible_time_window_mode == "FLEXIBLE" ? var.maximum_window_in_minutes : null
  }

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn

    dead_letter_config {
      arn = aws_sqs_queue.dlq.arn
    }

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_in_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }

    ecs_parameters {
      task_definition_arn     = aws_ecs_task_definition.job.arn
      group                   = local.name_prefix
      launch_type             = "FARGATE"
      platform_version        = var.platform_version
      task_count              = var.task_count
      enable_ecs_managed_tags = true
      propagate_tags          = "TASK_DEFINITION"

      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = var.assign_public_ip
      }
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "scheduler_target_errors" {
  alarm_name          = "${local.name_prefix}-scheduler-target-errors"
  alarm_description   = "EventBridge Scheduler target errors for ${local.name_prefix}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "TargetErrorCount"
  namespace           = "AWS/Scheduler"
  period              = 60
  statistic           = "Sum"
  threshold           = var.scheduler_target_error_alarm_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  tags                = local.tags

  lifecycle {
    precondition {
      condition     = var.environment != "prod" || length(var.alarm_actions) > 0
      error_message = "prod scheduled jobs must configure alarm_actions."
    }
  }

  dimensions = {
    ScheduleGroup = var.schedule_group_name
  }
}

resource "aws_cloudwatch_metric_alarm" "task_failures" {
  alarm_name          = "${local.name_prefix}-task-failures"
  alarm_description   = "Non-zero container exits for ${local.name_prefix} scheduled job"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "${local.name_prefix}-task-failures"
  namespace           = "ECS/ScheduledJobs"
  period              = 60
  statistic           = "Sum"
  threshold           = var.task_failure_alarm_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  tags                = local.tags
}

resource "aws_cloudwatch_metric_alarm" "dlq_visible_messages" {
  alarm_name          = "${local.name_prefix}-dlq-visible-messages"
  alarm_description   = "DLQ backlog for ${local.name_prefix} scheduled job"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = var.dlq_visible_messages_alarm_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  tags                = local.tags

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
}
