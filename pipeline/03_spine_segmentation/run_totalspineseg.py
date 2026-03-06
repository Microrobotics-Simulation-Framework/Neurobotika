#!/usr/bin/env python3
"""Run TotalSpineSeg on spinal MRI to segment cord, canal, and vertebrae."""

from pathlib import Path

import click


@click.command()
@click.option("--input", "input_path", required=True, help="Input spinal MRI NIfTI file")
@click.option("--output-dir", required=True, help="Output directory for segmentation masks")
@click.option("--gpu/--no-gpu", default=True, help="Use GPU acceleration")
def main(input_path: str, output_dir: str, gpu: bool):
    """Run TotalSpineSeg for spinal cord and canal segmentation."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Running TotalSpineSeg on: {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  GPU: {gpu}")

    try:
        from totalspineseg import run_totalspineseg
    except ImportError:
        print("\nTotalSpineSeg not found. Install it:")
        print("  pip install totalspineseg nnunetv2")
        raise SystemExit(1)

    # Run TotalSpineSeg
    # The API may vary by version — adjust as needed
    run_totalspineseg(
        input_path=input_path,
        output_dir=str(out),
        use_gpu=gpu,
    )

    # TotalSpineSeg outputs multiple label maps
    # Rename/organize as needed for downstream pipeline
    print(f"\nSegmentation complete. Check {output_dir} for outputs.")
    print("Expected outputs: spinal_cord.nii.gz, spinal_canal.nii.gz, vertebrae.nii.gz")
    print("\nNext step: python compute_spinal_sas.py")


if __name__ == "__main__":
    main()
