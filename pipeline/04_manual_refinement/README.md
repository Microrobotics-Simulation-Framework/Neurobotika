# Phase 4: Manual Refinement

Interactive segmentation of CSF structures that no ML model currently handles. This is the core scientific contribution of the project.

**This phase requires human interaction with 3D Slicer. It cannot be fully automated.**

## What Needs Manual Segmentation

| Structure | Why Manual |
|-----------|-----------|
| Cerebral aqueduct | ~1.5 mm diameter, no ML model segments it |
| Foramina of Monro (bilateral) | Connecting channels, not in training data |
| Foramen of Magendie | Median aperture, not in training data |
| Foramina of Luschka (bilateral) | ~2-3 mm, hardest structures to segment |
| Basal cisterns (multiple) | Ill-defined MRI boundaries |
| Foramen magnum junction | Critical brain-spine connection zone |

## Workflow

1. Open 3D Slicer
2. Load the MGH 100 um volume and the SynthSeg output from Phase 2
3. Use the Segment Editor to manually trace each structure
4. Export as NIfTI label maps
5. Run `validate_labels.py` to verify

See [docs/manual-segmentation-guide.md](../../docs/manual-segmentation-guide.md) for the full guide with per-structure instructions, label conventions, and tips.

## Scripts

### `slicer_scripts/load_volumes.py`

A 3D Slicer Python script (run from Slicer's Python console) that loads the relevant volumes and sets up the segmentation workspace.

### `validate_labels.py`

Checks manual segmentation for common errors.

```bash
python validate_labels.py \
    --input data/segmentations/manual/csf_labels.nii.gz \
    --check-connectivity \
    --check-overlaps
```

## Output

```
data/segmentations/manual/
├── csf_labels.nii.gz         # Combined label map (all manual structures)
├── aqueduct.nii.gz           # Individual structure masks (optional)
├── foramina_monro.nii.gz
├── foramen_magendie.nii.gz
├── foramina_luschka.nii.gz
├── basal_cisterns.nii.gz
└── foramen_magnum_zone.nii.gz
```
