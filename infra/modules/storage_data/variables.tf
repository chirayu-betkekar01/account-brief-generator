variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "accounts_file" {
  description = "Path to the synthetic accounts JSON (data/accounts.json). Each account becomes one DynamoDB item."
  type        = string
}

variable "extra_accounts_file" {
  description = "Optional second accounts file (data/eval_accounts.json: red-team fixtures). Null loads none."
  type        = string
  default     = null
}
