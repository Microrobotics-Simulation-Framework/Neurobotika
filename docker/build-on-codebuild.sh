#!/usr/bin/env bash
# Build a Docker image on AWS CodeBuild and push it to our ECR.
#
# Use this when the image's base is too large for local disk
# (e.g. freesurfer/freesurfer:7.4.1 ≈ 9.8 GB compressed). CodeBuild runs
# on a managed 128 GiB instance with no impact on your workstation.
#
# Usage:
#   ./docker/build-on-codebuild.sh brain
#
# Prereqs: `terraform apply` has deployed the `codebuild` module.

set -euo pipefail

IMAGE="${1:-}"
if [ -z "$IMAGE" ]; then
  echo "Usage: $0 {download|brain|spine|postproc|training}" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
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
: "${DATA_BUCKET:=${PROJECT_NAME}-data}"

export AWS_PROFILE AWS_REGION

CODEBUILD_PROJECT="${PROJECT_NAME}-image-build"
LOG_GROUP="/aws/codebuild/${PROJECT_NAME}"

# --- Stage a minimal source zip for this image ---

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/docker" "$STAGE/pipeline"
cp "$PROJECT_ROOT/docker/${IMAGE}.Dockerfile" "$STAGE/docker/"

case "$IMAGE" in
  brain)    cp -r "$PROJECT_ROOT/pipeline/02_brain_segmentation" "$STAGE/pipeline/" ;;
  spine)    cp -r "$PROJECT_ROOT/pipeline/03_spine_segmentation" "$STAGE/pipeline/" ;;
  postproc) cp -r "$PROJECT_ROOT/pipeline/05_registration"       "$STAGE/pipeline/"
            cp -r "$PROJECT_ROOT/pipeline/06_mesh_generation"    "$STAGE/pipeline/" ;;
  training) cp -r "$PROJECT_ROOT/pipeline/07_model_training"     "$STAGE/pipeline/" ;;
  download) cp -r "$PROJECT_ROOT/pipeline/01_data_acquisition"   "$STAGE/pipeline/" ;;
  *) echo "unknown image: $IMAGE" >&2; exit 1 ;;
esac

find "$STAGE" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# Generic buildspec — IMAGE_NAME supplied via start-build overrides.
cat > "$STAGE/buildspec.yml" <<'BUILDSPEC'
version: 0.2
phases:
  pre_build:
    commands:
      - ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
      - REGISTRY=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
      - REPO=$REGISTRY/neurobotika-$IMAGE_NAME
      - echo "Logging in to $REGISTRY"
      - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY
  build:
    commands:
      - echo "Building $REPO:latest from docker/${IMAGE_NAME}.Dockerfile"
      - docker build -f docker/${IMAGE_NAME}.Dockerfile -t $REPO:latest .
  post_build:
    commands:
      - echo "Pushing $REPO:latest"
      - docker push $REPO:latest
      - echo "Build complete for $IMAGE_NAME"
BUILDSPEC

ZIP="$(dirname "$STAGE")/neurobotika-${IMAGE}-src-$$.zip"
(cd "$STAGE" && zip -qr "$ZIP" .)
SIZE=$(du -h "$ZIP" | cut -f1)
echo "Uploading ${SIZE} zip to s3://${DATA_BUCKET}/build/src.zip"
aws s3 cp "$ZIP" "s3://${DATA_BUCKET}/build/src.zip"
rm -f "$ZIP"

# --- Launch the build ---

echo "Starting CodeBuild project ${CODEBUILD_PROJECT} with IMAGE_NAME=${IMAGE}"
BUILD_ID=$(aws codebuild start-build \
  --project-name "$CODEBUILD_PROJECT" \
  --environment-variables-override "name=IMAGE_NAME,value=${IMAGE},type=PLAINTEXT" \
  --query 'build.id' --output text)

echo "Build ID: ${BUILD_ID}"
echo "Console:  https://${AWS_REGION}.console.aws.amazon.com/codesuite/codebuild/${AWS_ACCOUNT_ID}/projects/${CODEBUILD_PROJECT}/build/${BUILD_ID//:/%3A}"

# --- Poll until terminal; stream a short status line each loop ---

PREV_PHASE=""
while true; do
  read -r PHASE STATUS < <(aws codebuild batch-get-builds --ids "$BUILD_ID" \
    --query 'builds[0].[currentPhase,buildStatus]' --output text)

  if [ "$PHASE" != "$PREV_PHASE" ]; then
    echo "  phase=$PHASE status=$STATUS  $(date -u +%H:%M:%S)"
    PREV_PHASE="$PHASE"
  fi

  case "$STATUS" in
    SUCCEEDED)
      echo "=== SUCCEEDED ==="
      exit 0
      ;;
    FAILED|FAULT|TIMED_OUT|STOPPED)
      echo "=== ${STATUS} ==="
      echo "Latest log tail:"
      aws logs tail "$LOG_GROUP" --format short --since 5m 2>/dev/null | tail -40 || true
      exit 1
      ;;
    IN_PROGRESS)
      sleep 10
      ;;
    *)
      sleep 10
      ;;
  esac
done
