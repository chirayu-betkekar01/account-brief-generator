# Bootstrap stack: applied FIRST, before the main stack exists.
#
# It is deliberately a separate root module with its own state so that
#   * the cost alarm exists before any billable resource can be created, and
#   * `make destroy` (which tears down the main stack) leaves the free budget in place.
#     `make destroy-all` removes the budget as well.

provider "aws" {
  region = var.region

  # Tags flow to every taggable resource; handy for Cost Explorer once the
  # "Project" cost-allocation tag is activated in the Billing console.
  default_tags {
    tags = {
      Project     = var.project
      ManagedBy   = "terraform"
      Environment = "sandbox"
    }
  }
}

module "budget" {
  source = "../modules/budget"

  project           = var.project
  monthly_limit_usd = var.monthly_budget_usd
  alert_emails      = var.alert_emails
}
