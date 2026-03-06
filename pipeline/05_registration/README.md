# Phase 5: Registration

Co-registers brain-derived and spine-derived segmentations into a single coordinate space (MNI152) and joins them at the foramen magnum.

## Why Registration Is Needed

The brain CSF segmentation (from Phases 2+4) and the spinal SAS segmentation (from Phase 3) come from different MRI datasets with different coordinate systems, resolutions, and fields of view. They must be aligned into a common space and merged seamlessly at the cranio-spinal junction (foramen magnum).

## Tool: ANTs (Advanced Normalization Tools)

We use ANTsPy (the Python interface to ANTs) for all registration operations.

```bash
pip install antspyx
```

## Scripts

### `register_brain_to_mni.py`

Registers the brain segmentation to MNI152 standard space using ANTs SyN nonlinear registration.

```bash
python register_brain_to_mni.py \
    --brain-volume data/raw/mgh_100um/brain_200um.nii.gz \
    --brain-labels data/segmentations/manual/csf_labels.nii.gz \
    --output-dir data/segmentations/merged/
```

### `register_spine_to_mni.py`

Registers the spinal segmentation to MNI space via the PAM50 template as an intermediate.

```bash
python register_spine_to_mni.py \
    --spine-volume data/raw/spine_generic/sub-001_T2w.nii.gz \
    --spine-labels data/segmentations/spine/spinal_sas.nii.gz \
    --output-dir data/segmentations/merged/
```

### `join_craniospinal.py`

Merges the brain and spinal label maps at the foramen magnum, resolving overlaps in the junction zone.

```bash
python join_craniospinal.py \
    --brain-labels data/segmentations/merged/brain_mni.nii.gz \
    --spine-labels data/segmentations/merged/spine_mni.nii.gz \
    --output data/segmentations/merged/csf_complete.nii.gz
```

## Critical Junction: Foramen Magnum

The foramen magnum is where the cranial and spinal CSF spaces meet. The key challenge is ensuring:

1. The cisterna magna (from brain segmentation) connects seamlessly with the C1 spinal canal (from spine segmentation)
2. There are no gaps or overlaps at the junction
3. The merged label map has consistent voxel spacing

The `join_craniospinal.py` script handles this by:
1. Identifying the overlap zone (approximately C0-C2 level)
2. Blending the two label maps using a weighted transition
3. Verifying connectivity across the junction

**Manual verification of this junction is strongly recommended.** Load the output in 3D Slicer and check the sagittal midline view.

## Output

```
data/segmentations/merged/
├── brain_mni.nii.gz          # Brain labels in MNI space
├── spine_mni.nii.gz          # Spine labels in MNI space
├── brain_to_mni_warp.nii.gz  # Forward warp field (brain -> MNI)
├── mni_to_brain_warp.nii.gz  # Inverse warp field (MNI -> brain)
└── csf_complete.nii.gz       # Final merged CSF label map
```
