variable "project_name" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "gpu_instance_types" {
  type    = list(string)
  default = ["g4dn.xlarge", "g5.xlarge", "g6.xlarge"]
}

variable "cpu_instance_types" {
  type    = list(string)
  default = ["c6i.4xlarge", "c7i.4xlarge", "c6i.2xlarge"]
}

variable "gpu_max_vcpus" {
  type    = number
  default = 8
}

variable "cpu_max_vcpus" {
  type    = number
  default = 32
}

variable "ecr_repository_urls" {
  description = "Map of repo name to ECR URL"
  type        = map(string)
}

variable "data_bucket_arn" {
  type = string
}

variable "public_bucket_arn" {
  type = string
}

variable "efs_file_system_id" {
  description = "EFS filesystem ID (empty string to disable)"
  type        = string
  default     = ""
}
