output "budget_name" {
  description = "Budget guarding this project. The main stack refuses to deploy if this is missing."
  value       = module.budget.budget_name
}

output "monthly_limit_usd" {
  description = "Monthly ceiling the budget enforces."
  value       = module.budget.monthly_limit_usd
}
