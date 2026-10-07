variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "grounding_threshold" {
  description = "Minimum grounding score (0 to 0.99) for the post-answer check. Higher blocks more; tuned in Phase 5."
  type        = number
  default     = 0.75
}

variable "relevance_threshold" {
  description = "Minimum relevance score (0 to 0.99) for the post-answer check."
  type        = number
  default     = 0.5
}
