locals {
  role_subjects = {
    plan  = var.plan_oidc_subject
    apply = var.apply_oidc_subject
  }
}

resource "terraform_data" "subject_bindings" {
  input = {
    plan  = var.plan_oidc_subject
    apply = var.apply_oidc_subject
  }
  lifecycle {
    precondition {
      condition     = var.plan_oidc_subject != var.apply_oidc_subject
      error_message = "plan and apply OIDC subjects must be distinct."
    }
    precondition {
      condition     = alltrue([for arn in var.apply_resource_arns : anytrue([for prefix in var.apply_resource_prefixes : startswith(arn, prefix)])])
      error_message = "apply resources must remain inside the manifest-bound platform namespaces."
    }
    precondition {
      condition     = alltrue([for subject in [var.plan_oidc_subject, var.apply_oidc_subject] : strcontains(subject, "repository_owner_id:${var.repository_owner_id}:repository_id:${var.repository_id}:environment:${var.environment}:job_workflow_ref:")])
      error_message = "OIDC subjects must match manifest repository IDs and Environment."
    }
  }
}

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket_name
  tags   = var.tags
  lifecycle {
    precondition {
      condition     = var.state_bucket_arn == "arn:aws:s3:::${var.state_bucket_name}"
      error_message = "state_bucket_arn must match state_bucket_name."
    }
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "trust" {
  for_each = local.role_subjects
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [each.value]
    }
  }
}

data "aws_iam_policy_document" "boundary" {
  statement {
    effect    = "Allow"
    actions   = concat(["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketVersioning", "s3:GetBucketLocation"], var.apply_actions)
    resources = concat([aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/${var.state_key}", "${aws_s3_bucket.state.arn}/${var.state_key}.tflock"], var.apply_resource_arns)
  }
  statement {
    effect    = "Deny"
    actions   = ["iam:CreateUser", "iam:CreateAccessKey", "iam:PutRolePolicy", "iam:DeleteRolePermissionsBoundary", "iam:UpdateAssumeRolePolicy", "iam:PassRole", "sts:AssumeRole"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "boundary" {
  name   = "${var.name}-permissions-boundary"
  policy = data.aws_iam_policy_document.boundary.json
  tags   = var.tags
}

data "aws_iam_policy_document" "plan" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.state.arn}/${var.state_key}", "${aws_s3_bucket.state.arn}/${var.state_key}.tflock"]
  }
  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketVersioning", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.state.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = [var.state_key, "${var.state_key}.tflock"]
    }
  }
}

data "aws_iam_policy_document" "apply" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/${var.state_key}", "${aws_s3_bucket.state.arn}/${var.state_key}.tflock"]
  }
  dynamic "statement" {
    for_each = length(var.apply_actions) > 0 && length(var.apply_resource_arns) > 0 ? [true] : []
    content {
      effect    = "Allow"
      actions   = var.apply_actions
      resources = var.apply_resource_arns
    }
  }
  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketVersioning", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.state.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = [var.state_key, "${var.state_key}.tflock"]
    }
  }
}

resource "aws_iam_role" "plan" {
  name                 = "${var.name}-plan"
  assume_role_policy   = data.aws_iam_policy_document.trust["plan"].json
  permissions_boundary = var.permissions_boundary_arn
  lifecycle {
    precondition {
      condition     = var.permissions_boundary_arn == aws_iam_policy.boundary.arn
      error_message = "permissions_boundary_arn must equal the module-owned boundary ARN."
    }
  }
  max_session_duration = var.plan_session_duration
  tags                 = merge(var.tags, { RoleType = "plan" })
}

resource "aws_iam_role" "apply" {
  name                 = "${var.name}-apply"
  assume_role_policy   = data.aws_iam_policy_document.trust["apply"].json
  permissions_boundary = var.permissions_boundary_arn
  lifecycle {
    precondition {
      condition     = var.permissions_boundary_arn == aws_iam_policy.boundary.arn
      error_message = "permissions_boundary_arn must equal the module-owned boundary ARN."
    }
  }
  max_session_duration = var.apply_session_duration
  tags                 = merge(var.tags, { RoleType = "apply" })
}

resource "aws_iam_role_policy" "plan" {
  name   = "${var.name}-plan"
  role   = aws_iam_role.plan.id
  policy = data.aws_iam_policy_document.plan.json
}

resource "aws_iam_role_policy" "apply" {
  name   = "${var.name}-apply"
  role   = aws_iam_role.apply.id
  policy = data.aws_iam_policy_document.apply.json
}
