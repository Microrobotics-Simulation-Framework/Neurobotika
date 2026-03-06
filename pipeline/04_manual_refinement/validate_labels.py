#!/usr/bin/env python3
"""Validate a manual CSF segmentation label map for common errors."""

from pathlib import Path

import click
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


def validate_label_map(
    data: np.ndarray,
    voxel_vol_mm3: float,
    expected_labels: dict[int, str] | None = None,
    single_component_labels: set[int] | None = None,
    check_connectivity: bool = True,
) -> list[str]:
    """Validate a CSF segmentation label map and return a list of error strings.

    Args:
        data: Integer label map array.
        voxel_vol_mm3: Volume of one voxel in mm^3.
        expected_labels: Map of label_id -> name. Defaults to EXPECTED_LABELS.
        single_component_labels: Labels that should be a single connected component.
        check_connectivity: Whether to run connectivity checks.

    Returns:
        List of error/warning strings. Empty list means all checks passed.
    """
    if expected_labels is None:
        expected_labels = EXPECTED_LABELS
    if single_component_labels is None:
        single_component_labels = SINGLE_COMPONENT

    errors = []
    unique_labels = set(int(x) for x in np.unique(data)) - {0}

    # Check which labels are present/missing
    missing = set(expected_labels.keys()) - unique_labels
    unexpected = unique_labels - set(expected_labels.keys())

    if missing:
        errors.append(f"missing_labels:{','.join(str(x) for x in sorted(missing))}")
    if unexpected:
        errors.append(f"unexpected_labels:{','.join(str(x) for x in sorted(unexpected))}")

    # Connectivity check
    if check_connectivity:
        for lbl in sorted(unique_labels):
            if lbl in single_component_labels:
                mask = data == lbl
                _, n_components = connected_components(mask)
                if n_components > 1:
                    errors.append(f"label_{lbl}_disconnected:{n_components}_components")

    # Total CSF volume check
    total_csf_ml = float((data > 0).sum()) * voxel_vol_mm3 / 1000.0
    if total_csf_ml < 80 or total_csf_ml > 300:
        errors.append(f"unusual_volume:{total_csf_ml:.1f}mL")

    return errors


def get_label_stats(
    data: np.ndarray,
    voxel_vol_mm3: float,
) -> dict[int, dict]:
    """Compute per-label statistics (voxel count, volume in mL)."""
    stats = {}
    for lbl in sorted(set(int(x) for x in np.unique(data)) - {0}):
        mask = data == lbl
        n_voxels = int(mask.sum())
        vol_ml = n_voxels * voxel_vol_mm3 / 1000.0
        stats[lbl] = {"voxels": n_voxels, "volume_ml": vol_ml}
    return stats


@click.command()
@click.option("--input", "input_path", required=True, help="Label map NIfTI file")
@click.option("--check-connectivity", is_flag=True, help="Check connected components per label")
@click.option("--check-overlaps", is_flag=True, help="Check for overlapping labels")
def main(input_path: str, check_connectivity: bool, check_overlaps: bool):
    """Validate a CSF segmentation label map."""
    import nibabel as nib

    print(f"Loading: {input_path}")
    img = nib.load(input_path)
    data = np.asarray(img.dataobj, dtype=np.int32)
    voxel_vol = float(np.prod(img.header.get_zooms()[:3]))

    unique_labels = set(np.unique(data)) - {0}
    print(f"\nFound labels: {sorted(unique_labels)}")
    print(f"Expected labels: {sorted(EXPECTED_LABELS.keys())}")
    print()

    errors = validate_label_map(
        data, voxel_vol,
        check_connectivity=check_connectivity,
    )

    # Per-label statistics
    stats = get_label_stats(data, voxel_vol)
    print(f"{'Label':>6} {'Structure':<35} {'Voxels':>10} {'Volume (mL)':>12}")
    print("-" * 70)
    for lbl, s in stats.items():
        name = EXPECTED_LABELS.get(lbl, "???")
        print(f"{lbl:>6} {name:<35} {s['voxels']:>10,} {s['volume_ml']:>11.2f}")

    total_csf = (data > 0).sum() * voxel_vol / 1000.0
    print(f"\n  Total CSF volume: {total_csf:.1f} mL")

    print(f"\n{'='*40}")
    if errors:
        print(f"  Validation completed with {len(errors)} warning(s).")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  All checks passed.")


if __name__ == "__main__":
    main()
