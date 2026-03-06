#!/usr/bin/env python3
"""Compute spinal subarachnoid space as the boolean difference: canal - cord."""

from pathlib import Path

import click
import numpy as np


def compute_sas(canal_data: np.ndarray, cord_data: np.ndarray) -> np.ndarray:
    """Compute spinal SAS as the boolean difference: canal AND NOT cord.

    Both inputs should be boolean or binary arrays of the same shape.
    Returns a uint8 binary mask.

    Raises ValueError if shapes don't match.
    """
    if canal_data.shape != cord_data.shape:
        raise ValueError(
            f"Shape mismatch: canal {canal_data.shape} vs cord {cord_data.shape}"
        )
    canal_bool = np.asarray(canal_data, dtype=bool)
    cord_bool = np.asarray(cord_data, dtype=bool)
    return (canal_bool & ~cord_bool).astype(np.uint8)


def compute_volume_ml(mask: np.ndarray, voxel_zooms: tuple[float, ...]) -> float:
    """Compute volume in mL from a binary mask and voxel dimensions in mm."""
    return float(mask.sum()) * float(np.prod(voxel_zooms[:3])) / 1000.0


@click.command()
@click.option("--canal", required=True, help="Spinal canal mask NIfTI file")
@click.option("--cord", required=True, help="Spinal cord mask NIfTI file")
@click.option("--output", required=True, help="Output spinal SAS mask NIfTI file")
def main(canal: str, cord: str, output: str):
    """Compute spinal SAS = canal mask - cord mask."""
    import nibabel as nib

    print(f"Loading canal: {canal}")
    canal_img = nib.load(canal)
    canal_data = np.asarray(canal_img.dataobj) > 0

    print(f"Loading cord: {cord}")
    cord_img = nib.load(cord)
    cord_data = np.asarray(cord_img.dataobj) > 0

    try:
        sas = compute_sas(canal_data, cord_data)
    except ValueError as e:
        print(f"ERROR: {e}")
        print("The volumes must be in the same space. Register them first.")
        raise SystemExit(1)

    voxel_zooms = canal_img.header.get_zooms()[:3]
    print(f"  Canal volume:  {compute_volume_ml(canal_data, voxel_zooms):.1f} mL")
    print(f"  Cord volume:   {compute_volume_ml(cord_data, voxel_zooms):.1f} mL")
    print(f"  SAS volume:    {compute_volume_ml(sas, voxel_zooms):.1f} mL")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(sas, canal_img.affine, canal_img.header), output)
    print(f"  Saved: {output}")


if __name__ == "__main__":
    main()
