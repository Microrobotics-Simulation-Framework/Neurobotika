# Phase 6: Mesh Generation

Converts the final merged CSF label map into 3D surface meshes, cleans them, and assembles a watertight mesh suitable for Unity import.

## Pipeline

```
csf_complete.nii.gz (label map)
        │
        ▼
labels_to_surface.py    →  per-structure STL surfaces
        │
        ▼
clean_mesh.py           →  cleaned, smoothed, decimated meshes
        │
        ▼
merge_meshes.py         →  single watertight CSF mesh
        │
        ▼
export_unity.py         →  .glb/.fbx with LOD variants → upload to S3
```

## Scripts

### `labels_to_surface.py`

Extracts 3D surfaces from a label map using marching cubes. Produces one STL per structure, plus a combined surface for all CSF.

```bash
python labels_to_surface.py \
    --input data/segmentations/merged/csf_complete.nii.gz \
    --output-dir data/meshes/surfaces/
```

### `clean_mesh.py`

Cleans a surface mesh: removes self-intersections, fills holes, applies Laplacian smoothing, and optionally decimates to a target face count.

```bash
python clean_mesh.py \
    --input data/meshes/surfaces/all_csf.stl \
    --output data/meshes/cleaned/all_csf_clean.stl \
    --smooth-iterations 50 \
    --decimate-target 500000
```

### `merge_meshes.py`

Performs boolean union of multiple mesh components into a single watertight mesh. Useful if per-structure meshes need to be merged rather than the combined label extraction.

```bash
python merge_meshes.py \
    --input-dir data/meshes/cleaned/ \
    --output data/meshes/final/csf_system.stl
```

### `export_unity.py`

Exports the final mesh in formats suitable for Unity (.glb, .fbx) and generates LOD variants at different decimation levels. Optionally uploads to S3.

```bash
python export_unity.py \
    --input data/meshes/final/csf_system.stl \
    --output-dir data/meshes/final/ \
    --lod-levels 3 \
    --upload-s3 s3://neurobotika-public/meshes/
```

**Produces:**
- `csf_system_lod0.glb` — Full resolution
- `csf_system_lod1.glb` — 50% decimation
- `csf_system_lod2.glb` — 10% decimation

## Output

```
data/meshes/
├── surfaces/                    # Raw marching cubes output
│   ├── lateral_ventricles.stl
│   ├── third_ventricle.stl
│   ├── aqueduct.stl
│   ├── fourth_ventricle.stl
│   ├── ...
│   └── all_csf.stl
├── cleaned/                     # After cleaning
│   └── all_csf_clean.stl
└── final/                       # Unity-ready
    ├── csf_system_lod0.glb
    ├── csf_system_lod1.glb
    └── csf_system_lod2.glb
```

## Mesh Quality Notes

- The marching cubes output will have staircase artifacts from voxel boundaries. Smoothing helps but be careful not to over-smooth small structures (aqueduct, foramina).
- For foramina, consider using a smaller smoothing kernel or no smoothing to preserve the narrow channel geometry.
- The final mesh should be watertight (no holes, no self-intersections) for proper rendering in Unity and potential future CFD simulation use.
