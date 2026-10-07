variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "lambda_arns" {
  description = "ARNs of the three tool Lambdas, keyed profile, roi and kb. The Gateway role may invoke exactly these."
  type = object({
    profile = string
    roi     = string
    kb      = string
  })
}

variable "guardrail_arn" {
  description = "Guardrail the harness applies to every model call."
  type        = string
}

variable "guardrail_version" {
  description = "Numbered guardrail version (never DRAFT)."
  type        = string
}

variable "guardrail_trace" {
  description = "Guardrail trace level: disabled, enabled or enabled_full. A trace echoes the text that matched, including any PII, into the response stream; keep it off outside a sandbox with synthetic data."
  type        = string
  default     = "enabled"

  validation {
    condition     = contains(["disabled", "enabled", "enabled_full"], var.guardrail_trace)
    error_message = "guardrail_trace must be disabled, enabled or enabled_full."
  }
}

variable "model_id" {
  description = "Inference profile the harness calls. Nova 2 Lite on the US profile; verify with scripts/price_check.py before changing."
  type        = string
  default     = "us.amazon.nova-2-lite-v1:0"
}

variable "model_profile_regions" {
  description = "Regions the US inference profile can route to. The execution role is allowed the one foundation model in each of these and nowhere else."
  type        = list(string)
  default     = ["us-east-1", "us-east-2", "us-west-2"]
}

variable "temperature" {
  description = "Sampling temperature. Low, because a brief should be consistent and factual."
  type        = number
  default     = 0.2
}

variable "model_max_tokens" {
  description = "Output-token limit for ONE model call. The finished brief needs about 1,200 tokens; the unset default cut the first test answer off at 1,000."
  type        = number
  default     = 3000
}

variable "system_prompt_file" {
  description = "Path to the markdown file holding the agent's system prompt."
  type        = string
}

variable "max_iterations" {
  description = "Hard cap on reasoning/action cycles per invocation. A normal brief needs about 6 (profile, 1-3 searches, ROI, answer)."
  type        = number
  default     = 12
}

variable "max_tokens" {
  description = "Hard cap on output tokens across all model calls in one invocation."
  type        = number
  default     = 6000
}

variable "timeout_seconds" {
  description = "Hard cap on wall-clock time for one invocation."
  type        = number
  default     = 180
}

variable "idle_session_timeout_seconds" {
  description = "How long an idle microVM stays warm. Memory is billed while it lives and every brief uses a new session, so keep this at the minimum (60)."
  type        = number
  default     = 60
}

variable "max_session_lifetime_seconds" {
  description = "Longest a microVM session may live."
  type        = number
  default     = 900
}
