#!/usr/bin/env bash
# Download the lumbosacral MRI dataset.
#
# Source: https://www.nature.com/articles/s41597-024-03919-4
# GitHub: https://github.com/Joshua-M-maker/SpineNerveModelGenerator

set -euo pipefail

OUTPUT_DIR="data/raw/lumbosacral"

while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--output-dir DIR]"
            echo "  --output-dir  Target directory (default: data/raw/lumbosacral)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

echo "=== Downloading Lumbosacral MRI Dataset ==="
echo "Output: ${OUTPUT_DIR}"
echo ""
echo "This dataset must be downloaded from the paper's data availability section."
echo "Paper: https://www.nature.com/articles/s41597-024-03919-4"
echo ""
echo "The associated Blender scripts are on GitHub:"
echo "  https://github.com/Joshua-M-maker/SpineNerveModelGenerator"
echo ""

# Clone the GitHub repo for the Blender scripts and any bundled data
if command -v git &> /dev/null; then
    echo "Cloning SpineNerveModelGenerator repository..."
    git clone --depth 1 https://github.com/Joshua-M-maker/SpineNerveModelGenerator.git \
        "${OUTPUT_DIR}/SpineNerveModelGenerator" 2>/dev/null || \
        echo "Repository already cloned or clone failed. Check ${OUTPUT_DIR}/SpineNerveModelGenerator"
else
    echo "git not found. Clone manually:"
    echo "  git clone https://github.com/Joshua-M-maker/SpineNerveModelGenerator.git ${OUTPUT_DIR}/SpineNerveModelGenerator"
fi

echo ""
echo "Follow the paper's data availability section for the MRI data download links."
echo "Place downloaded NIfTI files in: ${OUTPUT_DIR}/"
