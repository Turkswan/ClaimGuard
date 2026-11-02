terraform {
  required_version = ">= 1.11"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Remote state: shared, versioned, encrypted, and locked so two people can't apply at once.
  # Replace 067506873975 with your 12-digit account ID (backend blocks can't use variables).
  backend "s3" {
    bucket       = "claimguard-tfstate-067506873975"
    key          = "envs/dev/terraform.tfstate"
    region       = "eu-west-2"
    encrypt      = true
    use_lockfile = true # native S3 locking; older setups used a DynamoDB table for this
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "claimguard"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}
