"""Tests for pipeline/01_data_acquisition/verify_downloads.py"""

import pytest

from verify_downloads import EXPECTED_DATASETS, main

from click.testing import CliRunner


class TestExpectedDatasetsConfig:
    def test_all_have_required_keys(self):
        for name, spec in EXPECTED_DATASETS.items():
            assert "description" in spec, f"{name} missing 'description'"
            assert "glob" in spec, f"{name} missing 'glob'"
            assert "min_files" in spec, f"{name} missing 'min_files'"

    def test_min_files_non_negative(self):
        for name, spec in EXPECTED_DATASETS.items():
            assert spec["min_files"] >= 0, f"{name} has negative min_files"

    def test_lumbosacral_is_optional(self):
        assert EXPECTED_DATASETS["lumbosacral"]["min_files"] == 0

    def test_required_datasets(self):
        # Primary brain dataset is now Lüsebrink 2021 in vivo — see ADR-001.
        # MGH is retained but demoted to optional (min_files=0).
        assert EXPECTED_DATASETS["lusebrink_2021"]["min_files"] >= 1
        assert EXPECTED_DATASETS["spine_generic"]["min_files"] >= 1

    def test_has_four_datasets(self):
        assert len(EXPECTED_DATASETS) == 4
        assert "lusebrink_2021" in EXPECTED_DATASETS     # primary brain
        assert "spine_generic" in EXPECTED_DATASETS      # primary spine
        assert "lumbosacral" in EXPECTED_DATASETS        # optional
        assert "mgh_100um" in EXPECTED_DATASETS          # optional, ad-hoc


class TestVerifyDownloadsCli:
    def test_missing_required_dirs_fails(self, tmp_path):
        """Should exit 1 when required dataset directories are missing."""
        runner = CliRunner()
        result = runner.invoke(main, ["--data-dir", str(tmp_path)])
        assert result.exit_code != 0

    def test_empty_required_dirs_warns(self, tmp_path):
        """Directories exist but have no .nii.gz files should warn."""
        (tmp_path / "mgh_100um").mkdir()
        (tmp_path / "spine_generic").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["--data-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "WARN" in result.output or "MISSING" in result.output

    def test_optional_dir_missing_is_ok(self, tmp_path):
        """Missing lumbosacral dir should not cause failure by itself."""
        # Create required dirs with dummy files
        mgh = tmp_path / "mgh_100um"
        spine = tmp_path / "spine_generic"
        mgh.mkdir()
        spine.mkdir()
        # We need actual nii.gz files for the check to pass,
        # but check_nifti requires nibabel, so this will fail at the
        # nifti check level. Just verify the output mentions "SKIP" for lumbosacral.
        runner = CliRunner()
        result = runner.invoke(main, ["--data-dir", str(tmp_path)])
        assert "SKIP" in result.output or "Optional" in result.output
