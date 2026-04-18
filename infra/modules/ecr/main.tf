variable "project_name" {
  type = string
}

variable "repository_names" {
  type    = list(string)
  default = ["download", "brain", "spine", "postproc", "training"]
}

resource "aws_ecr_repository" "this" {
  for_each             = toset(var.repository_names)
  name                 = "${var.project_name}-${each.value}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = { Name = "${var.project_name}-${each.value}" }
}

# Keep only the 3 most recent images per repo to control storage costs
resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

output "repository_urls" {
  value = { for k, v in aws_ecr_repository.this : k => v.repository_url }
}
