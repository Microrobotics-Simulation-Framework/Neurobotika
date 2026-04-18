# Pipeline

The segmentation-to-mesh pipeline runs in nine phases. Phases 1–7 are the automated macro pipeline (downloads → brain/spine segmentation → registration → meshes); phases 8–9 are the microstructure + OpenUSD export work that's currently stubbed.

## Directory Structure

```
pipeline/
├── 01_data_acquisition/      # Download MRI datasets, upload to S3, verify
├── 02_brain_segmentation/    # SynthSeg-based brain CSF segmentation
├── 03_spine_segmentation/    # TotalSpineSeg + SCT spinal canal segmentation
├── 04_manual_refinement/     # 3D Slicer scripts + label-map validation
├── 05_registration/          # ANTs co-registration of brain + spine
├── 06_mesh_generation/       # Surface extraction, cleaning, Unity export
├── 07_model_training/        # (Optional) Custom nnU-Net training
├── 08_microstructure_generation/   # STUBS — LBM/SCA trabecular fields
└── 09_openusd_export/        # STUB — OpenUSD macro+micro stage assembly
```

## Running the Pipeline

The pipeline is designed to run end-to-end on **AWS Step Functions**. For local development, each script accepts CLI arguments.

### Cloud (primary path)

Deploy the infra once (`cd infra && terraform apply -var=enable_pipeline=true`), then start an execution:

```bash
aws stepfunctions start-execution \
  --profile neurobotika --region eu-central-1 \
  --state-machine-arn "$(cd infra && terraform output -raw state_machine_arn)" \
  --name "run-$(date -u +%Y-%m-%d-%H%M%S)" \
  --input '{
    "run_id":           "run-001",
    "brain_subject":    "sub-EXC004",
    "spine_subject":    "sub-douglas",
    "run_training":     false,
    "stop_after_phase": 1
  }'
```

The state machine is **idempotent**: each phase checks S3 for its expected output before running, so rerunning the same `run_id` resumes where a previous execution stopped. `stop_after_phase` (optional, default 99) aborts the state machine cleanly after the specified phase — useful while GPU quota is pending or while downstream phases aren't implemented.

### Local (development)

Individual scripts remain runnable locally. Most accept `--help`:

```bash
bash pipeline/01_data_acquisition/run_downloads.sh \
  --dataset mgh --subject sub-EXC004 \
  --s3-dest s3://neurobotika-data/runs/dev-001/raw/mgh_100um

python pipeline/02_brain_segmentation/run_synthseg.py --help
```

`scripts/run_full_pipeline.sh` wraps phases 1–7 for a local laptop run (see `scripts/README.md`).

## S3 Layout

A cloud execution with `run_id=run-001` produces:

```
s3://neurobotika-data/runs/run-001/
├── raw/                         # Phase 1 output
│   ├── mgh_100um/<brain_subject>/
│   │   ├── MNI/            Synthesized_FLASH25_in_MNI_v2_{200,500}um.nii.gz
│   │   └── downsampled_data/   acquired_FA25_…_200um.nii.gz  + synthesized_FLASH25_…_200um.nii.gz
│   ├── spine_generic/<spine_subject>/
│   │   ├── <spine_subject>/    T1w/T2w/T2star/DWI
│   │   └── derivatives/labels/<spine_subject>/
│   ├── lumbosacral/SpineNerveModelGenerator/
│   └── manifest.json            # Written by phase 1 verify
├── seg/
│   ├── brain/<brain_subject>.nii.gz        # Phase 2
│   ├── spine/<spine_subject>/              # Phase 3
│   └── merged.nii.gz                       # Phase 5 input (written during/after Phase 4)
├── registered/merged.nii.gz     # Phase 5 output
└── meshes/                      # Phase 6 output (STL per structure, GLB with LODs)
```

## Configuration

Most scripts take `--help` and share a few common flags:

| Flag | Description |
|------|-------------|
| `--input` | Input file (s3:// or local) |
| `--output` / `--output-dir` | Output file or directory (s3:// or local) |
| `--s3-prefix` | Operate entirely against an S3 prefix (used by `verify_downloads.py`) |
| `--subject` | BIDS subject id, where applicable |
| `--verbose` / `-v` | Detailed logging |

Phase-specific flags (e.g., `--gpu` for SynthSeg) are documented in each phase's README.
