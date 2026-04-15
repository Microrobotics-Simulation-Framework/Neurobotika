# Neurobotika

An open-source pipeline for constructing a high-fidelity 3D mesh of the complete human cerebrospinal fluid (CSF) system, paired with an interactive Unity WebGL viewer that lets you navigate the mesh as if you were a microrobot swimming through the CSF.

> **Note:** This is just a project stub for a project I intend to resume at some point in the coming couple months (as of April 2026). The hope is to also use the result for anatomical scale [MIME](https://github.com/Microrobotics-Simulation-Framework/MIME) microrobotics simulations.

## What This Project Produces

1. **A complete 3D mesh** of the human CSF system: lateral ventricles, 3rd ventricle, cerebral aqueduct, 4th ventricle, all foramina (Monro, Luschka, Magendie), basal cisterns, cerebral subarachnoid space, and the full spinal subarachnoid space from foramen magnum to sacrum.
2. **A web-based Unity viewer** where users can fly through the CSF system as a microrobot, hosted on AWS via S3 + CloudFront.

## Project Structure

```
Neurobotika/
├── docs/                    # Detailed documentation for every aspect of the project
├── pipeline/                # The segmentation-to-mesh pipeline (Python + Bash)
│   ├── 01_data_acquisition/ # Download and verify source MRI datasets
│   ├── 02_brain_segmentation/ # SynthSeg-based automated brain CSF segmentation
│   ├── 03_spine_segmentation/ # TotalSpineSeg + SCT spinal canal segmentation
│   ├── 04_manual_refinement/  # 3D Slicer scripts and guides for manual work
│   ├── 05_registration/       # ANTs-based co-registration of brain + spine
│   ├── 06_mesh_generation/    # Surface extraction, cleaning, and assembly
│   ├── 07_model_training/     # (Optional) Train custom nnU-Net model
│   ├── 08_microstructure_generation/ # SCA procedural generation of trabeculae
│   └── 09_openusd_export/     # Assemble macro and micro meshes to OpenUSD
├── unity/                   # Unity project for the microrobot CSF viewer
├── web/                     # Static site wrapper for the Unity WebGL build
├── infra/                   # Terraform IaC for AWS S3 + CloudFront hosting
├── data/                    # Local data directory (not committed — large files)
└── scripts/                 # Top-level convenience scripts
```

## Quick Start

```bash
# 1. Set up Python environment
./scripts/setup_environment.sh

# 2. Download source datasets (~50 GB for the minimal set)
./pipeline/01_data_acquisition/download_mgh_100um.sh
./pipeline/01_data_acquisition/download_spine_generic.sh

# 3. Run the automated pipeline
./scripts/run_full_pipeline.sh

# 4. Manual refinement (interactive — see docs/manual-segmentation-guide.md)
# 5. Deploy the viewer
cd infra && terraform apply
```

See [docs/pipeline-overview.md](docs/pipeline-overview.md) for the full walkthrough.

## Requirements

- Python 3.10+
- ~100 GB disk space for datasets and intermediate files
- GPU recommended for SynthSeg and TotalSpineSeg (CPU works but is slow)
- 3D Slicer 5.4+ for manual segmentation phases
- Unity 2022.3 LTS+ for viewer development
- Terraform 1.5+ for infrastructure deployment
- AWS account for hosting

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture and design decisions |
| [docs/pipeline-overview.md](docs/pipeline-overview.md) | End-to-end pipeline walkthrough |
| [docs/datasets.md](docs/datasets.md) | Source dataset details, access, and licensing |
| [docs/manual-segmentation-guide.md](docs/manual-segmentation-guide.md) | Guide for manual CSF structure segmentation |
| [docs/microstructure-generation.md](docs/microstructure-generation.md) | Procedural generation of trabeculae and sub-MRI SAS structures |
| [docs/openusd-compatibility.md](docs/openusd-compatibility.md) | Assembling macro and micro geometry via OpenUSD protocols |
| [docs/unity-viewer.md](docs/unity-viewer.md) | Unity microrobot viewer design and build |
| [docs/deployment.md](docs/deployment.md) | AWS infrastructure and deployment guide |

## License

See [LICENSE](LICENSE).
