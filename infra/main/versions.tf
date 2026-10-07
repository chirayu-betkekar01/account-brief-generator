terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.67" # same pin as the bootstrap stack
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4" # zips the Lambda source directories
    }
  }

  # Local state for now (one person, one sandbox); git-ignored because it contains the account ID.
  # Production: S3 backend with locking, one state per environment.
}
