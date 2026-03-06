#!/usr/bin/env python3
"""Export mesh in Unity-compatible formats (.glb) with LOD variants."""

import subprocess
from pathlib import Path

import click
import pymeshlab
import trimesh


@click.command()
@click.option("--input", "input_path", required=True, help="Input mesh file (STL, OBJ, PLY)")
@click.option("--output-dir", required=True, help="Output directory")
@click.option("--lod-levels", default=3, type=int, help="Number of LOD levels (default: 3)")
@click.option("--upload-s3", default=None, help="S3 URI to upload results (optional)")
def main(input_path: str, output_dir: str, lod_levels: int, upload_s3: str):
    """Export mesh as GLB with LOD variants for Unity WebGL."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading: {input_path}")
    mesh = trimesh.load(input_path)
    original_faces = len(mesh.faces)
    print(f"  Original: {len(mesh.vertices):,} vertices, {original_faces:,} faces")

    # LOD decimation ratios
    lod_ratios = [1.0]  # LOD0 = full resolution
    if lod_levels >= 2:
        lod_ratios.append(0.5)  # LOD1 = 50%
    if lod_levels >= 3:
        lod_ratios.append(0.1)  # LOD2 = 10%
    for i in range(3, lod_levels):
        lod_ratios.append(0.1 / (2 ** (i - 2)))  # Further LODs halve each time

    exported = []
    for i, ratio in enumerate(lod_ratios):
        target_faces = max(int(original_faces * ratio), 100)
        output_file = out / f"csf_system_lod{i}.glb"

        if ratio < 1.0:
            # Decimate using pymeshlab
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(input_path)
            ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target_faces)
            # Export to temp STL then convert to GLB via trimesh
            temp_stl = out / f"_temp_lod{i}.stl"
            ms.save_current_mesh(str(temp_stl))
            lod_mesh = trimesh.load(str(temp_stl))
            temp_stl.unlink()
        else:
            lod_mesh = mesh

        lod_mesh.export(str(output_file))
        print(f"  LOD{i}: {len(lod_mesh.faces):,} faces ({ratio:.0%}) -> {output_file.name}")
        exported.append(output_file)

    # Upload to S3 if requested
    if upload_s3:
        print(f"\nUploading to {upload_s3}...")
        for f in exported:
            s3_dest = f"{upload_s3.rstrip('/')}/{f.name}"
            subprocess.run(["aws", "s3", "cp", str(f), s3_dest], check=True)
            print(f"  Uploaded: {s3_dest}")

    print("\nDone.")


if __name__ == "__main__":
    main()
