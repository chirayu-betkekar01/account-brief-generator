output "guardrail_arn" {
  description = "ARN of the guardrail (the harness role is allowed ApplyGuardrail on exactly this)."
  value       = aws_bedrock_guardrail.this.guardrail_arn
}

output "guardrail_id" {
  description = "Guardrail ID, used by the client and evaluation script for ApplyGuardrail."
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_version" {
  description = "Numbered version the harness uses."
  value       = aws_bedrock_guardrail_version.this.version
}
