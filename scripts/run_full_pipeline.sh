#!/usr/bin/env bash
# Run the full Neurobotika pipeline (automated phases).
# Phase 4 (manual refinement) requires interactive 3D Slicer work.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="${PROJECT_DIR}/data"
USE_GPU="--gpu"

while [[ $# -gt 0 ]]; do
    case $1 in
        --data-dir) DATA_DIR="$2"; shift 2 ;;
        --no-gpu) USE_GPU="--no-gpu"; shift ;;
        --gpu) USE_GPU="--gpu"; shift ;;
        -h|--help)
            echo "Usage: $0 [--data-dir DIR] [--gpu|--no-gpu]"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$PROJECT_DIR"

echo "=========================================="
echo "  Neurobotika Pipeline"
echo "=========================================="
echo "Data dir: ${DATA_DIR}"
echo "GPU:      ${USE_GPU}"
echo ""

# --- Phase 1: Data Acquisition ---
echo "=== Phase 1: Data Acquisition ==="
if [ ! -d "${DATA_DIR}/raw/mgh_100um" ]; then
    echo "Downloading MGH 100um dataset..."
    bash pipeline/01_data_acquisition/download_mgh_100um.sh --output-dir "${DATA_DIR}/raw/mgh_100um"
else
    echo "MGH 100um data already present, skipping download."
fi

if [ ! -d "${DATA_DIR}/raw/spine_generic" ]; then
    echo "Downloading Spine Generic dataset..."
    bash pipeline/01_data_acquisition/download_spine_generic.sh --output-dir "${DATA_DIR}/raw/spine_generic"
else
    echo "Spine Generic data already present, skipping download."
fi

echo "Verifying downloads..."
python pipeline/01_data_acquisition/verify_downloads.py --data-dir "${DATA_DIR}/raw" || true
echo ""

# --- Phase 2: Brain Segmentation ---
echo "=== Phase 2: Brain Segmentation ==="
BRAIN_INPUT=$(find "${DATA_DIR}/raw/mgh_100um" -name "*.nii.gz" | head -1)
if [ -z "$BRAIN_INPUT" ]; then
    echo "ERROR: No brain NIfTI file found in ${DATA_DIR}/raw/mgh_100um/"
    exit 1
fi

echo "Resampling to 1mm..."
python pipeline/02_brain_segmentation/resample_volume.py \
    --input "$BRAIN_INPUT" \
    --output "${DATA_DIR}/segmentations/brain/brain_1mm.nii.gz" \
    --target-resolution 1.0

echo "Running SynthSeg..."
python pipeline/02_brain_segmentation/run_synthseg.py \
    --input "${DATA_DIR}/segmentations/brain/brain_1mm.nii.gz" \
    --output "${DATA_DIR}/segmentations/brain/synthseg_labels.nii.gz" \
    --volumes "${DATA_DIR}/segmentations/brain/volumes.csv" \
    ${USE_GPU}

echo "Extracting CSF labels..."
python pipeline/02_brain_segmentation/extract_csf_labels.py \
    --input "${DATA_DIR}/segmentations/brain/synthseg_labels.nii.gz" \
    --output-dir "${DATA_DIR}/segmentations/brain/"
echo ""

# --- Phase 3: Spine Segmentation ---
echo "=== Phase 3: Spine Segmentation ==="
SPINE_INPUT=$(find "${DATA_DIR}/raw/spine_generic" -name "*T2w*.nii.gz" | head -1)
if [ -z "$SPINE_INPUT" ]; then
    echo "WARN: No spine T2w NIfTI found. Skipping spine segmentation."
else
    echo "Running TotalSpineSeg..."
    python pipeline/03_spine_segmentation/run_totalspineseg.py \
        --input "$SPINE_INPUT" \
        --output-dir "${DATA_DIR}/segmentations/spine/" \
        ${USE_GPU}

    echo "Computing spinal SAS..."
    python pipeline/03_spine_segmentation/compute_spinal_sas.py \
        --canal "${DATA_DIR}/segmentations/spine/spinal_canal.nii.gz" \
        --cord "${DATA_DIR}/segmentations/spine/spinal_cord.nii.gz" \
        --output "${DATA_DIR}/segmentations/spine/spinal_sas.nii.gz"
fi
echo ""

# --- Phase 4: Manual Refinement ---
echo "=========================================="
echo "  Phase 4: Manual Refinement Required"
echo "=========================================="
echo ""
echo "Open 3D Slicer and manually segment the following structures:"
echo "  - Cerebral aqueduct"
echo "  - Foramina of Monro (bilateral)"
echo "  - Foramen of Magendie"
echo "  - Foramina of Luschka (bilateral)"
echo "  - Basal cisterns"
echo "  - Foramen magnum junction zone"
echo ""
echo "See docs/manual-segmentation-guide.md for instructions."
echo "Save output to: ${DATA_DIR}/segmentations/manual/csf_labels.nii.gz"
echo ""
read -p "Press Enter when manual segmentation is complete (or Ctrl+C to abort)..."

# Validate manual labels
echo "Validating manual labels..."
python pipeline/04_manual_refinement/validate_labels.py \
    --input "${DATA_DIR}/segmentations/manual/csf_labels.nii.gz" \
    --check-connectivity \
    --check-overlaps
echo ""

# --- Phase 5: Registration ---
echo "=== Phase 5: Registration ==="
python pipeline/05_registration/register_brain_to_mni.py \
    --brain-volume "$BRAIN_INPUT" \
    --brain-labels "${DATA_DIR}/segmentations/manual/csf_labels.nii.gz" \
    --output-dir "${DATA_DIR}/segmentations/merged/"

if [ -f "${DATA_DIR}/segmentations/spine/spinal_sas.nii.gz" ]; then
    python pipeline/05_registration/register_spine_to_mni.py \
        --spine-volume "$SPINE_INPUT" \
        --spine-labels "${DATA_DIR}/segmentations/spine/spinal_sas.nii.gz" \
        --output-dir "${DATA_DIR}/segmentations/merged/"

    python pipeline/05_registration/join_craniospinal.py \
        --brain-labels "${DATA_DIR}/segmentations/merged/brain_mni.nii.gz" \
        --spine-labels "${DATA_DIR}/segmentations/merged/spine_mni.nii.gz" \
        --output "${DATA_DIR}/segmentations/merged/csf_complete.nii.gz"
fi
echo ""

# --- Phase 6: Mesh Generation ---
echo "=== Phase 6: Mesh Generation ==="
python pipeline/06_mesh_generation/labels_to_surface.py \
    --input "${DATA_DIR}/segmentations/merged/csf_complete.nii.gz" \
    --output-dir "${DATA_DIR}/meshes/surfaces/"

python pipeline/06_mesh_generation/clean_mesh.py \
    --input "${DATA_DIR}/meshes/surfaces/all_csf.stl" \
    --output "${DATA_DIR}/meshes/cleaned/all_csf_clean.stl" \
    --smooth-iterations 30 \
    --decimate-target 500000

python pipeline/06_mesh_generation/export_unity.py \
    --input "${DATA_DIR}/meshes/cleaned/all_csf_clean.stl" \
    --output-dir "${DATA_DIR}/meshes/final/" \
    --lod-levels 3

echo ""
echo "=========================================="
echo "  Pipeline Complete"
echo "=========================================="
echo "Final meshes: ${DATA_DIR}/meshes/final/"
echo ""
echo "Next steps:"
echo "  1. Import meshes into Unity (see unity/README.md)"
echo "  2. Build Unity WebGL and deploy (see docs/deployment.md)"
echo "  3. (Optional) Train nnU-Net model (see pipeline/07_model_training/README.md)"
