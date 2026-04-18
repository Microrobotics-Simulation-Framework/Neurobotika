#!/usr/bin/env python3
"""Run brain segmentation using FreeSurfer's ``mri_synthseg``.

Includes a downsample-to-1-mm preprocessing step: SynthSeg was trained
at 1 mm isotropic, and handing it a 200 um volume directly blows past
the 16 GB of RAM on the smaller GPU tiers (it loads the full volume
before its own internal resample). Bringing the input down to 1 mm
first keeps memory modest and matches the model's training regime.

Output is written as a directory so the on-disk layout doesn't change
when we eventually migrate to ``mri_super_synth`` (which emits a
directory of seg + synth T1w/T2w + MNI affine + QC). Today the
directory just contains ``seg.nii.gz`` (and optional ``volumes.csv``).

Accepts local paths or ``s3://`` URIs for --input and --output-dir;
downloads / uploads via boto3 so AWS Batch can pass S3 URIs straight
from the Step Functions state machine.
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
    """Upload every file under local_dir to s3_prefix/<relative path>."""
    import boto3

    bucket, key_prefix = _parse_s3(s3_prefix)
    key_prefix = key_prefix.rstrip("/")
    client = boto3.client("s3")
    for f in local_dir.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(local_dir).as_posix()
        key = f"{key_prefix}/{rel}" if key_prefix else rel
        print(f"    upload {rel} -> s3://{bucket}/{key}")
        client.upload_file(str(f), bucket, key)


def _downsample_to_1mm(src: Path, dst: Path) -> None:
    """Resample ``src`` to 1 mm isotropic into ``dst`` if it's higher-res.

    Uses scipy.ndimage.zoom with linear interpolation — good enough for
    SynthSeg, which is contrast- and resolution-agnostic anyway.
    """
    import nibabel as nib
    import numpy as np
    from scipy.ndimage import zoom

    img = nib.load(str(src))
    header = img.header
    voxel = np.asarray(header.get_zooms()[:3], dtype=np.float64)
    print(f"  Input voxel size: {voxel.tolist()} mm")

    target = np.array([1.0, 1.0, 1.0])
    if np.all(voxel >= 0.95):
        # Already ~1 mm; no need to resample.
        print("  Input already at ~1 mm; skipping downsample")
        shutil.copy2(str(src), str(dst))
        return

    zoom_factors = voxel / target  # e.g. 0.2 mm -> factor 0.2 (shrink)
    data = img.get_fdata(dtype=np.float32)
    print(f"  Downsampling: zoom factors {zoom_factors.tolist()}")
    resampled = zoom(data, zoom_factors, order=1, mode="nearest", prefilter=False)

    new_affine = img.affine.copy()
    new_affine[:3, :3] = img.affine[:3, :3] @ np.diag(1.0 / zoom_factors)

    out = nib.Nifti1Image(resampled.astype(np.float32), new_affine, header)
    out.header.set_zooms((*target, *header.get_zooms()[3:]))
    nib.save(out, str(dst))
    print(f"  Wrote {dst} ({resampled.shape}, {out.header.get_zooms()} mm)")


@click.command()
@click.option("--input", "input_path", required=True,
              help="Input NIfTI file (local path or s3://)")
@click.option("--output-dir", "output_dir", required=True,
              help="Output directory (local path or s3:// prefix)")
@click.option("--gpu/--no-gpu", default=True,
              help="Use GPU (when available)")
@click.option("--robust/--no-robust", default=True,
              help="SynthSeg robust mode (contrast-agnostic, handles ex-vivo / synthetic contrasts)")
@click.option("--parc/--no-parc", default=True,
              help="Include cortical parcellation")
def main(input_path: str, output_dir: str, gpu: bool, robust: bool, parc: bool) -> None:
    """Run ``mri_synthseg`` on a brain MRI volume.

    The input is first downsampled to 1 mm isotropic (SynthSeg's native
    resolution) to keep RAM in check. Output lands in ``output-dir`` as
    ``seg.nii.gz`` (+ ``volumes.csv`` if requested).
    """
    print(f"Running brain segmentation on: {input_path}")
    print(f"  Output dir: {output_dir}")
    print(f"  GPU: {gpu}, Robust: {robust}, Parcellation: {parc}")

    binary = shutil.which("mri_synthseg")
    if binary is None:
        raise click.ClickException(
            "mri_synthseg not on PATH. The container should be built from "
            "docker/brain.Dockerfile (FROM freesurfer/freesurfer:7.4.1)."
        )

    with tempfile.TemporaryDirectory(prefix="brainseg_") as td:
        tmp = Path(td)
        tmp_in = tmp / "input.nii.gz"
        tmp_resampled = tmp / "input_1mm.nii.gz"
        tmp_out = tmp / "output"
        tmp_out.mkdir()

        # Resolve --input
        if _is_s3(input_path):
            print(f"  Fetching {input_path}")
            _download_from_s3(input_path, tmp_in)
            raw_in = tmp_in
        else:
            raw_in = Path(input_path)

        # Downsample to 1 mm if needed.
        _downsample_to_1mm(raw_in, tmp_resampled)

        # Build + run mri_synthseg command.
        seg_out = tmp_out / "seg.nii.gz"
        volumes = tmp_out / "volumes.csv"
        cmd = [
            binary,
            "--i", str(tmp_resampled),
            "--o", str(seg_out),
            "--vol", str(volumes),
        ]
        if parc:
            cmd.append("--parc")
        if robust:
            cmd.append("--robust")
        if not gpu:
            cmd.append("--cpu")

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

    print(f"\nBrain segmentation complete. Outputs in: {output_dir}")


if __name__ == "__main__":
    main()
