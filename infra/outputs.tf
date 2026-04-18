output "web_bucket_name" {
  description = "S3 bucket for web content"
  value       = module.web_bucket.bucket_id
}

output "public_bucket_name" {
  description = "S3 bucket for public mesh assets"
  value       = module.public_bucket.bucket_id
}

output "data_bucket_name" {
  description = "S3 bucket for pipeline data (private)"
  value       = module.data_bucket.bucket_id
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = module.cdn.distribution_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = module.cdn.distribution_id
}

# --- Pipeline outputs (only when enable_pipeline = true) ---

output "ecr_repository_urls" {
  description = "ECR repository URLs for Docker images"
  value       = var.enable_pipeline ? module.ecr[0].repository_urls : {}
}

output "gpu_job_queue_arn" {
  description = "AWS Batch GPU job queue ARN"
  value       = var.enable_pipeline ? module.batch[0].gpu_job_queue_arn : ""
}

output "cpu_job_queue_arn" {
  description = "AWS Batch CPU job queue ARN"
  value       = var.enable_pipeline ? module.batch[0].cpu_job_queue_arn : ""
}

output "state_machine_arn" {
  description = "Step Functions pipeline state machine ARN"
  value       = var.enable_pipeline ? module.step_functions[0].state_machine_arn : ""
}

output "codebuild_project_name" {
  description = "CodeBuild project name for building Docker images that are too large for local disk"
  value       = var.enable_pipeline ? module.codebuild[0].project_name : ""
}
