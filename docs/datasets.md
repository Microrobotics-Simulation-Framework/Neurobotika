# Source Datasets

All primary datasets are freely downloadable with no institutional affiliation required. Large datasets should be cached in S3 after initial download rather than stored in the git repository.

## Primary Datasets

### MGH 100 um Ex Vivo Brain (Edlow et al., 2019)

The highest resolution whole-brain MRI dataset in existence. A post-mortem human brain scanned at 7T with 100 um isotropic resolution.

| Field | Value |
|-------|-------|
| Resolution | 100 μm isotropic native; 200 μm and 500 μm derivatives included |
| Coverage | Whole brain, ex vivo (no spinal cord); one subject (sub-EXC004) |
| Format | NIfTI (.nii.gz) |
| Size | **~95 GB** total (not 2 TB): 4× 13.6 GB raw flip angles (FA15/20/25/30) + 38 GB derivatives + 6 GB TIFF stacks + 1 GB videos |
| Recommended subset | 200 μm volumes only (**~3.2 GB**, 3 files under `derivatives/…/processed_data/`) + 500 μm MNI quick-test (~74 MB) |
| Access | Free, no account required; public `s3://openneuro.org/ds002179/` |
| Download | [OpenNeuro ds002179](https://openneuro.org/datasets/ds002179) |
| Paper | [Edlow et al., Scientific Data 2019](https://www.nature.com/articles/s41597-019-0254-8) (Open Access) |

**Recommended starting point:** The three 200 μm NIfTIs under `derivatives/sub-EXC004/processed_data/` — one in MNI space (pre-registered), two in native space (reoriented + cropped + downsampled). Sufficient for SynthSeg and still well beyond clinical resolution. Included for pipeline use by `download_mgh_100um.sh` alongside the tiny 500 μm MNI volume for quick-test runs.

**Use in pipeline:** Primary anatomical reference for brain CSF structures. Used in Phases 2 (SynthSeg input) and 4 (manual segmentation reference for foramina, cisterns, aqueduct).

### Spine Generic Dataset + PAM50 Template (Cohen-Adad et al., 2021)

The standard open-access dataset for spinal cord MRI, with the PAM50 standardized spinal cord + canal atlas.

| Field | Value |
|-------|-------|
| Subjects | 260 healthy adults across 42 centres (multi-subject); for single-subject, ~20 "subjects" are the same person at different scanners |
| Atlas | PAM50 template: spinal cord + CSF canal segmentations, C1 to S5 |
| Format | NIfTI (BIDS-organized), distributed via **git-annex** |
| Access | Free, no account required |
| Download | [Single subject (GitHub + git-annex)](https://github.com/spine-generic/data-single-subject) · [Multi-subject (GitHub)](https://github.com/spine-generic/data-multi-subject) |
| Paper | [Cohen-Adad et al., Scientific Data 2021](https://www.nature.com/articles/s41597-021-00941-8) (Open Access) |

**Important — Zenodo caveat:** The [Zenodo mirror](https://doi.org/10.5281/zenodo.4299148) contains only a 215 KB zip of git-annex pointer files, *not* the MRI data itself. Use the GitHub repo + `git annex get` (the `download_spine_generic.sh` script handles this). The git-annex remotes `computecanada-public` and `amazon-private` hold the actual blobs.

**Use in pipeline:** Phase 3 input for spinal canal segmentation. Canal mask minus cord mask = spinal subarachnoid space. Default subject: `sub-douglas`.

### Lumbosacral MRI Dataset (2024)

14 healthy adults imaged with CISS, DESS, and T2-TSE sequences targeting the cauda equina and lumbosacral nerve roots.

| Field | Value |
|-------|-------|
| Coverage | Lumbosacral spine (L1-S2), spinal SAS, nerve roots, dura |
| Sequences | CISS, DESS, T2-TSE (CSF-optimized) |
| Access | Open access (Scientific Data / CC licence) |
| Download | [Paper + Data](https://www.nature.com/articles/s41597-024-03919-4) |
| Code | [GitHub (Blender scripts)](https://github.com/Joshua-M-maker/SpineNerveModelGenerator) |

**Use in pipeline:** Supplements the Spine Generic dataset for the L1-S2 region where the thecal sac and cauda equina are difficult to resolve.

## Phase 8 Validation Datasets

These datasets are not used for anatomy reconstruction but as quantitative **validation targets** for the Phase 8 LBM microstructure simulation pipeline.

### Yiallourou et al. 2012 — 4D Phase-Contrast MRI (Independent Test Tier)

Cervical CSF velocity waveforms measured with 4D phase-contrast MRI in healthy subjects. Provides the independent test tier targets for the Level 2 Brinkman simulation.

| Field | Value |
|-------|-------|
| Subjects | 10 healthy adults |
| Measurement | CSF velocity waveforms at C2–C3, C5–C6 (anterior and posterior SAS) |
| Key data | Peak cervical velocity 2–5 cm/s; anterior-posterior ratio 1.5–3×; phase lag ~40–60 ms/vertebral level |
| Access | Open access |
| Paper | [Yiallourou et al., PLoS ONE 2012](https://doi.org/10.1371/journal.pone.0052284) |

**Use in pipeline (Phase 8):** Independent test tier — Level 2 Brinkman simulation outputs are compared against these waveforms as the final validation step, never used during parameter calibration. Target: NRMSE < 0.2 against published waveform data.

### Rossinelli et al. 2023/2024 — ONSAS Morphometry and DNS

High-resolution SRμCT morphometry and DNS of CSF dynamics in the optic nerve subarachnoid space (ONSAS). The primary source for quantitative calibration and validation targets.

| Field | Value |
|-------|-------|
| Resolution | 1.625 μm/pixel (SRμCT-derived geometry) |
| Key morphometry (2023) | Trabecular thickness PDF (peak 40–60 μm, max 200 μm); separation PDF; volume fraction ~35%; surface area amplification 3.2–4.9× |
| Key DNS results (2024) | Pressure gradient 0.37–0.67 Pa/mm for 0.5 mm/s flow; exponential κ–VF scaling; 17× mass transfer decrease without microstructure |
| Access | Open access |
| Papers | [Rossinelli et al. 2023, Fluids Barriers CNS](https://doi.org/10.1186/s12987-023-00423-y) · [Rossinelli et al. 2024, Fluids Barriers CNS](https://doi.org/10.1186/s12987-024-00548-6) |

**Use in pipeline (Phase 8):** Calibration tier — thickness/separation PDFs are the quantitative morphometric targets (V6a/b, Wasserstein distance). DNS pressure gradient is the V5 target. Mass transfer amplification is the V7 target. κ–VF exponential scaling verified via V8 sweep-level fit.

## Supplementary References

### BigBrain (Amunts et al., 2013)

20 um histological 3D reconstruction. Useful as a cross-validation reference for tissue boundaries adjacent to CSF spaces.

| Field | Value |
|-------|-------|
| Resolution | 20 um histological; volumetric at 100-400 um (MNI-registered) |
| Format | NIfTI, MINC, STL, gii |
| Access | Free (non-commercial research/education) |
| Download | [BigBrain Project](https://bigbrainproject.org) or [EBRAINS](https://ebrains.eu/service/human-brain-atlas) |

## Storage Notes

These datasets are large. Do NOT commit them to the git repository. The recommended workflow:

1. Download to `data/raw/` locally for development
2. Upload to S3 (`s3://neurobotika-data/raw/`) for persistence and sharing
3. Pipeline scripts support both local paths and S3 URIs

The `data/` directory is in `.gitignore`. See [architecture.md](architecture.md) for the full S3 bucket layout.

**Phase 8 validation data:** The Yiallourou 2012 extracted waveform data and Rossinelli 2023 digitized PDFs (once available as .npy files) should be stored at:

```
s3://neurobotika-data/validation/
├── yiallourou_2012_waveforms.npy    # 4D PC-MRI velocity waveforms (independent test)
├── rossinelli_2023_thickness_pdf.npy  # thickness PDF (calibration target V6a)
└── rossinelli_2023_separation_pdf.npy # separation PDF (calibration target V6b)
```

Paths are referenced via `reference_pdf_path` / `reference_cld_path` in `pipeline/08_microstructure_generation/config.yaml`.
