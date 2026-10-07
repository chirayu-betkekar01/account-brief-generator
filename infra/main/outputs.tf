output "accounts_table_name" {
  description = "DynamoDB table holding the synthetic accounts."
  value       = module.storage_data.table_name
}

output "seeded_accounts" {
  description = "Number of synthetic accounts loaded into the table."
  value       = module.storage_data.account_count
}

output "account_profile_function_name" {
  description = "Deployed name of the account_profile Lambda."
  value       = module.account_profile.function_name
}

output "roi_estimator_function_name" {
  description = "Deployed name of the roi_estimator Lambda."
  value       = module.roi_estimator.function_name
}

output "budget_guard" {
  description = "The budget alarm that was confirmed to exist before anything was created."
  value       = data.aws_budgets_budget.guard.name
}
