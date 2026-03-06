# Data Directory

**This directory is gitignored.** It contains large files that should not be committed to the repository.

## Structure

```
data/
├── raw/                     # Source MRI datasets (downloaded in Phase 1)
│   ├── mgh_100um/           # MGH 100um ex vivo brain
│   ├── spine_generic/       # Spine Generic single-subject
│   └── lumbosacral/         # Lumbosacral MRI dataset
├── segmentations/           # Label maps from pipeline phases
│   ├── brain/               # SynthSeg output (Phase 2)
│   ├── spine/               # TotalSpineSeg/SCT output (Phase 3)
│   ├── manual/              # Manual refinements from 3D Slicer (Phase 4)
│   └── merged/              # Co-registered combined labels (Phase 5)
├── meshes/                  # 3D surface meshes (Phase 6)
│   ├── surfaces/            # Raw marching cubes output
│   ├── cleaned/             # After cleaning and smoothing
│   └── final/               # Watertight merged mesh + LOD variants
└── references/              # Atlas files, templates
```

## Storage

Large files should be stored in S3 rather than locally:

| Bucket | Content | Access |
|--------|---------|--------|
| `neurobotika-data` | Raw MRI, segmentations, intermediates | Private |
| `neurobotika-public` | Final meshes for download | Public read |

### Syncing to/from S3

```bash
# Upload local data to S3
aws s3 sync data/ s3://neurobotika-data/ --exclude "*.md"

# Download from S3 to local
aws s3 sync s3://neurobotika-data/ data/
```

## Size Estimates

| Dataset | Size |
|---------|------|
| MGH 100um (200um version) | ~5 GB |
| MGH 100um (full, all flip angles) | ~2 TB |
| Spine Generic (single subject) | ~1 GB |
| Lumbosacral dataset | ~2 GB |
| Segmentations (all phases) | ~10 GB |
| Meshes (all LODs) | ~1 GB |
