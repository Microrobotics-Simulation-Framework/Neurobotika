"""Tests for pipeline/03_spine_segmentation/compute_spinal_sas.py"""

import numpy as np
import pytest

from compute_spinal_sas import compute_sas, compute_volume_ml


class TestComputeSas:
    def test_basic_subtraction(self):
        canal = np.array([1, 1, 1, 0], dtype=np.uint8)
        cord = np.array([0, 1, 0, 0], dtype=np.uint8)
        sas = compute_sas(canal, cord)
        np.testing.assert_array_equal(sas, [1, 0, 1, 0])

    def test_sas_dtype_is_uint8(self):
        canal = np.ones((5, 5, 5), dtype=np.uint8)
        cord = np.zeros((5, 5, 5), dtype=np.uint8)
        sas = compute_sas(canal, cord)
        assert sas.dtype == np.uint8

    def test_cord_outside_canal_ignored(self):
        """Cord voxels outside the canal should not create negative SAS."""
        canal = np.array([1, 0, 0], dtype=np.uint8)
        cord = np.array([0, 1, 0], dtype=np.uint8)
        sas = compute_sas(canal, cord)
        np.testing.assert_array_equal(sas, [1, 0, 0])

    def test_complete_overlap(self):
        """If cord == canal, SAS should be zero."""
        vol = np.ones((5, 5, 5), dtype=np.uint8)
        sas = compute_sas(vol, vol)
        assert sas.sum() == 0

    def test_no_cord(self):
        """If no cord, SAS == canal."""
        canal = np.ones((5, 5, 5), dtype=np.uint8)
        cord = np.zeros((5, 5, 5), dtype=np.uint8)
        sas = compute_sas(canal, cord)
        np.testing.assert_array_equal(sas, canal)

    def test_shape_mismatch_raises(self):
        canal = np.ones((5, 5, 5), dtype=np.uint8)
        cord = np.ones((5, 5, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_sas(canal, cord)

    def test_synthetic_cylinder(self, synthetic_canal_cord):
        canal, cord = synthetic_canal_cord
        sas = compute_sas(canal, cord)

        # SAS should be non-empty
        assert sas.sum() > 0
        # SAS should be a subset of canal
        assert ((sas > 0) & (canal == 0)).sum() == 0
        # SAS should not overlap with cord
        assert ((sas > 0) & (cord > 0)).sum() == 0
        # SAS + cord should equal canal
        np.testing.assert_array_equal((sas | cord), canal)

    def test_accepts_bool_input(self):
        canal = np.array([True, True, False])
        cord = np.array([False, True, False])
        sas = compute_sas(canal, cord)
        np.testing.assert_array_equal(sas, [1, 0, 0])

    def test_accepts_int_input(self):
        canal = np.array([3, 5, 0], dtype=np.int32)
        cord = np.array([0, 2, 0], dtype=np.int32)
        sas = compute_sas(canal, cord)
        # Any nonzero is treated as True
        np.testing.assert_array_equal(sas, [1, 0, 0])


class TestComputeVolumeMl:
    def test_basic(self):
        mask = np.ones((10, 10, 10), dtype=np.uint8)
        assert compute_volume_ml(mask, (1.0, 1.0, 1.0)) == pytest.approx(1.0)

    def test_empty(self):
        mask = np.zeros((10, 10, 10), dtype=np.uint8)
        assert compute_volume_ml(mask, (1.0, 1.0, 1.0)) == 0.0
