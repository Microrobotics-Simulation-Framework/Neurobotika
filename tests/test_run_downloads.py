"""Tests for pipeline/01_data_acquisition/run_downloads.sh.

The dispatcher is a shell script, so the tests shell out with subprocess
and assert on stdout/stderr/exit code. To test dispatch without running
real aws/git-annex commands, we copy the dispatcher into a temp dir
alongside stub replacements of each download_*.sh that simply echo
their received arguments.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


DISPATCHER_SRC = (
    Path(__file__).parent.parent
    / "pipeline"
    / "01_data_acquisition"
    / "run_downloads.sh"
)

STUB = """#!/usr/bin/env bash
echo "SCRIPT=$(basename "$0")"
for arg in "$@"; do
    echo "ARG=$arg"
done
"""


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """Copy the dispatcher into a sandbox with stub child scripts."""
    sbx = tmp_path / "01_data_acquisition"
    sbx.mkdir()

    (sbx / "run_downloads.sh").write_text(DISPATCHER_SRC.read_text())
    (sbx / "run_downloads.sh").chmod(0o755)

    for name in (
        "download_mgh_100um.sh",
        "download_spine_generic.sh",
        "download_lumbosacral.sh",
    ):
        stub_path = sbx / name
        stub_path.write_text(STUB)
        stub_path.chmod(0o755)

    return sbx


def _run(sbx: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(sbx / "run_downloads.sh"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestArgParsing:
    def test_help_exits_zero(self, sandbox):
        result = _run(sandbox, "--help")
        assert result.returncode == 0
        assert "Usage" in result.stdout

    def test_missing_dataset_fails(self, sandbox):
        result = _run(sandbox, "--s3-dest", "s3://bucket/p")
        assert result.returncode != 0
        assert "required" in result.stderr.lower()

    def test_missing_s3_dest_fails(self, sandbox):
        result = _run(sandbox, "--dataset", "mgh")
        assert result.returncode != 0
        assert "required" in result.stderr.lower()

    def test_unknown_option_fails(self, sandbox):
        result = _run(
            sandbox,
            "--dataset", "mgh",
            "--s3-dest", "s3://b/p",
            "--bogus", "value",
        )
        assert result.returncode != 0

    def test_unknown_dataset_fails(self, sandbox):
        result = _run(
            sandbox,
            "--dataset", "invalid",
            "--s3-dest", "s3://b/p",
        )
        assert result.returncode != 0
        assert "unknown" in result.stderr.lower()


class TestDispatch:
    def test_mgh_dispatches_to_mgh_script(self, sandbox):
        result = _run(
            sandbox,
            "--dataset", "mgh",
            "--subject", "sub-EXC004",
            "--s3-dest", "s3://bucket/raw/mgh",
        )
        assert result.returncode == 0
        assert "SCRIPT=download_mgh_100um.sh" in result.stdout
        assert "ARG=--subject" in result.stdout
        assert "ARG=sub-EXC004" in result.stdout
        assert "ARG=--s3-dest" in result.stdout
        assert "ARG=s3://bucket/raw/mgh" in result.stdout

    def test_spine_dispatches_to_spine_script(self, sandbox):
        result = _run(
            sandbox,
            "--dataset", "spine",
            "--subject", "sub-douglas",
            "--s3-dest", "s3://bucket/raw/spine",
        )
        assert result.returncode == 0
        assert "SCRIPT=download_spine_generic.sh" in result.stdout
        assert "ARG=sub-douglas" in result.stdout

    def test_lumbosacral_dispatches_to_lumbosacral_script(self, sandbox):
        result = _run(
            sandbox,
            "--dataset", "lumbosacral",
            "--s3-dest", "s3://bucket/raw/lumbosacral",
        )
        assert result.returncode == 0
        assert "SCRIPT=download_lumbosacral.sh" in result.stdout
        assert "ARG=--s3-dest" in result.stdout
        assert "ARG=s3://bucket/raw/lumbosacral" in result.stdout

    def test_lumbosacral_does_not_forward_subject(self, sandbox):
        """The lumbosacral script has no --subject flag; dispatcher must not forward it."""
        result = _run(
            sandbox,
            "--dataset", "lumbosacral",
            "--subject", "ignored-value",
            "--s3-dest", "s3://bucket/raw/lumbosacral",
        )
        assert result.returncode == 0
        assert "ARG=--subject" not in result.stdout
        assert "ARG=ignored-value" not in result.stdout

    def test_subject_optional_uses_child_default(self, sandbox):
        """When --subject is omitted, dispatcher doesn't forward the flag so
        the child script falls back to its own default."""
        result = _run(
            sandbox,
            "--dataset", "mgh",
            "--s3-dest", "s3://bucket/raw/mgh",
        )
        assert result.returncode == 0
        assert "ARG=--subject" not in result.stdout


class TestChildScriptsExist:
    """Sanity: the real children the dispatcher would invoke in production
    are on disk and executable."""

    @pytest.mark.parametrize("script", [
        "download_mgh_100um.sh",
        "download_spine_generic.sh",
        "download_lumbosacral.sh",
    ])
    def test_child_script_exists_and_is_executable(self, script):
        path = DISPATCHER_SRC.parent / script
        assert path.exists(), f"{script} not found"
        assert path.stat().st_mode & 0o100, f"{script} not executable"

    def test_dispatcher_help_mentions_all_datasets(self):
        result = subprocess.run(
            ["bash", str(DISPATCHER_SRC), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "mgh" in result.stdout
        assert "spine" in result.stdout
        assert "lumbosacral" in result.stdout
