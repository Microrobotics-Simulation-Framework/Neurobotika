#!/usr/bin/env python3
"""Register brain volume and labels to MNI152 standard space using ANTs."""

from pathlib import Path

import click


@click.command()
@click.option("--brain-volume", required=True, help="Brain MRI volume (moving image)")
@click.option("--brain-labels", required=True, help="Brain CSF label map to warp")
@click.option("--output-dir", required=True, help="Output directory")
@click.option("--mni-template", default=None, help="MNI152 template (auto-downloaded if not provided)")
def main(brain_volume: str, brain_labels: str, output_dir: str, mni_template: str):
    """Register brain to MNI space and warp labels."""
    import ants

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Load MNI template
    if mni_template:
        fixed = ants.image_read(mni_template)
    else:
        print("Using ANTs built-in MNI template...")
        fixed = ants.get_ants_data("mni")
        fixed = ants.image_read(fixed)

    # Load brain volume
    print(f"Loading brain volume: {brain_volume}")
    moving = ants.image_read(brain_volume)

    # Run SyN registration
    print("Running SyN registration (this may take a while)...")
    reg = ants.registration(
        fixed=fixed,
        moving=moving,
        type_of_transform="SyN",
        syn_metric="CC",
        syn_sampling=2,
        verbose=True,
    )

    # Save the warped brain volume
    warped_brain = reg["warpedmovout"]
    ants.image_write(warped_brain, str(out / "brain_mni_volume.nii.gz"))
    print(f"  Warped brain volume: {out / 'brain_mni_volume.nii.gz'}")

    # Apply the transform to the label map (use nearest-neighbor interpolation)
    print(f"Warping labels: {brain_labels}")
    labels = ants.image_read(brain_labels)
    warped_labels = ants.apply_transforms(
        fixed=fixed,
        moving=labels,
        transformlist=reg["fwdtransforms"],
        interpolator="nearestNeighbor",
    )
    ants.image_write(warped_labels, str(out / "brain_mni.nii.gz"))
    print(f"  Warped labels: {out / 'brain_mni.nii.gz'}")

    # Save transform files for reference
    for i, tf in enumerate(reg["fwdtransforms"]):
        print(f"  Forward transform [{i}]: {tf}")
    for i, tf in enumerate(reg["invtransforms"]):
        print(f"  Inverse transform [{i}]: {tf}")

    print("\nRegistration complete.")


if __name__ == "__main__":
    main()
