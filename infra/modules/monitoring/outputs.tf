output "dashboard_name" {
  description = "CloudWatch dashboard name."
  value       = aws_cloudwatch_dashboard.this.dashboard_name
}

output "harness_log_group" {
  description = "Log group the harness writes to (retention managed here)."
  value       = aws_cloudwatch_log_group.harness.name
}

output "alarm_names" {
  description = "Names of all alarms."
  value = concat(
    [for a in aws_cloudwatch_metric_alarm.tool_errors : a.alarm_name],
    [aws_cloudwatch_metric_alarm.harness_system_errors.alarm_name],
  )
}
