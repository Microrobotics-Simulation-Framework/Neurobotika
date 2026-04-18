#!/usr/bin/env bash
# Dispatcher for Phase 1 dataset downloads. Selects the correct per-dataset
# script and forwards arguments. This is what the AWS Batch download job
# definitions invoke.
#
# Usage:
#   run_downloads.sh --dataset {mgh|spine|lumbosacral} \
#                    [--subject SUB] \
#                    --s3-dest s3://bucket/prefix
#
# The --subject arg is passed through to mgh and spine (ignored for
# lumbosacral, which is a single-repo clone with no per-subject partition).

set -euo pipefail

DATASET=""
SUBJECT=""
S3_DEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset) DATASET="$2"; shift 2 ;;
        --subject) SUBJECT="$2"; shift 2 ;;
        --s3-dest) S3_DEST="$2"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $0 --dataset {mgh|spine|lumbosacral} [--subject SUB] --s3-dest s3://bucket/prefix

Runs the dataset-specific download script and uploads the result to S3.

--subject defaults per dataset:
  mgh:          sub-EXC004
  spine:        sub-douglas
  lumbosacral:  (ignored)
EOF
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$DATASET" ] || [ -z "$S3_DEST" ]; then
    echo "Error: --dataset and --s3-dest are required" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SUBJECT_ARGS=()
[ -n "$SUBJECT" ] && SUBJECT_ARGS=(--subject "$SUBJECT")

case "$DATASET" in
    mgh)
        bash "$SCRIPT_DIR/download_mgh_100um.sh" \
            "${SUBJECT_ARGS[@]}" --s3-dest "$S3_DEST"
        ;;
    spine)
        bash "$SCRIPT_DIR/download_spine_generic.sh" \
            "${SUBJECT_ARGS[@]}" --s3-dest "$S3_DEST"
        ;;
    lumbosacral)
        bash "$SCRIPT_DIR/download_lumbosacral.sh" \
            --s3-dest "$S3_DEST"
        ;;
    *)
        echo "Error: unknown --dataset '$DATASET' (use mgh, spine, or lumbosacral)" >&2
        exit 1
        ;;
esac

echo "=== run_downloads.sh: ${DATASET} OK ==="
