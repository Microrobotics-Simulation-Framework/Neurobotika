# Source Datasets

All primary datasets are freely downloadable with no institutional affiliation required. Large datasets should be cached in S3 after initial download rather than stored in the git repository.

## Primary Datasets

### MGH 100 um Ex Vivo Brain (Edlow et al., 2019)

The highest resolution whole-brain MRI dataset in existence. A post-mortem human brain scanned at 7T with 100 um isotropic resolution.

| Field | Value |
|-------|-------|
| Resolution | 100 um isotropic (also available at 200 um and 500 um) |
| Coverage | Whole brain, ex vivo (no spinal cord) |
| Format | NIfTI (.nii.gz) |
| Size | ~2 TB per flip angle at full resolution; FLASH25 synthesized volume is much smaller |
| Access | Free, no account required |
| Download | [OpenNeuro ds002179](https://openneuro.org/datasets/ds002179) or [Dryad](https://datadryad.org/resource/doi:10.5061/dryad.119f80q) |
| Paper | [Edlow et al., Scientific Data 2019](https://www.nature.com/articles/s41597-019-0254-8) (Open Access) |

**Recommended starting point:** Download the 200 um version or the synthesized FLASH25 volume, not the full 100 um multi-flip-angle data. The 200 um version is sufficient for SynthSeg and still far beyond clinical resolution.

**Use in pipeline:** Primary anatomical reference for brain CSF structures. Used in Phases 2 (SynthSeg input) and 4 (manual segmentation reference for foramina, cisterns, aqueduct).

### Spine Generic Dataset + PAM50 Template (Cohen-Adad et al., 2021)

The standard open-access dataset for spinal cord MRI, with the PAM50 standardized spinal cord + canal atlas.

| Field | Value |
|-------|-------|
| Subjects | 260 healthy adults across 42 centres |
| Atlas | PAM50 template: spinal cord + CSF canal segmentations, C1 to S5 |
| Format | NIfTI (BIDS-organized) |
| Access | Free, no account required |
| Download | [Single subject (Zenodo)](https://doi.org/10.5281/zenodo.4299148) or [Multi-subject (GitHub)](https://github.com/spine-generic/data-multi-subject) |
| Paper | [Cohen-Adad et al., Scientific Data 2021](https://www.nature.com/articles/s41597-021-00941-8) (Open Access) |

**Use in pipeline:** Phase 3 input for spinal canal segmentation. Canal mask minus cord mask = spinal subarachnoid space.

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
