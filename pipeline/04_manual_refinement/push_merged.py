#!/usr/bin/env python3
"""Upload a refined manual CSF label map to S3 and resume the Step
Functions execution waiting on the Phase 4 task token.

Runs *outside* Slicer (regular Python on your laptop). Slicer exports
its segmentation to a NIfTI; this script takes that NIfTI, validates
it, uploads it to the canonical S3 location for the run, and calls
``stepfunctions send-task-success`` so Phase 5 starts.

Usage::

    python push_merged.py \\
        --run-id run-2026-04-18-125403 \\
        --input ~/neurobotika-slicer/merged_labels.nii.gz \\
        --task-token "$NEUROBOTIKA_TASK_TOKEN"

The task token is emailed to you (to the SNS-subscribed address) when
Phase 4 starts. Copy-paste the value into ``NEUROBOTIKA_TASK_TOKEN``.

--task-token is optional: if omitted, the label map is uploaded but
the state machine is NOT resumed. Useful for iterative uploads where
you want to review in S3 before committing.
"""

import subprocess
import sys
from pathlib import Path

import click


@click.command()
@click.option("--run-id", required=True,
              help="Pipeline run id (same as the value passed to start-execution).")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True),
              help="Local path to the merged manual label map NIfTI.")
@click.option("--task-token", default=None,
              help="Step Functions task token from the Phase 4 notification email.")
@click.option("--bucket", default="neurobotika-data",
              help="Target S3 bucket (default: neurobotika-data).")
@click.option("--skip-validation", is_flag=True, default=False,
              help="Don't run validate_labels.py before upload.")
@click.option("--region", default="eu-central-1",
              help="AWS region.")
@click.option("--profile", default="neurobotika",
              help="AWS CLI profile.")
def main(run_id, input_path, task_token, bucket, skip_validation, region, profile):
    input_path = Path(input_path).resolve()
    s3_dest = f"s3://{bucket}/runs/{run_id}/seg/merged.nii.gz"

    print(f"Run id:    {run_id}")
    print(f"Local:     {input_path}")
    print(f"S3 target: {s3_dest}")
    print("")

    # --- Optional validation pass ---
    if not skip_validation:
        validator = Path(__file__).parent / "validate_labels.py"
        if validator.exists():
            print("Running validate_labels.py...")
            try:
                subprocess.run(
                    [sys.executable, str(validator),
                     "--input", str(input_path),
                     "--check-connectivity",
                     "--check-overlaps"],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"  Validation reported issues (exit {e.returncode}).")
                if not click.confirm("Proceed with upload anyway?"):
                    raise click.Abort()
        else:
            print(f"  (validator not found at {validator}; skipping)")

    # --- Upload ---
    print(f"\nUploading to {s3_dest} ...")
    subprocess.run(
        ["aws", "s3", "cp", str(input_path), s3_dest,
         "--profile", profile, "--region", region],
        check=True,
    )
    print(f"  Uploaded.")

    # --- Resume Step Functions if we have a task token ---
    if not task_token:
        print("\nNo --task-token provided — state machine NOT resumed.")
        print("If you want to resume now:")
        print(f"  aws stepfunctions send-task-success --profile {profile} --region {region} \\")
        print(f"      --task-token \"$NEUROBOTIKA_TASK_TOKEN\" \\")
        print(f"      --task-output '{{}}'")
        return

    print("\nResuming Step Functions execution...")
    subprocess.run(
        ["aws", "stepfunctions", "send-task-success",
         "--profile", profile, "--region", region,
         "--task-token", task_token,
         "--task-output", "{}"],
        check=True,
    )
    print("  Done. Phase 5 will pick up from here.")


if __name__ == "__main__":
    main()
