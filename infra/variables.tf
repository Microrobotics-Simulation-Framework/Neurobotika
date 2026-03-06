variable "project_name" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "neurobotika"
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-1"
}

variable "domain_name" {
  description = "Custom domain name (optional). If empty, CloudFront default URL is used."
  type        = string
  default     = ""
}
