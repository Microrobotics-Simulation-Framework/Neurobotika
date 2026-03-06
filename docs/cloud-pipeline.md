# Running the Pipeline on AWS

This document covers how to run the entire Neurobotika pipeline on AWS in the **eu-central-1 (Frankfurt)** region, including service recommendations, instance types, service quotas, architecture, and cost estimates.

All on-demand prices are sourced from the [AWS EC2 bulk pricing API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-central-1/index.json) for eu-central-1. Spot prices are from [Vantage](https://instances.vantage.sh/) and fluctuate continuously.

## Why Run on AWS?

Running locally requires a GPU workstation, ~100 GB disk, and hours of compute time. Running on AWS offers:

- **No local hardware requirements** -- GPU instances on demand
- **Fast data downloads** -- AWS has multi-Gbps networking; c6gn instances offer 25 Gbps sustained
- **Persistent storage** -- Intermediate results survive instance termination
- **Spot instances** -- significant cost savings (varies by instance type in Frankfurt)
- **Reproducibility** -- Containerized environments, identical every run
- **Phase 4 (manual segmentation)** -- EC2 with NICE DCV provides a remote 3D Slicer desktop

## Service Quotas (Read This First)

New AWS accounts have **restrictive default vCPU quotas**. You must request increases before launching pipeline compute.

### Default Quotas (New Account)

| Quota Name | Instance Families | Default vCPUs | Impact |
|-----------|-------------------|---------------|--------|
| Running On-Demand G and VT instances | g4dn, g5, g6 | **0** | Cannot launch ANY GPU instance |
| All G and VT Spot Instance Requests | g4dn, g5, g6 | **0** | Cannot launch ANY GPU spot |
| Running On-Demand Standard instances | A, C, D, H, I, M, R, T, Z | **5** | Can only run t3.xlarge or smaller |
| All Standard Spot Instance Requests | A, C, D, H, I, M, R, T, Z | **5** | Cannot run c6i.2xlarge (8 vCPU) |
| Running On-Demand P instances | p3, p4, p5 | **0** | Cannot launch V100/A100 instances |

### Recommended Quota Increases

Request these via the [Service Quotas console](https://console.aws.amazon.com/servicequotas/) in eu-central-1. Small increases (marked "auto") are typically approved automatically within minutes. Larger ones may take hours and require a brief justification.

| Quota | Request Value | Why | Approval |
|-------|-------------|-----|----------|
| G and VT On-Demand | **4 vCPUs** | 1x g4dn.xlarge for Phase 4 (3D Slicer) | Auto |
| G and VT Spot | **8 vCPUs** | 1-2 GPU spot instances for Phases 2, 3 | Auto |
| Standard On-Demand | **16 vCPUs** | 1x c6i.4xlarge or c6gn.4xlarge | Auto |
| Standard Spot | **32 vCPUs** | Concurrent CPU jobs (Phase 5 + 6) | Auto |

**For Phase 7 (nnU-Net training):** Request G and VT Spot to **16 vCPUs** (for g5.2xlarge with 8 vCPUs). This may require justification -- mention ML model training for medical imaging research.

**Tip:** AWS automatically increases quotas based on sustained usage. Start with minimal requests, run a few jobs, then request more later if needed.

## Architecture Overview

```
                      +--------------------------+
                      |   AWS Step Functions     |
                      |   (orchestration)        |
                      +------------+-------------+
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
   +--------------+      +--------------+      +-------------------+
   |  AWS Batch   |      |  AWS Batch   |      |  EC2 + NICE DCV   |
   |  (GPU jobs)  |      |  (CPU jobs)  |      |  (3D Slicer GUI)  |
   |              |      |              |      |                   |
   |  Phases 2,3  |      |  Phases 1,5  |      |  Phase 4          |
   |  Phase 7     |      |  Phase 6     |      |  (manual)         |
   +------+-------+      +------+-------+      +--------+----------+
          |                      |                       |
          +----------------------+-----------------------+
                                 |
                                 v
                      +--------------------+
                      |   S3 + EFS         |
                      |   (shared storage) |
                      +--------------------+
```

## Per-Phase Service Recommendations

### Phase 1: Data Acquisition

| Aspect | Recommendation |
|--------|---------------|
| **Service** | AWS Batch (EC2) |
| **Instance** | c6gn.4xlarge (16 vCPU, 32 GB, Graviton2 ARM, **25 Gbps sustained**) |
| **Why** | Highest sustained network bandwidth at this price point; downloads from OpenNeuro/Zenodo benefit from parallel streams |
| **Storage** | Download directly to S3 using `aws s3 cp` or stream through instance |
| **Time** | 1-4 hours depending on dataset sizes and source bandwidth |
| **Cost (on-demand)** | $0.789/hr x 2-4 hrs = **$1.58-$3.16** |
| **Cost (spot)** | ~$0.30/hr x 2-4 hrs = **$0.60-$1.20** |
| **Quota needed** | Standard Spot: 16 vCPUs |

**Alternative:** c6i.xlarge ($0.194/hr on-demand) for lighter downloads. Only 4 vCPUs and "up to 12.5 Gbps" (burstable), but fits in the default 5 vCPU quota.

**Network bandwidth comparison:**

| Instance | vCPU | Network | On-Demand/hr | Spot/hr | Quota Category |
|----------|------|---------|-------------|---------|---------------|
| c6i.xlarge | 4 | up to 12.5 Gbps | $0.194 | ~$0.05 | Standard (5 default) |
| c6gn.xlarge | 4 | up to 25 Gbps | $0.197 | $0.073 | Standard (5 default) |
| c6gn.4xlarge | 16 | **25 Gbps sustained** | $0.789 | ~$0.30 | Standard (need 16) |
| c6gn.8xlarge | 32 | **50 Gbps sustained** | $1.578 | ~$0.60 | Standard (need 32) |

**Note:** External download speed is limited by the source (OpenNeuro, Zenodo), not AWS. The 25 Gbps bandwidth helps when downloading multiple datasets in parallel or when the source supports high-speed transfers. For a single dataset download, c6gn.xlarge is sufficient and fits in the default quota.

### Phase 2: Brain Segmentation (SynthSeg)

| Aspect | Recommendation |
|--------|---------------|
| **Service** | AWS Batch with GPU compute environment |
| **Instance** | g4dn.xlarge (1x T4 16GB, 4 vCPU, 16 GB RAM) |
| **Container** | Custom Docker image with SynthSeg + PyTorch/TensorFlow |
| **Storage** | Copy from/to S3 at job start/end |
| **Time** | ~30 min GPU, ~2 hrs CPU fallback |
| **Cost (on-demand)** | $0.658/hr x 0.5 hr = **$0.33** |
| **Cost (spot)** | $0.184/hr x 0.5 hr = **$0.09** |
| **Quota needed** | G and VT Spot: 4 vCPUs |

**Why g4dn over g5 in Frankfurt:** The g5.xlarge spot price in eu-central-1 is ~$0.96/hr (only 24% off the $1.258 on-demand), while g4dn.xlarge spot is $0.184/hr (72% off). This makes g4dn **5x cheaper** per hour on spot. SynthSeg fits comfortably in 16 GB VRAM.

**GPU instance comparison (eu-central-1):**

| Instance | GPU | VRAM | On-Demand/hr | Spot/hr | Spot Savings |
|----------|-----|------|-------------|---------|-------------|
| g4dn.xlarge | T4 | 16 GB | $0.658 | $0.184 | 72% |
| g5.xlarge | A10G | 24 GB | $1.258 | $0.961 | 24% |
| g6.xlarge | L4 | 24 GB | $1.006 | ~$0.40 | ~60% |

**Recommendation:** Use g4dn.xlarge spot for inference (Phases 2, 3). The spot discount in Frankfurt is exceptional. Only use g5 if you need >16 GB VRAM.

### Phase 3: Spine Segmentation (TotalSpineSeg + SCT)

| Aspect | Recommendation |
|--------|---------------|
| **Service** | AWS Batch with GPU compute environment |
| **Instance** | g4dn.xlarge (same as Phase 2, reuse compute environment) |
| **Container** | Custom Docker image with TotalSpineSeg + nnU-Net + SCT |
| **Time** | ~20 min GPU |
| **Cost (on-demand)** | $0.658/hr x 0.33 hr = **$0.22** |
| **Cost (spot)** | $0.184/hr x 0.33 hr = **$0.06** |
| **Quota needed** | G and VT Spot: 4 vCPUs (shared with Phase 2) |

**Note:** Phases 2 and 3 can run in parallel on separate instances since they process different datasets. Running both in parallel requires G and VT Spot quota of 8 vCPUs.

### Phase 4: Manual Refinement (3D Slicer)

| Aspect | Recommendation |
|--------|---------------|
| **Service** | EC2 with NICE DCV (free remote desktop for EC2) |
| **Instance** | g4dn.xlarge (1x T4 16GB) |
| **Software** | 3D Slicer 5.4+ pre-installed in custom AMI |
| **Storage** | EFS mount for reading segmentations, writing refined labels |
| **Time** | Days to weeks (interactive human work) |
| **Cost** | $0.658/hr (on-demand, stop when not in use) |
| **Quota needed** | G and VT On-Demand: 4 vCPUs |

**Three options compared (eu-central-1):**

| Option | Hourly Cost | Monthly Base | Best For |
|--------|------------|-------------|----------|
| EC2 + NICE DCV | $0.658/hr | $0 | Single user, cheapest |
| AppStream 2.0 | ~$0.90/hr | $4.19/user | Team use, browser access |
| WorkSpaces | ~$2.00/hr | ~$30/month | Persistent desktop (expensive) |

**Recommendation:** Use EC2 + NICE DCV. Create a custom AMI with 3D Slicer pre-installed. Start/stop the instance between sessions to avoid charges.

**Cost for 40 hrs of manual work:** $0.658 x 40 = **$26.32**

### Phase 5: Registration (ANTs)

| Aspect | Recommendation |
|--------|---------------|
| **Service** | AWS Batch (CPU compute environment) |
| **Instance** | c6i.4xlarge (16 vCPU, 32 GB RAM) or c7i.4xlarge |
| **Why CPU** | ANTs is CPU-bound, heavily multi-threaded; benefits from many cores |
| **Container** | Custom Docker image with ANTsPy, set `ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=16` |
| **Time** | 1-2 hours |
| **Cost (on-demand)** | c6i.4xlarge: $0.776/hr x 1.5 hr = **$1.16** |
| **Cost (spot)** | c6i.4xlarge: $0.309/hr x 1.5 hr = **$0.46** |
| **Quota needed** | Standard Spot: 16 vCPUs |

**Instance comparison for ANTs (eu-central-1):**

| Instance | vCPU | RAM | On-Demand/hr | Spot/hr | Spot Savings |
|----------|------|-----|-------------|---------|-------------|
| c6i.4xlarge (Intel Ice Lake) | 16 | 32 GB | $0.776 | $0.309 | 60% |
| c7i.4xlarge (Intel Sapphire Rapids) | 16 | 32 GB | $0.815 | $0.308 | 62% |
| c7a.4xlarge (AMD EPYC Genoa) | 16 | 32 GB | $0.937 | $0.732 | 22% |
| c7a.8xlarge (AMD EPYC Genoa) | 32 | 64 GB | $1.874 | $1.108 | 41% |

**Key finding:** In eu-central-1, c7a (AMD) instances have poor spot discounts (22-41%) compared to c6i/c7i (60-62%). Use **c6i.4xlarge** or **c7i.4xlarge** spot for the best value. ANTs registration scales well up to 16 threads; doubling to 32 vCPUs gives diminishing returns.

### Phase 6: Mesh Generation

| Aspect | Recommendation |
|--------|---------------|
| **Service** | AWS Batch (CPU compute environment) |
| **Instance** | c6i.2xlarge (8 vCPU, 16 GB RAM) |
| **Container** | Docker image with trimesh, pymeshlab, scikit-image |
| **Time** | ~30 min |
| **Cost (on-demand)** | $0.388/hr x 0.5 hr = **$0.19** |
| **Cost (spot)** | $0.155/hr x 0.5 hr = **$0.08** |
| **Quota needed** | Standard Spot: 8 vCPUs |

### Phase 7: Model Training (nnU-Net, Optional)

| Aspect | Recommendation |
|--------|---------------|
| **Service** | AWS Batch with GPU |
| **Instance** | g5.2xlarge (1x A10G 24GB, 8 vCPU, 32 GB RAM) |
| **Alternative** | g4dn.xlarge for smaller datasets (16 GB VRAM) |
| **Time** | 6-24 hours depending on dataset size and folds |
| **Cost (on-demand)** | g5.2xlarge: $1.516/hr x 12 hr = **$18.19** |
| **Cost (spot)** | g5.2xlarge: $1.020/hr x 12 hr = **$12.24** |
| **Quota needed** | G and VT Spot: 8 vCPUs (need quota increase request) |

**Note:** g5 spot discounts are poor in Frankfurt (~33% off). For training, consider g4dn.xlarge spot ($0.184/hr) if the model fits in 16 GB VRAM, bringing the cost to $0.184 x 12 = **$2.21**.

**SageMaker alternative:** SageMaker Training Jobs handle instance lifecycle automatically and integrate with S3, but add ~20-25% cost overhead (SageMaker ml.g5.2xlarge is more expensive than raw EC2). Use SageMaker only if you need managed experiment tracking or hyperparameter tuning.

## Storage

### S3 (Primary Storage)

S3 pricing in eu-central-1 is ~7% higher than us-east-1.

| Use Case | Tier | Cost (eu-central-1) |
|----------|------|------|
| Raw MRI data (infrequent access after download) | S3 Intelligent-Tiering | ~$0.0245/GB/month (frequent) -> ~$0.014/GB (infrequent) |
| Intermediate segmentations (active pipeline use) | S3 Standard | ~$0.0245/GB/month |
| Final meshes (public) | S3 Standard | ~$0.0245/GB/month |

**Estimated storage costs:**
- 50 GB raw data (200um volume): $1.23/month
- 10 GB segmentations: $0.25/month
- 1 GB meshes: $0.02/month
- **Total storage: ~$1.50/month**

With Intelligent-Tiering for raw data after pipeline completion: **~$1.00/month**

### EFS (Shared Filesystem for Compute)

| Use Case | Tier | Cost (eu-central-1) |
|----------|------|------|
| Active pipeline working directory | EFS Standard | ~$0.33/GB/month |
| Archived intermediate files | EFS Infrequent Access | ~$0.018/GB/month |

EFS is mounted by Batch jobs and EC2 instances for direct NIfTI file I/O. Data is synced to/from S3 at pipeline boundaries.

**Estimated EFS costs:** 20 GB active = $6.60/month. Delete after pipeline completion to save costs.

**Alternative:** Use S3 with `aws s3 cp` at the start/end of each Batch job to avoid EFS costs entirely. This is the recommended approach for initial setup.

### ECR (Container Registry)

| Containers | Cost |
|-----------|------|
| 3-4 Docker images (~8-15 GB each with DLC base) | $0.10/GB/month = **~$4-6/month** |

Use ECR lifecycle policies to auto-expire old image tags. Data transfer from ECR to Batch in the same region is **free**.

## Orchestration

### AWS Step Functions (Recommended)

Step Functions orchestrate the pipeline as a state machine:

```json
{
  "StartAt": "Phase1_Download",
  "States": {
    "Phase1_Download": {
      "Type": "Task",
      "Resource": "arn:aws:states:::batch:submitJob.sync",
      "Next": "ParallelSegmentation"
    },
    "ParallelSegmentation": {
      "Type": "Parallel",
      "Branches": [
        { "StartAt": "Phase2_BrainSeg", "States": { "Phase2_BrainSeg": { "Type": "Task", "Resource": "arn:aws:states:::batch:submitJob.sync", "End": true } } },
        { "StartAt": "Phase3_SpineSeg", "States": { "Phase3_SpineSeg": { "Type": "Task", "Resource": "arn:aws:states:::batch:submitJob.sync", "End": true } } }
      ],
      "Next": "Phase4_ManualWait"
    },
    "Phase4_ManualWait": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Comment": "Pauses until manual segmentation is complete and operator sends task token",
      "Next": "Phase5_Registration"
    },
    "Phase5_Registration": {
      "Type": "Task",
      "Resource": "arn:aws:states:::batch:submitJob.sync",
      "Next": "Phase6_Meshing"
    },
    "Phase6_Meshing": {
      "Type": "Task",
      "Resource": "arn:aws:states:::batch:submitJob.sync",
      "Next": "Phase7_Training"
    },
    "Phase7_Training": {
      "Type": "Task",
      "Resource": "arn:aws:states:::batch:submitJob.sync",
      "End": true
    }
  }
}
```

**Cost:** $0.025 per 1,000 state transitions. A full pipeline run uses <20 transitions = **effectively free**.

### AWS Batch (Compute)

AWS Batch manages job queues, instance provisioning, and container execution. No additional charge -- you pay only for the underlying EC2 resources.

**Configuration:**
- **GPU Compute Environment:** g4dn.xlarge spot instances, min 0 / max 4 vCPUs
- **CPU Compute Environment:** c6i + c7i instances spot, min 0 / max 32 vCPUs
- **Job Definitions:** One per pipeline phase, referencing ECR container images

## Cost Summary

### Single Pipeline Run (eu-central-1 Spot Pricing)

| Phase | Instance | Time | Cost (spot) |
|-------|----------|------|------------|
| 1. Data Acquisition | c6gn.xlarge | 2-4 hr | $0.15-$0.29 |
| 2. Brain Segmentation | g4dn.xlarge | 30 min | $0.09 |
| 3. Spine Segmentation | g4dn.xlarge | 20 min | $0.06 |
| 4. Manual Refinement | g4dn.xlarge (OD) | 40 hr | $26.32 |
| 5. Registration | c6i.4xlarge | 1.5 hr | $0.46 |
| 6. Mesh Generation | c6i.2xlarge | 30 min | $0.08 |
| 7. Model Training | g4dn.xlarge | 12 hr | $2.21 |
| **Compute subtotal** | | | **~$29.70** |

| Ongoing | Monthly Cost |
|---------|-------------|
| S3 storage (60 GB) | $1.50 |
| ECR images | $4-6 |
| CloudFront + web hosting | $2-5 |
| **Monthly subtotal (no EFS)** | **~$8-13** |

### Without Phase 4 and 7 (Automated Only)

If manual segmentation is done locally and model training is skipped:

| | Spot Cost |
|---|---------|
| Compute (Phases 1-3, 5-6) | **~$0.85** |
| Monthly storage | **~$8-13** |

### On-Demand vs Spot in eu-central-1

Spot discounts vary wildly by instance family in Frankfurt. g4dn has excellent spot pricing; g5 does not.

| Instance | On-Demand/hr | Spot/hr | Savings |
|----------|-------------|---------|---------|
| g4dn.xlarge (T4) | $0.658 | $0.184 | **72%** |
| g5.xlarge (A10G) | $1.258 | $0.961 | 24% |
| g5.2xlarge (A10G) | $1.516 | $1.020 | 33% |
| c6i.4xlarge | $0.776 | $0.309 | 60% |
| c7i.4xlarge | $0.815 | $0.308 | 62% |
| c7a.4xlarge | $0.937 | $0.732 | 22% |
| c6gn.xlarge | $0.197 | $0.073 | 63% |

**Takeaway:** In Frankfurt, prefer **g4dn** over g5 for GPU and **c6i/c7i** over c7a for CPU when using spot.

## Spot Instance Strategy

### Interruption Handling

Spot instances can be reclaimed with 2 minutes notice. Configure Batch job definitions with retry logic:

```json
{
  "retryStrategy": {
    "attempts": 3,
    "evaluateOnExit": [
      {
        "onStatusReason": "Host EC2*",
        "action": "RETRY"
      },
      {
        "onExitCode": "0",
        "action": "EXIT"
      }
    ]
  }
}
```

### Diversify Instance Types

Specify multiple instance types per compute environment to maximize Spot pool availability:

```
GPU: ["g4dn.xlarge", "g5.xlarge", "g6.xlarge"]
CPU: ["c6i.4xlarge", "c7i.4xlarge", "c6i.8xlarge", "c7i.8xlarge"]
```

Use `SPOT_CAPACITY_OPTIMIZED` allocation strategy (Batch default) -- AWS picks the pool with lowest interruption probability. With diversified pools, interruption rates are typically 5-10%.

### Checkpointing for Long Jobs

- **Phase 5 (ANTs):** Break registration into stages (rigid -> affine -> SyN) as separate Batch jobs. If interrupted, only the current stage restarts.
- **Phase 7 (nnU-Net):** Built-in checkpointing to disk. Mount EFS for checkpoint persistence across Spot interruptions.
- **Phases 2, 3, 6:** Short enough (<30 min) that interruption is rare and retry cost is negligible.

### Fallback to On-Demand

Create two compute environments in the same job queue -- Spot (higher priority) and On-Demand (lower priority). If Spot capacity is unavailable after retries, jobs fall through to on-demand automatically.

## Docker Images

Use [AWS Deep Learning Container Images (DLC)](https://github.com/aws/deep-learning-containers) as base images. These are free, include CUDA/cuDNN/PyTorch pre-installed, and are optimized for EC2 GPU instances.

### 1. `neurobotika-brain` (Phases 1-2)

```dockerfile
# AWS DLC: PyTorch 2.x GPU with CUDA 12.1 (free, pre-optimized)
FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2
RUN pip install synthseg nibabel numpy scipy click
COPY pipeline/01_data_acquisition/ /app/01/
COPY pipeline/02_brain_segmentation/ /app/02/
```

### 2. `neurobotika-spine` (Phase 3)

```dockerfile
FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2
RUN pip install totalspineseg nibabel numpy scipy click
RUN install_sct  # Spinal Cord Toolbox
COPY pipeline/03_spine_segmentation/ /app/03/
```

### 3. `neurobotika-postproc` (Phases 5-6)

```dockerfile
FROM python:3.11-slim
RUN pip install antspyx nibabel trimesh pymeshlab scikit-image numpy scipy click
COPY pipeline/05_registration/ /app/05/
COPY pipeline/06_mesh_generation/ /app/06/
```

### 4. `neurobotika-training` (Phase 7, optional)

```dockerfile
FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2
RUN pip install nnunetv2 nibabel numpy scipy click
COPY pipeline/07_model_training/ /app/07/
```

**Note:** DLC images are ~8-15 GB. Use the **eu-central-1** ECR endpoint to avoid cross-region transfer fees. Use ECR lifecycle policies to auto-expire old tags.

## Services Evaluated but Not Recommended

| Service | Why Not |
|---------|---------|
| **AWS Lambda** | No GPU support, 15-min timeout, 10 GB memory/storage limits. Not viable for any pipeline phase. |
| **FSx for Lustre** | Minimum 1.2 TiB filesystem = ~$168/month. Designed for HPC with hundreds of parallel jobs. Overkill for this pipeline. |
| **AWS ParallelCluster** | Deploys a Slurm-based HPC cluster with an always-on head node (~$50-150/month). Our phases are independent Docker containers, not MPI jobs. Batch is simpler and cheaper. |
| **Amazon WorkSpaces** | ~$30/month base + ~$2/hr for GPU in Frankfurt. Too expensive for sporadic Phase 4 sessions vs EC2 + NICE DCV. |
| **SageMaker (for pipeline)** | 20-25% markup over raw EC2 pricing. Our pipeline is straightforward Batch jobs. Consider only for Phase 7 if you need managed ML features. |
| **g5 Spot (in Frankfurt)** | Only 24% spot discount in eu-central-1 vs 72% for g4dn. Use g4dn for inference; g5 only if you need 24 GB VRAM. |
| **c7a Spot (in Frankfurt)** | Only 22% spot discount in eu-central-1 vs 60% for c6i. Use c6i/c7i for CPU workloads. |

## Terraform Additions

The existing Terraform in `infra/` handles web hosting. For cloud pipeline execution, add:

```
infra/
+-- main.tf                      # existing
+-- modules/
    +-- s3/                      # existing
    +-- cloudfront/              # existing
    +-- batch/                   # NEW: Batch compute environments + job queues
    |   +-- main.tf
    |   +-- variables.tf
    |   +-- outputs.tf
    +-- step-functions/          # NEW: Pipeline state machine
    |   +-- main.tf
    |   +-- variables.tf
    +-- ecr/                     # NEW: Container registries
    |   +-- main.tf
    +-- efs/                     # NEW: Shared filesystem (optional)
    |   +-- main.tf
    +-- vpc/                     # NEW: VPC for Batch + EFS
        +-- main.tf
```

**Key resources to add:**
- `aws_batch_compute_environment` (GPU + CPU, both spot and on-demand)
- `aws_batch_job_queue` (with mixed spot/on-demand compute environments)
- `aws_batch_job_definition` (one per phase)
- `aws_sfn_state_machine`
- `aws_ecr_repository` (one per container image)
- `aws_efs_file_system` + `aws_efs_mount_target` (optional)
- `aws_vpc`, `aws_subnet`, `aws_security_group` (for Batch networking)
- `aws_vpc_endpoint` (S3 gateway endpoint -- free, avoids NAT charges)
- IAM roles for Batch execution, Step Functions, and S3 access

## Network Considerations

- **Region:** eu-central-1 (Frankfurt) for all resources
- **Data transfer within region:** Free between EC2/Batch/EFS/S3
- **External downloads (Phase 1):** Transfer IN to AWS is free. Speed limited by source (OpenNeuro, Zenodo). Use c6gn instances for high-bandwidth parallel downloads.
- **VPC endpoints:** Add an S3 gateway endpoint (free) to avoid NAT gateway charges ($0.052/hr + $0.052/GB in Frankfurt) for S3 access from Batch jobs
- **Cross-region:** Avoid pulling DLC images from us-east-1 ECR; use the eu-central-1 endpoint

## Recommendations

1. **Request service quota increases immediately.** GPU quotas default to 0 vCPUs. Request G and VT Spot: 8 vCPUs and Standard Spot: 32 vCPUs before attempting to run anything. Small requests are auto-approved.

2. **Use g4dn.xlarge Spot** for GPU phases (2, 3, and optionally 7). At $0.184/hr in Frankfurt, it offers 72% spot savings and is 5x cheaper than g5 spot. SynthSeg and TotalSpineSeg fit in 16 GB VRAM.

3. **Use c6i or c7i Spot** for CPU phases (5, 6). They offer 60%+ spot savings in Frankfurt, while c7a only offers 22%. c6i.4xlarge spot at $0.309/hr is the sweet spot for ANTs registration.

4. **Use c6gn instances** for Phase 1 downloads if you need high bandwidth. The c6gn.4xlarge provides 25 Gbps sustained networking. For simple single-dataset downloads, c6gn.xlarge (up to 25 Gbps burst, fits in default quota) is sufficient.

5. **Skip EFS initially.** Use S3 with `aws s3 cp` at the start/end of each Batch job. This is simpler and cheaper. Only add EFS if you need checkpointing for Phase 7.

6. **Phase 4 locally** if possible. Manual segmentation in 3D Slicer on a local workstation avoids the $26+/session EC2 cost. Upload the refined labels to S3 when done.

7. **Use S3 Intelligent-Tiering** for raw data. After the initial pipeline run, raw MRI data is rarely accessed. Intelligent-Tiering automatically moves it to cheaper storage classes.

8. **Use AWS DLC base images** from the eu-central-1 ECR endpoint. They're free, include CUDA/PyTorch pre-installed, and avoid cross-region transfer fees.

9. **Add an S3 VPC gateway endpoint** to avoid NAT gateway charges ($0.052/hr + $0.052/GB in Frankfurt). The gateway endpoint is free.

10. **Delete EFS and stop EC2 instances** when not actively running the pipeline. Storage costs are the main ongoing expense.

## Pricing Sources

On-demand prices are from the [AWS EC2 bulk pricing API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-central-1/index.json) for eu-central-1 (retrieved March 2026). Spot prices are from [Vantage](https://instances.vantage.sh/) and fluctuate continuously. Verify current pricing at:

- EC2 on-demand: https://aws.amazon.com/ec2/pricing/on-demand/
- EC2 Spot: https://aws.amazon.com/ec2/spot/pricing/
- S3: https://aws.amazon.com/s3/pricing/
- EFS: https://aws.amazon.com/efs/pricing/
- Batch: https://aws.amazon.com/batch/pricing/
- Step Functions: https://aws.amazon.com/step-functions/pricing/
- ECR: https://aws.amazon.com/ecr/pricing/
- Service Quotas: https://docs.aws.amazon.com/ec2/latest/instancetypes/ec2-instance-quotas.html
