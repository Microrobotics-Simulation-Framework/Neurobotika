"""Tests for pipeline/07_model_training/prepare_nnunet_dataset.py"""

import json

import pytest

from prepare_nnunet_dataset import LABEL_MAP, main

from click.testing import CliRunner


class TestLabelMap:
    def test_background_is_zero(self):
        assert LABEL_MAP["background"] == 0

    def test_has_21_entries(self):
        """20 structures + background."""
        assert len(LABEL_MAP) == 21

    def test_values_are_0_to_20(self):
        assert set(LABEL_MAP.values()) == set(range(0, 21))

    def test_no_duplicate_values(self):
        values = list(LABEL_MAP.values())
        assert len(values) == len(set(values))

    def test_no_duplicate_keys(self):
        keys = list(LABEL_MAP.keys())
        assert len(keys) == len(set(keys))

    def test_all_keys_are_snake_case(self):
        for key in LABEL_MAP:
            assert key == key.lower(), f"Key '{key}' is not lowercase"
            assert " " not in key, f"Key '{key}' contains spaces"


class TestPrepareNnunetCli:
    def test_creates_dataset_json(self, tmp_path):
        """CLI should create dataset.json with correct structure."""
        images_dir = tmp_path / "images"
        labels_dir = tmp_path / "labels"
        output_dir = tmp_path / "output"
        images_dir.mkdir()
        labels_dir.mkdir()

        # Create fake label files (just empty files with .nii.gz extension)
        (labels_dir / "sub01_labels.nii.gz").write_bytes(b"fake")
        (labels_dir / "sub02_labels.nii.gz").write_bytes(b"fake")

        runner = CliRunner()
        result = runner.invoke(main, [
            "--images-dir", str(images_dir),
            "--labels-dir", str(labels_dir),
            "--output-dir", str(output_dir),
            "--dataset-name", "Dataset999_Test",
        ])
        assert result.exit_code == 0

        # Check dataset.json
        json_path = output_dir / "dataset.json"
        assert json_path.exists()
        with open(json_path) as f:
            ds = json.load(f)

        assert ds["name"] == "Dataset999_Test"
        assert ds["numTraining"] == 2
        assert ds["file_ending"] == ".nii.gz"
        assert ds["channel_names"] == {"0": "MRI"}
        assert ds["labels"] == LABEL_MAP

    def test_creates_directory_structure(self, tmp_path):
        images_dir = tmp_path / "images"
        labels_dir = tmp_path / "labels"
        output_dir = tmp_path / "output"
        images_dir.mkdir()
        labels_dir.mkdir()

        (labels_dir / "sub01_labels.nii.gz").write_bytes(b"fake")

        runner = CliRunner()
        runner.invoke(main, [
            "--images-dir", str(images_dir),
            "--labels-dir", str(labels_dir),
            "--output-dir", str(output_dir),
        ])

        assert (output_dir / "imagesTr").is_dir()
        assert (output_dir / "labelsTr").is_dir()

    def test_copies_label_files(self, tmp_path):
        images_dir = tmp_path / "images"
        labels_dir = tmp_path / "labels"
        output_dir = tmp_path / "output"
        images_dir.mkdir()
        labels_dir.mkdir()

        content = b"test_nifti_content"
        (labels_dir / "brain_labels.nii.gz").write_bytes(content)

        runner = CliRunner()
        runner.invoke(main, [
            "--images-dir", str(images_dir),
            "--labels-dir", str(labels_dir),
            "--output-dir", str(output_dir),
        ])

        copied = output_dir / "labelsTr" / "case_0000.nii.gz"
        assert copied.exists()
        assert copied.read_bytes() == content

    def test_no_labels_produces_empty_dataset(self, tmp_path):
        images_dir = tmp_path / "images"
        labels_dir = tmp_path / "labels"
        output_dir = tmp_path / "output"
        images_dir.mkdir()
        labels_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, [
            "--images-dir", str(images_dir),
            "--labels-dir", str(labels_dir),
            "--output-dir", str(output_dir),
        ])
        assert result.exit_code == 0

        with open(output_dir / "dataset.json") as f:
            ds = json.load(f)
        assert ds["numTraining"] == 0
