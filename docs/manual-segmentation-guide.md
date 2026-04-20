# Manual Segmentation Guide

Phase 4 is the most time-intensive phase of the pipeline and represents the core scientific contribution. No existing ML model segments the cerebral aqueduct, foramina, or individual basal cisterns cleanly enough for a downstream mesh. These have to be manually delineated in 3D Slicer on the Lüsebrink 2021 450 µm T2 SPACE volume (bright CSF — ideal for this task).

This document is structured as:

1. [Install](#install-on-ubuntu) — Slicer on Ubuntu, one-time
2. [Before your first session](#before-your-first-session) — the anatomy + tool reading list
3. [The Phase 4 session, step by step](#the-phase-4-session-step-by-step) — what to actually click
4. [Structure-by-structure painting guide](#structure-by-structure-painting-guide) — strategies, landmarks, difficulty
5. [Workflow tips + pitfalls](#workflow-tips--pitfalls)
6. [Validation + upload](#validation--upload)
7. [Reference — label map convention](#reference--label-map-convention)

Plan for **3–6 hours of reading/video before your first session**, then **20–40 hours of painting across multiple sessions** for a single subject. Save often, take breaks — fatigue turns into bad segmentations turns into bad meshes turns into bad LBM calibration.

---

## Tool: 3D Slicer

All manual work is done in [3D Slicer](https://www.slicer.org) (free, open-source). Version 5.4+ works; 5.6+ recommended.

### Install on Ubuntu

Slicer isn't in apt. Two options:

**Option A — official tarball (recommended, ~1 GB).** Grab the latest stable from [download.slicer.org](https://download.slicer.org/), extract, and link the *executable file* (not a subdirectory!) onto PATH:

```bash
cd ~/Downloads

# 1. Download. Either browse download.slicer.org and copy the signed URL,
#    or script it from the redirect endpoint:
wget -c "$(curl -sL 'https://download.slicer.org/bitstream?os=linux&stability=release' \
  | grep -oE 'https://[^\"]+\.tar\.gz' | head -1)"

# 2. Extract into ~/opt/slicer. The tarball lays out as:
#    ~/opt/slicer/Slicer          <- the executable (file, not directory)
#    ~/opt/slicer/bin/, lib/, share/, etc.
mkdir -p ~/opt
tar -xzf Slicer-5.*-linux-amd64.tar.gz -C ~/opt/
mv ~/opt/Slicer-5.*-linux-amd64 ~/opt/slicer

# 3. Verify the executable exists before symlinking:
test -x ~/opt/slicer/Slicer && echo "OK: found ~/opt/slicer/Slicer"

# 4. Link the executable. Explicit $HOME + quotes stop tab-completion from
#    expanding to share/ or bin/ (a real footgun otherwise).
mkdir -p ~/.local/bin
ln -sf "$HOME/opt/slicer/Slicer" "$HOME/.local/bin/Slicer"

# 5. Verify
readlink -f ~/.local/bin/Slicer        # should end in .../opt/slicer/Slicer
Slicer --version                       # should print 5.x
```

If `Slicer --version` prints nothing or "command not found":

- `readlink -f ~/.local/bin/Slicer` — target must be the file `~/opt/slicer/Slicer`, NOT a directory like `~/opt/slicer/share/`. If it's a directory, redo step 4.
- `echo "$PATH" | tr ':' '\n' | grep local/bin` — `~/.local/bin` must be on PATH.

**Option B — Flatpak.**

```bash
flatpak install flathub org.slicer.Slicer
# runs as: flatpak run org.slicer.Slicer
```

Option A is preferred because the Neurobotika `pull_from_s3.py` script needs the system `aws` CLI, and the Flatpak sandbox makes that awkward.

### First launch sanity check

```bash
Slicer &   # starts GUI
```

Close the `Welcome > Load DICOM data` dialog (Neurobotika uses NIfTI). You should see four views by default — three slice panels (Red = axial, Yellow = sagittal, Green = coronal) and a 3D view — with the Data module selected on the left. If this works, quit Slicer and move on.

---

## Before your first session

You can't make a good CSF mesh without knowing what the structures are. Plan ~3–6 hours total across these resources, in order:

### Tier 1 — must-do before touching Slicer

1. **Slicer UI fluency.** Watch the [3D Slicer YouTube Segment Editor tutorial](https://www.youtube.com/watch?v=xZwZfgkJ7WM) (~40 min) once, then do the [hands-on segmentation tutorial](https://github.com/Slicer/SlicerTraining/tree/main/SegmentationTutorial) (~45 min). You need the effects Paint, Erase, Threshold, Smoothing, Grow-from-seeds, and Scissors.

2. **[Radiopaedia — CSF spaces article](https://radiopaedia.org/articles/cerebrospinal-fluid)** and every linked cistern article: cisterna magna, prepontine, ambient, quadrigeminal, interpeduncular, Sylvian. Each has example MRI slices you can mentally match to what Slicer will show.

3. **[Ninja Nerd — Ventricular System lecture](https://www.youtube.com/watch?v=iM9uvb6X_QE)** (~45 min). Mental model for the CSF flow pathway: lateral ventricles → Monro → third → aqueduct → fourth → Magendie + Luschka → cisterns → SAS → arachnoid granulations. Understand this before doing the foramina.

### Tier 2 — before cisterns / foramina

4. **[Rhoton Cisterns chapter](https://academic.oup.com/neurosurgery/article/51/suppl_4/S1/2749583)**. The authoritative anatomical reference. Skim for spatial relationships between each cistern and neighbouring vessels/nerves — landmarks save you when the MRI boundary is fuzzy.

5. **[e-Anatomy brain atlas](https://www.imaios.com/en/e-anatomy/head-and-neck/brain-mri-3d)** at imaios.com. Click-to-label interactive 3D MRI. Free tier browses labeled slices; works well for "what am I looking at in this axial slice".

6. Textbook refresher, if you have one. Crossman & Neary's *Neuroanatomy: An Illustrated Colour Text* is the right level. If not, skip.

### Tier 3 — reference during painting

7. **[Slicer segmentation cookbook](https://slicer.readthedocs.io/en/latest/user_guide/image_segmentation.html)** — recipes like "thin tubular structure" (aqueduct) and "threshold + paint correction" (cisterns).

8. **MRI contrast intuition.** The Lüsebrink volume is a **T2 SPACE** — **CSF is bright**. T1-weighted images (including the `T1w.nii.gz` loaded as a secondary reference) invert this — CSF is dark. If you accidentally invert: window/level in Slicer's slice toolbar reverses intensity. [Radiopaedia MRI physics primer](https://radiopaedia.org/articles/mri-1) if you want a 10-min refresher.

Don't skip **#1 and #2** even if you're short on time.

---

## The Phase 4 session, step by step

Phase 4 fires when a Step Functions execution reaches it. You get an email at the SNS-subscribed address (currently `nicholas.ehsan.roy@gmail.com`). The email contains a **task token** — a long base64-ish string the state machine is waiting on.

### 1. Capture the task token + run context

From the email, copy the `task_token` value. In your shell:

```bash
export NEUROBOTIKA_TASK_TOKEN='eyJ...copy-from-email...'
export NEUROBOTIKA_RUN_ID='run-2026-04-20-...'   # same id you started the pipeline with
export NEUROBOTIKA_BRAIN_SUBJECT='sub-yv98'      # default — Lüsebrink
export NEUROBOTIKA_SPINE_SUBJECT='sub-douglas'   # default — spine-generic
export NEUROBOTIKA_LOCAL_DIR="$HOME/neurobotika-slicer"
export AWS_PROFILE=neurobotika
export AWS_DEFAULT_REGION=eu-central-1
```

Sanity-check that the previous phases actually produced what you expect:

```bash
aws s3 ls "s3://neurobotika-data/runs/${NEUROBOTIKA_RUN_ID}/seg/brain/${NEUROBOTIKA_BRAIN_SUBJECT}/"  --recursive
aws s3 ls "s3://neurobotika-data/runs/${NEUROBOTIKA_RUN_ID}/seg/spine/${NEUROBOTIKA_SPINE_SUBJECT}/" --recursive
```

Both should list files. If either is empty, something's wrong — don't start Phase 4; debug the upstream phase first.

### 2. Launch Slicer with the pull script

```bash
Slicer --python-script \
  ~/MSF/Neurobotika/pipeline/04_manual_refinement/slicer_scripts/pull_from_s3.py &
```

This does **all of the following automatically**:

- Downloads the Lüsebrink T2 SPACE (background), T1w (secondary reference), Phase 2 brain segmentation, Phase 3 spine cord + canal + multi-label volumes into `$NEUROBOTIKA_LOCAL_DIR` (or uses cached copies if they're already there).
- Loads the T2 SPACE as the slice-view background.
- Loads the Phase 2 brain segmentation as a 30% opacity label overlay so you can see which CSF structures are already done.
- Creates a `CSF_Manual_<run_id>` segmentation node **pre-populated with all 20 Phase 4 labels** — correct names, correct colors, correct label integers per the table at the bottom of this doc.
- Opens the Segment Editor module, wired to the new segmentation node with the T2w as source.

Expected output in the Slicer Python console:

```
=== Workspace ready for run_id=run-...
  Brain subject: sub-yv98 | Spine subject: sub-douglas
  Local staging dir: /home/nick/neurobotika-slicer
  Background   : Lüsebrink 450 µm T2 SPACE (CSF bright)
  Label overlay: Phase 2 SynthSeg output (30 % opacity)
  Segmentation : CSF_Manual_run-... (20 empty segments pre-configured)
```

If you see `[MISS]` lines in the console, an upstream file is missing — fix the cause before painting.

### 3. Orient yourself before painting

- **Slice views**: Red (axial), Yellow (sagittal), Green (coronal), plus a 3D view. Click inside any slice view, then scroll with the mouse wheel to move through slices.
- **Window/level**: right-click and drag in a slice view to adjust contrast. If CSF looks dark instead of bright, you're probably looking at the T1w, not the T2w — toggle via the **Data module**.
- **Crosshair**: shift + move the mouse in any slice view moves the crosshair; the other two views re-center on that point. Essential for cross-referencing a structure seen in axial with its sagittal view.
- **Segment list**: the Segment Editor shows all 20 pre-created segments. Click one to make it active — painting tools now write to *that* segment only.

### 4. Work through structures in this order (easy → hard)

Do *not* start with the foramina of Luschka. Build confidence first:

1. Verify ventricles (labels 1, 2, 3, 5) — Phase 2 already labeled these. Check the overlay looks right; only manually touch up if obvious errors.
2. **Cerebral aqueduct** (4) — 30 min–1 h on average.
3. **Foramen of Magendie** (8) — 30 min.
4. **Foramina of Monro** (6, 7) — 1 h.
5. **Cerebral subarachnoid space** (17) — 1–2 h; mostly threshold + clean-up.
6. **Cisterna magna** (11) — 30 min.
7. **Remaining basal cisterns** (12, 13, 14, 15, 16) — 2–4 h total.
8. **Foramen magnum junction** (19) — 30 min; overlaps with cisterna magna and spinal SAS deliberately.
9. **Foramina of Luschka** (9, 10) — 1–2 h. Last because they're the hardest.
10. **Copy choroid plexus** (20) from Phase 2 labels 31/63. Mostly mechanical.

Per structure: see the [structure-by-structure guide](#structure-by-structure-painting-guide) below.

### 5. Save often

- **Save the Slicer scene** every 30 min: `File > Save as Data Bundle (.mrb)` → `$HOME/neurobotika-slicer/slicer_scene.mrb`. An .mrb preserves your in-progress segments; the raw NIfTI export doesn't.
- Every ~hour, **export the segmentation node** as NIfTI (`Segmentations > Export/import models and labelmaps > Export > Labelmap > <filename>.nii.gz`) to `$HOME/neurobotika-slicer/merged_labels.nii.gz`. You can do a partial-work checkpoint upload with:

  ```bash
  python ~/MSF/Neurobotika/pipeline/04_manual_refinement/push_merged.py \
    --run-id "$NEUROBOTIKA_RUN_ID" \
    --input "$HOME/neurobotika-slicer/merged_labels.nii.gz"
  # (no --task-token means upload but don't resume yet)
  ```

### 6. Final export, validate, upload, resume

When every structure is done:

```bash
# Export merged labels from Slicer: Segmentations > Export/import ...
#   as /home/nick/neurobotika-slicer/merged_labels.nii.gz

python ~/MSF/Neurobotika/pipeline/04_manual_refinement/push_merged.py \
  --run-id "$NEUROBOTIKA_RUN_ID" \
  --input "$HOME/neurobotika-slicer/merged_labels.nii.gz" \
  --task-token "$NEUROBOTIKA_TASK_TOKEN"
```

`push_merged.py` runs `validate_labels.py` first (drops into an interactive "proceed anyway?" prompt if it flags issues), uploads to `s3://neurobotika-data/runs/<run_id>/seg/merged.nii.gz`, then calls `stepfunctions send-task-success` to resume Phase 5.

---

## Structure-by-structure painting guide

### Cerebral aqueduct (label 4) — medium difficulty

- **Size / shape.** A roughly cylindrical CSF channel, ~1.5 mm diameter (3–4 voxels at 450 µm), running vertically through the midbrain between the 3rd and 4th ventricles.
- **Best view.** Midline sagittal (Yellow) to identify it; axial (Red) to paint slice by slice.
- **Landmarks.** Posterior to cerebral peduncles, anterior to the colliculi (tectum), inferior to the posterior commissure. On T2 SPACE it's a thin bright line.
- **Procedure.**
  1. In Yellow (sagittal), scroll until you find the midline. You'll see the 3rd ventricle (top), the aqueduct (narrow bright line going down-and-back), and the 4th ventricle (bottom).
  2. Place the crosshair near the top of the aqueduct, then switch focus to Red (axial). The aqueduct should be a small bright dot near the midline.
  3. Select segment `cerebral_aqueduct`. Use **Paint** with brush diameter ≈ 2 voxels. Paint the bright dot in each axial slice, moving inferiorly until you hit the 4th ventricle.
  4. Toggle to coronal (Green) and sagittal (Yellow) to check — you should see a continuous thin bright line in all three planes.
- **Common mistake.** Painting outside the CSF into surrounding brainstem. Use a small brush and threshold the brightness to CSF only.

### Foramina of Monro (labels 6 left, 7 right) — medium

- **Size.** ~5 mm across. Paired.
- **Best view.** Coronal (Green), at the level of the anterior columns of the fornix.
- **Landmarks.** Columns of fornix (superior border), anterior thalamus (lateral/inferior), septum pellucidum (medial).
- **Procedure.**
  1. In Green (coronal), scroll until you find the Y-shape of the lateral ventricle body narrowing toward the 3rd ventricle. The foramen is the bright region bridging the two.
  2. Paint with a medium brush (3–4 voxels) on each of 2–3 coronal slices.
  3. Verify in sagittal (Yellow) at about 5 mm lateral of midline — you should see the foramen as a small bright opening connecting lateral to third.

### Foramen of Magendie (label 8) — medium

- **Size.** ~5 mm. Single, midline.
- **Best view.** Midline sagittal (Yellow).
- **Landmarks.** Obex (the inferior point of the 4th ventricle on midline sagittal), inferior cerebellar vermis (above), cisterna magna (posterior).
- **Procedure.** At the midline sagittal slice, locate the 4th ventricle. The foramen is the posterior opening connecting it to the cisterna magna. Paint with a medium brush on 2–3 sagittal slices centered on midline. Verify in axial — the foramen should appear as a single bright opening posterior to the medulla.

### Foramina of Luschka (labels 9 left, 10 right) — hard, do these last

- **Size.** 2–3 mm. Paired. Smallest structures in the whole segmentation.
- **Best view.** Axial (Red), at the level of the pontomedullary junction.
- **Landmarks.** Lateral recesses of the 4th ventricle, flocculus of cerebellum, cerebellopontine angle (CPA) cistern.
- **Procedure.**
  1. In the 3D Scissors-equivalent way: first identify the 4th ventricle in axial. Its **lateral recesses** are thin extensions running laterally from the main body. Follow them outward.
  2. Where each lateral recess exits the parenchyma into the CPA cistern is the foramen of Luschka. Paint each foramen as a small bright opening (1–2 voxels wide) on 2–3 axial slices.
  3. Verify in coronal (Green) — you should see the foramen as a tiny bright gap on either side of the 4th ventricle at approximately the pontomedullary junction.
- **Common mistake.** Confusing the lateral recess with the foramen itself. The recess is *inside* the 4th ventricle compartment; the foramen is where it exits into SAS.

### Basal cisterns (labels 11–16) — hard, ill-defined boundaries

Cisterns are SAS subregions between the pia and arachnoid. Boundaries are fuzzy because the arachnoid isn't directly visible on MRI — use *brain structure* as the landmark.

- **Cisterna magna (11).** Below the cerebellum, above the posterior arch of C1. Continuous with foramen of Magendie (superiorly) and spinal SAS (inferiorly). Large bright posterior fossa CSF pocket on midline sagittal. Easiest cistern.
- **Prepontine cistern (12).** Anterior to the pons, posterior to the clivus. Contains the basilar artery (visible as a dark dot amid bright CSF). Paint the cistern *including* the artery — we're labeling the CSF compartment, not excluding vessels.
- **Ambient cistern (13, left + right combined).** Wraps around the midbrain laterally, connecting prepontine/interpeduncular anteriorly to quadrigeminal posteriorly. Contains posterior cerebral + superior cerebellar arteries.
- **Quadrigeminal cistern (14).** Posterior to the midbrain tectum (superior + inferior colliculi). Contains the great vein of Galen.
- **Interpeduncular cistern (15).** Between the cerebral peduncles, anterior to the midbrain. Contains branches of the posterior cerebral artery.
- **Sylvian cistern (16, left + right combined).** Along the lateral sulcus (Sylvian fissure). Bilateral. Contains the middle cerebral artery.

**Strategy for all cisterns.** Threshold first (**Effects > Threshold** with a range tuned to the bright CSF signal), then use **Scissors** effect to carve out the cistern you want from the thresholded blob, then **Paint / Erase** to refine.

### Cerebral SAS (label 17) — the "everything else" CSF

After all named cisterns are done, label 17 captures the remaining sulcal + convexity subarachnoid space. Use **Threshold** across the T2 SPACE (CSF-bright), then use **Logical operators > Subtract** to remove everything already labeled (ventricles, aqueduct, foramina, cisterns) — what's left on the brain surface is the cerebral SAS. Clean up with Erase.

### Spinal SAS (label 18)

Phase 3 already provides the spinal cord and canal masks. The spinal SAS is their difference: canal − cord. Either run `pipeline/03_spine_segmentation/compute_spinal_sas.py` locally before painting, or paint by thresholding the spine T2w and excluding the cord.

### Foramen magnum junction (label 19)

A generous transition zone around the foramen magnum (C0–C2 level) where cranial and spinal CSF spaces meet. Overlap deliberately with cisterna magna above and spinal SAS below so Phase 5 has tissue to register against. Paint with a large brush in sagittal for ~5–10 slices around the foramen magnum.

### Choroid plexus (label 20)

Already labeled in the Phase 2 brain segmentation as aseg labels 31 (left) and 63 (right). Either manually copy those voxels to segment `choroid_plexus`, or use Slicer's logical operators: add segment 20 where the overlay labels are 31 or 63.

---

## Workflow tips + pitfalls

1. **Save the .mrb every 30 min.** Slicer can crash on large volumes — losing 2 h of aqueduct work is soul-destroying.
2. **Threshold first, refine with paint.** For most cisterns, start with the Threshold effect tuned to bright CSF, then subtract / add individual voxels. Pure freehand painting is 5× slower.
3. **Work in all three planes.** Something that looks clean in axial frequently has gaps or extras when viewed sagittally. Verify every structure in the two non-primary planes before moving on.
4. **Smoothing is your friend, but don't over-use it.** After manual work on a structure, run the Smoothing effect once (Median or Closing kernel) to kill voxel jaggedness. Twice is too much.
5. **The 3D view catches mistakes.** Every few structures, rotate the 3D Slicer view — disconnected islands or implausible bridges are obvious in 3D that aren't in 2D.
6. **Use the Show 3D button.** In the Segment Editor, there's a "Show 3D" toggle next to each segment. Turn it on for the segments you're refining — it updates live as you paint.
7. **Don't paint across pial surfaces.** If you accidentally paint into grey matter, Erase immediately — label maps shouldn't overlap tissue classes.
8. **Fatigue kills quality.** Take 10-min breaks every 1–2 h. After 3–4 h in one session, stop and come back tomorrow.

## Validation + upload

Before `push_merged.py` resumes the state machine, it runs:

```bash
python pipeline/04_manual_refinement/validate_labels.py \
    --input $HOME/neurobotika-slicer/merged_labels.nii.gz \
    --check-connectivity \
    --check-overlaps
```

Checks:

- All 20 expected labels present (unless explicitly optional).
- Single-component structures (aqueduct, foramina, 3rd/4th ventricles, cisterna magna, prepontine, interpeduncular, foramen magnum junction) don't have multiple disconnected pieces. A disconnected aqueduct means you missed a slice.
- No two labels overlap in the same voxel.
- Total CSF volume is physiologically plausible (100–200 mL for adults).

Fix any errors, re-export, re-validate, then:

```bash
python pipeline/04_manual_refinement/push_merged.py \
  --run-id "$NEUROBOTIKA_RUN_ID" \
  --input "$HOME/neurobotika-slicer/merged_labels.nii.gz" \
  --task-token "$NEUROBOTIKA_TASK_TOKEN"
```

This uploads the final labels and resumes the state machine. Phase 5 starts ~1 minute later.

---

## Reference — label map convention

Each CSF structure gets a unique integer. This is pre-populated by `pull_from_s3.py` — you don't need to set it up in Slicer.

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
