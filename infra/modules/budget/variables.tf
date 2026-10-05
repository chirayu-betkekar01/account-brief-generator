variable "project" {
  description = "Short project slug, used in the budget name."
  type        = string
}

variable "monthly_limit_usd" {
  description = "Monthly cost ceiling in USD. All alert thresholds are percentages of this."
  type        = number

  validation {
    condition     = var.monthly_limit_usd > 0
    error_message = "monthly_limit_usd must be greater than zero."
  }
}

variable "alert_emails" {
  description = "Addresses that receive budget alerts. Budgets e-mails need no subscription confirmation."
  type        = list(string)

  validation {
    condition     = length(var.alert_emails) > 0 && alltrue([for e in var.alert_emails : can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", e))])
    error_message = "Provide at least one valid e-mail address."
  }
}

variable "actual_thresholds_percent" {
  description = "Alert when ACTUAL spend passes each of these percentages of the limit."
  type        = list(number)
  default     = [20, 50, 80, 100]
}

variable "forecast_threshold_percent" {
  description = "Alert when FORECASTED spend passes this percentage of the limit."
  type        = number
  default     = 100
}
