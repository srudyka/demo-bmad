data "aws_iam_policy_document" "launch_assume_role" {
  statement {
    sid     = "AllowExactCellProcessManager"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.cell_process_manager_role_arn]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:PrincipalArn"
      values   = [var.cell_process_manager_role_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:PrincipalAccount"
      values   = [var.account_id]
    }
  }
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    sid     = "AllowEcsTasksFromTargetAccount"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:ecs:${var.region}:${var.account_id}:*"]
    }
  }
}

locals {
  role_name_prefix          = local.name_prefix
  launch_role_name          = "${local.role_name_prefix}-launch"
  execution_role_name       = "${local.role_name_prefix}-execution"
  task_role_name            = "${local.role_name_prefix}-task"
  task_family_arn           = "arn:${data.aws_partition.current.partition}:ecs:${var.region}:${var.account_id}:task-definition/${local.name_prefix}:*"
  job_log_group_arn         = "arn:${data.aws_partition.current.partition}:logs:${var.region}:${var.account_id}:log-group:/platform/jobs/${replace(local.job_id, "/", "-")}:*"
  secretsmanager_references = [for reference in var.secret_references : reference if startswith(reference, "arn:${data.aws_partition.current.partition}:secretsmanager:")]
  ssm_references            = [for reference in var.secret_references : reference if startswith(reference, "arn:${data.aws_partition.current.partition}:ssm:")]
  secret_kms_resources      = var.secret_kms_key_arn == null ? [] : [var.secret_kms_key_arn]
  iam_catalog               = jsondecode(file("${path.module}/../../contracts/v1/catalogs/iam.json"))
  catalog_task_actions      = toset(try(local.iam_catalog.roles.task.actions, []))
  policy_catalog_findings = flatten([
    for permission in var.permissions : [
      for action in permission.actions : {
        statement_id = permission.statement_id
        action       = action
        severity     = contains(local.catalog_task_actions, action) ? "advisory" : "blocking"
        reason       = contains(local.catalog_task_actions, action) ? "Action is present in the versioned task-role catalog." : "Action is not present in the versioned task-role catalog."
      }
    ]
  ])
}

resource "aws_iam_role" "launch" {
  name                 = local.launch_role_name
  path                 = local.role_path
  assume_role_policy   = data.aws_iam_policy_document.launch_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.merged_tags
}

resource "aws_iam_role" "execution" {
  name                 = local.execution_role_name
  path                 = local.role_path
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.merged_tags
}

resource "aws_iam_role" "task" {
  name                 = local.task_role_name
  path                 = local.role_path
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  permissions_boundary = var.permissions_boundary_arn
  tags                 = local.merged_tags
}

data "aws_iam_policy_document" "launch" {
  statement {
    sid       = "RunCanonicalJobTaskFamily"
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = [local.task_family_arn]

    condition {
      test     = "ArnEquals"
      variable = "ecs:cluster"
      values   = [var.ecs_cluster_arn]
    }
  }

  statement {
    sid       = "PassOnlyThisJobsEcsRoles"
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
  name   = "${local.launch_role_name}-policy-v1"
  role   = aws_iam_role.launch.id
  policy = data.aws_iam_policy_document.launch.json
}

data "aws_iam_policy_document" "execution" {
  statement {
    sid       = "PullImmutableImageFromApprovedRepository"
    effect    = "Allow"
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [var.ecr_repository_arn]
  }

  # ECR requires GetAuthorizationToken on Resource="*"; it is isolated here
  # as the only service-required wildcard in the module.
  statement {
    sid       = "EcrAuthorizationTokenServiceRequiredWildcard"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid       = "WriteOnlyThisJobsLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [local.job_log_group_arn]
  }

  dynamic "statement" {
    for_each = var.secret_mode == "ecs-agent" && length(local.secretsmanager_references) > 0 ? [1] : []
    content {
      sid       = "ReadEcsAgentSecretsManagerReferences"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = local.secretsmanager_references
    }
  }

  dynamic "statement" {
    for_each = var.secret_mode == "ecs-agent" && length(local.ssm_references) > 0 ? [1] : []
    content {
      sid       = "ReadEcsAgentSsmReferences"
      effect    = "Allow"
      actions   = ["ssm:GetParameters"]
      resources = local.ssm_references
    }
  }

  dynamic "statement" {
    for_each = var.secret_mode == "ecs-agent" && var.secret_kms_key_arn != null ? [1] : []
    content {
      sid       = "DecryptEcsAgentSecretKey"
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = local.secret_kms_resources
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["secretsmanager.${var.region}.amazonaws.com", "ssm.${var.region}.amazonaws.com"]
      }
    }
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "${local.execution_role_name}-policy-v1"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

data "aws_iam_policy_document" "task" {
  dynamic "statement" {
    for_each = var.permissions
    content {
      sid       = statement.value.statement_id
      effect    = "Allow"
      actions   = tolist(statement.value.actions)
      resources = tolist(statement.value.resources)

      dynamic "condition" {
        for_each = statement.value.conditions
        content {
          test     = "StringEquals"
          variable = condition.key
          values   = [condition.value]
        }
      }
    }
  }

  dynamic "statement" {
    for_each = var.secret_mode == "application-pull" && length(local.secretsmanager_references) > 0 ? [1] : []
    content {
      sid       = "ReadApplicationPullSecretsManagerReferences"
      effect    = "Allow"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = local.secretsmanager_references
    }
  }

  dynamic "statement" {
    for_each = var.secret_mode == "application-pull" && length(local.ssm_references) > 0 ? [1] : []
    content {
      sid       = "ReadApplicationPullSsmReferences"
      effect    = "Allow"
      actions   = ["ssm:GetParameters"]
      resources = local.ssm_references
    }
  }

  dynamic "statement" {
    for_each = var.secret_mode == "application-pull" && var.secret_kms_key_arn != null ? [1] : []
    content {
      sid       = "DecryptApplicationPullSecretKey"
      effect    = "Allow"
      actions   = ["kms:Decrypt"]
      resources = local.secret_kms_resources
      condition {
        test     = "StringEquals"
        variable = "kms:ViaService"
        values   = ["secretsmanager.${var.region}.amazonaws.com", "ssm.${var.region}.amazonaws.com"]
      }
    }
  }
}

resource "aws_iam_role_policy" "task" {
  name   = "${local.task_role_name}-policy-v1"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task.json
}

data "aws_iam_policy" "customer_managed" {
  for_each = {
    for attachment in var.customer_managed_policy_attachments : attachment.policy_arn => attachment
  }
  arn = each.key
}

resource "aws_iam_role_policy_attachment" "customer_managed" {
  for_each   = data.aws_iam_policy.customer_managed
  role       = aws_iam_role.task.name
  policy_arn = each.value.arn
}
