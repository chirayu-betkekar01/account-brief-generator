variable "region" {
  description = "AWS region. Credentials come from the environment (AWS_PROFILE), never from code."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short project slug used in resource names and tags."
  type        = string
  default     = "discovery-brief-agent"
}

variable "monthly_budget_usd" {
  description = "Hard ceiling for the whole build, in USD. Alerts fire at 20/50/80/100% of this."
  type        = number
  default     = 25
}

variable "alert_emails" {
  description = "Who gets budget alerts. No default: set it in terraform.tfvars (git-ignored)."
  type        = list(string)
}
