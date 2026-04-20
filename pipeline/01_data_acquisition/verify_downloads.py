#!/usr/bin/env python3
"""Verify downloaded MRI datasets.

Supports two modes:

* Local   — `--data-dir` points at a directory on disk (the original
            contract; kept for local development and existing tests).
* S3      — `--s3-prefix` points at an S3 prefix containing the three
            dataset sub-prefixes (mgh_100um/, spine_generic/,
            lumbosacral/). Used as the Phase1_Verify step after the
            three parallel download jobs land their payloads.

In either mode an optional `--manifest-out` writes a JSON manifest
(file list, sizes, NIfTI metadata, per-dataset totals) to a local
path or an s3:// URI.
"""

import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

EXPECTED_DATASETS = {
    "lusebrink_2021": {
        "description": "Lüsebrink 2021 in vivo 450 µm T2 SPACE (primary brain reference)",
        "glob": "*.nii.gz",
        "min_files": 1,
    },
    "spine_generic": {
        "description": "spine-generic single-subject (one site)",
        "glob": "*.nii.gz",
        "min_files": 1,
    },
    "lumbosacral": {
        "description": "SpineNerveModelGenerator (repo + optional MRI)",
        "glob": "*",
        "min_files": 0,  # MRI volumes arrive manually; repo clone only
    },
    "mgh_100um": {
        "description": "MGH ds002179 ex vivo brain (optional; ad-hoc cortical-ribbon reference)",
        "glob": "*.nii.gz",
        "min_files": 0,  # demoted 2026-04-20: ex-vivo SAS is fixation-collapsed
    },
}


@dataclass
class FileRecord:
    key: str
    size_bytes: int
    nifti: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class DatasetResult:
    name: str
    description: str
    file_count: int = 0
    total_bytes: int = 0
    files: list[FileRecord] = field(default_factory=list)
    ok: bool = True
    messages: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# NIfTI inspection                                                            #
# --------------------------------------------------------------------------- #

def check_nifti(filepath: Path) -> dict:
    """Check a NIfTI file for basic validity."""
    try:
        import nibabel as nib

        img = nib.load(str(filepath))
        header = img.header
        return {
            "valid": True,
            "shape": tuple(int(x) for x in img.shape),
            "voxel_size": tuple(float(x) for x in header.get_zooms()),
            "dtype": str(header.get_data_dtype()),
            "size_mb": filepath.stat().st_size / (1024 * 1024),
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


# --------------------------------------------------------------------------- #
# Local-directory mode                                                        #
# --------------------------------------------------------------------------- #

def verify_local(data_dir: Path, verbose: bool) -> tuple[bool, list[DatasetResult]]:
    all_ok = True
    results: list[DatasetResult] = []

    for name, spec in EXPECTED_DATASETS.items():
        dataset_dir = data_dir / name
        result = DatasetResult(name=name, description=spec["description"])
        print(f"\n{'='*60}")
        print(f"  {spec['description']} ({name})")
        print(f"  Path: {dataset_dir}")
        print(f"{'='*60}")

        if not dataset_dir.exists():
            if spec["min_files"] > 0:
                print("  [MISSING] Directory not found")
                result.ok = False
                result.messages.append("directory missing")
                all_ok = False
            else:
                print("  [SKIP] Optional dataset not downloaded")
                result.messages.append("optional, not downloaded")
            results.append(result)
            continue

        files = list(dataset_dir.rglob(spec["glob"]))
        files = [f for f in files if f.is_file()]
        result.file_count = len(files)
        print(f"  Found {result.file_count} file(s)")

        if result.file_count < spec["min_files"]:
            print(f"  [WARN] Expected at least {spec['min_files']} file(s)")
            result.ok = False
            result.messages.append(
                f"only {result.file_count} files, expected ≥ {spec['min_files']}"
            )
            all_ok = False

        for f in files:
            rec = FileRecord(
                key=str(f.relative_to(data_dir)),
                size_bytes=f.stat().st_size,
            )
            result.total_bytes += rec.size_bytes

            if f.suffix in (".gz", ".nii") or f.name.endswith(".nii.gz"):
                info = check_nifti(f)
                if info["valid"]:
                    rec.nifti = {
                        "shape": info["shape"],
                        "voxel_size": info["voxel_size"],
                        "dtype": info["dtype"],
                    }
                    status = "OK"
                    details = (
                        f"shape={info['shape']} voxel={info['voxel_size']} "
                        f"dtype={info['dtype']} size={info['size_mb']:.1f}MB"
                    )
                else:
                    rec.error = info["error"]
                    status = "FAIL"
                    details = info["error"]
                    result.ok = False
                    all_ok = False

                if verbose or status == "FAIL":
                    print(f"  [{status}] {f.name}: {details}")
                else:
                    print(f"  [{status}] {f.name} ({info.get('size_mb', 0):.1f} MB)")

            result.files.append(rec)

        results.append(result)

    return all_ok, results


# --------------------------------------------------------------------------- #
# S3 mode                                                                     #
# --------------------------------------------------------------------------- #

def _parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise click.ClickException(f"expected s3:// URI, got {uri!r}")
    body = uri[len("s3://"):]
    if "/" in body:
        bucket, key = body.split("/", 1)
    else:
        bucket, key = body, ""
    return bucket, key.rstrip("/")


def verify_s3(s3_prefix: str, verbose: bool) -> tuple[bool, list[DatasetResult]]:
    import boto3

    s3 = boto3.client("s3")
    bucket, key_prefix = _parse_s3_uri(s3_prefix)
    all_ok = True
    results: list[DatasetResult] = []

    with tempfile.TemporaryDirectory(prefix="neurobotika_verify_") as td:
        tmp_dir = Path(td)

        for name, spec in EXPECTED_DATASETS.items():
            dataset_key = f"{key_prefix}/{name}" if key_prefix else name
            result = DatasetResult(name=name, description=spec["description"])
            print(f"\n{'='*60}")
            print(f"  {spec['description']} ({name})")
            print(f"  S3:   s3://{bucket}/{dataset_key}/")
            print(f"{'='*60}")

            paginator = s3.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket, Prefix=f"{dataset_key}/")
            objects: list[dict] = []
            for page in pages:
                objects.extend(page.get("Contents", []))

            result.file_count = len(objects)
            result.total_bytes = sum(o["Size"] for o in objects)
            print(f"  Found {result.file_count} object(s), {result.total_bytes / 1e9:.2f} GB")

            if result.file_count < spec["min_files"]:
                print(f"  [WARN] Expected at least {spec['min_files']} object(s)")
                result.ok = False
                result.messages.append(
                    f"only {result.file_count} objects, expected ≥ {spec['min_files']}"
                )
                all_ok = False

            for obj in objects:
                key = obj["Key"]
                rec = FileRecord(
                    key=f"s3://{bucket}/{key}",
                    size_bytes=obj["Size"],
                )

                # Only download + inspect NIfTI volumes — skip README, JSON, etc.
                if key.endswith(".nii.gz") or key.endswith(".nii"):
                    local_path = tmp_dir / Path(key).name
                    try:
                        s3.download_file(bucket, key, str(local_path))
                        info = check_nifti(local_path)
                        if info["valid"]:
                            rec.nifti = {
                                "shape": info["shape"],
                                "voxel_size": info["voxel_size"],
                                "dtype": info["dtype"],
                            }
                            status = "OK"
                            details = (
                                f"shape={info['shape']} voxel={info['voxel_size']} "
                                f"dtype={info['dtype']} size={info['size_mb']:.1f}MB"
                            )
                        else:
                            rec.error = info["error"]
                            status = "FAIL"
                            details = info["error"]
                            result.ok = False
                            all_ok = False
                    finally:
                        local_path.unlink(missing_ok=True)

                    basename = Path(key).name
                    if verbose or status == "FAIL":
                        print(f"  [{status}] {basename}: {details}")
                    else:
                        print(f"  [{status}] {basename} ({rec.size_bytes / 1e6:.1f} MB)")

                result.files.append(rec)

            results.append(result)

    return all_ok, results


# --------------------------------------------------------------------------- #
# Manifest output                                                             #
# --------------------------------------------------------------------------- #

def write_manifest(
    manifest_out: str,
    source_uri: str,
    results: list[DatasetResult],
    all_ok: bool,
) -> None:
    manifest = {
        "source": source_uri,
        "ok": all_ok,
        "datasets": [
            {
                "name": r.name,
                "description": r.description,
                "ok": r.ok,
                "file_count": r.file_count,
                "total_bytes": r.total_bytes,
                "messages": r.messages,
                "files": [
                    {
                        "key": f.key,
                        "size_bytes": f.size_bytes,
                        "nifti": f.nifti,
                        "error": f.error,
                    }
                    for f in r.files
                ],
            }
            for r in results
        ],
    }

    body = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    if manifest_out.startswith("s3://"):
        import boto3

        bucket, key = _parse_s3_uri(manifest_out)
        boto3.client("s3").put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        print(f"\nManifest written to {manifest_out}")
    else:
        Path(manifest_out).write_bytes(body)
        print(f"\nManifest written to {manifest_out}")


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #

@click.command()
@click.option("--data-dir", default=None,
              help="Local data directory (mutually exclusive with --s3-prefix)")
@click.option("--s3-prefix", default=None,
              help="S3 URI prefix (e.g. s3://bucket/runs/run-001/raw)")
@click.option("--manifest-out", default=None,
              help="Write a JSON manifest here (local path or s3:// URI)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed file info")
def main(data_dir: str | None,
         s3_prefix: str | None,
         manifest_out: str | None,
         verbose: bool) -> None:
    """Verify downloaded MRI datasets."""
    if bool(data_dir) == bool(s3_prefix):
        raise click.ClickException(
            "exactly one of --data-dir or --s3-prefix is required"
        )

    if data_dir:
        source_uri = str(Path(data_dir).resolve())
        all_ok, results = verify_local(Path(data_dir), verbose)
    else:
        source_uri = s3_prefix
        all_ok, results = verify_s3(s3_prefix, verbose)

    print(f"\n{'='*60}")
    if all_ok:
        print("  All checks passed.")
    else:
        print("  Some checks failed. Review output above.")

    if manifest_out:
        write_manifest(manifest_out, source_uri, results, all_ok)

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
