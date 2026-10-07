# Main stack: everything the agent runs on. Applied only after the bootstrap stack (the budget).
# Phase 2 contents: the accounts table and the two action Lambdas. Later phases add the
# knowledge base, guardrail, AgentCore gateway + harness and monitoring.

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      ManagedBy   = "terraform"
      Environment = "sandbox"
    }
  }
}

locals {
  budget_name = "${var.project}-monthly-cost"
  lambda_src  = "${path.root}/../../src/lambdas"
  data_dir    = "${path.root}/../../data"
}

# --- Cost guard-rail ---------------------------------------------------------------------------
# Ask AWS itself (not a local state file) whether the budget alarm exists. If it does not, this
# data source fails and the plan stops before anything billable can be created.
data "aws_budgets_budget" "guard" {
  name = local.budget_name
}

resource "terraform_data" "budget_guard" {
  lifecycle {
    precondition {
      condition     = data.aws_budgets_budget.guard.name == local.budget_name
      error_message = "The budget alarm ${local.budget_name} was not found. Run `make bootstrap-apply` first."
    }
  }
}

# --- Data --------------------------------------------------------------------------------------
module "storage_data" {
  source = "../modules/storage_data"

  project       = var.project
  accounts_file = "${local.data_dir}/accounts.json"

  depends_on = [terraform_data.budget_guard]
}

# --- Action Lambdas ----------------------------------------------------------------------------
module "account_profile" {
  source = "../modules/lambda_function"

  project            = var.project
  function_name      = "account-profile"
  description        = "Looks up one synthetic company profile by name."
  source_dir         = "${local.lambda_src}/account_profile"
  log_retention_days = var.log_retention_days

  environment = {
    TABLE_NAME = module.storage_data.table_name
  }

  policy_statements = [
    {
      # The handler makes exactly one AWS call, get_item. So it gets that one action on that one
      # table: no Scan or Query (it cannot list other rows), no Put or Delete (it cannot change
      # data), no other table.
      sid       = "ReadOneAccountRow"
      actions   = ["dynamodb:GetItem"]
      resources = [module.storage_data.table_arn]
    },
  ]

  depends_on = [terraform_data.budget_guard]
}

module "roi_estimator" {
  source = "../modules/lambda_function"

  project            = var.project
  function_name      = "roi-estimator"
  description        = "Computes a 3-year on-premises vs AWS ROI from stated assumptions."
  source_dir         = "${local.lambda_src}/roi_estimator"
  log_retention_days = var.log_retention_days

  # No policy_statements on purpose: this function is pure arithmetic and calls no AWS service,
  # so its role can only write its own logs.

  depends_on = [terraform_data.budget_guard]
}
