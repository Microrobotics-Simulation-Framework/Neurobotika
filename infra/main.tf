terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- S3 Buckets ---

module "web_bucket" {
  source      = "./modules/s3"
  bucket_name = "${var.project_name}-web"
  is_website  = true
}

module "public_bucket" {
  source      = "./modules/s3"
  bucket_name = "${var.project_name}-public"
  is_website  = false
  public_read = true
}

module "data_bucket" {
  source      = "./modules/s3"
  bucket_name = "${var.project_name}-data"
  is_website  = false
  public_read = false
}

# --- CloudFront ---

module "cdn" {
  source             = "./modules/cloudfront"
  project_name       = var.project_name
  web_bucket_id      = module.web_bucket.bucket_id
  web_bucket_arn     = module.web_bucket.bucket_arn
  web_bucket_domain  = module.web_bucket.bucket_regional_domain_name
  domain_name        = var.domain_name
}
