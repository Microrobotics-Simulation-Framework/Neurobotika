# Architecture

## Overview

Neurobotika has three major components:

1. **Pipeline** — A series of Python scripts that transform raw MRI data into a watertight 3D mesh of the CSF system, augmented with procedurally generated sub-MRI-resolution microstructure, and validated via pore-resolved LBM fluid simulations.
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
 ┌─ 07_model_training (optional) ────────────┐
 │  nnU-Net fine-tuning on new anatomy       │
 └───────────────────────────────────────────┘
         │
         ▼
 ┌─ 08_microstructure_generation ────────────────────────────────────────┐
 │  SCA (generate_trabeculae_sca.py) + septa (generate_septa.py)         │
 │    → binary voxel grid (200³–400³, dx=5–10 μm per RVE)                │
 │                                                                       │
 │  LHS sweep (lhs_sweep.py) — N=100 parameter samples:                  │
 │    Level 1: MIME IBLBMFluidNode (D3Q19 + Bouzidi IBB)                 │
 │      × 3 pressure-gradient directions → κ_ij tensor (V1)              │
 │      + VelocityStatisticsAnalyzer (V10) + DispersionProxy (V11)       │
 │    Level 2: MIME BrinkmanFluidNode (TRT, anisotropic κ_ij(x))         │
 │      → full-domain independent test vs. 4D PC-MRI                     │
 │                                                                       │
 │  ValidationFramework (validation_framework.py):                       │
 │    Tier 1 calibration → Tier 2 validation → Tier 3 independent test   │
 │    → Pareto-optimal parameters → HDF5 results dataset                 │
 └───────────────────────────────────────────────────────────────────────┘
         │
         ├──► S3: lbm_results/sweep_results.h5 (HDF5, all V1–V11 metrics)
         │
         ▼
 ┌─ 09_openusd_export ───────────────────────┐
 │  Assemble macro-mesh + microstructure     │
 │  into OpenUSD stage for MIME/simulation   │
 │  and MICROBOTICA visualization            │
 └───────────────────────────────────────────┘
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
├── meshes/
│   ├── surfaces/
│   ├── cleaned/
│   └── final/
└── lbm_results/               (Phase 8 simulation outputs)
    ├── sweep_results.h5        (HDF5: all LHS sample metrics V1–V11)
    ├── optimal_params.yaml     (Pareto-optimal parameter sets)
    ├── rve_binaries/           (binary voxel grids for top parameter sets)
    └── brinkman/               (Level 2 Brinkman simulation outputs)

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

### MIME/MADDENING for Phase 8 CFD simulations

The microstructure LBM simulations (Phase 8) use the **MIME** node framework, which is built on top of **MADDENING** (the GPU-accelerated lattice Boltzmann engine). The two-level simulation architecture uses:

- **MIME `IBLBMFluidNode`** — D3Q19 LBM with Bouzidi interpolated bounce-back for pore-resolved RVE simulations (Level 1). Sub-0.5% torque error, O(dx²) convergence. This is the workhorse for permeability tensor extraction.
- **MIME `BrinkmanFluidNode`** *(to be implemented)* — D3Q19 LBM with anisotropic Brinkman forcing (Seta 2009, TRT stabilization per Ginzburg 2015) for full-domain coarse simulations (Level 2). Takes the spatially varying κ_ij tensor from Level 1 as input.

**MADDENING integrates with SkyPilot** to dispatch GPU jobs to whichever cloud provider is currently cheapest — RunPod, Lambda Labs, Vast.ai, or AWS (p4de/p5 instances). The Level 1 LHS sweep (~100 RVEs × 3 LBM runs, ~50 minutes on H100) runs on a single GPU; the Level 2 Brinkman simulation is single-GPU feasible at dx=100–200 μm. Full-spine pore-resolved simulation (if ever needed) would require multi-GPU distribution via SkyPilot.

**AWS note:** AWS supports p4de.24xlarge (8× A100 80GB SXM4) and p5.48xlarge (8× H100 80GB SXM5) instances, but GPU quota requests for P-family instances require manual justification and can take days. RunPod/Lambda Labs offer H100 SXMs at spot-like pricing without quota friction — prefer these for LBM workloads. AWS remains the primary choice for Phases 1–7 (CPU/moderate-GPU) and for persistent storage (S3).
