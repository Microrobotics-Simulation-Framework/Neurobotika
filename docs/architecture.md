# Architecture

## Overview

Neurobotika has three major components:

1. **Pipeline** — A series of Python and Bash scripts that transform raw MRI data into a watertight 3D mesh of the CSF system.
2. **Unity Viewer** — A WebGL application where users navigate the mesh as a microrobot.
3. **Infrastructure** — Terraform-managed AWS resources (S3 + CloudFront) for hosting both the viewer and large data assets.

## Data Flow

```
 Source MRI Datasets (OpenNeuro, Zenodo, etc.)
         │
         ▼
 ┌─ 01_data_acquisition ──────────────────────┐
 │  Download → verify checksums → store in S3 │
 └────────────────────────────────────────────┘
         │
         ▼
 ┌─ 02_brain_segmentation ───────────────────┐
 │  SynthSeg → ventricle + CSF label maps    │
 └───────────────────────────────────────────┘
         │                    ┌─ 03_spine_segmentation ──────────────┐
         │                    │  TotalSpineSeg + SCT → spinal SAS    │
         │                    └──────────────────────────────────────┘
         ▼                                   │
 ┌─ 04_manual_refinement ────────────────────┤
 │  3D Slicer: aqueduct, foramina, cisterns  │
 │  (interactive, human-in-the-loop)         │
 └───────────────────────────────────────────┘
         │
         ▼
 ┌─ 05_registration ─────────────────────────┐
 │  ANTs: co-register brain + spine in MNI   │
 │  Join at foramen magnum                   │
 └───────────────────────────────────────────┘
         │
         ▼
 ┌─ 06_mesh_generation ──────────────────────┐
 │  Surface extraction → clean → boolean     │
 │  union → watertight CSF mesh              │
 └───────────────────────────────────────────┘
         │
         ├──► S3 (public): final mesh files (.obj, .fbx, .glb)
         │
         ▼
 ┌─ Unity Viewer ────────────────────────────┐
 │  Import mesh → microrobot navigation      │
 │  Build WebGL → deploy to S3/CloudFront    │
 └───────────────────────────────────────────┘
```

## Storage Strategy

The git repository contains **only code, scripts, configuration, and documentation**. All large files live in S3:

| What | Where | Why |
|------|-------|-----|
| Source MRI datasets (50–2000 GB) | S3 `neurobotika-data` bucket | Too large for git; downloaded on-demand by pipeline scripts |
| Intermediate segmentations (.nii.gz) | S3 `neurobotika-data` bucket | Reproducible from pipeline but expensive to recompute |
| Final meshes (.obj, .glb, .fbx) | S3 `neurobotika-public` bucket (public) | Served to Unity viewer and available for download |
| Unity WebGL build | S3 `neurobotika-web` bucket (public, CloudFront) | Static site hosting |
| Pipeline scripts, docs, config | Git repository | Small text files, version-controlled |

### S3 Bucket Layout

```
neurobotika-data/              (private, pipeline artifacts)
├── raw/
│   ├── mgh_100um/
│   ├── spine_generic/
│   └── lumbosacral/
├── segmentations/
│   ├── brain/
│   ├── spine/
│   ├── manual/
│   └── merged/
└── meshes/
    ├── surfaces/
    ├── cleaned/
    └── final/

neurobotika-public/            (public read, serves assets)
└── meshes/
    ├── csf_system_full.glb
    ├── csf_system_full.obj
    └── csf_system_decimated.glb

neurobotika-web/               (public read, CloudFront origin)
├── index.html
├── css/
└── unity/
    ├── Build/
    ├── TemplateData/
    └── StreamingAssets/
```

## Key Design Decisions

### SynthSeg over full FreeSurfer
We use SynthSeg as a standalone Python package rather than requiring a full FreeSurfer installation. SynthSeg is the actual ML model that does the segmentation — FreeSurfer is just one distribution channel. The standalone version is lighter, pip-installable, and sufficient for our needs.

### Scripts over monolithic application
Each pipeline phase is a collection of independent scripts that read from and write to well-defined paths. This makes it easy to:
- Re-run a single phase after making changes
- Swap out a tool (e.g., replace TotalSpineSeg with a newer model)
- Debug by inspecting intermediate outputs

### Local `data/` for development, S3 for persistence
During development, scripts read/write to `data/` locally. For production runs and sharing, scripts support `--s3-prefix` flags to read/write directly from S3. The `data/` directory is gitignored.

### Unity for the viewer
Unity was chosen for the microrobot viewer because:
- Mature WebGL export pipeline
- Good support for large mesh rendering with LOD
- Built-in physics for microrobot navigation
- Wide community and asset ecosystem
