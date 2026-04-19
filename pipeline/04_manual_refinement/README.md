# Phase 4: Manual Refinement

Interactive segmentation of CSF structures that no ML model currently handles. **This is the core scientific contribution of Neurobotika** — every subsequent mesh/viewer/microrobotics simulation depends on the quality of the manual labels produced here.

This phase cannot be fully automated. The Step Functions state machine calls `sns:publish.waitForTaskToken` when it reaches Phase 4, emails a callback token to the configured address, and pauses until you run `push_merged.py` with that token.

## Structures to segment manually

Phase 2 (SynthSeg) gives you the ventricles + extraventricular CSF. Phase 3 (TotalSpineSeg) gives you the spinal cord + canal. Everything in the list below has to be drawn by hand:

| Structure | Label | Notes |
|---|---|---|
| Cerebral aqueduct | 4 | ~1.5 mm diameter, midbrain |
| Foramina of Monro | 6 / 7 | Lateral ↔ third ventricle, bilateral |
| Foramen of Magendie | 8 | Median aperture of 4th ventricle |
| Foramina of Luschka | 9 / 10 | Lateral apertures, bilateral, ~2-3 mm (hardest) |
| Basal cisterns | 11–16 | Cisterna magna, prepontine, ambient, quadrigeminal, interpeduncular, Sylvian |
| Cerebral SAS | 17 | Overall subarachnoid space |
| Spinal SAS | 18 | Already delineated by Phase 3 as (canal − cord); extend to the foramen magnum |
| Foramen magnum junction | 19 | Critical bridge — register brain and spine here in Phase 5 |
| Choroid plexus | 20 | (Already in SynthSeg as labels 31/63; copy over) |

Full protocol + per-structure anatomy notes + strategy tips: [docs/manual-segmentation-guide.md](../../docs/manual-segmentation-guide.md).

## Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 0. (one-time) Install 3D Slicer — see docs/manual-segmentation-    │
│    guide.md §Setup.                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Kick off a pipeline run (or resume one). When it reaches Phase 4 │
│    you get an email with a task token.                              │
│      aws stepfunctions start-execution \                            │
│        --input '{"run_id":"run-2026-04-20-...", ...}' ...           │
├─────────────────────────────────────────────────────────────────────┤
│ 2. Save the task token into your shell:                             │
│      export NEUROBOTIKA_TASK_TOKEN='...value from email...'         │
│      export NEUROBOTIKA_RUN_ID='run-2026-04-20-...'                 │
├─────────────────────────────────────────────────────────────────────┤
│ 3. Launch Slicer with the pull script to download inputs + set up   │
│    the segmentation workspace in one call:                          │
│      Slicer --python-script \                                       │
│          pipeline/04_manual_refinement/slicer_scripts/pull_from_s3.py │
├─────────────────────────────────────────────────────────────────────┤
│ 4. Do the segmentation work. Save Slicer scene as you go.           │
├─────────────────────────────────────────────────────────────────────┤
│ 5. Export merged labels from Slicer:                                │
│      Segmentations > Export to File > NIfTI (.nii.gz)               │
│      Save as $HOME/neurobotika-slicer/merged_labels.nii.gz          │
├─────────────────────────────────────────────────────────────────────┤
│ 6. Upload + resume:                                                 │
│      python pipeline/04_manual_refinement/push_merged.py \          │
│          --run-id "$NEUROBOTIKA_RUN_ID" \                           │
│          --input "$HOME/neurobotika-slicer/merged_labels.nii.gz" \  │
│          --task-token "$NEUROBOTIKA_TASK_TOKEN"                     │
└─────────────────────────────────────────────────────────────────────┘
```

Phase 5 (registration) picks up automatically from `s3://neurobotika-data/runs/<run_id>/seg/merged.nii.gz` once the task token resume fires.

## Scripts

### `slicer_scripts/pull_from_s3.py` (runs inside Slicer)

Downloads the set of volumes the manual work needs — MGH 200 μm brain, Phase 2 SynthSeg labels, spine T2w + cord + canal, spine multi-label — and sets up a Slicer workspace:

- Brain volume as the background on all slice views.
- SynthSeg labels as a 30 % opacity overlay so you can see what's already segmented.
- A new `CSF_Manual_<run_id>` segmentation node **pre-populated with the 20-segment schema** (correct names + colors + label integers per `docs/manual-segmentation-guide.md`).
- Segment Editor module opened and wired to the new node.

Config via environment variables (defaults hard-coded for local quick-start):

```bash
export NEUROBOTIKA_RUN_ID=run-2026-04-18-125403
export NEUROBOTIKA_BRAIN_SUBJECT=sub-EXC004
export NEUROBOTIKA_SPINE_SUBJECT=sub-douglas
export NEUROBOTIKA_LOCAL_DIR="$HOME/neurobotika-slicer"
export NEUROBOTIKA_BUCKET=neurobotika-data
export AWS_PROFILE=neurobotika
export AWS_DEFAULT_REGION=eu-central-1
```

Uses the system `aws` CLI (not boto3) so Slicer's embedded Python doesn't need extra pip installs.

### `push_merged.py` (runs on your laptop, outside Slicer)

1. Optionally runs `validate_labels.py` on the merged label map.
2. `aws s3 cp` to `s3://neurobotika-data/runs/<run_id>/seg/merged.nii.gz`.
3. Calls `aws stepfunctions send-task-success` with the Phase 4 task token to resume the pipeline.

Pass `--task-token` when you're ready to commit; omit it to upload without resuming (useful for iterative uploads / mid-work sanity checks in S3).

### `slicer_scripts/load_volumes.py` (legacy, local-only)

Older script that loads from local `data/raw/…` paths. Kept for laptop-only workflows without S3; prefer `pull_from_s3.py` for cloud runs.

### `validate_labels.py`

Sanity-check the merged label map (expected labels present, single-component invariants, total CSF volume plausible). `push_merged.py` runs this by default; invoke standalone like:

```bash
python validate_labels.py --input <merged.nii.gz> --check-connectivity --check-overlaps
```

## Output

```
s3://neurobotika-data/runs/<run_id>/seg/merged.nii.gz
```

Single NIfTI containing the 20-label CSF schema. Phase 5 reads this as the registration input.

Locally (in your Slicer staging dir):

```
$HOME/neurobotika-slicer/
├── brain_200um.nii.gz          # downloaded, read-only
├── brain_seg.nii.gz            # downloaded, read-only
├── spine_*.nii.gz              # downloaded, read-only
├── merged_labels.nii.gz        # YOUR WORK — upload this
└── slicer_scene.mrb            # save from File > Save Scene As (recommended)
```
