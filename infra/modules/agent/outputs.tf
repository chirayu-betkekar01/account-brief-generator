output "gateway_arn" {
  description = "ARN of the AgentCore Gateway."
  value       = aws_bedrockagentcore_gateway.this.gateway_arn
}

output "gateway_url" {
  description = "MCP endpoint of the Gateway (SigV4-signed requests only)."
  value       = aws_bedrockagentcore_gateway.this.gateway_url
}

output "gateway_tool_names" {
  description = "Tool names as the model sees them (target___tool)."
  value       = [for key, t in local.targets : "${key}___${t.tool_name}"]
}

output "harness_arn" {
  description = "ARN of the harness: what the client passes to InvokeHarness."
  value       = aws_bedrockagentcore_harness.this.arn
}

output "harness_id" {
  description = "ID of the harness."
  value       = aws_bedrockagentcore_harness.this.harness_id
}

output "harness_name" {
  description = "Name of the harness."
  value       = aws_bedrockagentcore_harness.this.harness_name
}

output "harness_runtime_id" {
  description = "ID of the managed runtime behind the harness (its log group is named after it)."
  value       = one(one(aws_bedrockagentcore_harness.this.environment_actual).agentcore_runtime_environment).agent_runtime_id
}

output "harness_runtime_name" {
  description = "Name of the managed runtime behind the harness (used in AgentCore metric dimensions)."
  value       = one(one(aws_bedrockagentcore_harness.this.environment_actual).agentcore_runtime_environment).agent_runtime_name
}

output "invoker_policy_arn" {
  description = "Unattached least-privilege policy for analysts who run briefs."
  value       = aws_iam_policy.invoker.arn
}

output "gateway_role_arn" {
  description = "ARN of the Gateway's service role."
  value       = aws_iam_role.gateway.arn
}

output "harness_role_arn" {
  description = "ARN of the harness execution role."
  value       = aws_iam_role.harness.arn
}
