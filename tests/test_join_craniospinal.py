"""Tests for pipeline/05_registration/join_craniospinal.py"""

import numpy as np
import pytest

from join_craniospinal import check_connectivity, merge_brain_spine


class TestMergeBrainSpine:
    def test_brain_priority(self):
        """Brain labels should take priority over spine labels."""
        brain = np.array([1, 0, 0, 2], dtype=np.int32)
        spine = np.array([0, 3, 0, 4], dtype=np.int32)
        merged, stats = merge_brain_spine(brain, spine)
        # Brain voxels kept as-is
        assert merged[0] == 1
        assert merged[3] == 2
        # Spine fills gaps
        assert merged[1] == 3
        # Background stays background
        assert merged[2] == 0

    def test_overlap_keeps_brain(self):
        """Where both have labels, brain should win."""
        brain = np.array([5, 5, 0], dtype=np.int32)
        spine = np.array([9, 9, 9], dtype=np.int32)
        merged, stats = merge_brain_spine(brain, spine)
        np.testing.assert_array_equal(merged, [5, 5, 9])

    def test_stats_correct(self):
        brain = np.array([1, 0, 0, 2], dtype=np.int32)
        spine = np.array([0, 3, 0, 4], dtype=np.int32)
        merged, stats = merge_brain_spine(brain, spine)
        assert stats["brain_voxels"] == 2
        assert stats["spine_voxels"] == 1  # Only voxel 1 fills a gap
        assert stats["overlap_voxels"] == 1  # Voxel 3 overlaps
        assert stats["total_voxels"] == 3

    def test_no_overlap(self):
        brain = np.array([1, 0, 0], dtype=np.int32)
        spine = np.array([0, 0, 2], dtype=np.int32)
        merged, stats = merge_brain_spine(brain, spine)
        np.testing.assert_array_equal(merged, [1, 0, 2])
        assert stats["overlap_voxels"] == 0

    def test_both_empty(self):
        brain = np.zeros((5, 5, 5), dtype=np.int32)
        spine = np.zeros((5, 5, 5), dtype=np.int32)
        merged, stats = merge_brain_spine(brain, spine)
        assert stats["total_voxels"] == 0
        assert merged.sum() == 0

    def test_shape_mismatch_raises(self):
        brain = np.zeros((5, 5, 5), dtype=np.int32)
        spine = np.zeros((5, 5, 3), dtype=np.int32)
        with pytest.raises(ValueError, match="Shape mismatch"):
            merge_brain_spine(brain, spine)

    def test_3d_merge(self):
        brain = np.zeros((10, 10, 10), dtype=np.int32)
        spine = np.zeros((10, 10, 10), dtype=np.int32)
        brain[0:5, :, :] = 1  # Upper half is brain
        spine[5:10, :, :] = 2  # Lower half is spine
        merged, stats = merge_brain_spine(brain, spine)
        assert merged[0, 0, 0] == 1
        assert merged[9, 0, 0] == 2
        assert stats["overlap_voxels"] == 0
        assert stats["total_voxels"] == 1000

    def test_does_not_modify_input(self):
        brain = np.array([1, 0], dtype=np.int32)
        spine = np.array([0, 2], dtype=np.int32)
        brain_copy = brain.copy()
        spine_copy = spine.copy()
        merge_brain_spine(brain, spine)
        np.testing.assert_array_equal(brain, brain_copy)
        np.testing.assert_array_equal(spine, spine_copy)


class TestCheckConnectivity:
    def test_single_component(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        data[3:7, 3:7, 3:7] = 1
        assert check_connectivity(data) == 1

    def test_two_components(self):
        data = np.zeros((20, 20, 20), dtype=np.int32)
        data[0:3, 0:3, 0:3] = 1
        data[17:20, 17:20, 17:20] = 2
        assert check_connectivity(data) == 2

    def test_empty_volume(self):
        data = np.zeros((5, 5, 5), dtype=np.int32)
        assert check_connectivity(data) == 0
