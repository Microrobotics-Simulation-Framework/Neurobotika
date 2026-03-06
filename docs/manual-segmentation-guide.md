# Manual Segmentation Guide

This is the most time-intensive phase of the pipeline and represents the core scientific contribution. No existing ML model segments the cerebral aqueduct, foramina, or individual basal cisterns. These must be manually delineated.

## Tool: 3D Slicer

All manual segmentation is done in [3D Slicer](https://www.slicer.org) (free, open-source). Version 5.4+ recommended.

### Setup

1. Download and install 3D Slicer from https://www.slicer.org
2. Load the MGH 100 um volume (or 200 um downsampled version): `File > Add Data > Choose File(s) to Add`
3. Optionally load the SynthSeg output as a label overlay to see what has already been segmented
4. Open the Segment Editor module: `Modules > Segmentation > Segment Editor`

The `slicer_scripts/load_volumes.py` script can automate the loading step from the 3D Slicer Python console.

## Label Map Convention

Each CSF structure gets a unique integer label. This convention is used throughout the pipeline:

| Label | Structure | Color (R,G,B) |
|-------|-----------|---------------|
| 1 | Left lateral ventricle | (120, 18, 134) |
| 2 | Right lateral ventricle | (236, 13, 176) |
| 3 | 3rd ventricle | (204, 182, 142) |
| 4 | Cerebral aqueduct | (0, 255, 255) |
| 5 | 4th ventricle | (196, 58, 250) |
| 6 | Left foramen of Monro | (255, 165, 0) |
| 7 | Right foramen of Monro | (255, 200, 0) |
| 8 | Foramen of Magendie | (255, 0, 0) |
| 9 | Left foramen of Luschka | (0, 255, 0) |
| 10 | Right foramen of Luschka | (0, 200, 0) |
| 11 | Cisterna magna | (255, 218, 185) |
| 12 | Prepontine cistern | (180, 210, 255) |
| 13 | Ambient cistern (L+R) | (210, 180, 140) |
| 14 | Quadrigeminal cistern | (100, 200, 200) |
| 15 | Interpeduncular cistern | (200, 150, 200) |
| 16 | Sylvian cistern (L+R) | (150, 200, 150) |
| 17 | Cerebral subarachnoid space | (60, 60, 220) |
| 18 | Spinal subarachnoid space | (220, 100, 60) |
| 19 | Foramen magnum junction | (128, 128, 0) |
| 20 | Choroid plexus | (100, 100, 100) |

## Structure-by-Structure Guide

### Cerebral Aqueduct (Label 4)

- **Difficulty:** Medium
- **Diameter:** ~1.5 mm (15 voxels at 100 um)
- **Best viewed in:** Sagittal (midline) and axial planes
- **Strategy:** Start at the midline sagittal slice. The aqueduct runs between the 3rd and 4th ventricles through the midbrain, posterior to the tectum. Trace it slice-by-slice in axial view, moving superiorly from the 4th ventricle to the 3rd ventricle. Use the Paint tool with a small brush (2-3 voxel radius).
- **Landmarks:** Posterior to the cerebral peduncles, anterior to the superior and inferior colliculi.

### Foramina of Monro (Labels 6-7)

- **Difficulty:** Medium
- **Size:** ~5 mm
- **Best viewed in:** Coronal plane
- **Strategy:** These connect each lateral ventricle to the 3rd ventricle. Best seen in coronal sections at the level of the columns of the fornix. The foramen is bounded by the fornix superiorly and the thalamus inferiorly. Trace in coronal view, confirm in sagittal.
- **Landmarks:** Columns of fornix, anterior thalamus, septum pellucidum.

### Foramen of Magendie (Label 8)

- **Difficulty:** Medium
- **Size:** ~5 mm
- **Best viewed in:** Sagittal (midline)
- **Strategy:** The median aperture of the 4th ventricle, opening posteriorly into the cisterna magna. Visible on midline sagittal as a gap between the inferior medullary velum and the cerebellum. Trace in sagittal, verify in axial.
- **Landmarks:** Obex, inferior cerebellar vermis, cisterna magna.

### Foramina of Luschka (Labels 9-10)

- **Difficulty:** Hard (most challenging structure)
- **Size:** ~2-3 mm
- **Best viewed in:** Axial oblique
- **Strategy:** The lateral apertures of the 4th ventricle, opening into the cerebellopontine angle cisterns. Follow the lateral recesses of the 4th ventricle laterally until they exit through the foramina. These are the smallest structures in the segmentation and require careful slice-by-slice work.
- **Landmarks:** Lateral recesses of 4th ventricle, flocculus of cerebellum, cerebellopontine angle.

### Basal Cisterns (Labels 11-16)

- **Difficulty:** Hard (ill-defined boundaries)
- **Strategy:** Cisterns are CSF-filled spaces between the brain surface and the arachnoid membrane. Their boundaries are often indistinct on MRI because the arachnoid is not directly visible. Use the surrounding brain anatomy as landmarks:
  - **Cisterna magna (11):** Below the cerebellum, above the posterior arch of C1. Continuous with the foramen of Magendie superiorly and the spinal SAS inferiorly.
  - **Prepontine cistern (12):** Anterior to the pons, posterior to the clivus. Contains the basilar artery.
  - **Ambient cistern (13):** Wraps around the midbrain laterally. Contains the posterior cerebral and superior cerebellar arteries.
  - **Quadrigeminal cistern (14):** Posterior to the midbrain tectum. Contains the great vein of Galen.

### Foramen Magnum Junction (Label 19)

- **Difficulty:** Hard (critical junction)
- **Strategy:** This is where the cranial and spinal CSF spaces meet. In the final model, the brain-derived segmentation and the spine-derived segmentation must be seamlessly joined here. Segment a generous transition zone around the foramen magnum (approximately C0-C2 level) to ensure overlap between the two datasets during registration (Phase 5).

## Workflow Tips

1. **Save frequently.** Slicer can crash on large volumes.
2. **Use the Threshold tool** to get a rough initial CSF boundary, then refine with Paint/Erase.
3. **Work in all three planes.** A structure that looks correct in axial may have errors visible in sagittal.
4. **Use the Smoothing effect** (median or closing) after manual painting to reduce jaggedness.
5. **Export as NIfTI** (`Segmentations > Export to File > .nii.gz`) to preserve voxel coordinates.
6. **Run `validate_labels.py`** after each session to catch errors (disconnected components, overlapping labels).

## Validation

After completing manual segmentation, run:

```bash
python pipeline/04_manual_refinement/validate_labels.py \
    --input data/segmentations/manual/csf_labels.nii.gz \
    --check-connectivity \
    --check-overlaps
```

This checks that:
- All expected labels are present
- Each structure is a single connected component (or expected number of components)
- No two labels overlap in the same voxel
- Total CSF volume is within physiologically plausible range (100-200 mL for adults)
