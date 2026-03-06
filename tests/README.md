# Tests

Unit tests for the Neurobotika pipeline, using pytest.

## Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run a specific test file
python3 -m pytest tests/test_extract_csf_labels.py -v

# Run a specific test class or method
python3 -m pytest tests/test_validate_labels.py::TestValidateLabelMap::test_missing_labels_detected -v

# Run with short output
python3 -m pytest tests/
```

## Minimum Requirements

The tests are designed to run with only the standard scientific Python stack:

- **Python 3.10+**
- **numpy** (array operations)
- **scipy** (connected components, resampling)
- **click** (CLI invocation testing)
- **pytest** (test runner)

No domain-specific packages (nibabel, trimesh, pymeshlab, antspyx, SynthSeg, etc.) are required to run the current test suite.

## Test Structure

| Test File | Tests For | What It Covers |
|-----------|-----------|---------------|
| `test_extract_csf_labels.py` | `pipeline/02_brain_segmentation/extract_csf_labels.py` | Label mask extraction, volume computation, CSF group config |
| `test_resample_volume.py` | `pipeline/02_brain_segmentation/resample_volume.py` | Zoom factor computation, affine updates, array resampling |
| `test_compute_spinal_sas.py` | `pipeline/03_spine_segmentation/compute_spinal_sas.py` | Boolean canal-cord subtraction, edge cases, volume calculation |
| `test_validate_labels.py` | `pipeline/04_manual_refinement/validate_labels.py` | Missing/unexpected labels, connectivity, volume range checks |
| `test_join_craniospinal.py` | `pipeline/05_registration/join_craniospinal.py` | Brain-spine merge logic, priority rules, stats, connectivity |
| `test_export_unity.py` | `pipeline/06_mesh_generation/export_unity.py` | LOD ratio computation, target face count, decimation schedule |
| `test_prepare_nnunet.py` | `pipeline/07_model_training/prepare_nnunet_dataset.py` | Label map config, CLI dataset creation, directory structure |
| `test_verify_downloads.py` | `pipeline/01_data_acquisition/verify_downloads.py` | Dataset config, CLI with missing/empty dirs |
| `test_label_consistency.py` | Cross-module | Label IDs match across validate_labels, labels_to_surface, prepare_nnunet |

## Test Design

### Approach: extracted pure functions

Pipeline scripts were refactored to separate **core logic** (pure numpy/scipy array operations) from **I/O wrappers** (nibabel file loading, click CLI). Tests target the pure functions directly with synthetic numpy arrays, avoiding the need for real MRI data or heavy dependencies.

For example, `extract_csf_labels.py` exposes:
- `extract_label_mask(seg, label_ids)` — pure numpy, tested directly
- `compute_volume_ml(mask, voxel_zooms)` — pure numpy, tested directly
- `extract_all_csf_masks(seg)` — pure numpy, tested directly
- `main()` — click CLI wrapper with nibabel I/O, not tested here

### Synthetic fixtures

`conftest.py` provides reusable fixtures:
- `synthetic_brain_seg` — 32x32x32 volume with known SynthSeg labels
- `synthetic_canal_cord` — Concentric cylinders simulating spinal canal and cord
- `synthetic_label_map` — 16x16x16 volume with all 20 expected labels
- `voxel_1mm` — Standard 1mm isotropic voxel dimensions

### Cross-module consistency

`test_label_consistency.py` verifies that the label conventions (IDs 1-20, names, contiguity) are identical across:
- `validate_labels.EXPECTED_LABELS`
- `labels_to_surface.LABEL_NAMES`
- `prepare_nnunet_dataset.LABEL_MAP`

This catches drift if one module's labels are updated but others are not.

---

## What Is NOT Currently Tested

The following scripts and functionality are **not covered** by the current test suite because they depend on packages or resources not available in a minimal test environment.

### Scripts not tested

| Script | Reason | Dependencies |
|--------|--------|-------------|
| `run_synthseg.py` | Requires SynthSeg model weights + TensorFlow/PyTorch | SynthSeg |
| `run_totalspineseg.py` | Requires TotalSpineSeg model + nnU-Net runtime | totalspineseg, nnunetv2 |
| `register_brain_to_mni.py` | Requires ANTs registration engine | antspyx |
| `register_spine_to_mni.py` | Requires ANTs registration engine | antspyx |
| `labels_to_surface.py` | Requires marching cubes + mesh library | scikit-image, trimesh, nibabel |
| `clean_mesh.py` | Requires mesh processing library | pymeshlab |
| `merge_meshes.py` | Requires mesh library | trimesh |
| `export_unity.py` (CLI) | Requires mesh libraries (pure functions ARE tested) | trimesh, pymeshlab |
| `run_sct_pipeline.sh` | Requires Spinal Cord Toolbox installation | SCT |
| `train_nnunet.sh` | Requires nnU-Net + GPU | nnunetv2, torch |
| `download_*.sh` | Requires network access + external services | curl, openneuro-cli |
| `slicer_scripts/load_volumes.py` | Requires 3D Slicer runtime | slicer |

### NIfTI I/O round-trip tests

The click CLI commands (`main()` functions) that load/save NIfTI files via nibabel are not tested end-to-end. The core array logic IS tested, but the file I/O wrapper is not.

### Terraform / Infrastructure

The `infra/` Terraform modules have no automated tests. `terraform validate` and `terraform plan` are the recommended verification method.

### Unity / Web

The Unity project and web static site have no automated tests.

---

## Strategy for Testing What's Missing

### Tier 1: Add nibabel I/O tests (easy, high value)

Install nibabel in the test environment and add end-to-end CLI tests using `click.testing.CliRunner` with synthetic NIfTI files created via `nibabel.Nifti1Image`. This covers the full pipeline scripts (extract_csf_labels, compute_spinal_sas, validate_labels, join_craniospinal, resample_volume) reading and writing real `.nii.gz` files.

```python
nib = pytest.importorskip("nibabel")

def test_extract_csf_labels_cli(tmp_path):
    img = nib.Nifti1Image(synthetic_seg, np.eye(4))
    nib.save(img, str(tmp_path / "seg.nii.gz"))
    runner = CliRunner()
    result = runner.invoke(main, ["--input", str(tmp_path / "seg.nii.gz"), ...])
    assert result.exit_code == 0
    # Check output files exist and have correct shapes
```

**Effort:** Low. Add `pip install nibabel` to CI.

### Tier 2: Add mesh pipeline tests (moderate)

Install trimesh and scikit-image, then test `labels_to_surface.py` and `merge_meshes.py` end-to-end with small synthetic volumes (e.g., a 10x10x10 sphere). Verify the output mesh is non-empty and has expected topology.

```python
trimesh = pytest.importorskip("trimesh")
skimage = pytest.importorskip("skimage")

def test_sphere_produces_closed_mesh():
    # Create 20x20x20 volume with a sphere of label 1
    # Run marching cubes, verify mesh.is_watertight
```

**Effort:** Moderate. trimesh and scikit-image are pip-installable.

### Tier 3: Integration tests with real data (high value, high cost)

Download a small slice of the MGH 100um dataset (or create a realistic synthetic brain phantom) and run the full automated pipeline (Phases 2, 3, 5, 6) end-to-end. Store expected checksums for outputs.

This would require:
- A CI runner with GPU (or very patient CPU runs)
- ~1 GB of test data (can be stored in S3 and downloaded at CI time)
- SynthSeg, TotalSpineSeg, and ANTs installed

**Effort:** High. Best done as a nightly CI job, not per-commit.

### Tier 4: ML model smoke tests (low effort, high value)

For `run_synthseg.py` and `run_totalspineseg.py`, add smoke tests that verify:
- The import succeeds
- The model can be loaded (weights download)
- A tiny (8x8x8) volume can be processed without crashing

These don't validate correctness but catch installation and API-change breakages.

```python
synthseg = pytest.importorskip("SynthSeg")

def test_synthseg_loads():
    from SynthSeg.predict import predict
    # Just verify it doesn't crash on import
```

### Tier 5: Infrastructure tests

- `terraform validate` in CI to catch syntax errors
- `terraform plan` with a mock backend to catch resource misconfigurations
- HTML validation for `web/index.html`

### Recommended CI configuration

```yaml
# .github/workflows/test.yml
jobs:
  unit-tests:          # Tier 0: current tests, no extra deps
    runs-on: ubuntu-latest
    steps:
      - pip install numpy scipy click pytest
      - pytest tests/ -v

  nibabel-tests:       # Tier 1: add nibabel I/O tests
    runs-on: ubuntu-latest
    steps:
      - pip install nibabel numpy scipy click pytest
      - pytest tests/ -v -m "not needs_trimesh"

  mesh-tests:          # Tier 2: mesh pipeline
    runs-on: ubuntu-latest
    steps:
      - pip install nibabel trimesh scikit-image numpy scipy click pytest
      - pytest tests/ -v

  integration:         # Tier 3: full pipeline (nightly)
    runs-on: [self-hosted, gpu]
    schedule: cron('0 3 * * *')
    steps:
      - pip install -r requirements.txt
      - ./scripts/run_full_pipeline.sh --data-dir test_data/
```
