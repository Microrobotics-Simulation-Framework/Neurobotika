#!/usr/bin/env python3
"""Run SynthSeg brain segmentation (standalone, no FreeSurfer required)."""

from pathlib import Path

import click


@click.command()
@click.option("--input", "input_path", required=True, help="Input NIfTI file (any resolution/contrast)")
@click.option("--output", "output_path", required=True, help="Output segmentation NIfTI file")
@click.option("--volumes", default=None, help="Output CSV with structure volumes (optional)")
@click.option("--gpu/--no-gpu", default=True, help="Use GPU acceleration (default: yes)")
@click.option("--robust", is_flag=True, default=True, help="Use robust mode (handles unusual contrasts)")
@click.option("--parc", is_flag=True, default=True, help="Include cortical parcellation")
def main(input_path: str, output_path: str, volumes: str, gpu: bool, robust: bool, parc: bool):
    """Run SynthSeg on a brain MRI volume.

    SynthSeg is a contrast-agnostic segmentation model. It produces a label map
    using the FreeSurfer aseg convention. CSF-related labels include:
    4/43 (lateral ventricles), 14 (3rd ventricle), 15 (4th ventricle),
    24 (extraventricular CSF), 31/63 (choroid plexus).
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"Running SynthSeg on: {input_path}")
    print(f"  Output: {output_path}")
    print(f"  GPU: {gpu}, Robust: {robust}, Parcellation: {parc}")

    try:
        from SynthSeg.predict import predict as synthseg_predict
    except ImportError:
        # Try the pip-installed version
        try:
            from synthseg import predict as synthseg_predict
        except ImportError:
            print("\nSynthSeg not found. Install it:")
            print("  Option A: pip install synthseg")
            print("  Option B: git clone https://github.com/BBillot/SynthSeg.git && pip install -e SynthSeg/")
            print("\nAlternatively, if FreeSurfer >= 7.3 is installed:")
            print("  mri_synthseg --i input.nii.gz --o seg.nii.gz --parc --robust")
            raise SystemExit(1)

    # Run SynthSeg prediction
    synthseg_predict(
        path_images=input_path,
        path_segmentations=output_path,
        path_volumes=volumes,
        robust=robust,
        parc=parc,
    )

    print(f"\nSegmentation complete: {output_path}")
    if volumes:
        print(f"Volumes CSV: {volumes}")


if __name__ == "__main__":
    main()
