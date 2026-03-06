#!/usr/bin/env python3
"""Extract CSF-specific labels from a SynthSeg segmentation into separate binary masks."""

from pathlib import Path

import click
import nibabel as nib
import numpy as np


# SynthSeg labels (FreeSurfer aseg convention) relevant to CSF
CSF_GROUPS = {
    "lateral_ventricles": {
        "labels": [4, 5, 43, 44],
        "description": "Left + Right lateral ventricles (including inferior horns)",
    },
    "third_ventricle": {
        "labels": [14],
        "description": "Third ventricle",
    },
    "fourth_ventricle": {
        "labels": [15],
        "description": "Fourth ventricle",
    },
    "extraventricular_csf": {
        "labels": [24],
        "description": "Extraventricular CSF (subarachnoid space)",
    },
    "choroid_plexus": {
        "labels": [31, 63],
        "description": "Left + Right choroid plexus",
    },
}


@click.command()
@click.option("--input", "input_path", required=True, help="SynthSeg label map (.nii.gz)")
@click.option("--output-dir", required=True, help="Directory for output masks")
@click.option("--combined/--no-combined", default=True, help="Also save a combined CSF mask")
def main(input_path: str, output_dir: str, combined: bool):
    """Extract CSF labels from SynthSeg output into separate binary masks."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading segmentation: {input_path}")
    img = nib.load(input_path)
    seg = np.asarray(img.dataobj, dtype=np.int32)

    all_csf = np.zeros_like(seg, dtype=np.uint8)

    for name, spec in CSF_GROUPS.items():
        mask = np.isin(seg, spec["labels"]).astype(np.uint8)
        voxel_count = mask.sum()
        volume_ml = voxel_count * np.prod(img.header.get_zooms()[:3]) / 1000.0

        output_path = out / f"{name}.nii.gz"
        nib.save(nib.Nifti1Image(mask, img.affine, img.header), str(output_path))
        print(f"  {name}: {voxel_count} voxels ({volume_ml:.1f} mL) -> {output_path}")

        all_csf = np.maximum(all_csf, mask)

    if combined:
        combined_path = out / "all_csf_combined.nii.gz"
        nib.save(nib.Nifti1Image(all_csf, img.affine, img.header), str(combined_path))
        total_ml = all_csf.sum() * np.prod(img.header.get_zooms()[:3]) / 1000.0
        print(f"  all_csf_combined: {all_csf.sum()} voxels ({total_ml:.1f} mL) -> {combined_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
