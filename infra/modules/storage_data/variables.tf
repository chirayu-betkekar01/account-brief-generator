variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "accounts_file" {
  description = "Path to the synthetic accounts JSON (data/accounts.json). Each account becomes one DynamoDB item."
  type        = string
}
