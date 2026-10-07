# One Lambda function with its own IAM role and its own log group.
# Calling this module once per function is what gives each function its own badge.

locals {
  name = "${var.project}-${var.function_name}"
}

# --- Package the code -------------------------------------------------------------------------

data "archive_file" "package" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.root}/build/${local.name}.zip"
  excludes    = ["__pycache__", "__pycache__/*", "**/__pycache__/*", "*.pyc"]
}

# --- Logs --------------------------------------------------------------------------------------

# Created here (not left for Lambda to create on first run) so we control the retention and so the
# role below can be limited to writing to this one group.
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = var.log_retention_days
}

# --- Identity ----------------------------------------------------------------------------------

data "aws_iam_policy_document" "trust" {
  # Who may put on this badge: only the Lambda service, and only to run this kind of function.
  statement {
    sid     = "LambdaServiceMayAssume"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${local.name}-role"
  description        = "Execution role for ${local.name}. Nothing else may use it."
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "permissions" {
  # Needed so the function can write its own logs. Limited to this function's log group:
  # CreateLogGroup is deliberately NOT granted because Terraform creates the group above.
  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  # Anything else this function needs (each justified where the module is called).
  dynamic "statement" {
    for_each = var.policy_statements

    content {
      sid       = statement.value.sid
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }
}

resource "aws_iam_role_policy" "permissions" {
  name   = "${local.name}-permissions"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.permissions.json
}

# --- The function ------------------------------------------------------------------------------

resource "aws_lambda_function" "this" {
  function_name = local.name
  description   = var.description
  role          = aws_iam_role.this.arn

  runtime       = var.runtime
  handler       = var.handler
  architectures = [var.architecture]
  memory_size   = var.memory_mb
  timeout       = var.timeout_seconds

  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256

  # Structured (JSON) logs make the Phase 4 error and latency metric filters simple and reliable.
  logging_config {
    log_format = "JSON"
    log_group  = aws_cloudwatch_log_group.this.name
  }

  dynamic "environment" {
    for_each = length(var.environment) > 0 ? [var.environment] : []

    content {
      variables = environment.value
    }
  }

  # The role's permissions and the log group must exist before the first invocation.
  depends_on = [aws_iam_role_policy.permissions]
}
