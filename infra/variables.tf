variable "project_name" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "neurobotika"
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-central-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name (from ~/.aws/credentials)"
  type        = string
  default     = "neurobotika"
}

variable "domain_name" {
  description = "Custom domain name (optional). If empty, CloudFront default URL is used."
  type        = string
  default     = ""
}

# --- Pipeline compute (used by batch/ecr/efs modules when added) ---

variable "enable_pipeline" {
  description = "Set to true to create pipeline compute resources (Batch, ECR, Step Functions, VPC)"
  type        = bool
  default     = false
}

variable "gpu_instance_types" {
  description = "GPU instance types for Batch compute environment"
  type        = list(string)
  default     = ["g4dn.xlarge", "g5.xlarge", "g6.xlarge"]
}

variable "cpu_instance_types" {
  description = "CPU instance types for Batch compute environment"
  type        = list(string)
  default     = ["c6i.4xlarge", "c7i.4xlarge", "c6i.2xlarge"]
}

variable "gpu_max_vcpus" {
  description = "Maximum vCPUs for GPU Batch compute environment. Must be ≤ the approved G-family quota in the target region — exceeding it doesn't break anything (Batch caps at the quota) but is misleading."
  type        = number
  default     = 4
}

variable "cpu_max_vcpus" {
  description = "Maximum vCPUs for CPU Batch compute environment"
  type        = number
  default     = 32
}

variable "enable_efs" {
  description = "Create an EFS filesystem for inter-phase data sharing"
  type        = bool
  default     = false
}

variable "notification_email" {
  description = "Email for Phase 4 manual segmentation notifications (SNS)"
  type        = string
  default     = ""
}
