# Pipeline

The segmentation-to-mesh pipeline is organized into seven sequential phases. Each phase is a directory containing Python and/or Bash scripts that can be run independently.

## Directory Structure

```
pipeline/
├── 01_data_acquisition/     # Download and verify source MRI datasets
├── 02_brain_segmentation/   # SynthSeg-based automated brain CSF segmentation
├── 03_spine_segmentation/   # TotalSpineSeg + SCT spinal canal segmentation
├── 04_manual_refinement/    # 3D Slicer scripts and validation for manual work
├── 05_registration/         # ANTs-based co-registration of brain + spine
├── 06_mesh_generation/      # Surface extraction, cleaning, and assembly
└── 07_model_training/       # (Optional) nnU-Net custom model training
```

## Data Flow

All scripts read from and write to the `data/` directory at the project root (or S3 when using `--s3-prefix`):

```
data/
├── raw/                     # Source MRI volumes (Phase 1 output)
│   ├── mgh_100um/
│   ├── spine_generic/
│   └── lumbosacral/
├── segmentations/           # Label maps (Phases 2-5 output)
│   ├── brain/               # SynthSeg output
│   ├── spine/               # TotalSpineSeg/SCT output
│   ├── manual/              # Manual refinements from 3D Slicer
│   └── merged/              # Co-registered combined labels
├── meshes/                  # 3D surface meshes (Phase 6 output)
│   ├── surfaces/            # Raw marching cubes output
│   ├── cleaned/             # After cleaning and smoothing
│   └── final/               # Watertight merged mesh + LOD variants
└── references/              # Atlas files, templates, lookup tables
```

## Running

Run the full automated pipeline:
```bash
./scripts/run_full_pipeline.sh
```

Or run individual phases — each script has `--help` for usage:
```bash
python pipeline/02_brain_segmentation/run_synthseg.py --help
```

## Configuration

Scripts use CLI arguments for all configuration. Common flags:

| Flag | Description |
|------|-------------|
| `--input` | Input file or directory |
| `--output` | Output file or directory |
| `--data-dir` | Base data directory (default: `./data`) |
| `--s3-prefix` | S3 URI prefix for remote data access |
| `--gpu` | Use GPU acceleration (default: auto-detect) |
| `--verbose` | Enable verbose logging |
