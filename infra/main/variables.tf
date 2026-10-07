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

variable "log_retention_days" {
  description = "CloudWatch log retention for every Lambda."
  type        = number
  default     = 14
}
