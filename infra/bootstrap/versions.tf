terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.67" # verified latest on 2026-10-05: 6.67.0 (S3 Vectors + AgentCore resources)
    }
  }

  # Local state on purpose: this stack holds one free resource and the main stack reads
  # its output. State files are git-ignored because they contain the account ID.
  # Production: move both stacks to an S3 backend with locking (see README).
}
