# CodeBuild project that builds Docker images in a managed environment and
# pushes them to ECR. Offloads the build from the developer's laptop —
# essential when a base image is larger than the local disk can hold
# (e.g. freesurfer/freesurfer:7.4.1 ≈ 9.8 GB compressed).
#
# The caller zips the relevant source subtree (Dockerfile + pipeline code),
# uploads it to the data bucket under a well-known key, then starts a build
# with the IMAGE_NAME env var overridden. CodeBuild authenticates to our
# ECR, builds, and pushes.

variable "project_name" {
  type = string
}

variable "data_bucket_arn" {
  description = "ARN of the bucket where source zips are uploaded."
  type        = string
}

variable "data_bucket_name" {
  type = string
}

variable "aws_region" {
  type = string
}

# --- IAM role for CodeBuild ---

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codebuild" {
  name               = "${var.project_name}-codebuild"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "policy" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }

  # ECR push/pull. PutImage is the write permission we need on top of
  # the read-only permissions that ecs-instance has in the Batch module.
  statement {
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = ["*"]
  }

  # Read the source zip the developer uploads.
  statement {
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:ListBucket",
    ]
    resources = [
      var.data_bucket_arn,
      "${var.data_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "codebuild" {
  name   = "codebuild-inline"
  role   = aws_iam_role.codebuild.id
  policy = data.aws_iam_policy_document.policy.json
}

# --- Project ---

resource "aws_codebuild_project" "image_build" {
  name          = "${var.project_name}-image-build"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 60 # minutes

  source {
    type                = "S3"
    location            = "${var.data_bucket_name}/build/src.zip"
    buildspec           = "buildspec.yml"
    insecure_ssl        = false
    report_build_status = false
  }

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    # LARGE = 8 vCPU, 15 GiB RAM, 128 GiB disk — plenty for the
    # freesurfer/freesurfer:7.4.1 pull (9.8 GB compressed, ~20 GB extracted).
    compute_type                = "BUILD_GENERAL1_LARGE"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true # required for docker inside CodeBuild

    environment_variable {
      name  = "AWS_REGION"
      value = var.aws_region
    }
  }

  logs_config {
    cloudwatch_logs {
      status     = "ENABLED"
      group_name = "/aws/codebuild/${var.project_name}"
    }
  }
}

# --- Outputs ---

output "project_name" {
  value = aws_codebuild_project.image_build.name
}

output "project_arn" {
  value = aws_codebuild_project.image_build.arn
}
