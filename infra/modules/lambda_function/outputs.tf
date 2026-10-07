output "function_name" {
  description = "Deployed function name."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "Function ARN (the Gateway role will be allowed to invoke exactly this)."
  value       = aws_lambda_function.this.arn
}

output "role_arn" {
  description = "ARN of this function's execution role."
  value       = aws_iam_role.this.arn
}

output "log_group_name" {
  description = "CloudWatch log group for this function."
  value       = aws_cloudwatch_log_group.this.name
}
