# VPC: public subnets for load balancers and the NAT gateway, private subnets for the worker nodes.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = local.name
  cidr = "10.20.0.0/16"
  azs  = local.azs

  private_subnets = ["10.20.1.0/24", "10.20.2.0/24"]
  public_subnets  = ["10.20.101.0/24", "10.20.102.0/24"]

  # Nodes in private subnets reach the internet (ECR, S3, updates) through a NAT gateway.
  # One NAT instead of one per AZ: cheaper, acceptable for dev, NOT for production.
  enable_nat_gateway = var.eks_enabled
  single_nat_gateway = true

  # Tags that tell Kubernetes which subnets to use for load balancers.
  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}
