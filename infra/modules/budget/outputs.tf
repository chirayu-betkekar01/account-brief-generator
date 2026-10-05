output "budget_name" {
  description = "Name of the cost budget (the main stack checks this exists before creating anything billable)."
  value       = aws_budgets_budget.monthly_cost.name
}

output "monthly_limit_usd" {
  description = "Monthly limit the budget enforces."
  value       = var.monthly_limit_usd
}
