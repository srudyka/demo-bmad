resource "aws_cloudwatch_log_group" "job" {
  name              = local.log_group_name
  kms_key_id        = try(local.contract.encryption.kms_key_arn, null)
  retention_in_days = local.effective_log_retention_days
  skip_destroy      = true
  tags              = local.merged_tags
}

resource "aws_ecs_task_definition" "job" {
  family                   = local.name_prefix
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  track_latest             = false
  skip_destroy             = true
  ephemeral_storage {
    size_in_gib = var.ephemeral_storage_gib
  }
  runtime_platform {
    operating_system_family = var.operating_system_family
    cpu_architecture        = var.cpu_architecture
  }
  container_definitions = jsonencode([
    {
      name       = local.name_prefix
      image      = var.image
      essential  = true
      command    = var.command
      entryPoint = var.entrypoint
      environment = concat(
        [
          { name = "JOB_ID", value = local.job_id },
          { name = "SOURCE_REVISION", value = var.source_revision },
          { name = "MODULE_VERSION", value = var.module_version },
          { name = "DEPLOYMENT_IDENTITY", value = local.deployment_identity_json },
          { name = "SECRET_MODE", value = var.secret_mode },
        ],
        var.secret_mode == "application-pull" ? [
          {
            name  = "SECRET_REFERENCE_LOCATORS"
            value = jsonencode([for index, reference in var.secret_references : { name = var.secret_environment_names[index], valueFrom = reference }])
          },
          { name = "SECRET_NETWORK_PATH", value = jsonencode(var.application_secret_network_path) },
        ] : [],
        [for name, value in var.environment_variables : { name = name, value = value }],
      )
      secrets = var.secret_mode == "ecs-agent" ? [
        for index, reference in var.secret_references : {
          name      = var.secret_environment_names[index]
          valueFrom = reference
        }
      ] : []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.job.name
          awslogs-region        = var.region
          awslogs-stream-prefix = local.name_prefix
        }
      }
    }
  ])
  tags = local.merged_tags

  depends_on = [terraform_data.declaration_validation]
}
