data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
  name                = replace(lower("${var.tags["Environment"]}-${var.tags["Application"]}-${var.tags["Service"]}"), "/[^a-z0-9-]/", "-")
  schedule_group_name = coalesce(var.schedule_group_name, local.name)

  tags = merge(var.tags, {
    Name = local.name
  })

  log_group_name              = "/aws/ecs/${local.name}"
  task_failure_log_group_name = "/aws/events/${local.name}-ecs-task-failures"
  schedule_arn                = "arn:${data.aws_partition.current.partition}:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule/${local.schedule_group_name}/${local.name}"
  cluster_arn_parts           = split(":", var.cluster_arn)
  cluster_region              = local.cluster_arn_parts[3]
  cluster_account_id          = local.cluster_arn_parts[4]
  is_private_ecr_image        = can(regex("\\.dkr\\.ecr\\.[a-z0-9-]+\\.${data.aws_partition.current.dns_suffix}/", var.container_image))

  container_environment = [
    for key, value in var.environment_variables : {
      name  = key
      value = value
    }
  ]

  container_secrets = [
    for key, value_from in var.container_secrets : {
      name      = key
      valueFrom = value_from
    }
  ]

  secret_arns                 = values(var.container_secrets)
  secrets_manager_secret_arns = [for arn in local.secret_arns : arn if can(regex(":secretsmanager:", arn))]
  ssm_parameter_arns          = [for arn in local.secret_arns : arn if can(regex(":ssm:", arn))]

  base_container_definition = {
    name                   = var.container_name
    image                  = var.container_image
    essential              = true
    readonlyRootFilesystem = var.readonly_root_filesystem
    environment            = local.container_environment
    secrets                = local.container_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this.name
        awslogs-region        = data.aws_region.current.region
        awslogs-stream-prefix = var.container_name
      }
    }
  }

  container_definition = merge(
    local.base_container_definition,
    length(var.container_command) > 0 ? { command = var.container_command } : {}
  )
}

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "ecs_task_failures" {
  name              = local.task_failure_log_group_name
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = local.tags
}

data "aws_subnet" "selected" {
  for_each = toset(var.subnet_ids)

  id = each.value
}

data "aws_security_group" "selected" {
  for_each = toset(var.security_group_ids)

  id = each.value
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    sid     = "AllowEcsTasksAssumeRole"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  description        = "Execution role for ${local.name} scheduled ECS task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json

  tags = local.tags
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid = "WriteContainerLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  dynamic "statement" {
    for_each = length(local.secrets_manager_secret_arns) > 0 ? [1] : []

    content {
      sid       = "ReadSecretsManagerSecrets"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = local.secrets_manager_secret_arns
    }
  }

  dynamic "statement" {
    for_each = length(local.ssm_parameter_arns) > 0 ? [1] : []

    content {
      sid       = "ReadSsmParameters"
      actions   = ["ssm:GetParameters"]
      resources = local.ssm_parameter_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.secret_kms_key_arns) > 0 ? [1] : []

    content {
      sid       = "DecryptConfiguredSecretKeys"
      actions   = ["kms:Decrypt"]
      resources = var.secret_kms_key_arns
    }
  }
}

resource "aws_iam_policy" "execution" {
  name        = "${local.name}-execution"
  description = "Execution permissions for ${local.name} scheduled ECS task"
  policy      = data.aws_iam_policy_document.execution.json

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = aws_iam_policy.execution.arn
}

data "aws_iam_policy_document" "execution_ecr" {
  count = length(var.ecr_repository_arns) > 0 ? 1 : 0

  # ecr:GetAuthorizationToken does not support resource-level permissions.
  statement {
    sid       = "GetEcrAuthorizationToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "PullFromConfiguredRepositories"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = var.ecr_repository_arns
  }
}

resource "aws_iam_policy" "execution_ecr" {
  count = length(var.ecr_repository_arns) > 0 ? 1 : 0

  name        = "${local.name}-execution-ecr"
  description = "ECR pull permissions for ${local.name} scheduled ECS task"
  policy      = data.aws_iam_policy_document.execution_ecr[0].json

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "execution_ecr" {
  count = length(var.ecr_repository_arns) > 0 ? 1 : 0

  role       = aws_iam_role.execution.name
  policy_arn = aws_iam_policy.execution_ecr[0].arn
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  description        = "Application task role for ${local.name} scheduled ECS task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json

  tags = local.tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.compute.cpu)
  memory                   = tostring(var.compute.memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.container_definition])

  runtime_platform {
    operating_system_family = var.runtime_platform.operating_system_family
    cpu_architecture        = var.runtime_platform.cpu_architecture
  }

  dynamic "ephemeral_storage" {
    for_each = var.ephemeral_storage_gib > 20 ? [var.ephemeral_storage_gib] : []

    content {
      size_in_gib = ephemeral_storage.value
    }
  }

  tags = local.tags

  lifecycle {
    precondition {
      condition     = !local.is_private_ecr_image || length(var.ecr_repository_arns) > 0
      error_message = "Private ECR images require ecr_repository_arns so the execution role can pull the image."
    }
  }
}

resource "aws_sqs_queue" "dlq" {
  name                       = "${local.name}-dlq"
  message_retention_seconds  = var.dlq_message_retention_seconds
  kms_master_key_id          = var.kms_key_arn
  sqs_managed_sse_enabled    = var.kms_key_arn == null ? true : null
  visibility_timeout_seconds = 30

  tags = local.tags
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    sid     = "AllowSchedulerAssumeRole"
    actions = ["sts:AssumeRole"]

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
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [local.schedule_arn]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  description        = "EventBridge Scheduler invocation role for ${local.name}"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json

  tags = local.tags
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "RunConfiguredTask"
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.this.arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.cluster_arn]
    }
  }

  statement {
    sid = "PassConfiguredTaskRoles"
    actions = [
      "iam:PassRole"
    ]
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
    sid       = "SendFailedInvocationsToDlq"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.dlq.arn]
  }

  dynamic "statement" {
    for_each = var.kms_key_arn == null ? [] : [1]

    content {
      sid = "UseConfiguredDlqKey"
      actions = [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ]
      resources = [var.kms_key_arn]
    }
  }
}

resource "aws_iam_policy" "scheduler" {
  name        = "${local.name}-scheduler"
  description = "EventBridge Scheduler permissions for ${local.name}"
  policy      = data.aws_iam_policy_document.scheduler.json

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "scheduler" {
  role       = aws_iam_role.scheduler.name
  policy_arn = aws_iam_policy.scheduler.arn
}

resource "aws_scheduler_schedule_group" "this" {
  name = local.schedule_group_name

  tags = local.tags
}

resource "aws_scheduler_schedule" "this" {
  name                         = local.name
  group_name                   = aws_scheduler_schedule_group.this.name
  description                  = "Run ${local.name} ECS Fargate scheduled job"
  kms_key_arn                  = var.kms_key_arn
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_expression_timezone
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode                      = var.flexible_time_window.mode
    maximum_window_in_minutes = var.flexible_time_window.maximum_window_in_minutes
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
      task_definition_arn     = aws_ecs_task_definition.this.arn
      launch_type             = "FARGATE"
      platform_version        = var.platform_version
      task_count              = var.task_count
      enable_ecs_managed_tags = true
      propagate_tags          = "TASK_DEFINITION"

      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = var.security_group_ids
        assign_public_ip = false
      }
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.scheduler
  ]

  lifecycle {
    precondition {
      condition     = local.cluster_account_id == data.aws_caller_identity.current.account_id && local.cluster_region == data.aws_region.current.region
      error_message = "cluster_arn must be in the same AWS account and region as the module provider."
    }

    precondition {
      condition     = length(distinct(concat([for subnet in data.aws_subnet.selected : subnet.vpc_id], [for security_group in data.aws_security_group.selected : security_group.vpc_id]))) == 1
      error_message = "subnet_ids and security_group_ids must all belong to the same VPC."
    }

    precondition {
      condition     = var.alarm_datapoints_to_alarm <= var.alarm_evaluation_periods
      error_message = "alarm_datapoints_to_alarm must be less than or equal to alarm_evaluation_periods."
    }
  }
}

resource "aws_cloudwatch_event_rule" "ecs_task_failures" {
  name        = "${local.name}-task-failures"
  description = "Capture stopped ${local.name} ECS tasks with non-zero container exit codes"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn        = [var.cluster_arn]
      taskDefinitionArn = [aws_ecs_task_definition.this.arn]
      lastStatus        = ["STOPPED"]
      containers = {
        exitCode = [{
          "anything-but" = 0
        }]
      }
    }
  })

  tags = local.tags
}

data "aws_iam_policy_document" "eventbridge_logs" {
  statement {
    sid = "AllowEventBridgeToWriteTaskFailureEvents"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["${aws_cloudwatch_log_group.ecs_task_failures.arn}:*"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.ecs_task_failures.arn]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "eventbridge_logs" {
  policy_name     = "${local.name}-eventbridge-logs"
  policy_document = data.aws_iam_policy_document.eventbridge_logs.json
}

resource "aws_cloudwatch_event_target" "ecs_task_failures" {
  rule      = aws_cloudwatch_event_rule.ecs_task_failures.name
  target_id = "LogTaskFailures"
  arn       = aws_cloudwatch_log_group.ecs_task_failures.arn

  depends_on = [
    aws_cloudwatch_log_resource_policy.eventbridge_logs
  ]
}

resource "aws_cloudwatch_log_metric_filter" "ecs_task_failures" {
  name           = "${local.name}-task-failures"
  log_group_name = aws_cloudwatch_log_group.ecs_task_failures.name
  pattern        = "{ $.detail.lastStatus = \"STOPPED\" }"

  metric_transformation {
    name      = "TaskFailureCount"
    namespace = "ECS/ScheduledJob"
    value     = "1"
    dimensions = {
      JobName = local.name
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_task_failures" {
  alarm_name          = "${local.name}-task-failures"
  alarm_description   = "ECS scheduled task ${local.name} stopped with a non-zero container exit code. Check task failure event logs and container logs."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  datapoints_to_alarm = var.alarm_datapoints_to_alarm
  threshold           = var.scheduler_failure_alarm_threshold
  metric_name         = aws_cloudwatch_log_metric_filter.ecs_task_failures.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.ecs_task_failures.metric_transformation[0].namespace
  period              = var.alarm_period_seconds
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_sns_topic_arns
  ok_actions          = var.alarm_sns_topic_arns

  dimensions = {
    JobName = local.name
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "scheduler_target_errors" {
  alarm_name          = "${local.name}-scheduler-target-errors"
  alarm_description   = "EventBridge Scheduler target invocation errors for ${local.name}. Check the schedule, ECS RunTask permissions, cluster capacity, and DLQ."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  datapoints_to_alarm = var.alarm_datapoints_to_alarm
  threshold           = var.scheduler_failure_alarm_threshold
  metric_name         = "TargetErrorCount"
  namespace           = "AWS/Scheduler"
  period              = var.alarm_period_seconds
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_sns_topic_arns
  ok_actions          = var.alarm_sns_topic_arns

  dimensions = {
    ScheduleGroup = aws_scheduler_schedule_group.this.name
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "scheduler_dropped_invocations" {
  alarm_name          = "${local.name}-scheduler-dropped-invocations"
  alarm_description   = "EventBridge Scheduler dropped invocations for ${local.name}. Check retry age, retry attempts, and DLQ delivery."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  datapoints_to_alarm = var.alarm_datapoints_to_alarm
  threshold           = var.scheduler_failure_alarm_threshold
  metric_name         = "InvocationDroppedCount"
  namespace           = "AWS/Scheduler"
  period              = var.alarm_period_seconds
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_sns_topic_arns
  ok_actions          = var.alarm_sns_topic_arns

  dimensions = {
    ScheduleGroup = aws_scheduler_schedule_group.this.name
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "dlq_oldest_message_age" {
  alarm_name          = "${local.name}-dlq-oldest-message-age"
  alarm_description   = "Messages are aging in the ${local.name} scheduler DLQ. Inspect and replay or purge after triage."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  datapoints_to_alarm = var.alarm_datapoints_to_alarm
  threshold           = var.dlq_age_alarm_threshold_seconds
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = var.alarm_period_seconds
  statistic           = "Maximum"
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_sns_topic_arns
  ok_actions          = var.alarm_sns_topic_arns

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  tags = local.tags
}
