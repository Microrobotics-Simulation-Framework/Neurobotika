"""Tests for pipeline/06_mesh_generation/export_unity.py"""

import pytest

from export_unity import compute_lod_ratios, compute_target_faces


class TestComputeLodRatios:
    def test_one_level(self):
        ratios = compute_lod_ratios(1)
        assert ratios == [1.0]

    def test_two_levels(self):
        ratios = compute_lod_ratios(2)
        assert ratios == [1.0, 0.5]

    def test_three_levels(self):
        ratios = compute_lod_ratios(3)
        assert ratios == [1.0, 0.5, 0.1]

    def test_four_levels(self):
        ratios = compute_lod_ratios(4)
        assert len(ratios) == 4
        assert ratios[0] == 1.0
        assert ratios[1] == 0.5
        assert ratios[2] == 0.1
        assert ratios[3] == pytest.approx(0.05)  # 0.1 / 2^(3-2)

    def test_five_levels(self):
        ratios = compute_lod_ratios(5)
        assert len(ratios) == 5
        assert ratios[4] == pytest.approx(0.025)  # 0.1 / 2^(4-2)

    def test_ratios_are_decreasing(self):
        for levels in range(1, 7):
            ratios = compute_lod_ratios(levels)
            for i in range(1, len(ratios)):
                assert ratios[i] < ratios[i - 1], (
                    f"Level {levels}: ratio[{i}]={ratios[i]} >= ratio[{i-1}]={ratios[i-1]}"
                )

    def test_all_ratios_positive(self):
        for levels in range(1, 10):
            ratios = compute_lod_ratios(levels)
            assert all(r > 0 for r in ratios)

    def test_first_ratio_always_one(self):
        for levels in range(1, 10):
            ratios = compute_lod_ratios(levels)
            assert ratios[0] == 1.0


class TestComputeTargetFaces:
    def test_full_resolution(self):
        assert compute_target_faces(100000, 1.0) == 100000

    def test_half(self):
        assert compute_target_faces(100000, 0.5) == 50000

    def test_tenth(self):
        assert compute_target_faces(100000, 0.1) == 10000

    def test_minimum_enforced(self):
        """Very small ratios should not go below the minimum."""
        assert compute_target_faces(100, 0.01) == 100  # 1 < 100, so min wins

    def test_custom_minimum(self):
        assert compute_target_faces(100, 0.01, minimum=50) == 50

    def test_zero_ratio(self):
        """Zero ratio should return the minimum."""
        assert compute_target_faces(100000, 0.0) == 100

    def test_large_mesh(self):
        assert compute_target_faces(5_000_000, 0.1) == 500_000
