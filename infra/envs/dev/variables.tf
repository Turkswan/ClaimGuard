variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "github_repo" {
  description = "GitHub repo allowed to deploy, as owner/name"
  type        = string
}

variable "eks_enabled" {
  description = "Create the EKS cluster and NAT gateway (the parts that cost money per hour)"
  type        = bool
  default     = false
}

variable "kubernetes_version" {
  type    = string
  default = "1.35"
}

variable "node_instance_type" {
  type    = string
  default = "t3.large"
}

locals {
  name       = "claimguard-dev"
  account_id = data.aws_caller_identity.current.account_id
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)
}

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}
