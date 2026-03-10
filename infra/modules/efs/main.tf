variable "project_name" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

resource "aws_efs_file_system" "this" {
  creation_token = "${var.project_name}-pipeline"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_14_DAYS"
  }

  tags = { Name = "${var.project_name}-pipeline-efs" }
}

resource "aws_security_group_rule" "efs_ingress" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  security_group_id        = var.security_group_id
  source_security_group_id = var.security_group_id
}

resource "aws_efs_mount_target" "this" {
  count           = length(var.subnet_ids)
  file_system_id  = aws_efs_file_system.this.id
  subnet_id       = var.subnet_ids[count.index]
  security_groups = [var.security_group_id]
}

output "file_system_id" {
  value = aws_efs_file_system.this.id
}
