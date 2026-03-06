#!/usr/bin/env python3
"""Resample a NIfTI volume to a target isotropic resolution."""

from pathlib import Path

import click
import numpy as np
from scipy.ndimage import zoom


def compute_zoom_factors(
    current_zooms: tuple[float, ...],
    target_resolution: float,
) -> list[float]:
    """Compute zoom factors to resample from current voxel size to target isotropic resolution."""
    return [cz / target_resolution for cz in current_zooms[:3]]


def update_affine(affine: np.ndarray, zoom_factors: list[float]) -> np.ndarray:
    """Update a 4x4 affine matrix to reflect new voxel sizes after resampling."""
    new_affine = affine.copy()
    for i in range(3):
        new_affine[:3, i] = new_affine[:3, i] / zoom_factors[i]
    return new_affine


def resample_array(
    data: np.ndarray,
    zoom_factors: list[float],
    order: int = 3,
) -> np.ndarray:
    """Resample a 3D array using scipy.ndimage.zoom."""
    return zoom(data, zoom_factors, order=order)


@click.command()
@click.option("--input", "input_path", required=True, help="Input NIfTI file")
@click.option("--output", "output_path", required=True, help="Output NIfTI file")
@click.option(
    "--target-resolution",
    default=1.0,
    type=float,
    help="Target isotropic resolution in mm (default: 1.0)",
)
@click.option("--order", default=3, type=int, help="Spline interpolation order (default: 3)")
def main(input_path: str, output_path: str, target_resolution: float, order: int):
    """Resample a NIfTI volume to isotropic resolution for SynthSeg input."""
    import nibabel as nib

    print(f"Loading: {input_path}")
    img = nib.load(input_path)
    data = img.get_fdata()
    current_zooms = img.header.get_zooms()[:3]

    print(f"  Current shape: {data.shape}")
    print(f"  Current voxel size: {current_zooms}")

    zf = compute_zoom_factors(current_zooms, target_resolution)
    print(f"  Zoom factors: {[f'{z:.3f}' for z in zf]}")

    resampled = resample_array(data, zf, order=order)
    print(f"  Resampled shape: {resampled.shape}")

    new_affine = update_affine(img.affine, zf)

    new_img = nib.Nifti1Image(resampled.astype(np.float32), new_affine)
    new_img.header.set_zooms([target_resolution] * 3)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    nib.save(new_img, output_path)
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    main()
