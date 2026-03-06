# Infrastructure — AWS (Terraform)

Terraform configuration for hosting the Neurobotika web viewer on AWS using S3 and CloudFront.

## Resources Created

| Resource | Purpose |
|----------|---------|
| S3 bucket: `{project}-web` | Static website hosting (HTML, CSS, Unity WebGL) |
| S3 bucket: `{project}-public` | Public asset storage (downloadable mesh files) |
| S3 bucket: `{project}-data` | Private pipeline data (raw MRI, segmentations, intermediate files) |
| CloudFront distribution | CDN for the web bucket with HTTPS |
| Origin Access Identity | Secure S3 access from CloudFront |

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5

## Usage

```bash
cd infra

# Initialize
terraform init

# Preview changes
terraform plan -var="project_name=neurobotika"

# Apply
terraform apply -var="project_name=neurobotika"

# Outputs include the CloudFront URL
terraform output

# Destroy all resources
terraform destroy -var="project_name=neurobotika"
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_name` | `neurobotika` | Prefix for all resource names |
| `aws_region` | `eu-west-1` | AWS region |
| `domain_name` | `""` | Custom domain (optional; uses CloudFront URL if empty) |

## Cost

For a low-traffic personal project: ~$2-10/month. See [docs/deployment.md](../docs/deployment.md) for details.
