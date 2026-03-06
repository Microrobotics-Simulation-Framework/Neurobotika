# Phase 1: Data Acquisition

Downloads the source MRI datasets required for the pipeline.

## Scripts

### `download_mgh_100um.sh`

Downloads the MGH 100 um ex vivo brain dataset from OpenNeuro.

By default, downloads only the synthesized FLASH25 volume and the 200 um downsampled version (a few GB). The full 100 um multi-flip-angle dataset is ~2 TB and should only be downloaded if needed for the highest-resolution manual segmentation.

**Usage:**
```bash
./download_mgh_100um.sh [--full] [--output-dir data/raw/mgh_100um]
```

Options:
- `--full` — Download the complete 100 um dataset (~2 TB). Without this flag, only the 200 um version is downloaded.
- `--output-dir` — Target directory (default: `data/raw/mgh_100um`)

### `download_spine_generic.sh`

Downloads the Spine Generic single-subject dataset from Zenodo.

**Usage:**
```bash
./download_spine_generic.sh [--output-dir data/raw/spine_generic]
```

### `download_lumbosacral.sh`

Downloads the lumbosacral MRI dataset.

**Usage:**
```bash
./download_lumbosacral.sh [--output-dir data/raw/lumbosacral]
```

### `verify_downloads.py`

Validates downloaded files using checksums and basic NIfTI header checks.

**Usage:**
```bash
python verify_downloads.py --data-dir data/raw
```

## Output

```
data/raw/
├── mgh_100um/
│   ├── brain_200um.nii.gz          # 200 um downsampled volume
│   └── brain_flash25.nii.gz        # Synthesized FLASH25 contrast
├── spine_generic/
│   ├── sub-001_T1w.nii.gz
│   ├── sub-001_T2w.nii.gz
│   └── ...
└── lumbosacral/
    └── ...
```

## Storage Note

These datasets are large. After downloading locally, consider uploading to S3 for persistence:

```bash
aws s3 sync data/raw/ s3://neurobotika-data/raw/
```

The local `data/` directory is gitignored.
