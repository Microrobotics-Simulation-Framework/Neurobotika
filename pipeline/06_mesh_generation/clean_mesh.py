#!/usr/bin/env python3
"""Clean a 3D surface mesh: remove artifacts, smooth, and optionally decimate."""

from pathlib import Path

import click
import pymeshlab


@click.command()
@click.option("--input", "input_path", required=True, help="Input mesh file (STL, OBJ, PLY)")
@click.option("--output", "output_path", required=True, help="Output mesh file")
@click.option("--smooth-iterations", default=30, type=int, help="Laplacian smoothing iterations")
@click.option("--decimate-target", default=None, type=int, help="Target face count for decimation (skip if not set)")
@click.option("--fill-holes", is_flag=True, default=True, help="Fill small holes")
def main(input_path: str, output_path: str, smooth_iterations: int, decimate_target: int, fill_holes: bool):
    """Clean a surface mesh for use in Unity or simulation."""
    ms = pymeshlab.MeshSet()

    print(f"Loading: {input_path}")
    ms.load_new_mesh(input_path)
    mesh = ms.current_mesh()
    print(f"  Vertices: {mesh.vertex_number():,}, Faces: {mesh.face_number():,}")

    # Remove duplicate vertices and faces
    print("  Removing duplicates...")
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()

    # Remove unreferenced vertices
    ms.meshing_remove_unreferenced_vertices()

    # Remove self-intersecting faces
    print("  Removing self-intersections...")
    ms.meshing_repair_non_manifold_edges()
    ms.meshing_repair_non_manifold_vertices()

    # Fill holes
    if fill_holes:
        print("  Filling holes...")
        ms.meshing_close_holes(maxholesize=100)

    # Smooth
    if smooth_iterations > 0:
        print(f"  Laplacian smoothing ({smooth_iterations} iterations)...")
        ms.apply_coord_laplacian_smoothing(stepsmoothnum=smooth_iterations)

    # Decimate
    if decimate_target and mesh.face_number() > decimate_target:
        print(f"  Decimating to {decimate_target:,} faces...")
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=decimate_target)

    mesh = ms.current_mesh()
    print(f"  Final: {mesh.vertex_number():,} vertices, {mesh.face_number():,} faces")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    ms.save_current_mesh(output_path)
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    main()
