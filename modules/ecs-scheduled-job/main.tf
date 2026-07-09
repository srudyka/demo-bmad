locals {
  container_name       = coalesce(var.container_name, var.name)
  log_group_name       = coalesce(var.log_group_name, "/ecs/scheduled/${var.name}")
  schedule_group_name  = coalesce(var.schedule_group_name, var.name)
  task_failure_targets = length(var.task_failure_event_target_arns) > 0 ? var.task_failure_event_target_arns : var.alarm_action_arns
  secret_arns          = [for arn in values(var.secrets) : arn if can(regex(":secretsmanager:", arn))]
  parameter_arns       = [for arn in values(var.secrets) : arn if can(regex(":ssm:", arn))]

  fargate_memory_by_cpu = {
    "256"  = [512, 1024, 2048]
    "512"  = [1024, 2048, 3072, 4096]
    "1024" = [2048, 3072, 4096, 5120, 6144, 7168, 8192]
    "2048" = [4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384]
    "4096" = [8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384, 17408, 18432, 19456, 20480, 21504, 22528, 23552, 24576, 25600, 26624, 27648, 28672, 29696, 30720]
  }

  common_tags = merge(
    var.tags,
    {
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
      name      = local.container_name
      image     = var.container_image
      essential = true

      environment = [
        for name, value in var.environment_variables : {
          name  = name
          value = value
        }
      ]

      secrets = [
        for name, value_from in var.secrets : {
          name      = name
          valueFrom = value_from
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = local.container_name
        }
      }
    },
    length(var.command) == 0 ? {} : { command = var.command }
  )
}

data "aws_region" "current" {}
data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
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
      values = [
        "arn:${data.aws_partition.current.partition}:scheduler:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:schedule/${local.schedule_group_name}/${var.name}"
      ]
    }
  }
}

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_iam_role" "execution" {
  name               = "${var.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "execution_secrets" {
  count = length(var.secrets) > 0 || length(var.kms_key_arns) > 0 ? 1 : 0

  dynamic "statement" {
    for_each = length(local.secret_arns) > 0 ? [1] : []

    content {
      sid       = "ReadContainerSecrets"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = local.secret_arns
    }
  }

  dynamic "statement" {
    for_each = length(local.parameter_arns) > 0 ? [1] : []

    content {
      sid       = "ReadContainerParameters"
      actions   = ["ssm:GetParameters"]
      resources = local.parameter_arns
    }
  }

  dynamic "statement" {
    for_each = length(var.kms_key_arns) > 0 ? [1] : []

    content {
      sid       = "DecryptContainerSecrets"
      actions   = ["kms:Decrypt"]
      resources = var.kms_key_arns
    }
  }
}

resource "aws_iam_policy" "execution_secrets" {
  count  = length(var.secrets) > 0 || length(var.kms_key_arns) > 0 ? 1 : 0
  name   = "${var.name}-execution-secrets"
  policy = data.aws_iam_policy_document.execution_secrets[0].json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution_secrets" {
  count      = length(var.secrets) > 0 || length(var.kms_key_arns) > 0 ? 1 : 0
  role       = aws_iam_role.execution.name
  policy_arn = aws_iam_policy.execution_secrets[0].arn
}

resource "aws_iam_role" "task" {
  name               = "${var.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.common_tags
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

resource "aws_iam_policy" "task" {
  count  = length(var.task_policy_statements) > 0 ? 1 : 0
  name   = "${var.name}-task"
  policy = data.aws_iam_policy_document.task[0].json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "task" {
  count      = length(var.task_policy_statements) > 0 ? 1 : 0
  role       = aws_iam_role.task.name
  policy_arn = aws_iam_policy.task[0].arn
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode([local.container_definition])
  tags                     = local.common_tags

  dynamic "ephemeral_storage" {
    for_each = var.ephemeral_storage_gib == null ? [] : [var.ephemeral_storage_gib]

    content {
      size_in_gib = ephemeral_storage.value
    }
  }

  lifecycle {
    precondition {
      condition     = contains(local.fargate_memory_by_cpu[tostring(var.cpu)], var.memory)
      error_message = "memory must be a valid Fargate memory value for the selected cpu."
    }

    precondition {
      condition     = length(setintersection(keys(var.environment_variables), keys(var.secrets))) == 0
      error_message = "environment_variables and secrets must not define the same container environment variable name."
    }
  }
}

resource "aws_scheduler_schedule_group" "this" {
  name = local.schedule_group_name
  tags = local.common_tags
}

data "aws_iam_policy_document" "scheduler_run_task" {
  statement {
    sid       = "RunScheduledTask"
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.this.arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.cluster_arn]
    }
  }

  statement {
    sid       = "PassTaskRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.execution.arn, aws_iam_role.task.arn]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

  dynamic "statement" {
    for_each = var.dead_letter_queue_arn == null ? [] : [var.dead_letter_queue_arn]

    content {
      sid       = "SendToDeadLetterQueue"
      actions   = ["sqs:SendMessage"]
      resources = [statement.value]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_policy" "scheduler_run_task" {
  name   = "${var.name}-scheduler-run-task"
  policy = data.aws_iam_policy_document.scheduler_run_task.json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "scheduler_run_task" {
  role       = aws_iam_role.scheduler.name
  policy_arn = aws_iam_policy.scheduler_run_task.arn
}

resource "aws_scheduler_schedule" "this" {
  name                         = var.name
  group_name                   = aws_scheduler_schedule_group.this.name
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_expression_timezone
  state                        = var.schedule_state

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn
    input    = var.schedule_input_json

    retry_policy {
      maximum_event_age_in_seconds = var.maximum_event_age_in_seconds
      maximum_retry_attempts       = var.maximum_retry_attempts
    }

    dynamic "dead_letter_config" {
      for_each = var.dead_letter_queue_arn == null ? [] : [var.dead_letter_queue_arn]

      content {
        arn = dead_letter_config.value
      }
    }

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.this.arn
      launch_type         = "FARGATE"
      platform_version    = var.platform_version
      propagate_tags      = "TASK_DEFINITION"
      task_count          = 1

      network_configuration {
        assign_public_ip = var.assign_public_ip
        security_groups  = var.security_group_ids
        subnets          = var.subnet_ids
      }
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.execution_managed,
    aws_iam_role_policy_attachment.execution_secrets,
    aws_iam_role_policy_attachment.scheduler_run_task,
    aws_iam_role_policy_attachment.task
  ]
}

resource "aws_cloudwatch_event_rule" "task_failures" {
  name        = "${var.name}-ecs-task-failures"
  description = "Matches stopped ECS tasks for ${var.name} when a container exits non-zero."

  event_pattern = jsonencode({
    source        = ["aws.ecs"]
    "detail-type" = ["ECS Task State Change"]
    detail = {
      clusterArn        = [var.cluster_arn]
      taskDefinitionArn = [aws_ecs_task_definition.this.arn]
      lastStatus        = ["STOPPED"]
      containers = {
        exitCode = [
          {
            "anything-but" = 0
          }
        ]
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "task_failures" {
  for_each = toset(local.task_failure_targets)

  rule = aws_cloudwatch_event_rule.task_failures.name
  arn  = each.value
}

resource "aws_cloudwatch_metric_alarm" "target_errors" {
  alarm_name          = "${var.name}-scheduler-target-errors"
  alarm_description   = "EventBridge Scheduler target errors for ${var.name}."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "TargetErrorCount"
  namespace           = "AWS/Scheduler"
  period              = var.alarm_period_seconds
  statistic           = "Sum"
  threshold           = var.failed_invocation_alarm_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns
  ok_actions          = var.ok_action_arns

  dimensions = {
    ScheduleGroup = aws_scheduler_schedule_group.this.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "dropped_invocations" {
  alarm_name          = "${var.name}-scheduler-dropped-invocations"
  alarm_description   = "EventBridge Scheduler dropped invocations for ${var.name}."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = var.alarm_evaluation_periods
  metric_name         = "InvocationDroppedCount"
  namespace           = "AWS/Scheduler"
  period              = var.alarm_period_seconds
  statistic           = "Sum"
  threshold           = var.failed_invocation_alarm_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_action_arns
  ok_actions          = var.ok_action_arns

  dimensions = {
    ScheduleGroup = aws_scheduler_schedule_group.this.name
  }

  tags = local.common_tags
}
