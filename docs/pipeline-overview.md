# Pipeline Overview

The pipeline transforms raw MRI datasets into a complete, watertight 3D mesh of the human CSF system. It is organized into nine phases, each corresponding to a directory under `pipeline/`. Phases 1–7 are the implemented macro pipeline; phases 8–9 are the microstructure + OpenUSD export work that is currently stubbed.

## Prerequisites

- Python 3.10+ with dependencies from `requirements.txt`
- ~100 GB local disk space (or use S3 directly)
- GPU recommended for ML segmentation phases (CPU fallback available)
- 3D Slicer 5.4+ for Phase 4 (manual refinement)

## Phase Summary

| Phase | Directory | Automation | Time Estimate | Output |
|-------|-----------|-----------|---------------|--------|
| 1. Data Acquisition | `01_data_acquisition/` | Fully automated | Depends on bandwidth | Raw NIfTI volumes in `data/raw/` |
| 2. Brain Segmentation | `02_brain_segmentation/` | Fully automated | ~30 min (GPU) | Brain CSF label maps in `data/segmentations/brain/` |
| 3. Spine Segmentation | `03_spine_segmentation/` | Fully automated | ~20 min (GPU) | Spinal SAS label maps in `data/segmentations/spine/` |
| 4. Manual Refinement | `04_manual_refinement/` | Interactive | Days to weeks | Refined labels in `data/segmentations/manual/` |
| 5. Registration | `05_registration/` | Fully automated | ~1–2 hours | Merged label map in `data/segmentations/merged/` |
| 6. Mesh Generation | `06_mesh_generation/` | Fully automated | ~30 min | Final meshes in `data/meshes/final/` |
| 7. Model Training | `07_model_training/` | Fully automated | Hours (GPU) | Trained nnU-Net model (optional) |
| 8. Microstructures | `08_microstructure_generation/` | Fully automated | Minutes (GPU) | Trabeculae fields and graphs |
| 9. OpenUSD Export | `09_openusd_export/` | Fully automated | Minutes | Unified .usda / .usdz stage |

## Phase Details

### Phase 1: Data Acquisition

Downloads the source MRI datasets and uploads them to S3. The entry point in cloud mode is `run_downloads.sh`, invoked by three parallel Batch jobs (one per dataset); a fourth `verify-downloads` job writes a `manifest.json` that the state machine uses as the skip-marker for idempotent resumes. See [datasets.md](datasets.md) for dataset provenance and `pipeline/01_data_acquisition/README.md` for script-level detail.

**Scripts:**
- `run_downloads.sh` — Dispatcher used by AWS Batch jobs; selects per-dataset script.
- `download_mgh_100um.sh` — Server-side S3-to-S3 copy from public `s3://openneuro.org/` of the 200 μm + 500 μm volumes (~3.2 GB). No openneuro-cli dependency.
- `download_spine_generic.sh` — Clones `github.com/spine-generic/data-single-subject` and runs `git annex get` for the selected subject. Requires the git-annex branch, so a full (not shallow) clone is used.
- `download_lumbosacral.sh` — Clones SpineNerveModelGenerator scripts. The MRI volumes referenced in the paper must be fetched manually.
- `verify_downloads.py` — NIfTI header checks; supports both `--data-dir` (local) and `--s3-prefix` (cloud) modes, and writes `manifest.json`.

**Outputs:** Under `s3://neurobotika-data/runs/<run_id>/raw/{mgh_100um,spine_generic,lumbosacral}/` plus `manifest.json`.

### Phase 2: Brain Segmentation

Runs SynthSeg (standalone, no FreeSurfer required) on the brain MRI to automatically segment the ventricular system and extraventricular CSF.

**Scripts:**
- `resample_volume.py` — Resamples the 100 um volume to 1 mm isotropic for SynthSeg input (SynthSeg works at any resolution but 1 mm is its training resolution)
- `run_synthseg.py` — Runs SynthSeg inference, producing a label map with ventricles + CSF
- `extract_csf_labels.py` — Extracts specific CSF-related labels into separate binary masks (lateral ventricles, 3rd ventricle, 4th ventricle, extraventricular CSF)

**Key labels from SynthSeg (FreeSurfer aseg convention):**
- 4/43: Left/Right lateral ventricle
- 5/44: Left/Right lateral ventricle inferior horn
- 14: 3rd ventricle
- 15: 4th ventricle
- 24: Extraventricular CSF (subarachnoid)
- 31/63: Left/Right choroid plexus

**Outputs:** Label maps and binary masks in `data/segmentations/brain/`

### Phase 3: Spine Segmentation

Segments the spinal canal and cord to derive the spinal subarachnoid space.

**Scripts:**
- `run_totalspineseg.py` — Runs TotalSpineSeg on spinal MRI for vertebrae, cord, and canal segmentation
- `run_sct_pipeline.sh` — Runs SCT for cord segmentation, PAM50 registration, and level labelling
- `compute_spinal_sas.py` — Computes spinal SAS = canal mask minus cord mask

**Outputs:** Spinal SAS label map in `data/segmentations/spine/`

### Phase 4: Manual Refinement

The most time-intensive phase. Uses 3D Slicer to manually segment structures that no ML model currently handles.

**What must be manually segmented:**
- Cerebral aqueduct (~1.5 mm diameter)
- Foramina of Monro (bilateral, connecting lateral ventricles to 3rd ventricle)
- Foramen of Magendie (median aperture of 4th ventricle)
- Foramina of Luschka (lateral apertures of 4th ventricle, bilateral)
- Basal cisterns (cisterna magna, prepontine, ambient, quadrigeminal, etc.)
- Foramen magnum junction zone

See [manual-segmentation-guide.md](manual-segmentation-guide.md) for detailed instructions.

**Scripts:**
- `slicer_scripts/load_volumes.py` — 3D Slicer Python script to load volumes and set up the segmentation workspace
- `validate_labels.py` — Checks label map integrity (connected components, no overlaps, expected label values)

**Outputs:** Manually refined label maps in `data/segmentations/manual/`

### Phase 5: Registration

Co-registers the brain-derived and spine-derived segmentations into a single coordinate space (MNI152) and joins them at the foramen magnum.

**Scripts:**
- `register_brain_to_mni.py` — Registers brain segmentation to MNI space using ANTs
- `register_spine_to_mni.py` — Registers spine segmentation to MNI space (via PAM50 intermediate)
- `join_craniospinal.py` — Merges brain and spine label maps at the foramen magnum with overlap resolution

**Outputs:** Unified CSF label map in `data/segmentations/merged/`

### Phase 6: Mesh Generation

Converts the final label map into 3D surface meshes, cleans them, and assembles a watertight CSF system mesh.

**Scripts:**
- `labels_to_surface.py` — Marching cubes surface extraction from label maps (per-structure)
- `clean_mesh.py` — Removes self-intersections, fills holes, smooths, and decimates
- `merge_meshes.py` — Boolean union of all CSF compartments into a single watertight mesh
- `export_unity.py` — Exports in formats suitable for Unity (.fbx, .glb) with LOD variants

**Outputs:** Final meshes in `data/meshes/final/`, uploaded to S3

### Phase 7: Model Training (Optional)

Trains a custom nnU-Net model on the manually refined segmentations, producing a reusable tool that can segment CSF structures (including foramina) from new MRI scans.

**Scripts:**
- `prepare_nnunet_dataset.py` — Converts label maps to nnU-Net dataset format
- `train_nnunet.sh` — Runs nnU-Net training with automatic configuration

**Outputs:** Trained model weights (publishable)

### Phase 8: Microstructure Generation

Generates computational models of arachnoid trabeculae and septa to augment the standard macro-mesh. Clinical MRIs lack the resolution to capture these sub-structures. The algorithmic parameters serve as a biological stepping stone for future in-vivo experimental mapping (e.g., using OCT catheter SLAM datasets).

**Scripts:**
- `generate_trabeculae_sca.py` — Runs the Space Colonization Algorithm built from `config.yaml` parameters.
- `generate_septa.py` — A second pass for septa sheet modeling.

**Outputs:** Volumetric LBM grids and/or geometric graphs.

### Phase 9: OpenUSD Export

Unifies the huge macro-meshes and millions of micro-scale trabecular struts into OpenUSD representations via the `pxr` toolkit. Enables high-performance instancing and semantic labeling.

**Scripts:**
- `assemble_usd_stage.py` — Integrates the parts into a single readable USD file structure.

**Outputs:** `.usdz` and `.usda` stage definitions.

## Running the Pipeline

### Cloud (AWS Step Functions)

```bash
aws stepfunctions start-execution \
  --profile neurobotika --region eu-central-1 \
  --state-machine-arn "$(cd infra && terraform output -raw state_machine_arn)" \
  --name "run-$(date -u +%Y-%m-%d-%H%M%S)" \
  --input '{
    "run_id":           "run-001",
    "brain_subject":    "sub-EXC004",
    "spine_subject":    "sub-douglas",
    "run_training":     false,
    "stop_after_phase": 1
  }'
```

The state machine is idempotent — rerunning with the same `run_id` skips any phase whose output is already in S3 (via `s3:HeadObject` / `ListObjectsV2` checks). `stop_after_phase` (optional, default 99) aborts cleanly after the specified phase.

### Local

```bash
# Laptop-scale, sequential, local filesystem
./scripts/run_full_pipeline.sh

# Or run individual phases
python pipeline/02_brain_segmentation/run_synthseg.py \
    --input data/raw/mgh_100um/sub-EXC004/MNI/Synthesized_FLASH25_in_MNI_v2_200um.nii.gz

python pipeline/02_brain_segmentation/run_synthseg.py \
    --input s3://neurobotika-data/runs/run-001/raw/mgh_100um/sub-EXC004/MNI/Synthesized_FLASH25_in_MNI_v2_200um.nii.gz \
    --output s3://neurobotika-data/runs/run-001/seg/brain/sub-EXC004.nii.gz
```
