variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "function_name" {
  description = "Short function name; the deployed name is <project>-<function_name>."
  type        = string
}

variable "description" {
  description = "What the function does (shown in the Lambda console)."
  type        = string
}

variable "source_dir" {
  description = "Directory zipped as the deployment package. The handler module must sit at its top level."
  type        = string
}

variable "handler" {
  description = "Entry point as <module>.<function>."
  type        = string
  default     = "handler.lambda_handler"
}

variable "runtime" {
  description = "Lambda runtime. python3.14 is supported until 2029-06-30 (checked against the Lambda runtimes page on 2026-10-07)."
  type        = string
  default     = "python3.14"
}

variable "architecture" {
  description = "arm64 (Graviton) is billed at a lower per-GB-second rate than x86_64 and all managed runtimes support it."
  type        = string
  default     = "arm64"
}

variable "memory_mb" {
  description = "Memory size. Lambda also scales CPU with memory; 128 MB is plenty for lookups and arithmetic."
  type        = number
  default     = 128
}

variable "timeout_seconds" {
  description = "Hard stop for one invocation. A short timeout is a cost and safety cap."
  type        = number
  default     = 10
}

variable "environment" {
  description = "Environment variables for the function (configuration only, never secrets)."
  type        = map(string)
  default     = {}
}

variable "policy_statements" {
  description = "Extra IAM permissions beyond writing its own logs. Every statement should be justified by a comment at the call site."
  type = list(object({
    sid       = string
    actions   = list(string)
    resources = list(string)
  }))
  default = []
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps this function's logs. Without a setting they are kept (and billed) forever."
  type        = number
  default     = 14
}
