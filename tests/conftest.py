"""Shared fixtures for Neurobotika tests."""

import sys
from pathlib import Path

import numpy as np
import pytest

# Add pipeline directories to sys.path so scripts are importable
PROJECT_ROOT = Path(__file__).parent.parent
for phase_dir in sorted((PROJECT_ROOT / "pipeline").iterdir()):
    if phase_dir.is_dir():
        sys.path.insert(0, str(phase_dir))


@pytest.fixture
def rng():
    """Reproducible random number generator."""
    return np.random.default_rng(42)


@pytest.fixture
def synthetic_brain_seg(rng):
    """A small synthetic brain segmentation label map (32x32x32).

    Contains labels 4, 14, 15, 24, 31 (a subset of FreeSurfer aseg labels
    used by SynthSeg for CSF structures).
    """
    data = np.zeros((32, 32, 32), dtype=np.int32)
    # Lateral ventricles (labels 4, 43)
    data[10:20, 8:12, 12:20] = 4
    data[10:20, 20:24, 12:20] = 43
    # 3rd ventricle (label 14)
    data[12:18, 14:18, 14:18] = 14
    # 4th ventricle (label 15)
    data[6:10, 14:18, 14:18] = 15
    # Extra-ventricular CSF (label 24)
    data[0:3, :, :] = 24
    data[29:32, :, :] = 24
    # Choroid plexus (labels 31, 63)
    data[14:16, 10:12, 15:17] = 31
    data[14:16, 22:24, 15:17] = 63
    return data


@pytest.fixture
def synthetic_canal_cord():
    """Synthetic spinal canal and cord binary masks (20x20x40).

    Canal is a cylinder of radius 5, cord is a cylinder of radius 2,
    centered along the z-axis.
    """
    shape = (20, 20, 40)
    canal = np.zeros(shape, dtype=np.uint8)
    cord = np.zeros(shape, dtype=np.uint8)

    cy, cx = 10, 10
    for y in range(shape[0]):
        for x in range(shape[1]):
            dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
            if dist <= 5:
                canal[y, x, :] = 1
            if dist <= 2:
                cord[y, x, :] = 1

    return canal, cord


@pytest.fixture
def synthetic_label_map():
    """A synthetic CSF label map with all 20 expected labels (16x16x16).

    Each label gets a small cube of voxels. Voxel volume is 1mm^3.
    """
    data = np.zeros((16, 16, 16), dtype=np.int32)
    # Assign a 2x2x2 cube per label at different positions
    for label_id in range(1, 21):
        x = (label_id - 1) % 4 * 4
        y = ((label_id - 1) // 4) % 4 * 4
        z = ((label_id - 1) // 16) * 4
        data[y : y + 2, x : x + 2, z : z + 2] = label_id
    return data


@pytest.fixture
def voxel_1mm():
    """Voxel dimensions for a 1mm isotropic volume."""
    return (1.0, 1.0, 1.0)
