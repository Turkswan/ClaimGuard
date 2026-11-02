# ---------------------------------------------------------------------------
# Pod Identity: Kubernetes service accounts -> IAM roles. No access keys anywhere.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "pod_identity_trust" {
  statement {
    actions = ["sts:AssumeRole", "sts:TagSession"]
    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
  }
}

# EBS CSI driver: creates and attaches disks for PersistentVolumeClaims.
resource "aws_iam_role" "ebs_csi" {
  name               = "${local.name}-ebs-csi"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

# MLflow server: read/write model artefacts under s3://<bucket>/mlflow/
resource "aws_iam_role" "mlflow" {
  name               = "${local.name}-mlflow"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
}

data "aws_iam_policy_document" "mlflow" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
  }
  statement {
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.data.arn}/mlflow/*"]
  }
}

resource "aws_iam_role_policy" "mlflow" {
  role   = aws_iam_role.mlflow.id
  policy = data.aws_iam_policy_document.mlflow.json
}

# ML jobs (training, drift): read data, write drift reports.
resource "aws_iam_role" "ml_jobs" {
  name               = "${local.name}-ml-jobs"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
}

data "aws_iam_policy_document" "ml_jobs" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
  }
  statement {
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.data.arn}/data/*",
      "${aws_s3_bucket.data.arn}/incoming/*",
    ]
  }
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.data.arn}/reports/*"]
  }
}

resource "aws_iam_role_policy" "ml_jobs" {
  role   = aws_iam_role.ml_jobs.id
  policy = data.aws_iam_policy_document.ml_jobs.json
}

resource "aws_eks_pod_identity_association" "mlflow" {
  count           = var.eks_enabled ? 1 : 0
  cluster_name    = module.eks.cluster_name
  namespace       = "mlops"
  service_account = "mlflow"
  role_arn        = aws_iam_role.mlflow.arn
}

resource "aws_eks_pod_identity_association" "ml_jobs" {
  count           = var.eks_enabled ? 1 : 0
  cluster_name    = module.eks.cluster_name
  namespace       = "mlops"
  service_account = "ml-jobs"
  role_arn        = aws_iam_role.ml_jobs.arn
}
