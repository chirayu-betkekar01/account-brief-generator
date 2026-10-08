variable "region" {
  description = "AWS region. Credentials come from the environment (AWS_PROFILE), never from code."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short project slug used in resource names and tags. Must match the bootstrap stack, which names the budget after it."
  type        = string
  default     = "discovery-brief-agent"
}

variable "include_eval_fixtures" {
  description = "Load the two red-team test companies (data/eval_accounts.json) into the accounts table so the evaluation can test attacks that arrive through tool results. Set false for a demo with only the five real accounts."
  type        = bool
  default     = true
}

variable "comparison_model_ids" {
  description = "Extra inference profiles the agent role may call, used only for a model comparison via a per-call override. Empty (the default) grants nothing beyond the main model; the Haiku 4.5 comparison was not run, so its permission was removed. To run one: [\"us.anthropic.claude-haiku-4-5-20251001-v1:0\"] (and submit Anthropic's use-case form in the Bedrock console first)."
  type        = list(string)
  default     = []
}

variable "alarm_email" {
  description = "Optional address for CloudWatch alarm notifications. Leave empty for none. If set, put it in a git-ignored terraform.tfvars, never in the repo; AWS sends a confirmation email."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention for every Lambda."
  type        = number
  default     = 14
}
