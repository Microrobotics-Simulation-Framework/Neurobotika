"""Tests for pipeline/02_brain_segmentation/extract_csf_labels.py"""

import numpy as np
import pytest

from extract_csf_labels import (
    CSF_GROUPS,
    compute_volume_ml,
    extract_all_csf_masks,
    extract_label_mask,
)


class TestExtractLabelMask:
    def test_single_label(self):
        seg = np.array([0, 1, 2, 3, 1, 0], dtype=np.int32)
        mask = extract_label_mask(seg, [1])
        assert mask.dtype == np.uint8
        np.testing.assert_array_equal(mask, [0, 1, 0, 0, 1, 0])

    def test_multiple_labels(self):
        seg = np.array([0, 4, 5, 43, 44, 14], dtype=np.int32)
        mask = extract_label_mask(seg, [4, 5, 43, 44])
        np.testing.assert_array_equal(mask, [0, 1, 1, 1, 1, 0])

    def test_no_matching_labels(self):
        seg = np.array([0, 1, 2, 3], dtype=np.int32)
        mask = extract_label_mask(seg, [99])
        np.testing.assert_array_equal(mask, [0, 0, 0, 0])

    def test_all_matching(self):
        seg = np.array([5, 5, 5], dtype=np.int32)
        mask = extract_label_mask(seg, [5])
        np.testing.assert_array_equal(mask, [1, 1, 1])

    def test_3d_array(self, synthetic_brain_seg):
        mask = extract_label_mask(synthetic_brain_seg, [4, 43])
        assert mask.shape == synthetic_brain_seg.shape
        # Labels 4 and 43 should be present
        assert mask.sum() > 0
        # No voxels where original is 0 should be set
        assert mask[synthetic_brain_seg == 0].sum() == 0


class TestComputeVolumeMl:
    def test_1mm_isotropic(self):
        mask = np.ones((10, 10, 10), dtype=np.uint8)
        vol = compute_volume_ml(mask, (1.0, 1.0, 1.0))
        assert vol == pytest.approx(1.0)  # 1000 voxels * 1mm^3 / 1000 = 1 mL

    def test_2mm_isotropic(self):
        mask = np.ones((10, 10, 10), dtype=np.uint8)
        vol = compute_volume_ml(mask, (2.0, 2.0, 2.0))
        assert vol == pytest.approx(8.0)  # 1000 * 8 / 1000 = 8 mL

    def test_anisotropic(self):
        mask = np.ones((5, 5, 5), dtype=np.uint8)
        vol = compute_volume_ml(mask, (1.0, 1.0, 2.0))
        assert vol == pytest.approx(0.25)  # 125 * 2 / 1000 = 0.25 mL

    def test_empty_mask(self):
        mask = np.zeros((10, 10, 10), dtype=np.uint8)
        vol = compute_volume_ml(mask, (1.0, 1.0, 1.0))
        assert vol == 0.0

    def test_100um_voxels(self):
        mask = np.ones((100, 100, 100), dtype=np.uint8)
        vol = compute_volume_ml(mask, (0.1, 0.1, 0.1))
        assert vol == pytest.approx(1.0)  # 1e6 * 0.001 / 1000 = 1 mL


class TestExtractAllCsfMasks:
    def test_returns_all_groups_plus_combined(self, synthetic_brain_seg):
        masks = extract_all_csf_masks(synthetic_brain_seg)
        expected_keys = set(CSF_GROUPS.keys()) | {"all_csf_combined"}
        assert set(masks.keys()) == expected_keys

    def test_masks_are_binary(self, synthetic_brain_seg):
        masks = extract_all_csf_masks(synthetic_brain_seg)
        for name, mask in masks.items():
            assert mask.dtype == np.uint8
            unique_vals = set(np.unique(mask))
            assert unique_vals <= {0, 1}, f"{name} has non-binary values: {unique_vals}"

    def test_lateral_ventricles_mask(self, synthetic_brain_seg):
        masks = extract_all_csf_masks(synthetic_brain_seg)
        lv = masks["lateral_ventricles"]
        # Labels 4 and 43 are in the fixture
        assert lv[synthetic_brain_seg == 4].all()
        assert lv[synthetic_brain_seg == 43].all()
        # Label 14 should NOT be in lateral ventricles mask
        assert not lv[synthetic_brain_seg == 14].any()

    def test_combined_is_union(self, synthetic_brain_seg):
        masks = extract_all_csf_masks(synthetic_brain_seg)
        combined = masks["all_csf_combined"]
        manual_union = np.zeros_like(combined)
        for name, mask in masks.items():
            if name != "all_csf_combined":
                manual_union = np.maximum(manual_union, mask)
        np.testing.assert_array_equal(combined, manual_union)

    def test_no_overlap_between_groups(self, synthetic_brain_seg):
        masks = extract_all_csf_masks(synthetic_brain_seg)
        group_masks = [m for k, m in masks.items() if k != "all_csf_combined"]
        total = sum(m.astype(np.int32) for m in group_masks)
        assert total.max() <= 1, "Overlapping masks detected between CSF groups"

    def test_custom_groups(self):
        seg = np.array([0, 1, 2, 3], dtype=np.int32)
        custom = {"group_a": {"labels": [1, 2]}, "group_b": {"labels": [3]}}
        masks = extract_all_csf_masks(seg, csf_groups=custom)
        assert set(masks.keys()) == {"group_a", "group_b", "all_csf_combined"}
        np.testing.assert_array_equal(masks["group_a"], [0, 1, 1, 0])
        np.testing.assert_array_equal(masks["group_b"], [0, 0, 0, 1])


class TestCsfGroupsConfig:
    def test_all_labels_are_integers(self):
        for name, spec in CSF_GROUPS.items():
            assert all(isinstance(lbl, int) for lbl in spec["labels"]), (
                f"{name} has non-int labels"
            )

    def test_no_duplicate_labels_across_groups(self):
        all_labels = []
        for spec in CSF_GROUPS.values():
            all_labels.extend(spec["labels"])
        assert len(all_labels) == len(set(all_labels)), "Duplicate labels across CSF groups"

    def test_all_groups_have_description(self):
        for name, spec in CSF_GROUPS.items():
            assert "description" in spec, f"{name} missing description"
            assert len(spec["description"]) > 0
