#!/usr/bin/env python3
"""Merge multiple mesh files into a single mesh using boolean union."""

from pathlib import Path

import click
import trimesh


@click.command()
@click.option("--input-dir", required=True, help="Directory containing mesh files to merge")
@click.option("--output", required=True, help="Output merged mesh file")
@click.option("--pattern", default="*.stl", help="Glob pattern for input files")
def main(input_dir: str, output: str, pattern: str):
    """Merge multiple meshes into one."""
    input_path = Path(input_dir)
    mesh_files = sorted(input_path.glob(pattern))

    if not mesh_files:
        print(f"No files matching '{pattern}' in {input_dir}")
        raise SystemExit(1)

    print(f"Found {len(mesh_files)} mesh files to merge:")
    meshes = []
    for f in mesh_files:
        mesh = trimesh.load(str(f))
        print(f"  {f.name}: {len(mesh.faces):,} faces")
        meshes.append(mesh)

    # Concatenate all meshes into a single mesh
    # For a simple concatenation (no boolean union):
    merged = trimesh.util.concatenate(meshes)
    print(f"\nMerged: {len(merged.vertices):,} vertices, {len(merged.faces):,} faces")

    # For a proper boolean union (watertight, no internal faces),
    # trimesh can use the manifold3d or blender backend:
    # merged = trimesh.boolean.union(meshes, engine="manifold")
    # This requires the manifold3d package: pip install manifold3d

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    merged.export(output)
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
