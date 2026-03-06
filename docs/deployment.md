# Deployment Guide

The web viewer is hosted on AWS using S3 for storage and CloudFront for CDN delivery. Infrastructure is managed with Terraform.

## Architecture

```
User Browser
    │
    ▼
CloudFront Distribution (CDN, HTTPS, caching)
    │
    ├── Origin: S3 "neurobotika-web" bucket
    │   ├── index.html (landing page)
    │   ├── css/style.css
    │   └── unity/ (WebGL build files)
    │
    └── Origin: S3 "neurobotika-public" bucket
        └── meshes/ (downloadable mesh files)
```

## S3 Buckets

### neurobotika-web
- **Purpose:** Static website hosting (HTML, CSS, JS, Unity WebGL build)
- **Access:** Public read via CloudFront (not directly public)
- **CORS:** Configured for Unity WebGL loading

### neurobotika-public
- **Purpose:** Public asset hosting (final mesh files for download)
- **Access:** Public read

### neurobotika-data
- **Purpose:** Pipeline data storage (raw datasets, intermediate files)
- **Access:** Private (IAM-authenticated pipeline access only)
- **Lifecycle:** Consider S3 Intelligent-Tiering for infrequently accessed raw data

## Prerequisites

1. AWS account with appropriate IAM permissions
2. Terraform 1.5+ installed
3. AWS CLI configured (`aws configure`)
4. A domain name (optional — CloudFront provides a `*.cloudfront.net` URL)

## Deploying

```bash
cd infra

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var="project_name=neurobotika"

# Apply
terraform apply -var="project_name=neurobotika"

# Upload the web content
aws s3 sync ../web/ s3://neurobotika-web/ --delete
aws s3 sync ../unity/WebGLBuild/ s3://neurobotika-web/unity/ --delete

# Upload public mesh assets
aws s3 sync ../data/meshes/final/ s3://neurobotika-public/meshes/
```

## CloudFront Configuration

The Terraform config sets up:
- HTTPS with a managed ACM certificate (or CloudFront default cert)
- Brotli/gzip compression (important for Unity .br files)
- Cache behaviors:
  - `/unity/Build/*` — long cache TTL (files are content-hashed)
  - `/*.html` — short cache TTL (allows quick updates)
  - `/meshes/*` — long cache TTL
- Custom error page: redirect 404 to index.html (for SPA-like behavior)

### Content-Type Headers for Unity WebGL

Unity WebGL with Brotli compression requires specific Content-Type and Content-Encoding headers. The S3 upload script must set:

| File Pattern | Content-Type | Content-Encoding |
|-------------|-------------|-----------------|
| `*.data.br` | `application/octet-stream` | `br` |
| `*.wasm.br` | `application/wasm` | `br` |
| `*.js.br` | `application/javascript` | `br` |
| `*.framework.js.br` | `application/javascript` | `br` |

These are handled by `scripts/deploy_web.sh` (to be created).

## Cost Estimate

For a low-traffic informational site:
- S3: ~$0.50/month (a few GB of storage)
- CloudFront: ~$1-5/month (depends on traffic)
- Data transfer: first 1 TB/month is $0.085/GB

Total: roughly $2-10/month for a personal project.

## Teardown

```bash
cd infra
terraform destroy -var="project_name=neurobotika"
```

This removes all AWS resources. Make sure to back up any data in S3 first.
