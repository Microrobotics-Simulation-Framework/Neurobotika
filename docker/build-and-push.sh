#!/usr/bin/env bash
# Build and push all Docker images to ECR.
#
# Prerequisites:
#   - AWS CLI configured
#   - ECR repositories created (via terraform apply with enable_pipeline=true)
#   - infra/.env sourced or AWS_ACCOUNT_ID / AWS_REGION set
#
# Usage:
#   source infra/.env
#   ./docker/build-and-push.sh          # build + push all images
#   ./docker/build-and-push.sh brain    # build + push one image
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Auto-source infra/.env so callers don't have to remember `set -a`.
ENV_FILE="${PROJECT_ROOT}/infra/.env"
if [ -z "${AWS_ACCOUNT_ID:-}" ] && [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID in infra/.env or environment}"
: "${AWS_REGION:=eu-central-1}"
: "${AWS_PROFILE:=neurobotika}"
: "${PROJECT_NAME:=neurobotika}"

export AWS_PROFILE AWS_REGION

REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Authenticate Docker to our ECR (for pushing our images) and to the AWS Deep
# Learning Container ECR (for pulling pytorch-training base images). DLC ECR
# account 763104351884 is readable with any valid AWS ECR token.
DLC_REGISTRY="763104351884.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Logging in to ECR: ${REGISTRY} (profile: ${AWS_PROFILE})"
aws ecr get-login-password --region "${AWS_REGION}" --profile "${AWS_PROFILE}" | \
  docker login --username AWS --password-stdin "${REGISTRY}"

echo "Logging in to AWS DLC ECR: ${DLC_REGISTRY}"
aws ecr get-login-password --region "${AWS_REGION}" --profile "${AWS_PROFILE}" | \
  docker login --username AWS --password-stdin "${DLC_REGISTRY}"

IMAGES=("download" "brain" "spine" "postproc" "training")

# If a specific image is requested, build only that one
if [ $# -gt 0 ]; then
  IMAGES=("$@")
fi

for img in "${IMAGES[@]}"; do
  DOCKERFILE="${SCRIPT_DIR}/${img}.Dockerfile"
  REPO="${REGISTRY}/${PROJECT_NAME}-${img}"
  TAG="latest"

  if [ ! -f "$DOCKERFILE" ]; then
    echo "ERROR: ${DOCKERFILE} not found, skipping"
    continue
  fi

  echo ""
  echo "=== Building ${PROJECT_NAME}-${img} ==="
  docker build \
    -f "$DOCKERFILE" \
    -t "${REPO}:${TAG}" \
    "$PROJECT_ROOT"

  echo "=== Pushing ${REPO}:${TAG} ==="
  docker push "${REPO}:${TAG}"

  echo "=== Done: ${img} ==="
done

echo ""
echo "All images built and pushed."
