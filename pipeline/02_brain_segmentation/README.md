# Phase 2: Brain Segmentation

Automated segmentation of brain CSF structures using SynthSeg.

## SynthSeg (Standalone)

We use SynthSeg as a standalone Python package, **not** through a full FreeSurfer installation. SynthSeg is a contrast-agnostic deep learning model that segments brain structures from any MRI scan.

### Installing SynthSeg Standalone

Option A — pip (if available):
```bash
pip install synthseg
```

Option B — from source:
```bash
git clone https://github.com/BBillot/SynthSeg.git
cd SynthSeg
pip install -e .
```

The model weights are downloaded automatically on first run.

## Scripts

### `resample_volume.py`

Resamples the high-resolution MGH volume to a lower resolution suitable for SynthSeg input. SynthSeg was trained on 1mm isotropic data and works at any resolution, but 1mm gives the most reliable results.

```bash
python resample_volume.py \
    --input data/raw/mgh_100um/brain_200um.nii.gz \
    --output data/segmentations/brain/brain_1mm.nii.gz \
    --target-resolution 1.0
```

### `run_synthseg.py`

Runs SynthSeg inference on the resampled brain volume.

```bash
python run_synthseg.py \
    --input data/segmentations/brain/brain_1mm.nii.gz \
    --output data/segmentations/brain/synthseg_labels.nii.gz \
    --volumes data/segmentations/brain/volumes.csv \
    --gpu
```

### `extract_csf_labels.py`

Extracts CSF-specific labels from the SynthSeg output into separate binary masks.

```bash
python extract_csf_labels.py \
    --input data/segmentations/brain/synthseg_labels.nii.gz \
    --output-dir data/segmentations/brain/
```

**Produces:**
- `lateral_ventricles.nii.gz` — Labels 4, 5, 43, 44
- `third_ventricle.nii.gz` — Label 14
- `fourth_ventricle.nii.gz` — Label 15
- `extraventricular_csf.nii.gz` — Label 24
- `choroid_plexus.nii.gz` — Labels 31, 63
- `all_csf_combined.nii.gz` — Union of all CSF labels

## SynthSeg Label Reference (FreeSurfer aseg convention)

| Label | Structure |
|-------|-----------|
| 4 | Left lateral ventricle |
| 5 | Left lateral ventricle inferior horn |
| 14 | 3rd ventricle |
| 15 | 4th ventricle |
| 24 | Extraventricular CSF |
| 31 | Left choroid plexus |
| 43 | Right lateral ventricle |
| 44 | Right lateral ventricle inferior horn |
| 63 | Right choroid plexus |

## What SynthSeg Does NOT Segment

These structures require manual work in Phase 4:
- Cerebral aqueduct (of Sylvius)
- Foramina of Monro
- Foramina of Luschka
- Foramen of Magendie
- Individual basal cisterns
- Foramen magnum junction
