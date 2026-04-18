# Phase 2: Brain Segmentation

Automated brain segmentation using FreeSurfer's `mri_synthseg` (a contrast-agnostic deep-learning model for whole-brain aseg). The wrapper downsamples the input to 1 mm isotropic first — SynthSeg's training regime — before inference. This keeps memory reasonable and matches the model's expectations.

Output is written as a directory to match the shape of the upcoming migration to **SuperSynth** (`mri_super_synth`), which emits a directory of segmentation + synthetic T1w/T2w + MNI affine + QC. SuperSynth is the cleaner long-term answer for our ex-vivo data but isn't yet shipped in the `freesurfer/freesurfer:7.4.1` Docker image; swapping to it later will be a one-binary change.

## Scripts

### `run_brainseg.py`

Thin Python wrapper around the `mri_synthseg` CLI. Handles:

1. Download the input NIfTI from S3 if an `s3://` URI is passed.
2. Downsample to 1 mm isotropic (via `scipy.ndimage.zoom`, linear interp) if the input voxel size is < 0.95 mm. No-op for inputs already at ~1 mm.
3. Invoke `mri_synthseg --parc --robust` (defaults) on the 1 mm volume, writing `seg.nii.gz` + `volumes.csv` to a tempdir.
4. Upload the output directory back to S3 if `--output-dir` is an `s3://` prefix.

```bash
python3 run_brainseg.py \
  --input s3://neurobotika-data/runs/run-001/raw/mgh_100um/sub-EXC004/MNI/Synthesized_FLASH25_in_MNI_v2_200um.nii.gz \
  --output-dir s3://neurobotika-data/runs/run-001/seg/brain/sub-EXC004
```

| Flag | Default | Notes |
|---|---|---|
| `--gpu / --no-gpu` | `--gpu` | Disables GPU via `--cpu` passed through to `mri_synthseg`. |
| `--robust / --no-robust` | `--robust` | Keeps SynthSeg's contrast-agnostic path — essential for the MGH synthetic-FLASH25 contrast. |
| `--parc / --no-parc` | `--parc` | Include cortical parcellation. |

### `resample_volume.py`, `extract_csf_labels.py`

Standalone helpers retained for the local development workflow. The cloud pipeline's Batch job just calls `run_brainseg.py`, which handles resampling internally.

## Memory & instance requirements

After the 1 mm downsample, `mri_synthseg --robust --parc` fits comfortably on **g5.xlarge** / **g6.xlarge** (4 vCPU, 16 GB RAM, 24 GB VRAM). g4dn.xlarge (16 GB T4 VRAM) also works *after downsampling*, but was removed from `gpu_instance_types` for headroom — the 24 GB-VRAM families cope better when downstream phases (e.g. training) load larger models.

## Output layout

```
<output-dir>/
├── seg.nii.gz       # aseg-style segmentation
└── volumes.csv      # per-structure volumes in mm³
```

The state machine's `Check_Phase2` state uses `ListObjectsV2` with `MaxKeys=1` on the `seg/brain/<subject>/` prefix — presence of any object means "Phase 2 done, skip". Delete the prefix to force a re-run.

## aseg Label Reference (FreeSurfer convention)

CSF-relevant labels emitted by SynthSeg:

| Label | Structure |
|-------|-----------|
| 4 | Left lateral ventricle |
| 5 | Left lateral ventricle inferior horn |
| 14 | 3rd ventricle |
| 15 | 4th ventricle |
| 24 | Extraventricular CSF |
| 31 | Left choroid plexus |
| 43 | Right lateral ventricle |
| 44 | Right lateral ventricle inferior horn |
| 63 | Right choroid plexus |

## What Phase 2 does NOT produce

Still manual in Phase 4:

- Cerebral aqueduct (of Sylvius)
- Foramina of Monro, Luschka, Magendie
- Individual basal cisterns
- Foramen magnum junction

## Future upgrade: SuperSynth

When the FreeSurfer image ships `mri_super_synth` (promised for a release after 7.4.1; 8.x images may include it — worth re-checking), swap the `mri_synthseg` call for:

```bash
mri_super_synth --i <input> --o <output-dir> --mode exvivo --device cuda
```

SuperSynth handles ex-vivo contrast natively, does super-resolution (1 mm T1w/T2w/FLAIR), registers to MNI, and includes extracerebral structures — which would trim Phase 4 manual work and obsolete part of Phase 5. Keeping the directory-based output contract today means the swap will be a one-binary-line change in `run_brainseg.py`.
