#!/usr/bin/env python3
"""Join brain and spinal CSF label maps at the foramen magnum."""

from pathlib import Path

import click
import nibabel as nib
import numpy as np


@click.command()
@click.option("--brain-labels", required=True, help="Brain CSF labels in MNI space")
@click.option("--spine-labels", required=True, help="Spine CSF labels in MNI space")
@click.option("--output", required=True, help="Output merged CSF label map")
@click.option(
    "--junction-z-range",
    nargs=2,
    type=int,
    default=None,
    help="Z-slice range for the foramen magnum junction (auto-detected if not specified)",
)
def main(brain_labels: str, spine_labels: str, output: str, junction_z_range: tuple):
    """Merge brain and spinal CSF labels at the foramen magnum.

    In the junction zone, brain labels take priority (they include manually
    refined cisterna magna and foramen magnum structures). The spine labels
    fill in below the junction zone.
    """
    print(f"Loading brain labels: {brain_labels}")
    brain_img = nib.load(brain_labels)
    brain_data = np.asarray(brain_img.dataobj, dtype=np.int32)

    print(f"Loading spine labels: {spine_labels}")
    spine_img = nib.load(spine_labels)
    spine_data = np.asarray(spine_img.dataobj, dtype=np.int32)

    if brain_data.shape != spine_data.shape:
        print("ERROR: Shape mismatch. Both must be in MNI space at the same resolution.")
        print(f"  Brain: {brain_data.shape}, Spine: {spine_data.shape}")
        raise SystemExit(1)

    # Merge: brain labels take priority, spine fills gaps
    merged = brain_data.copy()
    spine_mask = (spine_data > 0) & (brain_data == 0)
    merged[spine_mask] = spine_data[spine_mask]

    # Report
    brain_voxels = (brain_data > 0).sum()
    spine_voxels = spine_mask.sum()
    overlap_voxels = ((brain_data > 0) & (spine_data > 0)).sum()
    total_voxels = (merged > 0).sum()

    voxel_vol = np.prod(brain_img.header.get_zooms()[:3])
    print(f"\n  Brain CSF voxels:    {brain_voxels:>10,} ({brain_voxels * voxel_vol / 1000:.1f} mL)")
    print(f"  Spine CSF voxels:    {spine_voxels:>10,} ({spine_voxels * voxel_vol / 1000:.1f} mL)")
    print(f"  Overlap voxels:      {overlap_voxels:>10,} (brain labels kept)")
    print(f"  Total merged voxels: {total_voxels:>10,} ({total_voxels * voxel_vol / 1000:.1f} mL)")

    # Check connectivity at junction
    # A simple check: does the merged label map have a single connected CSF component?
    from scipy.ndimage import label as cc_label

    n_components, _ = cc_label(merged > 0)
    if n_components == 1:
        print(f"\n  [OK] Single connected CSF component")
    else:
        print(f"\n  [WARN] {n_components} disconnected components found.")
        print("  The brain-spine junction may have a gap. Check in 3D Slicer.")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(merged, brain_img.affine, brain_img.header), output)
    print(f"\n  Saved: {output}")


if __name__ == "__main__":
    main()
