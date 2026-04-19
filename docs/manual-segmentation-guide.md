# Manual Segmentation Guide

This is the most time-intensive phase of the pipeline and represents the core scientific contribution. No existing ML model segments the cerebral aqueduct, foramina, or individual basal cisterns. These must be manually delineated.

## Tool: 3D Slicer

All manual segmentation is done in [3D Slicer](https://www.slicer.org) (free, open-source). Version 5.4+ recommended; 5.6 is what the Ubuntu instructions below install.

### Install on Ubuntu

Slicer isn't in the Ubuntu apt repo. Two options, pick one:

**Option A — official tarball (recommended, ~1 GB).** Grab the latest stable from [download.slicer.org](https://download.slicer.org/), extract, run:

```bash
cd ~/Downloads
# replace VERSION with whatever's current on download.slicer.org
wget https://download.slicer.org/bitstream/<hash>/Slicer-5.6.2-linux-amd64.tar.gz
tar -xzf Slicer-5.6.2-linux-amd64.tar.gz
mv Slicer-5.6.2-linux-amd64 ~/opt/slicer
ln -s ~/opt/slicer/Slicer ~/.local/bin/Slicer   # assumes ~/.local/bin is on PATH
```

**Option B — Flatpak.**

```bash
flatpak install flathub org.slicer.Slicer
# runs as: flatpak run org.slicer.Slicer
```

Option A is preferred because the Neurobotika `pull_from_s3.py` script needs to shell out to the system `aws` CLI, and the Flatpak sandbox makes that awkward (you'd need `--filesystem=home` and matching PATH exports).

Verify install:

```bash
Slicer --version   # should print 5.6 or later
```

### First-time launch

1. Launch Slicer. `Welcome > Load DICOM data` dialog pops up — close it; Neurobotika uses NIfTI, not DICOM.
2. Open **Modules > Segmentation > Segment Editor**. This is where you'll live during Phase 4.
3. Familiarise with the three slice views (Red = axial, Yellow = sagittal, Green = coronal) and the 3D view.

### Using the Neurobotika workflow

Once Phase 4 fires (you get an SNS email with a task token):

```bash
# 1. Save the task token from the email
export NEUROBOTIKA_TASK_TOKEN='eyJ...'       # copy-paste from email
export NEUROBOTIKA_RUN_ID='run-...'          # same run_id you started
export AWS_PROFILE=neurobotika
export AWS_DEFAULT_REGION=eu-central-1

# 2. Launch Slicer with the pull script
Slicer --python-script ~/MSF/Neurobotika/pipeline/04_manual_refinement/slicer_scripts/pull_from_s3.py

# → Slicer opens with brain + SynthSeg overlay + empty 20-segment node, Segment Editor active.
```

Full workflow (including export + upload + Step Functions resume) lives in `pipeline/04_manual_refinement/README.md`.

### Background learning — do this before your first segmentation session

You can't make a good CSF mesh without knowing what the structures are. Plan for 3–6 hours of reading + video *before* you start painting. Resources in order of importance:

1. **Slicer UI fluency.** The [3D Slicer YouTube channel's SegmentEditor tutorial](https://www.youtube.com/watch?v=xZwZfgkJ7WM) is the quickest path to competence. Watch it once, then do the [hands-on segmentation tutorial](https://github.com/Slicer/SlicerTraining/tree/main/SegmentationTutorial) (45 min). Paint, Erase, Threshold, Smoothing, Grow-from-seeds, and Scissors are the effects you'll use most.
2. **Radiopaedia — CSF spaces.** The [CSF spaces overview](https://radiopaedia.org/articles/cerebrospinal-fluid) + the linked articles on individual cisterns is the cleanest introduction. Click through "cisterna magna", "prepontine cistern", "ambient cistern", "quadrigeminal cistern", "interpeduncular cistern", "foramen of Monro", "cerebral aqueduct", "foramen of Magendie", "foramen of Luschka". Each page has example MRI slices.
3. **Neuroanatomy textbook refresher.** Whichever you have handy. If you don't, [Crossman & Neary's *Neuroanatomy: An Illustrated Colour Text*](https://www.elsevier.com/en-gb/books/neuroanatomy/crossman/978-0-7020-7463-0) (~$50 used) covers ventricles + basal cisterns with the right level of detail. Free alternative: the [e-Anatomy brain atlas at imaios.com](https://www.imaios.com/en/e-anatomy/head-and-neck/brain-mri-3d) — interactive 3D, click to label structures. 1-week trial, then paid; the free mode still lets you browse labeled MRIs.
4. **Ventricular system animation.** [Ninja Nerd's "Ventricular System" lecture on YouTube](https://www.youtube.com/watch?v=iM9uvb6X_QE) is 45 min and covers the CSF flow pathway (lateral → Monro → third → aqueduct → fourth → Magendie/Luschka → cisterns → SAS → arachnoid granulations) with clear diagrams. Watch this before doing the foramina.
5. **Cisterns deep-dive.** [Rhoton's Cranial Anatomy atlas chapter on cisterns](https://academic.oup.com/neurosurgery/article/51/suppl_4/S1/2749583) is dense but authoritative — skim for the spatial relationships between each cistern and the neighbouring vessels/nerves (landmarks help you find cistern boundaries when the MRI signal is ambiguous).
6. **MRI contrast intuition.** CSF is bright on T2, dark on T1. The MGH ds002179 volume is a *synthetic* FLASH25 (T1-weighted) — CSF appears dark. If it helps, toggle the overlay colour in Slicer or invert the window/level. [This Radiopaedia MRI physics primer](https://radiopaedia.org/articles/mri-1) is a 10-min read.
7. **Segmentation-specific tips.** [The 3D Slicer segmentation recipe wiki](https://slicer.readthedocs.io/en/latest/user_guide/image_segmentation.html) has concrete recipes for common tasks — e.g. "thin tubular structure" (applies to the cerebral aqueduct), "threshold + paint correction" (the approach for most cisterns).

Don't skip **#1 and #2** even if you're short on time. Everything else is build-your-intuition material you can layer on top.

The `slicer_scripts/load_volumes.py` script (legacy, local-only) or `slicer_scripts/pull_from_s3.py` (cloud-integrated) can automate the loading step.

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
