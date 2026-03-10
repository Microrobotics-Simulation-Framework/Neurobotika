#!/usr/bin/env bash
# Generate terraform.tfvars from .env
#
# Usage:
#   cd infra
#   ./env-to-tfvars.sh        # reads .env, writes terraform.tfvars
#   source .env && terraform plan  # alternative: source .env directly
#
set -euo pipefail

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found. Copy .env.example to .env first:" >&2
  echo "  cp .env.example .env" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

cat > terraform.tfvars <<EOF
# Auto-generated from .env — do not edit directly.
# Regenerate with: ./env-to-tfvars.sh

project_name       = "${PROJECT_NAME:-neurobotika}"
aws_region         = "${AWS_REGION:-eu-central-1}"
aws_profile        = "${AWS_PROFILE:-neurobotika}"
domain_name        = "${DOMAIN_NAME:-}"
enable_pipeline    = ${ENABLE_PIPELINE:-false}
gpu_instance_types = $(echo "[\"${GPU_INSTANCE_TYPES:-g4dn.xlarge,g5.xlarge,g6.xlarge}\"]" | sed 's/,/","/g')
cpu_instance_types = $(echo "[\"${CPU_INSTANCE_TYPES:-c6i.4xlarge,c7i.4xlarge,c6i.2xlarge}\"]" | sed 's/,/","/g')
gpu_max_vcpus      = ${GPU_MAX_VCPUS:-8}
cpu_max_vcpus      = ${CPU_MAX_VCPUS:-32}
enable_efs         = ${ENABLE_EFS:-false}
notification_email = "${NOTIFICATION_EMAIL:-}"
EOF

echo "Generated terraform.tfvars from $ENV_FILE"
