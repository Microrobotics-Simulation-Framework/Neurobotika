#!/usr/bin/env python3
"""Register spinal segmentation to MNI space via PAM50 template."""

from pathlib import Path

import click


@click.command()
@click.option("--spine-volume", required=True, help="Spinal MRI volume")
@click.option("--spine-labels", required=True, help="Spinal SAS label map")
@click.option("--output-dir", required=True, help="Output directory")
@click.option("--pam50-to-mni-warp", default=None, help="Pre-computed PAM50-to-MNI warp (optional)")
def main(spine_volume: str, spine_labels: str, output_dir: str, pam50_to_mni_warp: str):
    """Register spinal labels to MNI space.

    Strategy:
    1. Register spine to PAM50 (using SCT's warp from Phase 3, or recompute)
    2. Apply PAM50-to-MNI transform
    3. Result: spine labels in MNI space, ready to merge with brain labels
    """
    import ants

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading spine volume: {spine_volume}")
    moving = ants.image_read(spine_volume)

    print(f"Loading spine labels: {spine_labels}")
    labels = ants.image_read(spine_labels)

    # If SCT warp files exist from Phase 3, use them
    # Otherwise, do a direct spine-to-MNI registration
    print("Running spine-to-MNI registration...")
    print("(For better results, use SCT's PAM50 warp from Phase 3 as intermediate)")

    # Direct registration to MNI (simplified — production should use PAM50 intermediate)
    mni_path = ants.get_ants_data("mni")
    fixed = ants.image_read(mni_path)

    reg = ants.registration(
        fixed=fixed,
        moving=moving,
        type_of_transform="SyN",
        verbose=True,
    )

    warped_labels = ants.apply_transforms(
        fixed=fixed,
        moving=labels,
        transformlist=reg["fwdtransforms"],
        interpolator="nearestNeighbor",
    )

    ants.image_write(warped_labels, str(out / "spine_mni.nii.gz"))
    print(f"  Warped spine labels: {out / 'spine_mni.nii.gz'}")

    print("\nSpine registration complete.")


if __name__ == "__main__":
    main()
