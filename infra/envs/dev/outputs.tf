output "region" {
  value = var.region
}

output "account_id" {
  value = local.account_id
}

output "cluster_name" {
  value = var.eks_enabled ? module.eks.cluster_name : "(eks disabled)"
}

output "data_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "ecr_repositories" {
  value = { for k, r in aws_ecr_repository.images : k => r.repository_url }
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}
