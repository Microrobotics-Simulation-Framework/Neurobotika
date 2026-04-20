#!/usr/bin/env bash
# Fetch the Lüsebrink 2021 in-vivo 450 µm T2 SPACE (+ co-registered T1w,
# with bias-corrected derivatives) from the public OpenNeuro bucket.
#
# Dataset: OpenNeuro ds003563 — Lüsebrink et al., Scientific Data 2021
#   https://doi.org/10.18112/openneuro.ds003563.v1.0.1
#   7T Siemens, single subject (sub-yv98), multiple sessions.
#
# We pull only ses-3777 (the primary 450 µm T2 SPACE acquisition) because
# that's the session Phase 2 / 4 / 8 operate on:
#
#   raw T2 SPACE           (71 MB)   — for Slicer display / QC
#   raw T1w                (89 MB)   — co-registered reference
#   biasCorrected T2w      (73 MB)   — SynthSeg input (default brain_input)
#   biasCorrected T1w      (90 MB)   — optional dual-modal overlay
#   + JSON sidecars        (~few KB)
#   Total                  ≈ 325 MB
#
# Uploaded S3 layout (session stripped from filenames so downstream paths
# key only on the subject id):
#
#   <s3-dest>/<subject>/anat/
#     <subject>_T1w.nii.gz
#     <subject>_T1w.json
#     <subject>_T1w_biasCorrected.nii.gz
#     <subject>_T2w.nii.gz
#     <subject>_T2w.json
#     <subject>_T2w_biasCorrected.nii.gz

set -euo pipefail

SUBJECT="sub-yv98"
SESSION="ses-3777"
S3_DEST=""
WORK_DIR="${WORK_DIR:-/tmp/lusebrink_download}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --subject)  SUBJECT="$2"; shift 2 ;;
        --session)  SESSION="$2"; shift 2 ;;
        --s3-dest)  S3_DEST="$2"; shift 2 ;;
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $0 [--subject SUB] [--session SES] --s3-dest s3://bucket/prefix

Copies the 450 µm T2 SPACE + T1w (raw and bias-corrected) for SUB+SES
from OpenNeuro's public bucket to the specified S3 destination.

Defaults: SUB=sub-yv98, SES=ses-3777 (the canonical 450 µm session).
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

SRC_BASE="s3://openneuro.org/ds003563"
DST_BASE="${S3_DEST%/}/${SUBJECT}/anat"

# (source_relative_path, destination_filename_without_session)
FILES=(
    "sub-yv98/${SESSION}/anat/${SUBJECT}_${SESSION}_T1w.nii.gz|${SUBJECT}_T1w.nii.gz"
    "sub-yv98/${SESSION}/anat/${SUBJECT}_${SESSION}_T1w.json|${SUBJECT}_T1w.json"
    "sub-yv98/${SESSION}/anat/${SUBJECT}_${SESSION}_T2w.nii.gz|${SUBJECT}_T2w.nii.gz"
    "sub-yv98/${SESSION}/anat/${SUBJECT}_${SESSION}_T2w.json|${SUBJECT}_T2w.json"
    "derivatives/sub-yv98/longitudinal_T1w/biasfield/${SESSION}/anat/${SUBJECT}_${SESSION}_T1w_biasCorrected.nii.gz|${SUBJECT}_T1w_biasCorrected.nii.gz"
    "derivatives/sub-yv98/longitudinal_T1w/biasfield/${SESSION}/anat/${SUBJECT}_${SESSION}_T2w_biasCorrected.nii.gz|${SUBJECT}_T2w_biasCorrected.nii.gz"
)

echo "=== Lüsebrink 2021 ds003563 → S3 ==="
echo "Subject:  ${SUBJECT}"
echo "Session:  ${SESSION}"
echo "Source:   ${SRC_BASE}"
echo "Dest:     ${DST_BASE}"
echo "Work dir: ${WORK_DIR}"
echo ""

mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

for entry in "${FILES[@]}"; do
    rel_src="${entry%|*}"
    dst_name="${entry#*|}"
    src="${SRC_BASE}/${rel_src}"
    dst="${DST_BASE}/${dst_name}"
    local_path="${WORK_DIR}/${dst_name}"

    echo "-> ${dst_name}"

    # Two-step (unsigned from public bucket, signed write to our bucket):
    # AWS CLI can't mix signed/unsigned auth in a single s3 cp straddling
    # buckets, so stage through local disk. Same pattern as MGH download.
    aws s3 cp "$src" "$local_path" \
        --no-sign-request \
        --region us-east-1

    aws s3 cp "$local_path" "$dst"

    rm -f "$local_path"
done

echo ""
echo "=== Lüsebrink download complete ==="
aws s3 ls --recursive --summarize "${DST_BASE}/" | tail -2
