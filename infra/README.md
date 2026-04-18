# Infrastructure -- AWS (Terraform)

Terraform configuration for the Neurobotika project on AWS. Covers both the web viewer hosting (S3 + CloudFront) and the optional cloud pipeline compute (Batch, ECR, Step Functions).

## Quick Start

```bash
cd infra

# 1. Create your .env from the template
cp .env.example .env

# 2. Edit .env with your AWS account details
#    At minimum, set: AWS_PROFILE, AWS_REGION, PROJECT_NAME, AWS_ACCOUNT_ID

# 3. Check service quotas (must pass before enabling pipeline)
./check-quotas.sh

# 4. Generate terraform.tfvars from .env
./env-to-tfvars.sh

# 5. Initialize and apply
terraform init
terraform plan
terraform apply
```

All AWS CLI commands use `--profile` from `AWS_PROFILE` in `.env` (default: `neurobotika`).

## Configuration: `.env`

All cloud configuration lives in a single `infra/.env` file. This file is:
- **Not committed to git** (listed in `.gitignore`)
- **Shared** across Terraform, pipeline scripts, and Docker containers
- **Documented** in `.env.example` with comments for every variable

Copy the example and fill in your values:

```bash
cp .env.example .env
```

### How `.env` flows into Terraform

```
.env  -->  ./env-to-tfvars.sh  -->  terraform.tfvars  -->  terraform plan/apply
```

The `env-to-tfvars.sh` script reads `.env` and generates `terraform.tfvars` (also gitignored). Run it whenever you change `.env`.

### How `.env` flows into pipeline scripts

```bash
# Option 1: source it
source infra/.env
python pipeline/02_brain_segmentation/run_synthseg.py \
  --input s3://$DATA_BUCKET/raw/brain.nii.gz

# Option 2: use with Docker
docker run --env-file infra/.env neurobotika-brain ...

# Option 3: use with AWS Batch (environment variables in job definition)
```

## Resources Created

### Always created (web hosting)

| Resource | Purpose |
|----------|---------|
| S3 bucket: `{project}-web` | Static website hosting (HTML, CSS, Unity WebGL) |
| S3 bucket: `{project}-public` | Public asset storage (downloadable mesh files) |
| S3 bucket: `{project}-data` | Private pipeline data (raw MRI, segmentations) |
| CloudFront distribution | CDN for the web bucket with HTTPS |

### Created when `enable_pipeline = true`

| Resource | Purpose |
|----------|---------|
| VPC + subnets | Networking for Batch + EFS |
| S3 VPC gateway endpoint | Free S3 access from Batch (avoids NAT charges) |
| ECR repositories (x5) | Docker images: download, brain, spine, postproc, training |
| Batch compute env (GPU) | g4dn/g5 spot instances for segmentation + training |
| Batch compute env (CPU) | c6i/c7i spot instances for registration + meshing |
| Batch job queue | Shared queue with spot + on-demand fallback |
| Batch job definitions | Per-phase: download-mgh, download-spine, download-lumbosacral, verify-downloads, brain-seg, spine-seg, registration, meshing, training |
| Step Functions state machine | Pipeline orchestration — idempotent resume via per-phase S3 checks; `stop_after_phase` input for early exit |
| SNS topic | Email notifications for Phase 4 callback |
| EFS filesystem (optional) | Shared storage between phases |

### State machine input contract

Every execution is keyed on a `run_id` (caller-supplied). All S3 paths are derived from `project_name + run_id + subject ids`, so no URIs need to be constructed by hand:

```json
{
  "run_id":           "run-2026-04-18-001",
  "brain_subject":    "sub-EXC004",
  "spine_subject":    "sub-douglas",
  "run_training":     false,
  "stop_after_phase": 1
}
```

Rerunning with the same `run_id` resumes where the previous attempt stopped — every phase checks S3 for its expected output first and skips if present. `stop_after_phase` (default 99) aborts cleanly after the specified phase.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_name` | `neurobotika` | Prefix for all resource names |
| `aws_region` | `eu-central-1` | AWS region |
| `domain_name` | `""` | Custom domain (optional) |
| `enable_pipeline` | `false` | Create pipeline compute resources |
| `gpu_instance_types` | `["g4dn.xlarge", "g5.xlarge", "g6.xlarge"]` | GPU instances for Batch |
| `cpu_instance_types` | `["c6i.4xlarge", "c7i.4xlarge", "c6i.2xlarge"]` | CPU instances for Batch |
| `gpu_max_vcpus` | `4` | GPU compute environment vCPU cap. Keep aligned with approved G-family quota. |
| `cpu_max_vcpus` | `32` | CPU compute environment vCPU cap |
| `enable_efs` | `false` | Create EFS filesystem |
| `notification_email` | `""` | Email for Phase 4 notifications |

## Service Quotas

New AWS accounts have restrictive defaults. Before running the pipeline, request quota increases in eu-central-1 via the [Service Quotas console](https://console.aws.amazon.com/servicequotas/):

| Quota | New-account default | Minimum request | Notes |
|-------|---------------------|-----------------|-------|
| G and VT On-Demand instances | 0 vCPUs | **4 vCPUs** | One g4dn.xlarge at a time |
| G and VT Spot instances | 0 vCPUs | **4 vCPUs** | Ask for 8 if you need parallel brain+spine seg |
| Standard On-Demand instances | 5 vCPUs | 16 vCPUs | Currently applied: 32 vCPUs on new accounts |
| Standard Spot instances | 5 vCPUs | 16 vCPUs | Currently applied: 32 vCPUs on new accounts |

Run `./check-quotas.sh` after your initial Terraform apply to verify what's actually granted. AWS has been silently applying higher Standard defaults on newer accounts (often 32, not 5).

See [docs/cloud-pipeline.md](../docs/cloud-pipeline.md) for full details.

## Cost

- **Web hosting only:** ~$2-10/month
- **Pipeline (automated phases, spot):** ~$1 per run
- **Full pipeline with manual + training:** ~$30 per run

See [docs/cloud-pipeline.md](../docs/cloud-pipeline.md) for per-phase breakdown.
