#!/usr/bin/env python3
"""Verify downloaded MRI datasets: check file existence, NIfTI validity, and basic metadata."""

import sys
from pathlib import Path

import click


EXPECTED_DATASETS = {
    "mgh_100um": {
        "description": "MGH 100um Ex Vivo Brain",
        "glob": "*.nii.gz",
        "min_files": 1,
    },
    "spine_generic": {
        "description": "Spine Generic Single-Subject",
        "glob": "*.nii.gz",
        "min_files": 1,
    },
    "lumbosacral": {
        "description": "Lumbosacral MRI",
        "glob": "*.nii.gz",
        "min_files": 0,  # Optional dataset
    },
}


def check_nifti(filepath: Path) -> dict:
    """Check a NIfTI file for basic validity."""
    try:
        import nibabel as nib

        img = nib.load(str(filepath))
        header = img.header
        return {
            "valid": True,
            "shape": img.shape,
            "voxel_size": tuple(header.get_zooms()),
            "dtype": str(header.get_data_dtype()),
            "size_mb": filepath.stat().st_size / (1024 * 1024),
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


@click.command()
@click.option("--data-dir", default="data/raw", help="Base data directory")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed file info")
def main(data_dir: str, verbose: bool):
    """Verify downloaded MRI datasets."""
    base = Path(data_dir)
    all_ok = True

    for name, spec in EXPECTED_DATASETS.items():
        dataset_dir = base / name
        print(f"\n{'='*60}")
        print(f"  {spec['description']} ({name})")
        print(f"  Path: {dataset_dir}")
        print(f"{'='*60}")

        if not dataset_dir.exists():
            if spec["min_files"] > 0:
                print(f"  [MISSING] Directory not found")
                all_ok = False
            else:
                print(f"  [SKIP] Optional dataset not downloaded")
            continue

        nifti_files = list(dataset_dir.rglob(spec["glob"]))
        print(f"  Found {len(nifti_files)} NIfTI file(s)")

        if len(nifti_files) < spec["min_files"]:
            print(f"  [WARN] Expected at least {spec['min_files']} file(s)")
            all_ok = False

        for f in nifti_files:
            info = check_nifti(f)
            if info["valid"]:
                status = "OK"
                details = (
                    f"shape={info['shape']} "
                    f"voxel={info['voxel_size']} "
                    f"dtype={info['dtype']} "
                    f"size={info['size_mb']:.1f}MB"
                )
            else:
                status = "FAIL"
                details = info["error"]
                all_ok = False

            if verbose or status == "FAIL":
                print(f"  [{status}] {f.name}: {details}")
            else:
                print(f"  [{status}] {f.name} ({info['size_mb']:.1f} MB)")

    print(f"\n{'='*60}")
    if all_ok:
        print("  All checks passed.")
    else:
        print("  Some checks failed. Review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
