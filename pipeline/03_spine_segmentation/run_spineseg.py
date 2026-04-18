#!/usr/bin/env python3
"""Run TotalSpineSeg on a T2w spinal MRI volume.

TotalSpineSeg is an nnUNetv2-based two-step pipeline: step 1 produces
soft segmentations for cord and canal; step 2 produces a full multi-
label segmentation (vertebrae + discs + cord + canal). For Phase 3
(spinal SAS extraction) both are useful — cord and canal masks feed the
SAS computation directly; the vertebral labels are retained for
downstream registration work in Phase 5.

Accepts local paths or ``s3://`` URIs for --input and --output-dir;
downloads / uploads via boto3 so AWS Batch can pass S3 URIs straight
from the Step Functions state machine.

Output directory layout (mirrors TotalSpineSeg's own):

    <output-dir>/
    ├── input/              # preprocessed input
    ├── step1_raw/          # raw model 1 outputs
    ├── step1_cord/         # soft cord segmentation
    ├── step1_canal/        # soft canal segmentation
    ├── step1_output/       # step 1 labels
    ├── step2_raw/          # raw model 2 outputs
    └── step2_output/       # final multi-label segmentation
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

import click


def _is_s3(uri: str) -> bool:
    return uri.startswith("s3://")


def _parse_s3(uri: str) -> Tuple[str, str]:
    p = urlparse(uri)
    return p.netloc, p.path.lstrip("/")


def _download_from_s3(uri: str, local_path: Path) -> None:
    import boto3

    bucket, key = _parse_s3(uri)
    boto3.client("s3").download_file(bucket, key, str(local_path))


def _upload_dir_to_s3(local_dir: Path, s3_prefix: str) -> None:
    import boto3

    bucket, key_prefix = _parse_s3(s3_prefix)
    key_prefix = key_prefix.rstrip("/")
    client = boto3.client("s3")
    uploaded = 0
    for f in local_dir.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(local_dir).as_posix()
        key = f"{key_prefix}/{rel}" if key_prefix else rel
        client.upload_file(str(f), bucket, key)
        uploaded += 1
    print(f"  Uploaded {uploaded} files to s3://{bucket}/{key_prefix}/")


@click.command()
@click.option("--input", "input_path", required=True,
              help="Input T2w NIfTI file (local path or s3://)")
@click.option("--output-dir", "output_dir", required=True,
              help="Output directory (local path or s3:// prefix)")
@click.option("--step1-only", is_flag=True, default=False,
              help="Run only step 1 (cord + canal soft segs, no vertebral labels)")
@click.option("--iso", is_flag=True, default=False,
              help="Resample to isotropic 1 mm before inference")
def main(input_path: str, output_dir: str, step1_only: bool, iso: bool) -> None:
    """Run ``totalspineseg`` on a spinal MRI volume."""
    print(f"Running TotalSpineSeg on: {input_path}")
    print(f"  Output dir: {output_dir}")
    print(f"  Step1-only: {step1_only}, Iso: {iso}")

    binary = shutil.which("totalspineseg")
    if binary is None:
        raise click.ClickException(
            "totalspineseg not on PATH. The container should be built from "
            "docker/spine.Dockerfile."
        )

    with tempfile.TemporaryDirectory(prefix="spineseg_") as td:
        tmp = Path(td)
        tmp_in_dir = tmp / "in"
        tmp_out = tmp / "out"
        tmp_in_dir.mkdir()
        tmp_out.mkdir()

        # TotalSpineSeg operates on a directory of inputs, not a single file.
        # Copy / download the one subject's T2w into a staged input folder.
        local_in = tmp_in_dir / "input.nii.gz"
        if _is_s3(input_path):
            print(f"  Fetching {input_path} -> {local_in}")
            _download_from_s3(input_path, local_in)
        else:
            shutil.copy2(input_path, local_in)

        cmd = [binary, str(tmp_in_dir), str(tmp_out)]
        if step1_only:
            cmd.append("--step1")
        if iso:
            cmd.append("--iso")

        print(f"  Invoking: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        # Resolve --output-dir
        if _is_s3(output_dir):
            print(f"  Uploading outputs -> {output_dir}")
            _upload_dir_to_s3(tmp_out, output_dir)
        else:
            dst = Path(output_dir)
            dst.mkdir(parents=True, exist_ok=True)
            for f in tmp_out.rglob("*"):
                if not f.is_file():
                    continue
                rel = f.relative_to(tmp_out)
                (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst / rel)

    print(f"\nSpine segmentation complete. Outputs in: {output_dir}")


if __name__ == "__main__":
    main()
