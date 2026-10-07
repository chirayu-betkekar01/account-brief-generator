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

output "knowledge_base_id" {
  description = "Bedrock knowledge base ID (used by scripts/kb_ingest.py)."
  value       = module.knowledge_base.knowledge_base_id
}

output "data_source_id" {
  description = "Knowledge base S3 data source ID (used by scripts/kb_ingest.py)."
  value       = module.knowledge_base.data_source_id
}

output "kb_documents" {
  description = "Number of documents uploaded to the knowledge base bucket."
  value       = module.knowledge_base.document_count
}

output "kb_retrieve_function_name" {
  description = "Deployed name of the kb_retrieve Lambda."
  value       = module.kb_retrieve.function_name
}

output "guardrail_id" {
  description = "Guardrail ID (used by the client and evaluation script for ApplyGuardrail)."
  value       = module.guardrails.guardrail_id
}

output "guardrail_version" {
  description = "Numbered guardrail version the agent uses."
  value       = module.guardrails.guardrail_version
}

output "harness_arn" {
  description = "ARN of the agent harness (what the client passes to InvokeHarness)."
  value       = module.agent.harness_arn
}

output "harness_runtime_id" {
  description = "ID of the runtime behind the harness (its log group is named after it)."
  value       = module.agent.harness_runtime_id
}

output "gateway_url" {
  description = "MCP endpoint of the AgentCore Gateway."
  value       = module.agent.gateway_url
}

output "gateway_tool_names" {
  description = "Tool names as the model sees them."
  value       = module.agent.gateway_tool_names
}

output "dashboard_name" {
  description = "CloudWatch dashboard for the agent."
  value       = module.monitoring.dashboard_name
}

output "harness_log_group" {
  description = "Log group the harness writes to."
  value       = module.monitoring.harness_log_group
}

output "alarm_names" {
  description = "CloudWatch alarms."
  value       = module.monitoring.alarm_names
}

output "invoker_policy_arn" {
  description = "Unattached least-privilege policy for people who run briefs."
  value       = module.agent.invoker_policy_arn
}

output "budget_guard" {
  description = "The budget alarm that was confirmed to exist before anything was created."
  value       = data.aws_budgets_budget.guard.name
}
