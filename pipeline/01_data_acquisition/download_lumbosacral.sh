#!/usr/bin/env bash
# Fetch the SpineNerveModelGenerator repository (the code + any bundled
# small data shipped with the paper) and upload to S3.
#
# Source: https://github.com/Joshua-M-maker/SpineNerveModelGenerator
# Paper:  Nature Scientific Data 2024 — https://www.nature.com/articles/s41597-024-03919-4
#
# Note: the actual high-res MRI volumes referenced in the paper are NOT in
# this repo — they must be fetched manually per the paper's data-availability
# section. This script grabs only what is automatable (the Blender-script
# toolchain + any bundled sample assets).

set -euo pipefail

S3_DEST=""
WORK_DIR="${WORK_DIR:-/tmp/lumbosacral_download}"
REPO_URL="https://github.com/Joshua-M-maker/SpineNerveModelGenerator.git"

while [[ $# -gt 0 ]]; do
    case $1 in
        --s3-dest)  S3_DEST="$2"; shift 2 ;;
        --work-dir) WORK_DIR="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $0 --s3-dest s3://bucket/prefix [--work-dir DIR]

Clones the SpineNerveModelGenerator repo and uploads its contents to
s3://bucket/prefix/ . The raw MRI volumes referenced in the paper are
not included in the repo — fetch those manually into the same prefix
once you've obtained them.
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

DST_BASE="${S3_DEST%/}"
REPO_DIR="${WORK_DIR}/SpineNerveModelGenerator"

echo "=== lumbosacral repo → S3 ==="
echo "Upstream:  ${REPO_URL}"
echo "Dest:      ${DST_BASE}"
echo "Work dir:  ${WORK_DIR}"
echo ""

mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

git clone --depth 1 "$REPO_URL" "$REPO_DIR"

# Strip .git before upload to avoid shipping the whole pack file
rm -rf "$REPO_DIR/.git"

aws s3 sync "$REPO_DIR/" "${DST_BASE}/SpineNerveModelGenerator/"

echo ""
echo "=== lumbosacral download complete ==="
echo "Note: manual MRI download still required — see paper's data availability section."
aws s3 ls --recursive --summarize "${DST_BASE}/" | tail -2
