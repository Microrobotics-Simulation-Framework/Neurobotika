#!/usr/bin/env python3
"""Convert CSF segmentation data into nnU-Net dataset format."""

import json
import shutil
from pathlib import Path

import click


LABEL_MAP = {
    "background": 0,
    "lateral_ventricle_left": 1,
    "lateral_ventricle_right": 2,
    "third_ventricle": 3,
    "aqueduct": 4,
    "fourth_ventricle": 5,
    "foramen_monro_left": 6,
    "foramen_monro_right": 7,
    "foramen_magendie": 8,
    "foramen_luschka_left": 9,
    "foramen_luschka_right": 10,
    "cisterna_magna": 11,
    "prepontine_cistern": 12,
    "ambient_cistern": 13,
    "quadrigeminal_cistern": 14,
    "interpeduncular_cistern": 15,
    "sylvian_cistern": 16,
    "cerebral_sas": 17,
    "spinal_sas": 18,
    "foramen_magnum_junction": 19,
    "choroid_plexus": 20,
}


@click.command()
@click.option("--images-dir", required=True, help="Directory with input MRI volumes")
@click.option("--labels-dir", required=True, help="Directory with label maps")
@click.option("--output-dir", required=True, help="Output nnU-Net dataset directory")
@click.option("--dataset-name", default="Dataset001_CSF", help="nnU-Net dataset name")
def main(images_dir: str, labels_dir: str, output_dir: str, dataset_name: str):
    """Prepare an nnU-Net dataset from CSF segmentation data."""
    images_path = Path(images_dir)
    labels_path = Path(labels_dir)
    out = Path(output_dir)

    images_tr = out / "imagesTr"
    labels_tr = out / "labelsTr"
    images_tr.mkdir(parents=True, exist_ok=True)
    labels_tr.mkdir(parents=True, exist_ok=True)

    # Find matching image-label pairs
    label_files = sorted(labels_path.glob("*.nii.gz"))
    print(f"Found {len(label_files)} label files")

    case_ids = []
    for i, label_file in enumerate(label_files):
        case_id = f"case_{i:04d}"
        case_ids.append(case_id)

        # Copy label
        dst_label = labels_tr / f"{case_id}.nii.gz"
        shutil.copy2(label_file, dst_label)

        # Find matching image (assumes same stem or index-based matching)
        image_candidates = list(images_path.rglob(f"*{label_file.stem.replace('_labels', '')}*.nii.gz"))
        if image_candidates:
            dst_image = images_tr / f"{case_id}_0000.nii.gz"
            shutil.copy2(image_candidates[0], dst_image)
            print(f"  {case_id}: {image_candidates[0].name} + {label_file.name}")
        else:
            print(f"  {case_id}: [WARN] No matching image for {label_file.name}")

    # Create dataset.json
    dataset_json = {
        "channel_names": {"0": "MRI"},
        "labels": LABEL_MAP,
        "numTraining": len(case_ids),
        "file_ending": ".nii.gz",
        "name": dataset_name,
        "description": "CSF system segmentation including ventricles, foramina, cisterns, and SAS",
        "reference": "Neurobotika project",
        "licence": "See project LICENSE",
    }

    json_path = out / "dataset.json"
    with open(json_path, "w") as f:
        json.dump(dataset_json, f, indent=2)
    print(f"\nDataset JSON: {json_path}")

    print(f"\nnnU-Net dataset ready: {out}")
    print(f"Training cases: {len(case_ids)}")
    print(f"\nNext: set environment variables and run training:")
    print(f"  export nnUNet_raw={out.parent}")
    print(f"  export nnUNet_preprocessed={out.parent / 'nnUNet_preprocessed'}")
    print(f"  export nnUNet_results={out.parent / 'nnUNet_results'}")
    print(f"  nnUNetv2_plan_and_preprocess -d 1")
    print(f"  nnUNetv2_train 1 3d_fullres 0")


if __name__ == "__main__":
    main()
