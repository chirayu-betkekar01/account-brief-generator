# The agent: an AgentCore Gateway that exposes the three Lambdas as MCP tools, and an AgentCore
# Harness (the managed agent loop) that calls the model, the guardrail and the Gateway.
#
# Two separate IAM roles, because they do different jobs:
#   gateway role  - lets the Gateway call the three Lambdas, nothing else
#   harness role  - lets the agent call one model, one guardrail and one gateway, and write telemetry

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region

  gateway_name = "${var.project}-gateway"
  # Harness names allow letters, digits and underscores only (no hyphens), max 40 characters.
  harness_name = replace("${var.project}", "-", "_")
  # The name the harness gives the gateway tool group. allowed_tools refers to it with "@".
  tool_group = "discovery_tools"

  # Targets are named short because the model sees every tool as <target>___<tool> (three
  # underscores) and the whole name must stay readable and under Converse's 64-character limit.
  targets = {
    profile = {
      lambda_arn  = var.lambda_arns.profile
      description = "Looks up the stored profile of one fictional company."
      tool_name   = "get_account_profile"
      tool_description = join(" ", [
        "Look up the profile of one company by name.",
        "Returns found=true with the profile (industry, employees, servers, storage_tb, annual_infra_cost_usd,",
        "annual_growth_pct, current_environment, workloads, stated_pain_points, compliance, cloud_maturity),",
        "or found=false when the company is not in the database.",
      ])
      properties = [
        { name = "company_name", type = "string", required = true, description = "Company name exactly as the user gave it, for example Northwind Logistics." },
      ]
    }
    roi = {
      lambda_arn  = var.lambda_arns.roi
      description = "Computes a 3-year on-premises versus AWS cost comparison."
      tool_name   = "estimate_roi"
      tool_description = join(" ", [
        "Estimate a preliminary 3-year ROI of moving from on-premises to AWS.",
        "Returns ok=true with per-year costs, totals, roi_pct, breakeven_year and the assumptions used",
        "(each with value, unit, rationale and source), or ok=false with an error.",
        "Use the four inputs exactly as they appear in the company profile.",
      ])
      properties = [
        { name = "on_prem_annual_cost_usd", type = "number", required = true, description = "Current annual on-premises infrastructure cost in US dollars (profile field annual_infra_cost_usd)." },
        { name = "servers", type = "integer", required = true, description = "Number of servers (profile field servers)." },
        { name = "storage_tb", type = "number", required = true, description = "Storage in terabytes (profile field storage_tb)." },
        { name = "annual_growth_pct", type = "number", required = true, description = "Expected yearly growth of the estate, in percent (profile field annual_growth_pct)." },
      ]
    }
    kb = {
      lambda_arn  = var.lambda_arns.kb
      description = "Searches short AWS best-practice documents and returns passages with source links."
      tool_name   = "search_knowledge_base"
      tool_description = join(" ", [
        "Search the AWS best-practice knowledge base.",
        "Returns found and a list of passages, each with text, score (0 to 1, higher is more relevant),",
        "title, topic, source_url and checked_on. Search always returns something, so judge relevance by score.",
      ])
      properties = [
        { name = "query", type = "string", required = true, description = "A natural-language question about migration, architecture, compliance, cost or resilience, at most 500 characters." },
        { name = "max_results", type = "integer", required = false, description = "How many passages to return, 1 to 8. Defaults to 4." },
      ]
    }
  }
}

# --- Gateway role -------------------------------------------------------------------------------

data "aws_iam_policy_document" "gateway_trust" {
  statement {
    sid     = "AgentCoreGatewayMayAssume"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }

    # Confused-deputy protection: only a gateway in this account, and only one named like ours.
    # (The gateway's ID is generated as <name>-<suffix>, so the name prefix is known in advance.)
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock-agentcore:${local.region}:${local.account_id}:gateway/${local.gateway_name}-*"]
    }
  }
}

resource "aws_iam_role" "gateway" {
  name               = "${var.project}-gateway-role"
  description        = "Assumed by the AgentCore Gateway to call the three tool Lambdas. Nothing else may use it."
  assume_role_policy = data.aws_iam_policy_document.gateway_trust.json
}

data "aws_iam_policy_document" "gateway_permissions" {
  # The Gateway runs a tool by invoking its Lambda. These three function ARNs are the whole list:
  # it cannot invoke any other function, and it cannot read or change anything else.
  statement {
    sid       = "InvokeTheThreeToolLambdas"
    actions   = ["lambda:InvokeFunction"]
    resources = [var.lambda_arns.profile, var.lambda_arns.roi, var.lambda_arns.kb]
  }
}

resource "aws_iam_role_policy" "gateway" {
  name   = "${var.project}-gateway-permissions"
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway_permissions.json
}

# --- Gateway and its three tools ------------------------------------------------------------------

resource "aws_bedrockagentcore_gateway" "this" {
  name        = local.gateway_name
  description = "MCP tool surface for the discovery brief agent: account profile, knowledge base search, ROI estimate."
  role_arn    = aws_iam_role.gateway.arn

  # AWS_IAM: callers must sign requests with SigV4 and hold bedrock-agentcore:InvokeGateway.
  # No JWT or identity provider is needed, and no anonymous access exists.
  authorizer_type = "AWS_IAM"
  protocol_type   = "MCP"

  depends_on = [aws_iam_role_policy.gateway]
}

resource "aws_bedrockagentcore_gateway_target" "tool" {
  for_each = local.targets

  gateway_identifier = aws_bedrockagentcore_gateway.this.gateway_id
  name               = each.key
  description        = each.value.description

  # The Gateway calls the Lambda with its own service role (the one above).
  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = each.value.lambda_arn

        tool_schema {
          inline_payload {
            name        = each.value.tool_name
            description = each.value.tool_description

            input_schema {
              type = "object"

              dynamic "property" {
                for_each = each.value.properties

                content {
                  name        = property.value.name
                  type        = property.value.type
                  required    = property.value.required
                  description = property.value.description
                }
              }
            }
          }
        }
      }
    }
  }
}

# --- Harness role -------------------------------------------------------------------------------

data "aws_iam_policy_document" "harness_trust" {
  statement {
    sid     = "AgentCoreMayAssume"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role" "harness" {
  name               = "${var.project}-harness-role"
  description        = "Assumed by the AgentCore harness while it runs the agent. Nothing else may use it."
  assume_role_policy = data.aws_iam_policy_document.harness_trust.json
}

data "aws_iam_policy_document" "harness_permissions" {
  # The model. The US inference profile routes a call to one of three regions, and Bedrock checks
  # permission on both the profile and the underlying foundation model in whichever region is used.
  # So: the one profile, and the one model in each of its three regions. No other model.
  statement {
    sid     = "CallTheOneModel"
    actions = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = concat(
      ["arn:aws:bedrock:${local.region}:${local.account_id}:inference-profile/${var.model_id}"],
      [for r in var.model_profile_regions : "arn:aws:bedrock:${r}::foundation-model/${trimprefix(var.model_id, "us.")}"],
    )
  }

  # The guardrail is applied to every model call, which requires this action on that guardrail.
  statement {
    sid       = "ApplyTheOneGuardrail"
    actions   = ["bedrock:ApplyGuardrail"]
    resources = [var.guardrail_arn]
  }

  # Calling the tools: invoke this one gateway (our gateway uses IAM sign-in, so this is the key).
  statement {
    sid       = "CallTheOneGateway"
    actions   = ["bedrock-agentcore:InvokeGateway"]
    resources = [aws_bedrockagentcore_gateway.this.gateway_arn]
  }

  # Workload identity: the token the harness uses to prove who it is to other AgentCore services.
  # Limited to the default directory and to identities named for this harness.
  statement {
    sid     = "WorkloadIdentityToken"
    actions = ["bedrock-agentcore:GetWorkloadAccessToken", "bedrock-agentcore:GetWorkloadAccessTokenForJWT"]
    resources = [
      "arn:aws:bedrock-agentcore:${local.region}:${local.account_id}:workload-identity-directory/default",
      "arn:aws:bedrock-agentcore:${local.region}:${local.account_id}:workload-identity-directory/default/workload-identity/harness_${local.harness_name}-*",
    ]
  }

  # Logs: the runtime writes to groups under this prefix. Limited to that prefix.
  statement {
    sid       = "RuntimeLogGroups"
    actions   = ["logs:CreateLogGroup", "logs:DescribeLogStreams"]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"]
  }

  statement {
    sid       = "RuntimeListLogGroups"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:*"]
  }

  statement {
    sid       = "RuntimeWriteLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]
  }

  # Metrics: only into the AgentCore namespace.
  statement {
    sid       = "PublishAgentCoreMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"] # this action cannot be limited to a resource; the condition below limits it instead

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["bedrock-agentcore"]
    }
  }

  # Traces. X-Ray actions do not support resource-level limits, so "*" is unavoidable here.
  statement {
    sid = "WriteTraces"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
    ]
    resources = ["*"]
  }

  # On the public network the harness pulls its managed container image from Amazon ECR Public,
  # which needs these two token actions. Neither supports resource-level limits.
  statement {
    sid       = "PullManagedImage"
    actions   = ["ecr-public:GetAuthorizationToken", "sts:GetServiceBearerToken"]
    resources = ["*"]
  }

  # Deliberately NOT granted: AgentCore Memory (turned off), Browser, Code Interpreter, any S3 or
  # DynamoDB access, sts:AssumeRole, and any other bedrock action.
}

resource "aws_iam_role_policy" "harness" {
  name   = "${var.project}-harness-permissions"
  role   = aws_iam_role.harness.id
  policy = data.aws_iam_policy_document.harness_permissions.json
}

# --- The harness (the agent itself) ----------------------------------------------------------------

resource "aws_bedrockagentcore_harness" "this" {
  harness_name       = local.harness_name
  execution_role_arn = aws_iam_role.harness.arn

  # Hard caps: a looping or manipulated agent stops here rather than running up the bill.
  max_iterations  = var.max_iterations
  max_tokens      = var.max_tokens
  timeout_seconds = var.timeout_seconds

  model {
    bedrock_model_config {
      model_id    = var.model_id
      api_format  = "converse_stream" # required for guardrails
      temperature = var.temperature
      max_tokens  = var.model_max_tokens

      # The harness passes this straight to the Converse API on every model call.
      additional_params = jsonencode({
        guardrailConfig = {
          guardrailIdentifier = var.guardrail_arn
          guardrailVersion    = var.guardrail_version
          trace               = var.guardrail_trace
        }
      })
    }
  }

  system_prompt {
    text = file(var.system_prompt_file)
  }

  # The only tools the agent has: everything on our gateway, using the harness role's IAM sign-in.
  tool {
    type = "agentcore_gateway"
    name = local.tool_group

    config {
      agentcore_gateway {
        gateway_arn = aws_bedrockagentcore_gateway.this.gateway_arn

        outbound_auth {
          aws_iam = true
        }
      }
    }
  }

  # Every harness session also gets a bash shell and a file editor unless told otherwise. A brief
  # writer needs neither, and a shell is exactly what a prompt-injection attack wants. This
  # allow-list leaves only the gateway's tools (and trims about 900 input tokens per model call).
  allowed_tools = ["@${local.tool_group}"]

  # No memory: each brief is independent, and managed memory is on by default and billed.
  memory {
    disabled {}
  }

  environment {
    agentcore_runtime_environment {
      # Declared although PUBLIC is the default: without it AWS fills in this block itself and
      # provider 6.67.0 reports "inconsistent result after apply" and marks the harness tainted.
      network_configuration {
        network_mode = "PUBLIC"
      }

      lifecycle_configuration {
        idle_runtime_session_timeout = var.idle_session_timeout_seconds
        max_lifetime                 = var.max_session_lifetime_seconds
      }
    }
  }

  depends_on = [
    aws_iam_role_policy.harness,
    aws_bedrockagentcore_gateway_target.tool,
  ]
}

# --- Who may call the agent ---------------------------------------------------------------------------

# A ready-made policy for analysts who should be able to run briefs and do nothing else. It is NOT
# attached to anyone: the sandbox admin user already has access. It documents the minimum a caller
# needs, which surprises people: InvokeHarness alone is not enough, InvokeAgentRuntime is needed too.
data "aws_iam_policy_document" "invoker" {
  statement {
    sid       = "RunBriefsOnTheOneHarness"
    actions   = ["bedrock-agentcore:InvokeHarness", "bedrock-agentcore:InvokeAgentRuntime"]
    resources = [aws_bedrockagentcore_harness.this.arn]
  }

  # The optional post-answer grounding check the client runs.
  statement {
    sid       = "RunGroundingCheckWithTheOneGuardrail"
    actions   = ["bedrock:ApplyGuardrail"]
    resources = [var.guardrail_arn]
  }
}

resource "aws_iam_policy" "invoker" {
  name        = "${var.project}-invoker"
  description = "Least privilege to run discovery briefs: invoke the one harness and apply the one guardrail."
  policy      = data.aws_iam_policy_document.invoker.json
}
