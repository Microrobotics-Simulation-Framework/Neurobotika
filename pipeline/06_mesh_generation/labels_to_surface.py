#!/usr/bin/env python3
"""Extract 3D surface meshes from a CSF label map using marching cubes."""

from pathlib import Path

import click
import nibabel as nib
import numpy as np
import trimesh
from scipy.ndimage import gaussian_filter


# Label mapping (must match manual-segmentation-guide.md)
LABEL_NAMES = {
    1: "lateral_ventricle_left",
    2: "lateral_ventricle_right",
    3: "third_ventricle",
    4: "aqueduct",
    5: "fourth_ventricle",
    6: "foramen_monro_left",
    7: "foramen_monro_right",
    8: "foramen_magendie",
    9: "foramen_luschka_left",
    10: "foramen_luschka_right",
    11: "cisterna_magna",
    12: "prepontine_cistern",
    13: "ambient_cistern",
    14: "quadrigeminal_cistern",
    15: "interpeduncular_cistern",
    16: "sylvian_cistern",
    17: "cerebral_sas",
    18: "spinal_sas",
    19: "foramen_magnum_junction",
    20: "choroid_plexus",
}


@click.command()
@click.option("--input", "input_path", required=True, help="CSF label map NIfTI file")
@click.option("--output-dir", required=True, help="Output directory for STL files")
@click.option("--smooth-sigma", default=0.5, type=float, help="Gaussian smoothing sigma before marching cubes (voxels)")
@click.option("--per-structure/--combined-only", default=True, help="Export per-structure meshes")
def main(input_path: str, output_dir: str, smooth_sigma: float, per_structure: bool):
    """Extract surfaces from label map using marching cubes."""
    from skimage.measure import marching_cubes

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {input_path}")
    img = nib.load(input_path)
    data = np.asarray(img.dataobj, dtype=np.int32)
    affine = img.affine

    # Combined CSF surface
    print("\nExtracting combined CSF surface...")
    binary = (data > 0).astype(np.float32)
    if smooth_sigma > 0:
        binary = gaussian_filter(binary, sigma=smooth_sigma)
    verts, faces, normals, _ = marching_cubes(binary, level=0.5, spacing=img.header.get_zooms()[:3])
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)
    combined_path = out / "all_csf.stl"
    mesh.export(str(combined_path))
    print(f"  all_csf: {len(mesh.faces):,} faces -> {combined_path}")

    # Per-structure surfaces
    if per_structure:
        for label_id, name in LABEL_NAMES.items():
            mask = (data == label_id).astype(np.float32)
            if mask.sum() == 0:
                print(f"  {name}: no voxels, skipping")
                continue

            if smooth_sigma > 0:
                mask = gaussian_filter(mask, sigma=smooth_sigma)

            try:
                verts, faces, normals, _ = marching_cubes(
                    mask, level=0.5, spacing=img.header.get_zooms()[:3]
                )
                mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)
                mesh_path = out / f"{name}.stl"
                mesh.export(str(mesh_path))
                print(f"  {name}: {len(mesh.faces):,} faces -> {mesh_path}")
            except Exception as e:
                print(f"  {name}: marching cubes failed ({e})")

    print(f"\nDone. Surfaces in: {output_dir}")


if __name__ == "__main__":
    main()
