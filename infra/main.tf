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
  region  = var.aws_region
  profile = var.aws_profile
}

# ============================================================
# Web Hosting (always created)
# ============================================================

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

module "cdn" {
  source             = "./modules/cloudfront"
  project_name       = var.project_name
  web_bucket_id      = module.web_bucket.bucket_id
  web_bucket_arn     = module.web_bucket.bucket_arn
  web_bucket_domain  = module.web_bucket.bucket_regional_domain_name
  domain_name        = var.domain_name
}

# ============================================================
# Pipeline Compute (created when enable_pipeline = true)
# ============================================================

module "vpc" {
  source       = "./modules/vpc"
  count        = var.enable_pipeline ? 1 : 0
  project_name = var.project_name
  aws_region   = var.aws_region
}

module "ecr" {
  source       = "./modules/ecr"
  count        = var.enable_pipeline ? 1 : 0
  project_name = var.project_name
}

module "efs" {
  source            = "./modules/efs"
  count             = var.enable_pipeline && var.enable_efs ? 1 : 0
  project_name      = var.project_name
  subnet_ids        = module.vpc[0].subnet_ids
  security_group_id = module.vpc[0].security_group_id
}

module "batch" {
  source              = "./modules/batch"
  count               = var.enable_pipeline ? 1 : 0
  project_name        = var.project_name
  subnet_ids          = module.vpc[0].subnet_ids
  security_group_id   = module.vpc[0].security_group_id
  gpu_instance_types  = var.gpu_instance_types
  cpu_instance_types  = var.cpu_instance_types
  gpu_max_vcpus       = var.gpu_max_vcpus
  cpu_max_vcpus       = var.cpu_max_vcpus
  ecr_repository_urls = module.ecr[0].repository_urls
  data_bucket_arn     = module.data_bucket.bucket_arn
  public_bucket_arn   = module.public_bucket.bucket_arn
  efs_file_system_id  = var.enable_efs ? module.efs[0].file_system_id : ""
}

module "step_functions" {
  source              = "./modules/step-functions"
  count               = var.enable_pipeline ? 1 : 0
  project_name        = var.project_name
  gpu_job_queue_arn   = module.batch[0].gpu_job_queue_arn
  cpu_job_queue_arn   = module.batch[0].cpu_job_queue_arn
  job_definition_arns = module.batch[0].job_definition_arns
  notification_email  = var.notification_email
}
