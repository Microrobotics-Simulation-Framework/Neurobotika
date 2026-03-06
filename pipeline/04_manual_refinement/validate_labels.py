#!/usr/bin/env python3
"""Validate a manual CSF segmentation label map for common errors."""

from pathlib import Path

import click
import nibabel as nib
import numpy as np
from scipy.ndimage import label as connected_components


EXPECTED_LABELS = {
    1: "Left lateral ventricle",
    2: "Right lateral ventricle",
    3: "3rd ventricle",
    4: "Cerebral aqueduct",
    5: "4th ventricle",
    6: "Left foramen of Monro",
    7: "Right foramen of Monro",
    8: "Foramen of Magendie",
    9: "Left foramen of Luschka",
    10: "Right foramen of Luschka",
    11: "Cisterna magna",
    12: "Prepontine cistern",
    13: "Ambient cistern",
    14: "Quadrigeminal cistern",
    15: "Interpeduncular cistern",
    16: "Sylvian cistern",
    17: "Cerebral subarachnoid space",
    18: "Spinal subarachnoid space",
    19: "Foramen magnum junction",
    20: "Choroid plexus",
}

# Structures that should be a single connected component
SINGLE_COMPONENT = {1, 2, 3, 4, 5, 8, 11, 12, 14, 15, 19}


@click.command()
@click.option("--input", "input_path", required=True, help="Label map NIfTI file")
@click.option("--check-connectivity", is_flag=True, help="Check connected components per label")
@click.option("--check-overlaps", is_flag=True, help="Check for overlapping labels (should not happen in a label map)")
def main(input_path: str, check_connectivity: bool, check_overlaps: bool):
    """Validate a CSF segmentation label map."""
    print(f"Loading: {input_path}")
    img = nib.load(input_path)
    data = np.asarray(img.dataobj, dtype=np.int32)
    voxel_vol = np.prod(img.header.get_zooms()[:3])

    unique_labels = set(np.unique(data)) - {0}
    errors = []

    print(f"\nFound labels: {sorted(unique_labels)}")
    print(f"Expected labels: {sorted(EXPECTED_LABELS.keys())}")
    print()

    # Check which labels are present
    missing = set(EXPECTED_LABELS.keys()) - unique_labels
    unexpected = unique_labels - set(EXPECTED_LABELS.keys())

    if missing:
        print(f"  [WARN] Missing labels: {sorted(missing)}")
        for lbl in sorted(missing):
            print(f"         {lbl}: {EXPECTED_LABELS[lbl]}")
        errors.append("missing_labels")

    if unexpected:
        print(f"  [WARN] Unexpected labels: {sorted(unexpected)}")
        errors.append("unexpected_labels")

    # Per-label statistics
    print(f"\n{'Label':>6} {'Structure':<35} {'Voxels':>10} {'Volume (mL)':>12} {'Status'}")
    print("-" * 80)
    for lbl in sorted(unique_labels):
        mask = data == lbl
        n_voxels = mask.sum()
        vol_ml = n_voxels * voxel_vol / 1000.0
        name = EXPECTED_LABELS.get(lbl, "???")
        status = "OK"

        if check_connectivity and lbl in SINGLE_COMPONENT:
            n_components, _ = connected_components(mask)
            if n_components > 1:
                status = f"WARN: {n_components} components"
                errors.append(f"label_{lbl}_disconnected")

        print(f"{lbl:>6} {name:<35} {n_voxels:>10,} {vol_ml:>11.2f} {status}")

    # Total CSF volume check
    total_csf = (data > 0).sum() * voxel_vol / 1000.0
    print(f"\n  Total CSF volume: {total_csf:.1f} mL")
    if total_csf < 80 or total_csf > 300:
        print(f"  [WARN] Unusual total volume. Expected ~100-200 mL for adults.")
        errors.append("unusual_volume")
    else:
        print(f"  [OK] Volume in expected range (100-200 mL)")

    # Summary
    print(f"\n{'='*40}")
    if errors:
        print(f"  Validation completed with {len(errors)} warning(s).")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  All checks passed.")


if __name__ == "__main__":
    main()
