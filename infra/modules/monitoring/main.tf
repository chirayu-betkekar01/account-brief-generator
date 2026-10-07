# Observability for the discovery brief agent.
#
#  - the harness log group, with a retention period (the harness would otherwise create it with
#    "never expire")
#  - error and latency metric filters on each tool Lambda's JSON logs
#  - alarms on tool errors and harness system errors
#  - one dashboard: tool latency and errors, harness traffic, guardrail interventions, tokens
#
# Cost: all of it fits the CloudWatch always-free tier (10 custom metrics, 10 alarms, 3 dashboards),
# so the idle cost is $0. The metrics created by filters count as custom metrics: 6 here.

locals {
  namespace = "DiscoveryBriefAgent"

  harness_dimensions = {
    HarnessId         = var.harness_arn
    EndpointQualifier = "DEFAULT"
    Operation         = "InvokeAgentRuntime"
    Name              = "${var.harness_runtime_name}::DEFAULT"
  }

  # Dashboard helpers. A metric entry is [namespace, name, dim1, val1, dim2, val2, ..., {options}].
  harness_dim_list = flatten([for k, v in local.harness_dimensions : [k, v]])
}

# --- Logs -------------------------------------------------------------------------------------------

# The harness creates this group itself on first use, with no retention. Creating it here first
# (the name is known once the harness exists) gives it a retention period. On the first deployment
# this was imported with: terraform import 'module.monitoring.aws_cloudwatch_log_group.harness' <name>
resource "aws_cloudwatch_log_group" "harness" {
  name              = "/aws/bedrock-agentcore/runtimes/${var.harness_runtime_id}-DEFAULT"
  retention_in_days = var.log_retention_days

  lifecycle {
    # While the harness is being updated the provider reports its runtime ID as "unknown until
    # apply", which would make Terraform delete and recreate this group (and its logs) even though
    # the ID, and so the name, never changes for a given harness. If the harness itself is ever
    # replaced it gets a new runtime ID: destroy and re-create this group then (terraform taint).
    ignore_changes = [name]
  }
}

# --- Metric filters on the Lambda JSON logs ---------------------------------------------------------

# Errors: an application line logged at ERROR, or Lambda itself reporting the invocation as an error
# or a timeout. WARNING lines (such as "rejected invalid input") are not errors on purpose: the
# handler handled those and returned a normal answer.
resource "aws_cloudwatch_log_metric_filter" "errors" {
  for_each = var.lambda_log_groups

  name           = "${var.project}-${each.key}-errors"
  log_group_name = each.value
  pattern        = "{ ($.level = \"ERROR\") || ($.record.status = \"error\") || ($.record.status = \"timeout\") }"

  metric_transformation {
    name      = "${each.key}-errors"
    namespace = local.namespace
    value     = "1"
    unit      = "Count"
  }
}

# Latency: Lambda writes one platform.report line per invocation with the duration in milliseconds.
resource "aws_cloudwatch_log_metric_filter" "duration" {
  for_each = var.lambda_log_groups

  name           = "${var.project}-${each.key}-duration"
  log_group_name = each.value
  pattern        = "{ $.type = \"platform.report\" }"

  metric_transformation {
    name      = "${each.key}-duration-ms"
    namespace = local.namespace
    value     = "$.record.metrics.durationMs"
    unit      = "Milliseconds"
  }
}

# --- Alarms -----------------------------------------------------------------------------------------

resource "aws_sns_topic" "alarms" {
  count = var.alarm_email == "" ? 0 : 1

  name = "${var.project}-alarms"
}

resource "aws_sns_topic_subscription" "alarm_email" {
  count = var.alarm_email == "" ? 0 : 1

  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

locals {
  alarm_actions = var.alarm_email == "" ? [] : [aws_sns_topic.alarms[0].arn]
}

# Any error in a tool Lambda within five minutes. A tool failing is how an agent starts guessing,
# so even one is worth seeing. No data (the usual state) is treated as healthy.
resource "aws_cloudwatch_metric_alarm" "tool_errors" {
  for_each = var.lambda_log_groups

  alarm_name          = "${var.project}-${each.key}-errors"
  alarm_description   = "At least one error in the ${each.key} tool Lambda in 5 minutes."
  namespace           = local.namespace
  metric_name         = "${each.key}-errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions

  depends_on = [aws_cloudwatch_log_metric_filter.errors]
}

# AgentCore reports server-side failures of the harness itself.
resource "aws_cloudwatch_metric_alarm" "harness_system_errors" {
  alarm_name          = "${var.project}-harness-system-errors"
  alarm_description   = "At least one server-side error from the harness in 5 minutes."
  namespace           = "AWS/Bedrock-AgentCore"
  metric_name         = "SystemErrors"
  dimensions          = local.harness_dimensions
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

# --- Dashboard --------------------------------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = "${var.project}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Tool Lambda duration (ms, average and maximum)"
          region = var.region
          view   = "timeSeries"
          stat   = "Average"
          period = 300
          metrics = concat(
            [for k in keys(var.lambda_log_groups) : [local.namespace, "${k}-duration-ms", { label = "${k} avg" }]],
            [for k in keys(var.lambda_log_groups) : [local.namespace, "${k}-duration-ms", { label = "${k} max", stat = "Maximum" }]],
          )
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title   = "Tool Lambda errors (count)"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [for k in keys(var.lambda_log_groups) : [local.namespace, "${k}-errors", { label = k }]]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6
        properties = {
          title  = "Agent (harness) invocations and system errors"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            concat(["AWS/Bedrock-AgentCore", "Invocations"], local.harness_dim_list, [{ label = "invocations" }]),
            concat(["AWS/Bedrock-AgentCore", "SystemErrors"], local.harness_dim_list, [{ label = "system errors" }]),
            concat(["AWS/Bedrock-AgentCore", "UserErrors"], local.harness_dim_list, [{ label = "user errors" }]),
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6
        properties = {
          title  = "Agent end-to-end latency (ms, average and maximum)"
          region = var.region
          view   = "timeSeries"
          stat   = "Average"
          period = 300
          metrics = [
            concat(["AWS/Bedrock-AgentCore", "Latency"], local.harness_dim_list, [{ label = "average" }]),
            concat(["AWS/Bedrock-AgentCore", "Latency"], local.harness_dim_list, [{ label = "maximum", stat = "Maximum" }]),
          ]
        }
      },
      {
        type = "metric", x = 0, y = 12, width = 12, height = 6
        properties = {
          title  = "Gateway tool-call latency by tool (ms, average)"
          region = var.region
          view   = "timeSeries"
          stat   = "Average"
          period = 300
          metrics = [for t in var.gateway_tool_names : [
            "AWS/Bedrock-AgentCore", "Latency", "Operation", "InvokeGateway", "Method", "tools/call", "Protocol", "MCP", "Name", t,
            { label = t },
          ]]
        }
      },
      {
        type = "metric", x = 12, y = 12, width = 12, height = 6
        properties = {
          title  = "Guardrail: checks and interventions"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/Bedrock/Guardrails", "Invocations", "GuardrailArn", var.guardrail_arn, "GuardrailVersion", var.guardrail_version, { label = "checks" }],
            ["AWS/Bedrock/Guardrails", "InvocationsIntervened", "GuardrailArn", var.guardrail_arn, "GuardrailVersion", var.guardrail_version, { label = "interventions" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 18, width = 24, height = 6
        properties = {
          title  = "Model tokens (input and output)"
          region = var.region
          view   = "timeSeries"
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/Bedrock", "InputTokenCount", "ModelId", var.model_id, { label = "input tokens" }],
            ["AWS/Bedrock", "OutputTokenCount", "ModelId", var.model_id, { label = "output tokens" }],
          ]
        }
      },
    ]
  })
}
