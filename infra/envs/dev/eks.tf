# The Kubernetes cluster. Only created when eks_enabled = true.
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  create             = var.eks_enabled
  name               = local.name
  kubernetes_version = var.kubernetes_version

  # API reachable from your laptop and GitHub Actions; authentication still required.
  endpoint_public_access = true

  # Whoever runs `terraform apply` (you) becomes cluster admin.
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Managed add-ons: AWS keeps these core components patched.
  addons = {
    vpc-cni                = { before_compute = true } # pod networking; must exist before nodes join
    eks-pod-identity-agent = { before_compute = true } # lets pods assume IAM roles
    kube-proxy             = {}
    coredns                = {}
    aws-ebs-csi-driver = { # lets pods use EBS disks (PersistentVolumes)
      pod_identity_association = [{
        role_arn        = aws_iam_role.ebs_csi.arn
        service_account = "ebs-csi-controller-sa"
      }]
    }
  }

  eks_managed_node_groups = {
    general = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = [var.node_instance_type]
      min_size       = 2
      max_size       = 3
      desired_size   = 2
    }
  }

  # GitHub Actions may deploy, but only into our two app namespaces (least privilege).
  access_entries = {
    github_actions = {
      principal_arn = aws_iam_role.github_actions.arn
      policy_associations = {
        apps = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"
          access_scope = { type = "namespace", namespaces = ["claimguard", "mlops"] }
        }
      }
    }
  }
}
