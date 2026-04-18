#!/usr/bin/env bash
# Fetch MGH ex vivo brain MRI at 200 μm (+ a 500 μm quick-test volume) for a
# given subject of OpenNeuro ds002179 and upload the files to S3.
#
# Source: s3://openneuro.org/ds002179/  (public, us-east-1)
# Paper:  Edlow et al., Scientific Data 2019
#
# ds002179 has a single subject today (sub-EXC004). The --subject flag is
# kept so the input contract remains stable when additional subjects are
# published, but will error out if the subject isn't in the dataset.

set -euo pipefail

SUBJECT="sub-EXC004"
S3_DEST=""
WORK_DIR="${WORK_DIR:-/tmp/mgh_download}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --subject)  SUBJECT="$2"; shift 2 ;;
        --s3-dest)  S3_DEST="$2"; shift 2 ;;
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $0 --subject SUB --s3-dest s3://bucket/prefix [--work-dir DIR]

Downloads MGH 200 μm volumes (+ 500 μm quick-test) for SUB from the public
OpenNeuro bucket and uploads them to s3://bucket/prefix/SUB/.
EOF
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$S3_DEST" ]; then
    echo "Error: --s3-dest is required" >&2
    exit 1
fi

SRC_BASE="s3://openneuro.org/ds002179/derivatives/${SUBJECT}/processed_data"
DST_BASE="${S3_DEST%/}/${SUBJECT}"

# Relative paths under SRC_BASE for each file we need.
# Keeping the source directory structure (MNI/, downsampled_data/) in the dest.
FILES=(
    "MNI/Synthesized_FLASH25_in_MNI_v2_200um.nii.gz"
    "downsampled_data/${SUBJECT}_acquired_FA25_reorient_crop_downsample_200um.nii.gz"
    "downsampled_data/${SUBJECT}_synthesized_FLASH25_reorient_crop_downsample_200um.nii.gz"
    "MNI/Synthesized_FLASH25_in_MNI_v2_500um.nii.gz"
)

echo "=== MGH ds002179 → S3 ==="
echo "Subject:   ${SUBJECT}"
echo "Source:    ${SRC_BASE}"
echo "Dest:      ${DST_BASE}"
echo "Work dir:  ${WORK_DIR}"
echo ""

mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

for rel_path in "${FILES[@]}"; do
    src="${SRC_BASE}/${rel_path}"
    dst="${DST_BASE}/${rel_path}"
    local_path="${WORK_DIR}/$(basename "$rel_path")"

    echo "-> ${rel_path}"

    # Two-step (download unsigned from public bucket, upload signed to ours):
    # server-side copy can't straddle signed/unsigned auth boundaries cleanly.
    aws s3 cp "$src" "$local_path" \
        --no-sign-request \
        --region us-east-1

    aws s3 cp "$local_path" "$dst"

    rm -f "$local_path"
done

echo ""
echo "=== MGH download complete ==="
aws s3 ls --recursive --summarize "${DST_BASE}/" | tail -2
