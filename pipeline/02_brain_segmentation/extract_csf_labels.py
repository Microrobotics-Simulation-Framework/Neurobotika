#!/usr/bin/env python3
"""Extract CSF-specific labels from a SynthSeg segmentation into separate binary masks."""

from pathlib import Path

import click
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


def extract_label_mask(seg: np.ndarray, label_ids: list[int]) -> np.ndarray:
    """Extract a binary mask for the given label IDs from a segmentation array."""
    return np.isin(seg, label_ids).astype(np.uint8)


def compute_volume_ml(mask: np.ndarray, voxel_zooms: tuple[float, ...]) -> float:
    """Compute volume in millilitres from a binary mask and voxel dimensions (in mm)."""
    voxel_vol_mm3 = float(np.prod(voxel_zooms[:3]))
    return float(mask.sum()) * voxel_vol_mm3 / 1000.0


def extract_all_csf_masks(
    seg: np.ndarray,
    csf_groups: dict | None = None,
) -> dict[str, np.ndarray]:
    """Extract binary masks for all CSF groups from a segmentation array.

    Returns a dict mapping group name -> binary uint8 mask, plus an
    "all_csf_combined" key with the union of all masks.
    """
    if csf_groups is None:
        csf_groups = CSF_GROUPS

    masks = {}
    combined = np.zeros_like(seg, dtype=np.uint8)

    for name, spec in csf_groups.items():
        mask = extract_label_mask(seg, spec["labels"])
        masks[name] = mask
        combined = np.maximum(combined, mask)

    masks["all_csf_combined"] = combined
    return masks


@click.command()
@click.option("--input", "input_path", required=True, help="SynthSeg label map (.nii.gz)")
@click.option("--output-dir", required=True, help="Directory for output masks")
@click.option("--combined/--no-combined", default=True, help="Also save a combined CSF mask")
def main(input_path: str, output_dir: str, combined: bool):
    """Extract CSF labels from SynthSeg output into separate binary masks."""
    import nibabel as nib

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading segmentation: {input_path}")
    img = nib.load(input_path)
    seg = np.asarray(img.dataobj, dtype=np.int32)
    voxel_zooms = img.header.get_zooms()[:3]

    masks = extract_all_csf_masks(seg)

    for name, mask in masks.items():
        if name == "all_csf_combined" and not combined:
            continue
        volume_ml = compute_volume_ml(mask, voxel_zooms)
        output_path = out / f"{name}.nii.gz"
        nib.save(nib.Nifti1Image(mask, img.affine, img.header), str(output_path))
        print(f"  {name}: {mask.sum()} voxels ({volume_ml:.1f} mL) -> {output_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
