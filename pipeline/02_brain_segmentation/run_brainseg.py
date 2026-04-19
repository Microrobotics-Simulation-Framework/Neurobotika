#!/usr/bin/env python3
"""Run SuperSynth brain segmentation (``mri_super_synth`` via FreeSurfer 8.2).

SuperSynth is a multi-task U-Net that performs:
  - aseg-style segmentation (cortical + subcortical + extracerebral + limbic)
  - MNI affine registration
  - super-resolution (1 mm isotropic T1w / T2w / FLAIR synths)
  - QC (per-structure Dice)

The ``--mode exvivo`` regime matches MGH ds002179 (post-mortem 7 T)
natively, so no downsampling preprocessing is needed — SuperSynth
internally resamples inputs of any resolution.

Known upstream bug (FS 8.2): label 24 (extraventricular CSF) is not
written correctly to the volumes CSV. As a work-around this wrapper
*always* recomputes per-label volumes from ``seg.nii.gz`` itself after
SuperSynth runs, and writes a trusted ``volumes.csv`` that downstream
phases can use. SuperSynth's original CSV is preserved alongside as
``volumes_supersynth.csv`` for audit.

Accepts local paths or ``s3://`` URIs for --input and --output-dir.
"""

import csv
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import click


def _downsample_if_needed(src: Path, dst: Path, max_voxels: int = 100_000_000) -> Path:
    """If the NIfTI has more than `max_voxels` voxels (default 1e8, i.e.
    ~400 MB float32 in RAM), downsample to 1 mm isotropic so SuperSynth's
    container doesn't OOM just loading the input. SuperSynth does its
    own internal resample to 1 mm anyway, so this is purely a memory
    relief valve.

    Returns the path actually used (either `src` if small enough, or
    `dst` after resampling).
    """
    import nibabel as nib
    import numpy as np
    from scipy.ndimage import zoom

    img = nib.load(str(src))
    shape = img.shape[:3]
    total = int(np.prod(shape))
    voxel = np.asarray(img.header.get_zooms()[:3], dtype=np.float64)
    print(f"  Input shape: {shape}, voxel size: {voxel.tolist()} mm, {total:,} voxels")

    if total <= max_voxels:
        print("  Input small enough; skipping preprocess downsample")
        return src

    target = np.array([1.0, 1.0, 1.0])
    zoom_factors = voxel / target  # e.g. 0.2 -> 0.2 (shrink x5)
    data = img.get_fdata(dtype=np.float32)
    print(f"  Downsampling to 1 mm isotropic (zoom factors {zoom_factors.tolist()})")
    resampled = zoom(data, zoom_factors, order=1, mode="nearest", prefilter=False)

    new_affine = img.affine.copy()
    new_affine[:3, :3] = img.affine[:3, :3] @ np.diag(1.0 / zoom_factors)
    out = nib.Nifti1Image(resampled.astype(np.float32), new_affine, img.header)
    out.header.set_zooms((*target, *img.header.get_zooms()[3:]))
    nib.save(out, str(dst))
    print(f"  Wrote downsampled input: {dst} shape={resampled.shape}")
    return dst


# FreeSurfer aseg label names for the labels SuperSynth emits. Not
# exhaustive — just the CSF-relevant ones we care about plus a few
# anchor structures. Downstream code only reads rows by label int.
ASEG_LABEL_NAMES = {
    2:  "left_cerebral_white_matter",
    3:  "left_cerebral_cortex",
    4:  "left_lateral_ventricle",
    5:  "left_inferior_lateral_ventricle",
    14: "third_ventricle",
    15: "fourth_ventricle",
    24: "csf_extraventricular",
    31: "left_choroid_plexus",
    41: "right_cerebral_white_matter",
    42: "right_cerebral_cortex",
    43: "right_lateral_ventricle",
    44: "right_inferior_lateral_ventricle",
    63: "right_choroid_plexus",
}


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


def _find_seg(output_dir: Path) -> Path:
    """Locate SuperSynth's segmentation volume inside its output directory.

    FS 8.2's mri_super_synth emits ``segmentation.mgz``. Older/other
    SynthSeg-family tools use ``seg.nii.gz``. Check both.
    """
    candidates = [
        "segmentation.mgz", "segmentation.nii.gz",
        "seg.mgz", "seg.nii.gz",
        "aseg.mgz", "aseg.nii.gz",
    ]
    for name in candidates:
        p = output_dir / name
        if p.exists():
            return p
    for p in list(output_dir.glob("*.mgz")) + list(output_dir.glob("*.nii.gz")):
        stem = p.stem.lower().replace(".nii", "")
        if "seg" in stem and "synth" not in stem and "ribbon" not in stem:
            return p
    raise FileNotFoundError(
        f"Could not find segmentation volume under {output_dir}. "
        f"Contents: {sorted(p.name for p in output_dir.iterdir())}"
    )


def _find_supersynth_csv(output_dir: Path) -> Optional[Path]:
    """Locate SuperSynth's own volumes CSV if it wrote one."""
    for name in ("volumes.csv", "vols.csv", "qc.csv"):
        p = output_dir / name
        if p.exists():
            return p
    return None


def _recompute_volumes(seg_path: Path, output_csv: Path) -> None:
    """Recompute per-label volumes directly from the segmentation NIfTI.

    Works around the FS 8.2 label-24 CSV bug by taking the NIfTI as
    ground truth. Writes a CSV with columns: label, name, voxels,
    volume_mm3, volume_ml.
    """
    import nibabel as nib
    import numpy as np

    img = nib.load(str(seg_path))
    data = np.asarray(img.dataobj).astype(np.int32)
    voxel_zooms = img.header.get_zooms()[:3]
    voxel_mm3 = float(np.prod(voxel_zooms))

    labels, counts = np.unique(data[data > 0], return_counts=True)
    rows = []
    for label, count in zip(labels.tolist(), counts.tolist()):
        vol_mm3 = count * voxel_mm3
        rows.append({
            "label": int(label),
            "name": ASEG_LABEL_NAMES.get(int(label), f"label_{int(label)}"),
            "voxels": int(count),
            "volume_mm3": round(vol_mm3, 3),
            "volume_ml": round(vol_mm3 / 1000.0, 4),
        })

    rows.sort(key=lambda r: r["label"])

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "name", "voxels", "volume_mm3", "volume_ml"])
        writer.writeheader()
        writer.writerows(rows)

    csf24 = next((r for r in rows if r["label"] == 24), None)
    if csf24:
        print(f"  Label 24 (extraventricular CSF): {csf24['volume_ml']:.2f} mL "
              f"(recomputed from NIfTI — works around FS 8.2 CSV bug)")
    print(f"  Wrote trusted volumes CSV: {output_csv} ({len(rows)} labels)")


@click.command()
@click.option("--input", "input_path", required=True,
              help="Input NIfTI file (local path or s3://)")
@click.option("--output-dir", "output_dir", required=True,
              help="Output directory (local path or s3:// prefix)")
@click.option("--mode",
              type=click.Choice(["invivo", "exvivo", "cerebrum",
                                 "left-hemi", "right-hemi"]),
              default="exvivo",
              help="Scan regime (default: exvivo — matches MGH ds002179)")
@click.option("--device", type=click.Choice(["cuda", "cpu"]), default="cuda",
              help="Compute device")
@click.option("--sharpen-synths", is_flag=True, default=False,
              help="Sharpen SuperSynth's T1w/T2w/FLAIR synthetic maps")
@click.option("--threads", type=int, default=-1,
              help="CPU thread count (-1 = all cores)")
def main(input_path: str, output_dir: str, mode: str, device: str,
         sharpen_synths: bool, threads: int) -> None:
    """Run ``mri_super_synth`` on a brain MRI volume and land a trusted
    volumes CSV alongside the segmentation."""
    print(f"Running SuperSynth on: {input_path}")
    print(f"  Output dir: {output_dir}")
    print(f"  Mode: {mode}, Device: {device}, Sharpen: {sharpen_synths}")

    binary = shutil.which("mri_super_synth")
    if binary is None:
        raise click.ClickException(
            "mri_super_synth not on PATH. The container should be built from "
            "docker/brain.Dockerfile (FROM freesurfer/freesurfer:8.2.0)."
        )

    with tempfile.TemporaryDirectory(prefix="supersynth_") as td:
        tmp = Path(td)
        tmp_in = tmp / "input.nii.gz"
        tmp_out = tmp / "output"
        tmp_out.mkdir()

        if _is_s3(input_path):
            print(f"  Fetching {input_path} -> {tmp_in}")
            _download_from_s3(input_path, tmp_in)
            raw_in = tmp_in
        else:
            raw_in = Path(input_path)

        # SuperSynth loads the full volume into RAM before its own internal
        # resample. For high-res MGH inputs (200 μm ≈ 4-5 GB uncompressed)
        # that pushes past 15 GB container memory on g5.xlarge. Downsample
        # to 1 mm first if the input is big. SuperSynth normalises
        # resolution internally so accuracy is unchanged.
        local_in = _downsample_if_needed(raw_in, tmp / "input_1mm.nii.gz")

        cmd = [
            binary,
            "--i", str(local_in),
            "--o", str(tmp_out),
            "--mode", mode,
            "--device", device,
            "--threads", str(threads),
        ]
        if sharpen_synths:
            cmd.append("--sharpen_synths")

        print(f"  Invoking: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        # Post-processing: preserve SuperSynth's own CSV (if any) for audit,
        # then recompute a trusted volumes.csv from the segmentation NIfTI.
        seg = _find_seg(tmp_out)
        print(f"  Segmentation NIfTI found at: {seg.name}")

        supersynth_csv = _find_supersynth_csv(tmp_out)
        if supersynth_csv is not None:
            backup = tmp_out / "volumes_supersynth.csv"
            if supersynth_csv.name != "volumes_supersynth.csv":
                shutil.copy2(supersynth_csv, backup)
                print(f"  Preserved SuperSynth CSV as {backup.name}")

        _recompute_volumes(seg, tmp_out / "volumes.csv")

        # Upload / copy outputs
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

    print(f"\nSuperSynth complete. Outputs in: {output_dir}")


if __name__ == "__main__":
    main()
