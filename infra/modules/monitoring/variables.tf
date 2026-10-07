variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "region" {
  description = "AWS region the dashboard widgets read from."
  type        = string
}

variable "lambda_log_groups" {
  description = "Tool Lambda log groups keyed by a short function name (for example kb-retrieve). Each gets an error and a latency metric filter."
  type        = map(string)
}

variable "harness_runtime_id" {
  description = "ID of the runtime behind the harness. The harness writes to /aws/bedrock-agentcore/runtimes/<id>-DEFAULT."
  type        = string
}

variable "harness_arn" {
  description = "Harness ARN, the HarnessId dimension on AgentCore metrics."
  type        = string
}

variable "harness_runtime_name" {
  description = "Name of the managed runtime (harness_<name>), used in the Name dimension as <name>::DEFAULT."
  type        = string
}

variable "gateway_tool_names" {
  description = "Tool names as the gateway publishes them (target___tool), one latency line each on the dashboard."
  type        = list(string)
}

variable "guardrail_arn" {
  description = "Guardrail ARN (dimension on the guardrail metrics)."
  type        = string
}

variable "guardrail_version" {
  description = "Guardrail version (dimension on the guardrail metrics)."
  type        = string
}

variable "model_id" {
  description = "Model or inference profile ID (ModelId dimension on the token metrics)."
  type        = string
}

variable "log_retention_days" {
  description = "Retention for the log group this module owns (the harness one)."
  type        = number
  default     = 14
}

variable "alarm_email" {
  description = "Optional address for alarm notifications. Leave empty for alarms that only change state. Set it in a git-ignored tfvars file, never in the repo; AWS emails a confirmation link."
  type        = string
  default     = ""
}
