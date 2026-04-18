# --- IAM: Batch Service Role ---

data "aws_iam_policy_document" "batch_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "batch_service" {
  name               = "${var.project_name}-batch-service"
  assume_role_policy = data.aws_iam_policy_document.batch_assume.json
}

resource "aws_iam_role_policy_attachment" "batch_service" {
  role       = aws_iam_role.batch_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# --- IAM: ECS Instance Role (for EC2-backed Batch) ---

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_instance" {
  name               = "${var.project_name}-ecs-instance"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_instance" {
  role       = aws_iam_role.ecs_instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance" {
  name = "${var.project_name}-ecs-instance"
  role = aws_iam_role.ecs_instance.name
}

# --- IAM: Job Execution Role (container-level) ---

data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "job_execution" {
  name               = "${var.project_name}-batch-job"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

# S3 access for pipeline data
data "aws_iam_policy_document" "job_s3" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:DeleteObject",
    ]
    resources = [
      var.data_bucket_arn,
      "${var.data_bucket_arn}/*",
      var.public_bucket_arn,
      "${var.public_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "job_s3" {
  name   = "s3-pipeline-access"
  role   = aws_iam_role.job_execution.id
  policy = data.aws_iam_policy_document.job_s3.json
}

# ECR pull access
resource "aws_iam_role_policy_attachment" "job_ecr" {
  role       = aws_iam_role.job_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# CloudWatch logs
resource "aws_iam_role_policy_attachment" "job_logs" {
  role       = aws_iam_role.job_execution.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# --- Launch Template: bigger root volume for large container images ---
#
# Default ECS-optimized AMIs ship a 30 GB root volume. The brain image
# (freesurfer/freesurfer:7.4.1 base) is 9.88 GB compressed and expands to
# ~25 GB, leaving no room for the job's working files. 100 GB gives
# headroom for brain + spine + training images without meaningful cost
# (gp3 storage is prorated hourly).

resource "aws_launch_template" "batch_storage" {
  name_prefix = "${var.project_name}-batch-"
  description = "Batch instances with 100 GiB root volume for large images (freesurfer etc.)"

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 100
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted             = true
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name    = "${var.project_name}-batch"
      Project = var.project_name
    }
  }
}

# --- Compute Environment: GPU (Spot) ---

resource "aws_batch_compute_environment" "gpu_spot" {
  compute_environment_name_prefix = "${var.project_name}-gpu-spot-"
  type                            = "MANAGED"
  service_role                    = aws_iam_role.batch_service.arn

  compute_resources {
    type                = "SPOT"
    bid_percentage      = 100
    spot_iam_fleet_role = aws_iam_role.spot_fleet.arn
    allocation_strategy = "SPOT_CAPACITY_OPTIMIZED"

    min_vcpus = 0
    max_vcpus = var.gpu_max_vcpus

    instance_type      = var.gpu_instance_types
    instance_role      = aws_iam_instance_profile.ecs_instance.arn
    subnets            = var.subnet_ids
    security_group_ids = [var.security_group_id]

    launch_template {
      launch_template_id = aws_launch_template.batch_storage.id
      version            = "$Latest"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# --- Compute Environment: GPU (On-Demand fallback) ---

resource "aws_batch_compute_environment" "gpu_ondemand" {
  compute_environment_name_prefix = "${var.project_name}-gpu-ondemand-"
  type                            = "MANAGED"
  service_role                    = aws_iam_role.batch_service.arn

  compute_resources {
    type = "EC2"

    min_vcpus = 0
    max_vcpus = var.gpu_max_vcpus

    instance_type      = var.gpu_instance_types
    instance_role      = aws_iam_instance_profile.ecs_instance.arn
    subnets            = var.subnet_ids
    security_group_ids = [var.security_group_id]

    launch_template {
      launch_template_id = aws_launch_template.batch_storage.id
      version            = "$Latest"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# --- Compute Environment: CPU (Spot) ---

resource "aws_batch_compute_environment" "cpu_spot" {
  compute_environment_name_prefix = "${var.project_name}-cpu-spot-"
  type                            = "MANAGED"
  service_role                    = aws_iam_role.batch_service.arn

  compute_resources {
    type                = "SPOT"
    bid_percentage      = 100
    spot_iam_fleet_role = aws_iam_role.spot_fleet.arn
    allocation_strategy = "SPOT_CAPACITY_OPTIMIZED"

    min_vcpus = 0
    max_vcpus = var.cpu_max_vcpus

    instance_type      = var.cpu_instance_types
    instance_role      = aws_iam_instance_profile.ecs_instance.arn
    subnets            = var.subnet_ids
    security_group_ids = [var.security_group_id]

    launch_template {
      launch_template_id = aws_launch_template.batch_storage.id
      version            = "$Latest"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# --- Compute Environment: CPU (On-Demand fallback) ---

resource "aws_batch_compute_environment" "cpu_ondemand" {
  compute_environment_name_prefix = "${var.project_name}-cpu-ondemand-"
  type                            = "MANAGED"
  service_role                    = aws_iam_role.batch_service.arn

  compute_resources {
    type = "EC2"

    min_vcpus = 0
    max_vcpus = var.cpu_max_vcpus

    instance_type      = var.cpu_instance_types
    instance_role      = aws_iam_instance_profile.ecs_instance.arn
    subnets            = var.subnet_ids
    security_group_ids = [var.security_group_id]

    launch_template {
      launch_template_id = aws_launch_template.batch_storage.id
      version            = "$Latest"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# --- Spot Fleet IAM Role ---

data "aws_iam_policy_document" "spot_fleet_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["spotfleet.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "spot_fleet" {
  name               = "${var.project_name}-spot-fleet"
  assume_role_policy = data.aws_iam_policy_document.spot_fleet_assume.json
}

resource "aws_iam_role_policy_attachment" "spot_fleet" {
  role       = aws_iam_role.spot_fleet.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

# --- Job Queues ---
# Spot environments have higher priority (order 1); on-demand is fallback (order 2).

resource "aws_batch_job_queue" "gpu" {
  name     = "${var.project_name}-gpu"
  state    = "ENABLED"
  priority = 10

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.gpu_spot.arn
  }

  compute_environment_order {
    order               = 2
    compute_environment = aws_batch_compute_environment.gpu_ondemand.arn
  }
}

resource "aws_batch_job_queue" "cpu" {
  name     = "${var.project_name}-cpu"
  state    = "ENABLED"
  priority = 10

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.cpu_spot.arn
  }

  compute_environment_order {
    order               = 2
    compute_environment = aws_batch_compute_environment.cpu_ondemand.arn
  }
}

# --- Log Group ---

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/aws/batch/${var.project_name}"
  retention_in_days = 30
}

# --- Job Definitions ---

locals {
  # Common retry strategy for spot interruptions
  retry_strategy = {
    attempts = 3
    evaluateOnExit = [
      { onStatusReason = "Host EC2*", action = "RETRY" },
      { onExitCode = "0", action = "EXIT" },
    ]
  }

  # EFS volume config (only if EFS is enabled)
  efs_volumes = var.efs_file_system_id != "" ? [
    {
      name = "pipeline-efs"
      efsVolumeConfiguration = {
        fileSystemId  = var.efs_file_system_id
        rootDirectory = "/"
      }
    }
  ] : []

  efs_mount_points = var.efs_file_system_id != "" ? [
    {
      containerPath = "/efs"
      sourceVolume  = "pipeline-efs"
    }
  ] : []

  job_definitions = {
    download-mgh = {
      name      = "${var.project_name}-download-mgh"
      image_key = "download"
      vcpus     = 4
      memory    = 4096
      gpu       = 0
      queue     = "cpu"
      command = [
        "bash", "/app/01/run_downloads.sh",
        "--dataset", "mgh",
        "--subject", "Ref::subject",
        "--s3-dest", "Ref::s3_dest",
      ]
      parameters = {
        subject = "sub-EXC004"
        s3_dest = ""
      }
    }
    download-spine = {
      name      = "${var.project_name}-download-spine"
      image_key = "download"
      vcpus     = 4
      memory    = 4096
      gpu       = 0
      queue     = "cpu"
      command = [
        "bash", "/app/01/run_downloads.sh",
        "--dataset", "spine",
        "--subject", "Ref::subject",
        "--s3-dest", "Ref::s3_dest",
      ]
      parameters = {
        subject = "sub-douglas"
        s3_dest = ""
      }
    }
    download-lumbosacral = {
      name      = "${var.project_name}-download-lumbosacral"
      image_key = "download"
      vcpus     = 4
      memory    = 4096
      gpu       = 0
      queue     = "cpu"
      command = [
        "bash", "/app/01/run_downloads.sh",
        "--dataset", "lumbosacral",
        "--s3-dest", "Ref::s3_dest",
      ]
      parameters = {
        s3_dest = ""
      }
    }
    verify-downloads = {
      name      = "${var.project_name}-verify-downloads"
      image_key = "download"
      vcpus     = 4
      memory    = 4096
      gpu       = 0
      queue     = "cpu"
      command = [
        "python", "/app/01/verify_downloads.py",
        "--s3-prefix", "Ref::s3_prefix",
        "--manifest-out", "Ref::manifest_out",
        "--verbose",
      ]
      parameters = {
        s3_prefix    = ""
        manifest_out = ""
      }
    }
    brain-seg = {
      name      = "${var.project_name}-brain-seg"
      image_key = "brain"
      vcpus     = 4
      # 15000 MB is fine on g5/g6 (16 GB system RAM); SuperSynth's heavy
      # allocations go into GPU VRAM (24 GB on both A10G and L4).
      memory = 15000
      gpu    = 1
      queue  = "gpu"
      # python3 (not python) because the FreeSurfer base only exposes python3.
      command = ["python3", "/app/02/run_brainseg.py", "--input", "Ref::input", "--output-dir", "Ref::output_dir"]
    }
    spine-seg = {
      name      = "${var.project_name}-spine-seg"
      image_key = "spine"
      vcpus     = 4
      memory    = 15000
      gpu       = 1
      queue     = "gpu"
      command   = ["python3", "/app/03/run_totalspineseg.py", "--input", "Ref::input", "--output-dir", "Ref::output_dir"]
    }
    registration = {
      name      = "${var.project_name}-registration"
      image_key = "postproc"
      vcpus     = 16
      memory    = 30000
      gpu       = 0
      queue     = "cpu"
      command   = ["python3", "/app/05/register_brain_to_mni.py", "--input", "Ref::input", "--output", "Ref::output"]
    }
    meshing = {
      name      = "${var.project_name}-meshing"
      image_key = "postproc"
      vcpus     = 8
      memory    = 15000
      gpu       = 0
      queue     = "cpu"
      command   = ["python3", "/app/06/labels_to_surface.py", "--input", "Ref::input", "--output-dir", "Ref::output_dir"]
    }
    training = {
      name      = "${var.project_name}-training"
      image_key = "training"
      vcpus     = 8
      memory    = 30000
      gpu       = 1
      queue     = "gpu"
      command   = ["bash", "/app/07/train_nnunet.sh"]
    }
  }
}

resource "aws_batch_job_definition" "this" {
  for_each = local.job_definitions

  name = each.value.name
  type = "container"

  platform_capabilities = ["EC2"]

  # Default values for Batch parameters referenced as Ref::name in the command.
  # Step Functions overrides these per-execution via the Parameters block.
  parameters = try(each.value.parameters, {})

  retry_strategy {
    attempts = 3

    evaluate_on_exit {
      on_status_reason = "Host EC2*"
      action           = "RETRY"
    }

    evaluate_on_exit {
      on_exit_code = "0"
      action       = "EXIT"
    }
  }

  timeout {
    attempt_duration_seconds = (
      each.key == "training" ? 86400 :
      startswith(each.key, "download-") || each.key == "verify-downloads" ? 1800 :
      7200
    )
  }

  container_properties = jsonencode({
    image   = lookup(var.ecr_repository_urls, each.value.image_key, "placeholder:latest")
    command = each.value.command

    resourceRequirements = concat(
      [
        { type = "VCPU", value = tostring(each.value.vcpus) },
        { type = "MEMORY", value = tostring(each.value.memory) },
      ],
      each.value.gpu > 0 ? [{ type = "GPU", value = tostring(each.value.gpu) }] : []
    )

    jobRoleArn       = aws_iam_role.job_execution.arn
    executionRoleArn = aws_iam_role.job_execution.arn

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.pipeline.name
        "awslogs-stream-prefix" = each.key
      }
    }

    volumes     = local.efs_volumes
    mountPoints = local.efs_mount_points

    environment = [
      { name = "AWS_DEFAULT_REGION", value = "eu-central-1" },
    ]
  })
}

# --- Outputs ---

output "gpu_job_queue_arn" {
  value = aws_batch_job_queue.gpu.arn
}

output "cpu_job_queue_arn" {
  value = aws_batch_job_queue.cpu.arn
}

output "job_definition_arns" {
  value = { for k, v in aws_batch_job_definition.this : k => v.arn }
}

output "job_role_arn" {
  value = aws_iam_role.job_execution.arn
}
