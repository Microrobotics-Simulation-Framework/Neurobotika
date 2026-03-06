#!/usr/bin/env bash
# Train an nnU-Net model on the prepared CSF dataset.
#
# Usage: ./train_nnunet.sh <dataset_name> <configuration> <fold>
#   e.g.: ./train_nnunet.sh Dataset001_CSF 3d_fullres 0
#
# Requires: pip install nnunetv2 torch

set -euo pipefail

DATASET_NAME="${1:-Dataset001_CSF}"
CONFIG="${2:-3d_fullres}"
FOLD="${3:-0}"

# Set nnU-Net paths (adjust to your data directory)
NNUNET_BASE="data/nnunet"
export nnUNet_raw="${NNUNET_BASE}/nnUNet_raw"
export nnUNet_preprocessed="${NNUNET_BASE}/nnUNet_preprocessed"
export nnUNet_results="${NNUNET_BASE}/nnUNet_results"

# Extract dataset ID from name (e.g., Dataset001_CSF -> 1)
DATASET_ID=$(echo "$DATASET_NAME" | grep -oP '\d+' | head -1)

echo "=== nnU-Net Training ==="
echo "Dataset:       ${DATASET_NAME} (ID: ${DATASET_ID})"
echo "Configuration: ${CONFIG}"
echo "Fold:          ${FOLD}"
echo "Raw data:      ${nnUNet_raw}"
echo "Preprocessed:  ${nnUNet_preprocessed}"
echo "Results:       ${nnUNet_results}"
echo ""

# Step 1: Plan and preprocess
echo "--- Step 1: Planning and preprocessing ---"
nnUNetv2_plan_and_preprocess -d "$DATASET_ID" --verify_dataset_integrity

# Step 2: Train
echo ""
echo "--- Step 2: Training ---"
nnUNetv2_train "$DATASET_ID" "$CONFIG" "$FOLD"

echo ""
echo "=== Training Complete ==="
echo "Results in: ${nnUNet_results}/${DATASET_NAME}"
