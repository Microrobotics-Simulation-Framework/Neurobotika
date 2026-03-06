#!/usr/bin/env bash
# Download the Spine Generic single-subject dataset from Zenodo.
#
# Source: https://doi.org/10.5281/zenodo.4299148
# Paper: Cohen-Adad et al., Scientific Data 2021

set -euo pipefail

OUTPUT_DIR="data/raw/spine_generic"
ZENODO_RECORD="4299148"

while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--output-dir DIR]"
            echo "  --output-dir  Target directory (default: data/raw/spine_generic)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

echo "=== Downloading Spine Generic Single-Subject Dataset ==="
echo "Source:  Zenodo record ${ZENODO_RECORD}"
echo "Output:  ${OUTPUT_DIR}"
echo ""

# Download from Zenodo using the API
ZENODO_URL="https://zenodo.org/api/records/${ZENODO_RECORD}"
echo "Fetching file list from Zenodo..."

if command -v curl &> /dev/null; then
    # Get the file URLs from the Zenodo API
    curl -sL "$ZENODO_URL" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for f in data.get('files', []):
    print(f['links']['self'], f['key'])
" | while read -r url filename; do
    echo "Downloading: ${filename}"
    curl -L -o "${OUTPUT_DIR}/${filename}" "$url"
done
else
    echo "curl not found. Please install curl or download manually from:"
    echo "  https://doi.org/10.5281/zenodo.${ZENODO_RECORD}"
    exit 1
fi

echo ""
echo "Download complete. Files in: ${OUTPUT_DIR}"
