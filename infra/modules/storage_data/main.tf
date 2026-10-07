# The synthetic customer accounts the agent looks up.

locals {
  # The partition key is the lower-cased company name. This must match
  # normalise() in src/lambdas/account_profile/handler.py; a unit test
  # (test_key_matches_what_terraform_will_compute) fails if the data ever breaks that.
  accounts = {
    for account in jsondecode(file(var.accounts_file)).accounts :
    lower(trimspace(account.company_name)) => account
  }
}

resource "aws_dynamodb_table" "accounts" {
  name         = "${var.project}-accounts"
  billing_mode = "PAY_PER_REQUEST" # pay per read/write; nothing to size, $0 while idle
  hash_key     = "company"

  attribute {
    name = "company"
    type = "S"
  }

  # Sandbox data that can be regenerated from data/accounts.json, so:
  #  * no deletion protection (it would block `make destroy`), and
  #  * no point-in-time recovery (continuous backups are billed per GB for no benefit here).
  # Encryption at rest uses the default AWS-owned key, which is free.
  deletion_protection_enabled = false

  point_in_time_recovery {
    enabled = false
  }
}

# One item per company. DynamoDB wants typed values: S = string, N = number, L = list.
resource "aws_dynamodb_table_item" "account" {
  for_each = local.accounts

  table_name = aws_dynamodb_table.accounts.name
  hash_key   = aws_dynamodb_table.accounts.hash_key

  item = jsonencode({
    company               = { S = each.key }
    company_name          = { S = each.value.company_name }
    industry              = { S = each.value.industry }
    employees             = { N = tostring(each.value.employees) }
    headquarters          = { S = each.value.headquarters }
    servers               = { N = tostring(each.value.servers) }
    storage_tb            = { N = tostring(each.value.storage_tb) }
    annual_infra_cost_usd = { N = tostring(each.value.annual_infra_cost_usd) }
    annual_growth_pct     = { N = tostring(each.value.annual_growth_pct) }
    current_environment   = { S = each.value.current_environment }
    workloads             = { L = [for w in each.value.workloads : { S = w }] }
    stated_pain_points    = { L = [for p in each.value.stated_pain_points : { S = p }] }
    compliance            = { L = [for c in each.value.compliance : { S = c }] }
    cloud_maturity        = { S = each.value.cloud_maturity }
  })
}
