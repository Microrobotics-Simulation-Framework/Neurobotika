# Phase 1: Data Acquisition

Fetches three MRI datasets and uploads them to S3:

- **Lüsebrink 2021** (OpenNeuro ds003563): **in-vivo 450 µm T2 SPACE** for `sub-yv98` + co-registered T1w and bias-corrected derivatives. Copied server-side from the public `s3://openneuro.org/` bucket. This is the **default brain reference** — see [docs/decisions.md ADR-001](../../docs/decisions.md) for why we replaced MGH.
- **spine-generic** (GitHub + git-annex): multi-site "single-subject" spinal dataset. One subject's worth of T1w/T2w/T2star/DWI, plus any manual labels.
- **SpineNerveModelGenerator** (GitHub): lumbosacral modelling scripts and a handful of bundled sample meshes. *The actual MRI volumes referenced by the paper must be fetched manually per its data-availability section* — this script only captures what's automatable.

**Optional (not in default Phase 1):** **MGH ds002179** (OpenNeuro, ex-vivo 200 µm). Retained as an ad-hoc downloader (`download-mgh` Batch job def still exists) for future cortical-ribbon / OCT-SLAM validation work. See `docs/datasets.md` for the ad-hoc submission command.

## Scripts

All scripts accept `--help`. The canonical entry point is `run_downloads.sh`, which is what the AWS Batch download job definitions invoke.

### `run_downloads.sh` — dispatcher

```bash
./run_downloads.sh --dataset {lusebrink|spine|lumbosacral|mgh} \
                   [--subject SUB] \
                   --s3-dest s3://bucket/prefix
```

Selects the correct per-dataset script and forwards arguments. `--subject` defaults to `sub-yv98` (lusebrink), `sub-douglas` (spine), or `sub-EXC004` (mgh); ignored for lumbosacral.

### `download_lusebrink_2021.sh` (default brain dataset)

Server-side copy of the Lüsebrink 2021 450 µm T2 SPACE + co-registered T1w (raw + bias-corrected) from OpenNeuro ds003563's public bucket. `sub-yv98`, `ses-3777`.

```bash
./download_lusebrink_2021.sh \
  --subject sub-yv98 \
  --s3-dest s3://neurobotika-data/runs/run-001/raw/lusebrink_2021
```

Files copied (~325 MB total; session id stripped from filenames on upload):

```
<subject>_T1w.nii.gz                 89 MB    raw MP2RAGE 450 µm
<subject>_T1w.json                             BIDS sidecar
<subject>_T1w_biasCorrected.nii.gz   90 MB    N4 bias-corrected
<subject>_T2w.nii.gz                 71 MB    raw T2 SPACE 450 µm (Slicer default)
<subject>_T2w.json                             BIDS sidecar
<subject>_T2w_biasCorrected.nii.gz   73 MB    SynthSeg input (default brain_input)
```

### `download_mgh_100um.sh` (optional, not in default Phase 1)

Copies the four MGH 200 μm + 500 μm files for a given subject from the public OpenNeuro S3 bucket to your destination prefix. **No `openneuro-cli` or Node.js dependency.**

Not wired into the default state-machine Phase 1 — MGH is ex-vivo and its CSF is fixation-collapsed (see [docs/decisions.md ADR-001](../../docs/decisions.md)). Kept for ad-hoc cortical-ribbon / OCT-SLAM work.

```bash
./download_mgh_100um.sh \
  --subject sub-EXC004 \
  --s3-dest s3://neurobotika-data/runs/mgh-ref-only/raw/mgh_100um
```

Specific files copied (per subject):

```
MNI/Synthesized_FLASH25_in_MNI_v2_200um.nii.gz                (~1.15 GB)
MNI/Synthesized_FLASH25_in_MNI_v2_500um.nii.gz                (~74 MB, quick-test)
downsampled_data/<subject>_acquired_FA25_reorient_crop_downsample_200um.nii.gz       (~1.02 GB)
downsampled_data/<subject>_synthesized_FLASH25_reorient_crop_downsample_200um.nii.gz (~1.03 GB)
```

**Note on sizes:** the full ds002179 dataset (raw 100 μm, 4 flip angles + derivatives + TIFF stacks + videos) is ~95 GB, not 2 TB as earlier docs claimed. This script downloads only the ~3.2 GB of 200 μm + 500 μm volumes.

### `download_spine_generic.sh`

Clones `github.com/spine-generic/data-single-subject`, fetches the binary payload for one subject via `git-annex` (which resolves to `computecanada-public` or `amazon-private` remotes), and uploads to S3.

```bash
./download_spine_generic.sh \
  --subject sub-douglas \
  --s3-dest s3://neurobotika-data/runs/run-001/raw/spine_generic
```

**Implementation notes:**
- The Zenodo mirror at `10.5281/zenodo.4299148` is only a 215 KB git-annex shim. The GitHub repo is the real source.
- The clone is a *full* clone (not `--depth 1` or `--single-branch`), because the `git-annex` branch holds the metadata mapping files to remote locations. A shallow clone returns "0 copies" for every file.
- The script fails loudly if `git annex get` leaves any `.nii.gz` under 4 KiB — earlier silent failures uploaded annex shims as "data".

### `download_lumbosacral.sh`

Clones the SpineNerveModelGenerator repository (~43 MB) and uploads the contents to S3. The real MRI volumes are not in this repo.

```bash
./download_lumbosacral.sh \
  --s3-dest s3://neurobotika-data/runs/run-001/raw/lumbosacral
```

### `verify_downloads.py`

Validates downloaded datasets in either a local directory or an S3 prefix, and optionally writes a JSON manifest.

```bash
# Local mode
python verify_downloads.py --data-dir data/raw [--verbose]

# S3 mode — used by the Phase1_Verify Batch job
python verify_downloads.py \
  --s3-prefix    s3://neurobotika-data/runs/run-001/raw \
  --manifest-out s3://neurobotika-data/runs/run-001/raw/manifest.json \
  --verbose
```

The manifest (`manifest.json`) lists every file, its size, and its NIfTI header metadata when applicable. It's the skip-marker the state machine's `Check_Phase1` state looks for when resuming a run.

## Output Layout (S3)

For a cloud run with `run_id=run-001`:

```
s3://neurobotika-data/runs/run-001/raw/
├── lusebrink_2021/<brain_subject>/anat/
│   ├── <brain_subject>_T1w.nii.gz            (+ .json)
│   ├── <brain_subject>_T1w_biasCorrected.nii.gz
│   ├── <brain_subject>_T2w.nii.gz            (+ .json)
│   └── <brain_subject>_T2w_biasCorrected.nii.gz
├── spine_generic/<spine_subject>/
│   ├── <spine_subject>/{anat,dwi}/*.nii.gz
│   └── derivatives/labels/<spine_subject>/
├── lumbosacral/SpineNerveModelGenerator/
└── manifest.json
```

## Storage Footprint

| Dataset | Subject | Size |
|---|---|---|
| Lüsebrink T1w + T2w (raw + bias-corrected) | sub-yv98 | ~325 MB |
| spine-generic | sub-douglas | ~30 MB |
| lumbosacral repo | n/a | ~110 MB |
| **Total (default)** |  | **~465 MB per run** |
| MGH 200 μm + 500 μm (optional, ad-hoc) | sub-EXC004 | ~3.3 GB |

At $0.024/GB·month (S3 Standard, eu-central-1): ~$0.01/month per default run. Reuse the same `run_id` across executions — Phase 1 will skip automatically via the state machine's idempotency check.
