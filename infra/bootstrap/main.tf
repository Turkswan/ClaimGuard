# Run ONCE per AWS account. Creates the S3 bucket that stores every other Terraform state file.
# This config keeps its own state locally (terraform.tfstate in this folder) because the
# remote bucket does not exist yet: the classic chicken-and-egg problem.

terraform {
  required_version = ">= 1.11"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "region" {
  type    = string
  default = "eu-west-2"
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "claimguard", ManagedBy = "terraform", Component = "bootstrap" }
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "tfstate" {
  bucket = "claimguard-tfstate-${data.aws_caller_identity.current.account_id}"

  lifecycle {
    prevent_destroy = true # losing state = Terraform forgets what it built
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled" # every state change is kept, so a bad apply can be rolled back
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # state files can contain secrets
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}
