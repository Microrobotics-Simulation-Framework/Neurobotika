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

variable "data_bucket_arn" {
  description = "ARN of the S3 bucket where pipeline artifacts live. Used by the state machine's idempotency checks (s3:HeadObject / ListObjectsV2)."
  type        = string
}

locals {
  data_bucket_name = "${var.project_name}-data"
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

  # S3 read — for the per-phase idempotency checks (HeadObject + ListObjectsV2).
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      var.data_bucket_arn,
      "${var.data_bucket_arn}/*",
    ]
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

  # Input contract:
  #
  #   {
  #     "run_id":           "run-2026-04-20-001",
  #     "brain_subject":    "sub-yv98",           // Lüsebrink 2021 primary subject
  #     "spine_subject":    "sub-douglas",
  #     "run_training":     false,
  #     "stop_after_phase": 1       // optional; omit to run through to the end
  #   }
  #
  # Every S3 path is derived from run_id + project_name + subject ids; the
  # caller never has to construct URIs by hand.
  #
  # Idempotency: before each phase runs, a Check state probes S3 for the
  # expected output. If present, the phase is skipped. A fresh execution
  # with the same run_id therefore resumes where the previous run left off
  # — re-runs after a quota-starved failure cost nothing for the
  # already-completed phases.
  #
  # stop_after_phase: if set to N, the state machine exits cleanly after
  # phase N's gate fires. Useful while downstream phases aren't implemented
  # or while GPU quota is pending. Omitting it runs the full pipeline.

  definition = jsonencode({
    Comment = "Neurobotika CSF pipeline (idempotent + early-stop)"
    StartAt = "Init_CheckStopAfter"
    States = {

      # -----------------------------------------------------------------
      # 0a. Default stop_after_phase to 99 (= "run everything") if the
      # caller omitted it. PrepareContext then uniformly reads $.stop_after_phase.
      # -----------------------------------------------------------------
      Init_CheckStopAfter = {
        Type = "Choice"
        Choices = [{
          Variable  = "$.stop_after_phase"
          IsPresent = true
          Next      = "PrepareContext"
        }]
        Default = "Init_SetDefaultStopAfter"
      }

      Init_SetDefaultStopAfter = {
        Type       = "Pass"
        Result     = 99
        ResultPath = "$.stop_after_phase"
        Next       = "PrepareContext"
      }

      # -----------------------------------------------------------------
      # 0b. Derive every downstream path from (project_name, run_id).
      # Pass stop_after_phase through so the Gate_* states can read it.
      # -----------------------------------------------------------------
      PrepareContext = {
        Type = "Pass"
        Parameters = {
          "brain_subject.$"    = "$.brain_subject"
          "spine_subject.$"    = "$.spine_subject"
          "run_id.$"           = "$.run_id"
          "run_training.$"     = "$.run_training"
          "stop_after_phase.$" = "$.stop_after_phase"
          "s3_root.$"          = "States.Format('s3://${local.data_bucket_name}/runs/{}', $.run_id)"
          "raw_prefix.$"       = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw', $.run_id)"
          "manifest_out.$"     = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw/manifest.json', $.run_id)"
          "lusebrink_dest.$"   = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw/lusebrink_2021', $.run_id)"
          "spine_dest.$"       = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw/spine_generic', $.run_id)"
          "lumbosacral_dest.$" = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw/lumbosacral', $.run_id)"
          # Default brain input: Lüsebrink 2021 bias-corrected T2 SPACE.
          # T2 SPACE's bright-CSF contrast is ideal for both SynthSeg and
          # Phase 4 manual refinement of the subarachnoid space.
          "brain_input.$"         = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw/lusebrink_2021/{}/anat/{}_T2w_biasCorrected.nii.gz', $.run_id, $.brain_subject, $.brain_subject)"
          "brain_output_dir.$"    = "States.Format('s3://${local.data_bucket_name}/runs/{}/seg/brain/{}', $.run_id, $.brain_subject)"
          "spine_input.$"         = "States.Format('s3://${local.data_bucket_name}/runs/{}/raw/spine_generic/{}/{}/anat/{}_T2w.nii.gz', $.run_id, $.spine_subject, $.spine_subject, $.spine_subject)"
          "spine_output_dir.$"    = "States.Format('s3://${local.data_bucket_name}/runs/{}/seg/spine/{}', $.run_id, $.spine_subject)"
          "registration_input.$"  = "States.Format('s3://${local.data_bucket_name}/runs/{}/seg/merged.nii.gz', $.run_id)"
          "registration_output.$" = "States.Format('s3://${local.data_bucket_name}/runs/{}/registered/merged.nii.gz', $.run_id)"
          "meshing_input.$"       = "States.Format('s3://${local.data_bucket_name}/runs/{}/registered/merged.nii.gz', $.run_id)"
          "meshing_output_dir.$"  = "States.Format('s3://${local.data_bucket_name}/runs/{}/meshes', $.run_id)"

          # S3 keys (no s3:// prefix) for HeadObject / ListObjectsV2 calls:
          "manifest_key.$"            = "States.Format('runs/{}/raw/manifest.json', $.run_id)"
          "brain_output_prefix.$"     = "States.Format('runs/{}/seg/brain/{}/', $.run_id, $.brain_subject)"
          "spine_output_prefix.$"     = "States.Format('runs/{}/seg/spine/{}/', $.run_id, $.spine_subject)"
          "registration_output_key.$" = "States.Format('runs/{}/registered/merged.nii.gz', $.run_id)"
          "meshing_output_prefix.$"   = "States.Format('runs/{}/meshes/', $.run_id)"
        }
        ResultPath = "$"
        Next       = "Check_Phase1"
      }

      # -----------------------------------------------------------------
      # Phase 1 — downloads + verify.
      # Skip-marker: raw/manifest.json written by the verify job.
      #
      # Note on Catch: on a first-time run for a run_id the HeadObject
      # returns a 404 (S3.NoSuchKey / S3.NotFound) because nothing is
      # there yet. That isn't a failure — the Catch routes the flow to
      # Phase1_Download, which is the expected behaviour. The execution
      # history will show a TaskFailed event for Check_Phase1 in that
      # case; it's informational, not a real failure. Subsequent runs
      # with the same run_id find the manifest and skip straight to
      # Gate_AfterPhase1.
      # -----------------------------------------------------------------
      Check_Phase1 = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:s3:headObject"
        Parameters = {
          Bucket  = local.data_bucket_name
          "Key.$" = "$.manifest_key"
        }
        ResultPath = "$.phase1_check"
        Next       = "Gate_AfterPhase1"
        Catch = [{
          # Only catch the "object not found" variants. Any other S3
          # error (permissions, throttling, service outage) propagates
          # up as a real failure so it isn't silently swallowed.
          ErrorEquals = ["S3.NoSuchKeyException", "S3.NotFoundException", "S3.404"]
          ResultPath  = "$.phase1_check"
          Next        = "Phase1_Download"
        }]
      }

      Phase1_Download = {
        Type = "Parallel"
        Branches = [
          {
            StartAt = "Download_Lusebrink"
            States = {
              Download_Lusebrink = {
                Type     = "Task"
                Resource = "arn:aws:states:::batch:submitJob.sync"
                Parameters = {
                  JobName       = "phase1-download-lusebrink"
                  JobQueue      = var.cpu_job_queue_arn
                  JobDefinition = lookup(var.job_definition_arns, "download-lusebrink", "")
                  Parameters = {
                    "subject.$" = "$.brain_subject"
                    "s3_dest.$" = "$.lusebrink_dest"
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
            StartAt = "Download_Spine"
            States = {
              Download_Spine = {
                Type     = "Task"
                Resource = "arn:aws:states:::batch:submitJob.sync"
                Parameters = {
                  JobName       = "phase1-download-spine"
                  JobQueue      = var.cpu_job_queue_arn
                  JobDefinition = lookup(var.job_definition_arns, "download-spine", "")
                  Parameters = {
                    "subject.$" = "$.spine_subject"
                    "s3_dest.$" = "$.spine_dest"
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
            StartAt = "Download_Lumbosacral"
            States = {
              Download_Lumbosacral = {
                Type     = "Task"
                Resource = "arn:aws:states:::batch:submitJob.sync"
                Parameters = {
                  JobName       = "phase1-download-lumbosacral"
                  JobQueue      = var.cpu_job_queue_arn
                  JobDefinition = lookup(var.job_definition_arns, "download-lumbosacral", "")
                  Parameters = {
                    "s3_dest.$" = "$.lumbosacral_dest"
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
        ResultPath = "$.phase1_downloads"
        Next       = "Phase1_Verify"
      }

      Phase1_Verify = {
        Type     = "Task"
        Resource = "arn:aws:states:::batch:submitJob.sync"
        Parameters = {
          JobName       = "phase1-verify"
          JobQueue      = var.cpu_job_queue_arn
          JobDefinition = lookup(var.job_definition_arns, "verify-downloads", "")
          Parameters = {
            "s3_prefix.$"    = "$.raw_prefix"
            "manifest_out.$" = "$.manifest_out"
          }
        }
        ResultPath = "$.phase1_verify"
        Next       = "Gate_AfterPhase1"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 30
          MaxAttempts     = 1
          BackoffRate     = 2
        }]
      }

      Gate_AfterPhase1 = {
        Type = "Choice"
        Choices = [{
          And = [
            { Variable = "$.stop_after_phase", IsPresent = true },
            { Variable = "$.stop_after_phase", NumericLessThanEquals = 1 }
          ]
          Next = "Done"
        }]
        Default = "ParallelSegmentation"
      }

      # -----------------------------------------------------------------
      # Phase 2 + Phase 3 — parallel segmentation.
      # Each branch checks its own output before submitting to GPU.
      # MaxAttempts=1 on the GPU tasks so a real failure doesn't burn
      # retry budget while the quota-sharing sibling is still running.
      # -----------------------------------------------------------------
      ParallelSegmentation = {
        Type = "Parallel"
        Branches = [
          {
            StartAt = "Check_Phase2"
            States = {
              Check_Phase2 = {
                Type     = "Task"
                Resource = "arn:aws:states:::aws-sdk:s3:listObjectsV2"
                Parameters = {
                  Bucket     = local.data_bucket_name
                  "Prefix.$" = "$.brain_output_prefix"
                  MaxKeys    = 1
                }
                ResultPath = "$.phase2_check"
                Next       = "Gate_Phase2_Exists"
              }
              Gate_Phase2_Exists = {
                Type = "Choice"
                Choices = [{
                  Variable           = "$.phase2_check.KeyCount"
                  NumericGreaterThan = 0
                  Next               = "Skip_Phase2"
                }]
                Default = "Phase2_BrainSeg"
              }
              Phase2_BrainSeg = {
                Type     = "Task"
                Resource = "arn:aws:states:::batch:submitJob.sync"
                Parameters = {
                  JobName = "phase2-brain-seg"
                  # CPU queue — SynthSeg runs CPU-only (see brain-seg job
                  # def comment in modules/batch/main.tf for why).
                  JobQueue      = var.cpu_job_queue_arn
                  JobDefinition = lookup(var.job_definition_arns, "brain-seg", "")
                  Parameters = {
                    "input.$"      = "$.brain_input"
                    "output_dir.$" = "$.brain_output_dir"
                  }
                }
                End = true
                # No retry: when quota is 4 vCPU and both branches share it,
                # a genuine failure here should surface immediately rather
                # than spin. Re-run the state machine with the same run_id
                # to resume — idempotency will skip what already succeeded.
              }
              Skip_Phase2 = { Type = "Succeed" }
            }
          },
          {
            StartAt = "Check_Phase3"
            States = {
              Check_Phase3 = {
                Type     = "Task"
                Resource = "arn:aws:states:::aws-sdk:s3:listObjectsV2"
                Parameters = {
                  Bucket     = local.data_bucket_name
                  "Prefix.$" = "$.spine_output_prefix"
                  MaxKeys    = 1
                }
                ResultPath = "$.phase3_check"
                Next       = "Gate_Phase3_Exists"
              }
              Gate_Phase3_Exists = {
                Type = "Choice"
                Choices = [{
                  Variable           = "$.phase3_check.KeyCount"
                  NumericGreaterThan = 0
                  Next               = "Skip_Phase3"
                }]
                Default = "Phase3_SpineSeg"
              }
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
              }
              Skip_Phase3 = { Type = "Succeed" }
            }
          }
        ]
        ResultPath = "$.parallel_seg"
        Next       = "Gate_AfterPhase2_3"
      }

      Gate_AfterPhase2_3 = {
        Type = "Choice"
        Choices = [{
          And = [
            { Variable = "$.stop_after_phase", IsPresent = true },
            { Variable = "$.stop_after_phase", NumericLessThanEquals = 3 }
          ]
          Next = "Done"
        }]
        Default = "Check_Phase5"
      }

      # -----------------------------------------------------------------
      # Phase 4 + Phase 5 — we gate them together on phase 5's output:
      # if the registered volume exists, phase 4's manual step was done
      # previously and phase 5 already produced output, so skip both.
      #
      # Same Catch convention as Check_Phase1: the expected first-run
      # 404 is caught and routed to Phase4_Notify. The visible
      # TaskFailed event in the execution history is informational, not
      # a real failure. Any other S3 error propagates.
      # -----------------------------------------------------------------
      Check_Phase5 = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:s3:headObject"
        Parameters = {
          Bucket  = local.data_bucket_name
          "Key.$" = "$.registration_output_key"
        }
        ResultPath = "$.phase5_check"
        Next       = "Gate_AfterPhase5"
        Catch = [{
          ErrorEquals = ["S3.NoSuchKeyException", "S3.NotFoundException", "S3.404"]
          ResultPath  = "$.phase5_check"
          Next        = "Phase4_Notify"
        }]
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
        Next       = "Gate_AfterPhase5"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 60
          MaxAttempts     = 2
          BackoffRate     = 2
        }]
      }

      Gate_AfterPhase5 = {
        Type = "Choice"
        Choices = [{
          And = [
            { Variable = "$.stop_after_phase", IsPresent = true },
            { Variable = "$.stop_after_phase", NumericLessThanEquals = 5 }
          ]
          Next = "Done"
        }]
        Default = "Check_Phase6"
      }

      # -----------------------------------------------------------------
      # Phase 6 — meshing. Output is a directory; use ListObjectsV2.
      # -----------------------------------------------------------------
      Check_Phase6 = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:s3:listObjectsV2"
        Parameters = {
          Bucket     = local.data_bucket_name
          "Prefix.$" = "$.meshing_output_prefix"
          MaxKeys    = 1
        }
        ResultPath = "$.phase6_check"
        Next       = "Gate_Phase6_Exists"
      }

      Gate_Phase6_Exists = {
        Type = "Choice"
        Choices = [{
          Variable           = "$.phase6_check.KeyCount"
          NumericGreaterThan = 0
          Next               = "Gate_AfterPhase6"
        }]
        Default = "Phase6_Meshing"
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
        Next       = "Gate_AfterPhase6"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 60
          MaxAttempts     = 2
          BackoffRate     = 2
        }]
      }

      Gate_AfterPhase6 = {
        Type = "Choice"
        Choices = [{
          And = [
            { Variable = "$.stop_after_phase", IsPresent = true },
            { Variable = "$.stop_after_phase", NumericLessThanEquals = 6 }
          ]
          Next = "Done"
        }]
        Default = "ShouldTrain"
      }

      # -----------------------------------------------------------------
      # Phase 7 — training (optional; no idempotency check because
      # re-running training is almost always the desired behaviour when
      # run_training is set true).
      # -----------------------------------------------------------------
      ShouldTrain = {
        Type = "Choice"
        Choices = [{
          Variable      = "$.run_training"
          BooleanEquals = true
          Next          = "Phase7_Training"
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
