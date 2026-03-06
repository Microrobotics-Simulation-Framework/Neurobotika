#!/usr/bin/env bash
# Download the MGH 100um ex vivo brain dataset from OpenNeuro.
# By default downloads only the 200um version. Use --full for the complete dataset.
#
# Source: https://openneuro.org/datasets/ds002179
# Paper: Edlow et al., Scientific Data 2019

set -euo pipefail

DATASET_ID="ds002179"
OUTPUT_DIR="data/raw/mgh_100um"
FULL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full) FULL=true; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--full] [--output-dir DIR]"
            echo "  --full        Download full 100um dataset (~2 TB)"
            echo "  --output-dir  Target directory (default: data/raw/mgh_100um)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

echo "=== Downloading MGH 100um Ex Vivo Brain ==="
echo "Dataset: OpenNeuro ${DATASET_ID}"
echo "Output:  ${OUTPUT_DIR}"
echo ""

# Check for openneuro-cli or aws cli
if command -v openneuro &> /dev/null; then
    echo "Using openneuro-cli..."
    if [ "$FULL" = true ]; then
        openneuro download --dataset "$DATASET_ID" "$OUTPUT_DIR"
    else
        echo "Downloading 200um version only (use --full for complete dataset)"
        # TODO: Specify exact file paths for selective download once dataset structure is confirmed
        openneuro download --dataset "$DATASET_ID" "$OUTPUT_DIR"
    fi
else
    echo "openneuro-cli not found."
    echo ""
    echo "Install it:  npm install -g @openneuro/cli"
    echo "Or download manually from: https://openneuro.org/datasets/${DATASET_ID}"
    echo "Alternative mirror: https://datadryad.org/resource/doi:10.5061/dryad.119f80q"
    exit 1
fi

echo ""
echo "Download complete. Files in: ${OUTPUT_DIR}"
echo "Run 'python pipeline/01_data_acquisition/verify_downloads.py --data-dir data/raw' to verify."
