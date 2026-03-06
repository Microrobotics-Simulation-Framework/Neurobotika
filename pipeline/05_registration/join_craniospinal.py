#!/usr/bin/env python3
"""Join brain and spinal CSF label maps at the foramen magnum."""

from pathlib import Path

import click
import numpy as np


def merge_brain_spine(
    brain_data: np.ndarray,
    spine_data: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Merge brain and spinal CSF label maps. Brain labels take priority.

    Args:
        brain_data: Integer label map from brain segmentation.
        spine_data: Integer label map from spine segmentation.

    Returns:
        Tuple of (merged label map, stats dict with voxel counts).

    Raises:
        ValueError if shapes don't match.
    """
    if brain_data.shape != spine_data.shape:
        raise ValueError(
            f"Shape mismatch: brain {brain_data.shape} vs spine {spine_data.shape}"
        )

    merged = brain_data.copy()
    spine_fills = (spine_data > 0) & (brain_data == 0)
    merged[spine_fills] = spine_data[spine_fills]

    stats = {
        "brain_voxels": int((brain_data > 0).sum()),
        "spine_voxels": int(spine_fills.sum()),
        "overlap_voxels": int(((brain_data > 0) & (spine_data > 0)).sum()),
        "total_voxels": int((merged > 0).sum()),
    }

    return merged, stats


def check_connectivity(data: np.ndarray) -> int:
    """Count the number of connected components in a binary mask."""
    from scipy.ndimage import label as cc_label
    _, n_components = cc_label(data > 0)
    return n_components


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
    """Merge brain and spinal CSF labels at the foramen magnum."""
    import nibabel as nib

    print(f"Loading brain labels: {brain_labels}")
    brain_img = nib.load(brain_labels)
    brain_data = np.asarray(brain_img.dataobj, dtype=np.int32)

    print(f"Loading spine labels: {spine_labels}")
    spine_img = nib.load(spine_labels)
    spine_data = np.asarray(spine_img.dataobj, dtype=np.int32)

    try:
        merged, stats = merge_brain_spine(brain_data, spine_data)
    except ValueError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)

    voxel_vol = float(np.prod(brain_img.header.get_zooms()[:3]))
    for key, val in stats.items():
        vol = val * voxel_vol / 1000.0
        print(f"  {key}: {val:>10,} ({vol:.1f} mL)")

    n_components = check_connectivity(merged)
    if n_components == 1:
        print(f"\n  [OK] Single connected CSF component")
    else:
        print(f"\n  [WARN] {n_components} disconnected components found.")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(merged, brain_img.affine, brain_img.header), output)
    print(f"\n  Saved: {output}")


if __name__ == "__main__":
    main()
