"""Tests for pipeline/02_brain_segmentation/resample_volume.py"""

import numpy as np
import pytest

from resample_volume import compute_zoom_factors, resample_array, update_affine


class TestComputeZoomFactors:
    def test_identity(self):
        """1mm voxels to 1mm target should give zoom factors of 1."""
        zf = compute_zoom_factors((1.0, 1.0, 1.0), 1.0)
        assert zf == [1.0, 1.0, 1.0]

    def test_downsample(self):
        """0.5mm voxels to 1mm target should give zoom factors of 0.5."""
        zf = compute_zoom_factors((0.5, 0.5, 0.5), 1.0)
        assert zf == [0.5, 0.5, 0.5]

    def test_upsample(self):
        """2mm voxels to 1mm target should give zoom factors of 2."""
        zf = compute_zoom_factors((2.0, 2.0, 2.0), 1.0)
        assert zf == [2.0, 2.0, 2.0]

    def test_anisotropic(self):
        """Anisotropic input should produce different zoom factors per axis."""
        zf = compute_zoom_factors((0.5, 1.0, 2.0), 1.0)
        assert zf == [0.5, 1.0, 2.0]

    def test_100um_to_1mm(self):
        """100um (0.1mm) voxels to 1mm: zoom factor 0.1 (downscale 10x)."""
        zf = compute_zoom_factors((0.1, 0.1, 0.1), 1.0)
        assert zf == pytest.approx([0.1, 0.1, 0.1])

    def test_custom_target(self):
        """1mm voxels to 0.5mm target: zoom factor 2."""
        zf = compute_zoom_factors((1.0, 1.0, 1.0), 0.5)
        assert zf == [2.0, 2.0, 2.0]

    def test_truncates_to_three(self):
        """Only the first 3 dimensions should be used."""
        zf = compute_zoom_factors((1.0, 2.0, 3.0, 4.0), 1.0)
        assert len(zf) == 3
        assert zf == [1.0, 2.0, 3.0]


class TestUpdateAffine:
    def test_identity_zoom(self):
        """Zoom factors of 1 should not change the affine."""
        affine = np.eye(4)
        result = update_affine(affine, [1.0, 1.0, 1.0])
        np.testing.assert_array_almost_equal(result, affine)

    def test_does_not_modify_input(self):
        affine = np.eye(4)
        original = affine.copy()
        update_affine(affine, [2.0, 2.0, 2.0])
        np.testing.assert_array_equal(affine, original)

    def test_scale_halves_columns(self):
        """Zoom factor 2 should halve the voxel direction vectors."""
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        result = update_affine(affine, [2.0, 2.0, 2.0])
        expected = np.diag([1.0, 1.0, 1.0, 1.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_anisotropic_zoom(self):
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        result = update_affine(affine, [2.0, 1.0, 0.5])
        # Column 0 should be halved (divided by 2)
        assert result[0, 0] == pytest.approx(0.5)
        # Column 1 unchanged (divided by 1)
        assert result[1, 1] == pytest.approx(1.0)
        # Column 2 doubled (divided by 0.5)
        assert result[2, 2] == pytest.approx(2.0)

    def test_preserves_translation(self):
        """The translation column (column 3) should be unchanged."""
        affine = np.eye(4)
        affine[:3, 3] = [10.0, 20.0, 30.0]
        result = update_affine(affine, [2.0, 2.0, 2.0])
        np.testing.assert_array_equal(result[:3, 3], [10.0, 20.0, 30.0])


class TestResampleArray:
    def test_identity_zoom(self):
        """Zoom factor 1 should produce same shape."""
        data = np.ones((10, 10, 10))
        result = resample_array(data, [1.0, 1.0, 1.0])
        assert result.shape == (10, 10, 10)

    def test_upsample_shape(self):
        """Zoom factor 2 should double each dimension."""
        data = np.ones((10, 10, 10))
        result = resample_array(data, [2.0, 2.0, 2.0])
        assert result.shape == (20, 20, 20)

    def test_downsample_shape(self):
        """Zoom factor 0.5 should halve each dimension."""
        data = np.ones((10, 10, 10))
        result = resample_array(data, [0.5, 0.5, 0.5])
        assert result.shape == (5, 5, 5)

    def test_anisotropic(self):
        data = np.ones((10, 20, 30))
        result = resample_array(data, [2.0, 0.5, 1.0])
        assert result.shape == (20, 10, 30)

    def test_preserves_constant_value(self):
        """A constant volume should remain constant after resampling."""
        data = np.full((10, 10, 10), 42.0)
        result = resample_array(data, [2.0, 2.0, 2.0], order=1)
        np.testing.assert_array_almost_equal(result, 42.0)

    def test_nearest_neighbor_order_0(self):
        """Order 0 is nearest-neighbor interpolation (for label maps)."""
        data = np.zeros((4, 4, 4))
        data[0:2, 0:2, 0:2] = 1
        result = resample_array(data, [2.0, 2.0, 2.0], order=0)
        assert result.shape == (8, 8, 8)
        # The 1-region should scale up
        assert result[0, 0, 0] == 1.0
        assert result[3, 3, 3] == 1.0
        # Outside the original region
        assert result[7, 7, 7] == 0.0
