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
