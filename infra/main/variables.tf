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
