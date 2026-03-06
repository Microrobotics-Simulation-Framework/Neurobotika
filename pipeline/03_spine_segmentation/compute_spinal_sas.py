#!/usr/bin/env python3
"""Compute spinal subarachnoid space as the boolean difference: canal - cord."""

from pathlib import Path

import click
import nibabel as nib
import numpy as np


@click.command()
@click.option("--canal", required=True, help="Spinal canal mask NIfTI file")
@click.option("--cord", required=True, help="Spinal cord mask NIfTI file")
@click.option("--output", required=True, help="Output spinal SAS mask NIfTI file")
def main(canal: str, cord: str, output: str):
    """Compute spinal SAS = canal mask - cord mask."""
    print(f"Loading canal: {canal}")
    canal_img = nib.load(canal)
    canal_data = np.asarray(canal_img.dataobj) > 0

    print(f"Loading cord: {cord}")
    cord_img = nib.load(cord)
    cord_data = np.asarray(cord_img.dataobj) > 0

    if canal_data.shape != cord_data.shape:
        print(f"ERROR: Shape mismatch — canal {canal_data.shape} vs cord {cord_data.shape}")
        print("The volumes must be in the same space. Register them first.")
        raise SystemExit(1)

    sas = (canal_data & ~cord_data).astype(np.uint8)

    voxel_vol = np.prod(canal_img.header.get_zooms()[:3])
    canal_vol_ml = canal_data.sum() * voxel_vol / 1000.0
    cord_vol_ml = cord_data.sum() * voxel_vol / 1000.0
    sas_vol_ml = sas.sum() * voxel_vol / 1000.0

    print(f"  Canal volume:  {canal_vol_ml:.1f} mL")
    print(f"  Cord volume:   {cord_vol_ml:.1f} mL")
    print(f"  SAS volume:    {sas_vol_ml:.1f} mL")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(sas, canal_img.affine, canal_img.header), output)
    print(f"  Saved: {output}")


if __name__ == "__main__":
    main()
