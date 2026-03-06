# Phase 3: Spine Segmentation

Automated segmentation of the spinal canal and cord to derive the spinal subarachnoid space (SAS).

## Tools

### TotalSpineSeg
nnU-Net-based pipeline for automatic segmentation of vertebrae, intervertebral discs, spinal cord, and spinal canal. Outputs separate cord and canal masks — the space between them is the spinal SAS.

```bash
pip install totalspineseg nnunetv2
```

### Spinal Cord Toolbox (SCT)
Complementary tool for cord segmentation, PAM50 template registration, and cross-sectional area measurements. Provides validated level labelling (C1-S5).

```bash
# See https://spinalcordtoolbox.com for installation
```

## Scripts

### `run_totalspineseg.py`

Runs TotalSpineSeg on a spinal MRI volume to produce cord and canal segmentations.

```bash
python run_totalspineseg.py \
    --input data/raw/spine_generic/sub-001_T2w.nii.gz \
    --output-dir data/segmentations/spine/
```

**Produces:**
- `spinal_cord.nii.gz` — Cord segmentation mask
- `spinal_canal.nii.gz` — Canal segmentation mask (outer boundary = dura)
- `vertebrae.nii.gz` — Vertebral body instance labels

### `run_sct_pipeline.sh`

Runs SCT for cord segmentation, PAM50 registration, and level labelling. Use this alongside TotalSpineSeg for cross-validation and atlas-based level labels.

```bash
./run_sct_pipeline.sh data/raw/spine_generic/sub-001_T2w.nii.gz data/segmentations/spine/
```

### `compute_spinal_sas.py`

Computes the spinal subarachnoid space as the boolean difference between canal and cord masks.

```bash
python compute_spinal_sas.py \
    --canal data/segmentations/spine/spinal_canal.nii.gz \
    --cord data/segmentations/spine/spinal_cord.nii.gz \
    --output data/segmentations/spine/spinal_sas.nii.gz
```

## Output

```
data/segmentations/spine/
├── spinal_cord.nii.gz       # Cord mask
├── spinal_canal.nii.gz      # Canal mask (dura boundary)
├── spinal_sas.nii.gz        # SAS = canal - cord
├── vertebrae.nii.gz         # Vertebral instance labels
└── sct/                     # SCT outputs (PAM50 registration, level labels)
```
