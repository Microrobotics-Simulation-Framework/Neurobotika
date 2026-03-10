variable "project_name" {
  type = string
}

variable "gpu_job_queue_arn" {
  type = string
}

variable "cpu_job_queue_arn" {
  type = string
}

variable "job_definition_arns" {
  description = "Map of job name to ARN"
  type        = map(string)
}

variable "notification_email" {
  type    = string
  default = ""
}

# --- SNS Topic for Phase 4 notifications ---

resource "aws_sns_topic" "manual_notify" {
  name = "${var.project_name}-manual-segmentation"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.manual_notify.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# --- IAM Role for Step Functions ---

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${var.project_name}-step-functions"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

data "aws_iam_policy_document" "sfn_policy" {
  # Submit and manage Batch jobs
  statement {
    actions = [
      "batch:SubmitJob",
      "batch:DescribeJobs",
      "batch:TerminateJob",
    ]
    resources = ["*"]
  }

  # Publish to SNS
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.manual_notify.arn]
  }

  # Describe events (for .sync integrations)
  statement {
    actions = [
      "events:PutTargets",
      "events:PutRule",
      "events:DescribeRule",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  name   = "step-functions-pipeline"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn_policy.json
}

# --- State Machine ---

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project_name}-pipeline"
  role_arn = aws_iam_role.sfn.arn

  definition = jsonencode({
    Comment = "Neurobotika CSF pipeline"
    StartAt = "Phase1_Download"
    States = {
      Phase1_Download = {
        Type     = "Task"
        Resource = "arn:aws:states:::batch:submitJob.sync"
        Parameters = {
          JobName       = "phase1-download"
          JobQueue      = var.cpu_job_queue_arn
          JobDefinition = lookup(var.job_definition_arns, "download", "")
          Parameters = {
            "input.$"  = "$.input_s3_uri"
          }
        }
        ResultPath = "$.phase1"
        Next       = "ParallelSegmentation"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 60
          MaxAttempts     = 2
          BackoffRate     = 2
        }]
      }

      ParallelSegmentation = {
        Type = "Parallel"
        Branches = [
          {
            StartAt = "Phase2_BrainSeg"
            States = {
              Phase2_BrainSeg = {
                Type     = "Task"
                Resource = "arn:aws:states:::batch:submitJob.sync"
                Parameters = {
                  JobName       = "phase2-brain-seg"
                  JobQueue      = var.gpu_job_queue_arn
                  JobDefinition = lookup(var.job_definition_arns, "brain-seg", "")
                  Parameters = {
                    "input.$"  = "$.brain_input"
                    "output.$" = "$.brain_output"
                  }
                }
                End = true
                Retry = [{
                  ErrorEquals     = ["States.TaskFailed"]
                  IntervalSeconds = 60
                  MaxAttempts     = 2
                  BackoffRate     = 2
                }]
              }
            }
          },
          {
            StartAt = "Phase3_SpineSeg"
            States = {
              Phase3_SpineSeg = {
                Type     = "Task"
                Resource = "arn:aws:states:::batch:submitJob.sync"
                Parameters = {
                  JobName       = "phase3-spine-seg"
                  JobQueue      = var.gpu_job_queue_arn
                  JobDefinition = lookup(var.job_definition_arns, "spine-seg", "")
                  Parameters = {
                    "input.$"      = "$.spine_input"
                    "output_dir.$" = "$.spine_output_dir"
                  }
                }
                End = true
                Retry = [{
                  ErrorEquals     = ["States.TaskFailed"]
                  IntervalSeconds = 60
                  MaxAttempts     = 2
                  BackoffRate     = 2
                }]
              }
            }
          }
        ]
        ResultPath = "$.parallel_seg"
        Next       = "Phase4_Notify"
      }

      Phase4_Notify = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish.waitForTaskToken"
        Parameters = {
          TopicArn = aws_sns_topic.manual_notify.arn
          Message = {
            "pipeline_run.$" = "$$.Execution.Name"
            "message"        = "Phases 2-3 complete. Please perform manual segmentation in 3D Slicer, then resume the pipeline."
            "task_token.$"   = "$$.Task.Token"
            "resume_command" = "aws stepfunctions send-task-success --task-token <TOKEN> --task-output '{}'"
          }
        }
        ResultPath = "$.phase4"
        Next       = "Phase5_Registration"
      }

      Phase5_Registration = {
        Type     = "Task"
        Resource = "arn:aws:states:::batch:submitJob.sync"
        Parameters = {
          JobName       = "phase5-registration"
          JobQueue      = var.cpu_job_queue_arn
          JobDefinition = lookup(var.job_definition_arns, "registration", "")
          Parameters = {
            "input.$"  = "$.registration_input"
            "output.$" = "$.registration_output"
          }
        }
        ResultPath = "$.phase5"
        Next       = "Phase6_Meshing"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 60
          MaxAttempts     = 2
          BackoffRate     = 2
        }]
      }

      Phase6_Meshing = {
        Type     = "Task"
        Resource = "arn:aws:states:::batch:submitJob.sync"
        Parameters = {
          JobName       = "phase6-meshing"
          JobQueue      = var.cpu_job_queue_arn
          JobDefinition = lookup(var.job_definition_arns, "meshing", "")
          Parameters = {
            "input.$"      = "$.meshing_input"
            "output_dir.$" = "$.meshing_output_dir"
          }
        }
        ResultPath = "$.phase6"
        Next       = "ShouldTrain"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 60
          MaxAttempts     = 2
          BackoffRate     = 2
        }]
      }

      ShouldTrain = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.run_training"
          BooleanEquals = true
          Next         = "Phase7_Training"
        }]
        Default = "Done"
      }

      Phase7_Training = {
        Type     = "Task"
        Resource = "arn:aws:states:::batch:submitJob.sync"
        Parameters = {
          JobName       = "phase7-training"
          JobQueue      = var.gpu_job_queue_arn
          JobDefinition = lookup(var.job_definition_arns, "training", "")
        }
        ResultPath = "$.phase7"
        Next       = "Done"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 120
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
      }

      Done = {
        Type = "Succeed"
      }
    }
  })
}

# --- Outputs ---

output "state_machine_arn" {
  value = aws_sfn_state_machine.pipeline.arn
}

output "sns_topic_arn" {
  value = aws_sns_topic.manual_notify.arn
}
