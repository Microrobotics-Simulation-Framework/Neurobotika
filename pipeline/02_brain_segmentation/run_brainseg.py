#!/usr/bin/env python3
"""Run brain segmentation via FreeSurfer 8.2's SynthSeg or SuperSynth.

Two tools are available; ``--tool`` selects which:

- ``synthseg`` (default): ``mri_synthseg --parc --robust`` — aseg + cortical
  parcellation (108 labels). Produces label 24 (extraventricular CSF)
  correctly, which SuperSynth omits. This is the right choice for
  Neurobotika's CSF-mesh goal.
- ``supersynth``: ``mri_super_synth --mode exvivo`` — aseg + limbic +
  extracerebral structures plus MNI registration and 1 mm synthetic
  T1w / T2w / FLAIR volumes. Currently omits label 24 (confirmed on
  both MGH ex-vivo and Lüsebrink in-vivo data); kept as an option for
  future work where its extras outweigh that gap.

Input pre-processing:
- Inputs higher-resolution than 1 mm are downsampled to 1 mm isotropic
  before invocation — both tools are trained at 1 mm, and this keeps
  the container's RAM footprint reasonable on g5.xlarge (16 GB).

Output:
- ``<output-dir>/seg.nii.gz`` (SynthSeg) or ``segmentation.mgz``
  (SuperSynth) — the segmentation volume.
- ``<output-dir>/volumes.csv`` — trusted per-label volumes recomputed
  from the segmentation NIfTI directly (works around FS 8.2's label-24
  CSV bug when SuperSynth is used, and gives a consistent schema for
  both tools).
- SuperSynth additionally emits SynthT1/T2/FLAIR.mgz + MNI + QC; those
  are uploaded alongside when present.

Accepts local paths or ``s3://`` URIs for --input and --output-dir.
"""

import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import click


def _downsample_if_needed(src: Path, dst: Path, min_voxel_mm: float = 0.95) -> Path:
    """Downsample to 1 mm isotropic if any input voxel is < min_voxel_mm.

    Both SynthSeg and SuperSynth are trained at 1 mm. Passing higher-res
    inputs (e.g. Lüsebrink 450 µm or MGH 200 µm) burns RAM holding the
    full volume before internal resample, and for SynthSeg specifically
    the accuracy regresses when inputs depart from the training regime.
    Shrinking to 1 mm first is defensively correct for both tools.

    Returns the path actually used (either `src` if already ≥ 1 mm, or
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

    if np.all(voxel >= min_voxel_mm):
        print(f"  Input already ≥ {min_voxel_mm} mm per axis; skipping preprocess downsample")
        return src

    target = np.array([1.0, 1.0, 1.0])
    zoom_factors = voxel / target  # e.g. 0.45 -> 0.45 (shrink ~2.2x)
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
@click.option("--tool",
              type=click.Choice(["synthseg", "supersynth"]),
              default="synthseg",
              help="Segmentation tool. synthseg (default) produces label 24 "
                   "(extraventricular CSF); supersynth omits it but adds "
                   "limbic + extracerebral + MNI + synthetic T1/T2/FLAIR.")
@click.option("--mode",
              type=click.Choice(["invivo", "exvivo", "cerebrum",
                                 "left-hemi", "right-hemi"]),
              default="exvivo",
              help="SuperSynth scan regime (ignored for synthseg).")
@click.option("--device", type=click.Choice(["cuda", "cpu"]), default="cuda",
              help="Compute device.")
@click.option("--sharpen-synths", is_flag=True, default=False,
              help="SuperSynth: sharpen synthetic T1/T2/FLAIR maps (ignored for synthseg).")
@click.option("--parc/--no-parc", default=True,
              help="SynthSeg: include cortical parcellation (108 labels). Ignored for supersynth.")
@click.option("--robust/--no-robust", default=True,
              help="SynthSeg: robust mode (contrast-agnostic). Ignored for supersynth.")
@click.option("--threads", type=int, default=4,
              help="CPU thread count (must be ≥ 1; mri_synthseg's TF threadpool rejects -1).")
def main(input_path: str, output_dir: str, tool: str, mode: str,
         device: str, sharpen_synths: bool, parc: bool, robust: bool,
         threads: int) -> None:
    """Run SynthSeg or SuperSynth on a brain MRI volume and land a trusted
    volumes CSV alongside the segmentation."""
    print(f"Running {tool} on: {input_path}")
    print(f"  Output dir: {output_dir}")
    print(f"  Device: {device}, Threads: {threads}")

    if tool == "synthseg":
        binary = shutil.which("mri_synthseg")
        binary_name = "mri_synthseg"
    else:
        binary = shutil.which("mri_super_synth")
        binary_name = "mri_super_synth"

    if binary is None:
        raise click.ClickException(
            f"{binary_name} not on PATH. The container should be built from "
            "docker/brain.Dockerfile (FROM freesurfer/freesurfer:8.2.0)."
        )

    with tempfile.TemporaryDirectory(prefix=f"{tool}_") as td:
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

        # Both SynthSeg and SuperSynth load the full volume into RAM
        # before internal resampling. For high-res MGH / Lüsebrink inputs
        # that pushes past 15 GB container memory on g5.xlarge.
        # Downsample to 1 mm first when needed — both tools are trained
        # at 1 mm so accuracy is unchanged.
        local_in = _downsample_if_needed(raw_in, tmp / "input_1mm.nii.gz")

        if tool == "synthseg":
            # mri_synthseg writes a single seg file + optional volumes CSV.
            # Place them inside tmp_out so the directory upload contract works.
            #
            # SynthSeg always runs on CPU here. The brain image also ships a
            # CUDA-12.1 PyTorch (required by SuperSynth) which conflicts with
            # FreeSurfer's bundled TensorFlow — attempting GPU-mode SynthSeg
            # throws std::bad_alloc deep in TF. On a 1 mm downsampled input
            # (~6 M voxels) CPU inference finishes in 3–5 min on c6i/g5,
            # which is well inside the job timeout.
            seg_file = tmp_out / "seg.nii.gz"
            synthseg_vol = tmp_out / "volumes_synthseg.csv"
            cmd = [
                binary,
                "--i", str(local_in),
                "--o", str(seg_file),
                "--vol", str(synthseg_vol),
                "--threads", str(threads),
                "--cpu",
            ]
            if parc:
                cmd.append("--parc")
            if robust:
                cmd.append("--robust")
        else:
            # mri_super_synth writes an entire output directory.
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

        # Build subprocess env. For SynthSeg we force TensorFlow off any
        # GPU entirely: the brain image ships a CUDA PyTorch for
        # SuperSynth, and TF's initialisation probe + implicit memory
        # allocation on the same GPU throws std::bad_alloc. The --cpu
        # flag alone isn't enough — TF still initialises GPU support
        # during import. CUDA_VISIBLE_DEVICES="" hides all GPUs from TF.
        env = os.environ.copy()
        if tool == "synthseg":
            env["CUDA_VISIBLE_DEVICES"] = ""
            # Cap TF's thread-pool memory growth too.
            env["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"

        print(f"  Invoking: {' '.join(cmd)}")
        subprocess.run(cmd, env=env, check=True)

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
