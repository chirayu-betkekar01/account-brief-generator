output "table_name" {
  description = "Name of the accounts table (passed to the account_profile Lambda)."
  value       = aws_dynamodb_table.accounts.name
}

output "table_arn" {
  description = "ARN of the accounts table (the only resource account_profile may read)."
  value       = aws_dynamodb_table.accounts.arn
}

output "account_count" {
  description = "How many synthetic accounts were seeded."
  value       = length(aws_dynamodb_table_item.account)
}
