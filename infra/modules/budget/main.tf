# Account-level cost guard-rail. This is the first thing we create (see infra/bootstrap)
# so that nothing billable ever exists without an alarm watching it.
#
# What it is NOT: a hard stop. AWS Budgets refreshes up to three times a day, roughly
# 8-12 hours apart, and AWS documents that spend can pass a threshold before the alert
# arrives. The hard limits live elsewhere (harness max_iterations / max_tokens /
# timeout, tiny per-request prices, and `make destroy`). See docs/costs.md.
#
# Cost of this resource: $0 ($0.00 per budget-day; no budget *actions* are configured,
# so the "first two action-enabled budgets free" allowance is not even used).
resource "aws_budgets_budget" "monthly_cost" {
  name         = "${var.project}-monthly-cost"
  budget_type  = "COST"
  limit_amount = format("%.2f", var.monthly_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Track gross usage: promotional credits and refunds must not hide a runaway bill.
  # (Every other cost type keeps the provider default, i.e. included.)
  cost_types {
    include_credit = false
    include_refund = false
  }

  # Account-wide on purpose: this is meant to be a dedicated sandbox account, and an
  # account-wide budget cannot be fooled by a resource that forgot its tags.

  dynamic "notification" {
    for_each = toset(var.actual_thresholds_percent)

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.alert_emails
    }
  }

  # Early warning based on AWS's spend forecast. Forecasts need usage history, so in a
  # brand-new account this may stay silent for a while; the ACTUAL alerts above still work.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.forecast_threshold_percent
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alert_emails
  }
}
