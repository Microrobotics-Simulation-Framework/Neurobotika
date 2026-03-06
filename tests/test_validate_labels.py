"""Tests for pipeline/04_manual_refinement/validate_labels.py"""

import numpy as np
import pytest

from validate_labels import (
    EXPECTED_LABELS,
    SINGLE_COMPONENT,
    get_label_stats,
    validate_label_map,
)


class TestValidateLabelMap:
    def test_all_labels_present_passes(self, synthetic_label_map):
        """A label map with all 20 expected labels should pass with no missing_labels error."""
        errors = validate_label_map(
            synthetic_label_map, voxel_vol_mm3=1.0, check_connectivity=False,
        )
        missing_errors = [e for e in errors if e.startswith("missing_labels")]
        assert len(missing_errors) == 0

    def test_missing_labels_detected(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        data[0:5, 0:5, 0:5] = 1  # Only label 1
        errors = validate_label_map(data, voxel_vol_mm3=1.0, check_connectivity=False)
        missing_errors = [e for e in errors if e.startswith("missing_labels")]
        assert len(missing_errors) == 1
        assert "2" in missing_errors[0]  # Label 2 is missing

    def test_unexpected_labels_detected(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        data[0:2, 0:2, 0:2] = 99  # Unexpected label
        errors = validate_label_map(data, voxel_vol_mm3=1.0, check_connectivity=False)
        unexpected_errors = [e for e in errors if e.startswith("unexpected_labels")]
        assert len(unexpected_errors) == 1
        assert "99" in unexpected_errors[0]

    def test_empty_volume_no_crash(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        errors = validate_label_map(data, voxel_vol_mm3=1.0, check_connectivity=False)
        # Should have missing_labels error (all labels missing)
        assert any(e.startswith("missing_labels") for e in errors)

    def test_disconnected_component_detected(self):
        data = np.zeros((20, 20, 20), dtype=np.int32)
        # Label 1 (in SINGLE_COMPONENT) split into two distant clusters
        data[0:3, 0:3, 0:3] = 1
        data[17:20, 17:20, 17:20] = 1
        errors = validate_label_map(
            data,
            voxel_vol_mm3=1.0,
            expected_labels={1: "test"},
            single_component_labels={1},
            check_connectivity=True,
        )
        disconnected = [e for e in errors if "disconnected" in e]
        assert len(disconnected) == 1
        assert "label_1_disconnected" in disconnected[0]

    def test_single_component_passes(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        # Label 1 as one connected blob
        data[3:7, 3:7, 3:7] = 1
        errors = validate_label_map(
            data,
            voxel_vol_mm3=1.0,
            expected_labels={1: "test"},
            single_component_labels={1},
            check_connectivity=True,
        )
        disconnected = [e for e in errors if "disconnected" in e]
        assert len(disconnected) == 0

    def test_unusual_volume_too_small(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        data[0, 0, 0] = 1  # Only 1 voxel = 0.001 mL
        errors = validate_label_map(
            data,
            voxel_vol_mm3=1.0,
            expected_labels={1: "test"},
            check_connectivity=False,
        )
        vol_errors = [e for e in errors if e.startswith("unusual_volume")]
        assert len(vol_errors) == 1

    def test_unusual_volume_too_large(self):
        data = np.ones((100, 100, 100), dtype=np.int32)  # 1e6 voxels = 1000 mL
        errors = validate_label_map(
            data,
            voxel_vol_mm3=1.0,
            expected_labels={1: "test"},
            check_connectivity=False,
        )
        vol_errors = [e for e in errors if e.startswith("unusual_volume")]
        assert len(vol_errors) == 1

    def test_normal_volume_passes(self):
        """~150 mL should not trigger a volume warning."""
        # 150 mL = 150,000 mm^3 = 150,000 voxels at 1mm^3
        # Use a 53x53x53 cube (~148,877 voxels)
        data = np.ones((53, 53, 53), dtype=np.int32)
        errors = validate_label_map(
            data,
            voxel_vol_mm3=1.0,
            expected_labels={1: "test"},
            check_connectivity=False,
        )
        vol_errors = [e for e in errors if e.startswith("unusual_volume")]
        assert len(vol_errors) == 0

    def test_connectivity_skipped_for_non_single_component_labels(self):
        """Labels NOT in single_component_labels should not be checked for connectivity."""
        data = np.zeros((20, 20, 20), dtype=np.int32)
        # Label 6 (foramen of Monro) is NOT in SINGLE_COMPONENT
        data[0:3, 0:3, 0:3] = 6
        data[17:20, 17:20, 17:20] = 6
        errors = validate_label_map(
            data,
            voxel_vol_mm3=1.0,
            expected_labels={6: "Left foramen of Monro"},
            single_component_labels=SINGLE_COMPONENT,
            check_connectivity=True,
        )
        disconnected = [e for e in errors if "disconnected" in e]
        assert len(disconnected) == 0  # 6 is not in SINGLE_COMPONENT


class TestGetLabelStats:
    def test_basic(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        data[0:5, 0:5, 0:5] = 1  # 125 voxels
        data[5:7, 5:7, 5:7] = 2  # 8 voxels
        stats = get_label_stats(data, voxel_vol_mm3=1.0)
        assert stats[1]["voxels"] == 125
        assert stats[1]["volume_ml"] == pytest.approx(0.125)
        assert stats[2]["voxels"] == 8
        assert stats[2]["volume_ml"] == pytest.approx(0.008)

    def test_ignores_background(self):
        data = np.zeros((10, 10, 10), dtype=np.int32)
        stats = get_label_stats(data, voxel_vol_mm3=1.0)
        assert 0 not in stats
        assert len(stats) == 0


class TestExpectedLabelsConfig:
    def test_labels_are_1_to_20(self):
        assert set(EXPECTED_LABELS.keys()) == set(range(1, 21))

    def test_single_component_is_subset(self):
        assert SINGLE_COMPONENT <= set(EXPECTED_LABELS.keys())

    def test_all_names_are_nonempty(self):
        for lbl, name in EXPECTED_LABELS.items():
            assert len(name) > 0, f"Label {lbl} has empty name"
