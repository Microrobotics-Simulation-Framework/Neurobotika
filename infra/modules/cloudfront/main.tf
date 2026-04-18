variable "project_name" {
  type = string
}

variable "web_bucket_id" {
  type = string
}

variable "web_bucket_arn" {
  type = string
}

variable "web_bucket_domain" {
  type = string
}

variable "domain_name" {
  type    = string
  default = ""
}

# Origin Access Identity for secure S3 access
resource "aws_cloudfront_origin_access_identity" "this" {
  comment = "${var.project_name} web origin access"
}

# Grant CloudFront access to the web bucket
resource "aws_s3_bucket_policy" "cloudfront_access" {
  bucket = var.web_bucket_id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudFrontReadAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.this.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${var.web_bucket_arn}/*"
      }
    ]
  })
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${var.project_name} web distribution"
  price_class         = "PriceClass_100" # US + Europe (cheapest)

  origin {
    domain_name = var.web_bucket_domain
    origin_id   = "S3-${var.web_bucket_id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.this.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${var.web_bucket_id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # Long cache for Unity build assets (content-hashed)
  ordered_cache_behavior {
    path_pattern     = "unity/Build/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${var.web_bucket_id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 86400
    default_ttl            = 604800
    max_ttl                = 31536000
    compress               = true
  }

  # Custom error: SPA fallback
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.domain_name == "" ? true : false
  }
}

output "distribution_url" {
  value = "https://${aws_cloudfront_distribution.this.domain_name}"
}

output "distribution_id" {
  value = aws_cloudfront_distribution.this.id
}
