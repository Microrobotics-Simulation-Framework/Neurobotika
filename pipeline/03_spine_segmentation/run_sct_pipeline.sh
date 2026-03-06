#!/usr/bin/env bash
# Run Spinal Cord Toolbox (SCT) pipeline for cord segmentation,
# PAM50 registration, and level labelling.
#
# Usage: ./run_sct_pipeline.sh <input_t2w.nii.gz> <output_dir>
#
# Requires: Spinal Cord Toolbox (https://spinalcordtoolbox.com)

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <input_t2w.nii.gz> <output_dir>"
    exit 1
fi

INPUT="$1"
OUTPUT_DIR="$2"

mkdir -p "${OUTPUT_DIR}/sct"

# Check SCT is installed
if ! command -v sct_deepseg_sc &> /dev/null; then
    echo "Spinal Cord Toolbox not found in PATH."
    echo "Install from: https://spinalcordtoolbox.com"
    exit 1
fi

echo "=== SCT Pipeline ==="
echo "Input:  ${INPUT}"
echo "Output: ${OUTPUT_DIR}/sct/"

# Step 1: Segment the spinal cord
echo ""
echo "--- Step 1: Cord segmentation ---"
sct_deepseg_sc -i "$INPUT" -c t2 -o "${OUTPUT_DIR}/sct/cord_seg.nii.gz"

# Step 2: Detect vertebral levels
echo ""
echo "--- Step 2: Vertebral labelling ---"
sct_label_vertebrae -i "$INPUT" -s "${OUTPUT_DIR}/sct/cord_seg.nii.gz" -c t2 \
    -ofolder "${OUTPUT_DIR}/sct/"

# Step 3: Register to PAM50 template
echo ""
echo "--- Step 3: PAM50 registration ---"
sct_register_to_template -i "$INPUT" -s "${OUTPUT_DIR}/sct/cord_seg.nii.gz" \
    -ldisc "${OUTPUT_DIR}/sct/cord_seg_labeled_discs.nii.gz" \
    -c t2 -ofolder "${OUTPUT_DIR}/sct/"

# Step 4: Warp PAM50 template to subject space
echo ""
echo "--- Step 4: Warp template to subject ---"
sct_warp_template -d "$INPUT" \
    -w "${OUTPUT_DIR}/sct/warp_template2anat.nii.gz" \
    -ofolder "${OUTPUT_DIR}/sct/"

# Step 5: Compute cross-sectional area
echo ""
echo "--- Step 5: Cross-sectional area ---"
sct_process_segmentation -i "${OUTPUT_DIR}/sct/cord_seg.nii.gz" \
    -vertfile "${OUTPUT_DIR}/sct/cord_seg_labeled.nii.gz" \
    -o "${OUTPUT_DIR}/sct/csa.csv"

echo ""
echo "=== SCT Pipeline Complete ==="
echo "Outputs in: ${OUTPUT_DIR}/sct/"
