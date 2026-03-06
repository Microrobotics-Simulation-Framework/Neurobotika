#!/usr/bin/env bash
# Set up the Python environment for the Neurobotika pipeline.
# Creates a virtual environment and installs all dependencies.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${PROJECT_DIR}/.venv"

echo "=== Neurobotika Environment Setup ==="
echo "Project: ${PROJECT_DIR}"
echo "Venv:    ${VENV_DIR}"
echo ""

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Activate
source "${VENV_DIR}/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install project dependencies
echo "Installing dependencies..."
pip install -r "${PROJECT_DIR}/requirements.txt"

# Install SynthSeg (standalone)
echo ""
echo "=== SynthSeg Installation ==="
echo "SynthSeg must be installed separately. Choose one:"
echo ""
echo "  Option A (pip, if available):"
echo "    pip install synthseg"
echo ""
echo "  Option B (from source):"
echo "    git clone https://github.com/BBillot/SynthSeg.git"
echo "    pip install -e SynthSeg/"
echo ""

# Check for optional tools
echo "=== Checking optional tools ==="

check_tool() {
    if command -v "$1" &> /dev/null; then
        echo "  [OK] $1"
    else
        echo "  [--] $1 not found ($2)"
    fi
}

check_tool "sct_version" "Spinal Cord Toolbox — https://spinalcordtoolbox.com"
check_tool "terraform" "Terraform — https://terraform.io"
check_tool "aws" "AWS CLI — https://aws.amazon.com/cli/"

echo ""
echo "=== Setup Complete ==="
echo "Activate with: source ${VENV_DIR}/bin/activate"
