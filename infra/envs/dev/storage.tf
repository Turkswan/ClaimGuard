# S3 bucket for training data, MLflow artefacts and drift reports.
resource "aws_s3_bucket" "data" {
  bucket        = "claimguard-data-${local.account_id}"
  force_destroy = true # dev only: lets `terraform destroy` empty the bucket. Never in prod.
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled" # an overwritten training file can always be recovered
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# One private container registry per image.
resource "aws_ecr_repository" "images" {
  for_each = toset(["train", "serve", "mlflow"])

  name                 = "claimguard-${each.key}"
  image_tag_mutability = "IMMUTABLE" # a tag (git SHA) always means the same image
  force_delete         = true        # dev only

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "images" {
  for_each   = aws_ecr_repository.images
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 15 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 15 }
      action       = { type = "expire" }
    }]
  })
}
