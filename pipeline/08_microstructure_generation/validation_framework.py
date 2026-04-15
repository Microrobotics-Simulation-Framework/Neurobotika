#!/usr/bin/env python3
"""
validation_framework.py

Three-tier validation framework for the microstructure generation pipeline.
Implements the calibration/validation/test paradigm described in
docs/microstructure-generation.md §5.6.

Tier structure (ML train/validation/test analogy):

    Calibration tier  — Used DURING parameter selection (the "loss function")
        κ_eff (V1), A-P flow ratio (V3), VF (V4), thickness/separation PDFs (V6a/b)

    Validation tier   — Computed POST-HOC, NOT used in selection
        κ anisotropy (V2), pressure drop (V5), mass transfer (V7),
        stagnation fraction (V10c), dispersion proxy (V11)

    Independent test  — Full-domain Brinkman simulation vs. clinical MRI
        Peak cervical velocity, waveform NRMSE, phase lag vs. 4D PC-MRI

Paper thesis support (§5.7):
    The framework explicitly separates permeability-based calibration from
    dispersion-based validation to test whether hydraulically equivalent
    microstructures produce different transport characteristics.

References:
    - Yiallourou et al. 2012: 4D PC-MRI cervical velocity waveforms
    - Gupta et al. 2010: Permeability target range
    - Rossinelli et al. 2023/2024: Morphometric and DNS targets
    - Stockman 2007: Dispersion enhancement baseline (5–10×)

Note: This is a stub for the future implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Validation Tier Definitions
# ──────────────────────────────────────────────────────────────────────────────


class ValidationTier(Enum):
    """The three validation tiers."""

    CALIBRATION = "calibration"
    VALIDATION = "validation"
    INDEPENDENT_TEST = "independent_test"


# ──────────────────────────────────────────────────────────────────────────────
# Metric Criteria
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class MetricCriterion:
    """Acceptance criterion for a single validation metric."""

    metric_id: str  # e.g., "V1", "V3", "V6a"
    name: str
    tier: ValidationTier
    # Target range [low, high] — sample passes if metric falls within
    target_range: Optional[tuple[float, float]] = None
    # Maximum acceptable value (e.g., Wasserstein distance)
    max_value: Optional[float] = None
    # Minimum acceptable value
    min_value: Optional[float] = None
    # Weight in composite objective (calibration tier only)
    weight: float = 1.0
    # Description
    description: str = ""


# Default calibration criteria from docs/microstructure-generation.md §5.4
DEFAULT_CALIBRATION_CRITERIA = [
    MetricCriterion(
        metric_id="V1",
        name="Permeability (dominant eigenvalue)",
        tier=ValidationTier.CALIBRATION,
        target_range=(1e-9, 1e-7),
        weight=1.0,
        description="κ_eff from full tensor extraction; target 10⁻⁹ to 10⁻⁷ m²",
    ),
    MetricCriterion(
        metric_id="V3",
        name="Anterior-posterior flow ratio",
        tier=ValidationTier.CALIBRATION,
        target_range=(1.5, 3.0),
        weight=1.0,
        description="Peak ventral / peak dorsal velocity; from 4D PC-MRI",
    ),
    MetricCriterion(
        metric_id="V4",
        name="Realized volume fraction",
        tier=ValidationTier.CALIBRATION,
        max_value=0.10,  # ±10% relative deviation
        weight=0.5,
        description="Relative deviation from VF_target; acceptable ±10%",
    ),
    MetricCriterion(
        metric_id="V6a",
        name="Trabecular thickness PDF match",
        tier=ValidationTier.CALIBRATION,
        max_value=20.0,  # Wasserstein distance in μm
        weight=1.0,
        description="Wasserstein distance to Rossinelli 2023 thickness PDF",
    ),
    MetricCriterion(
        metric_id="V6b",
        name="Trabecular separation PDF match",
        tier=ValidationTier.CALIBRATION,
        max_value=50.0,  # Wasserstein distance in μm
        weight=0.8,
        description="Wasserstein distance to Rossinelli 2023 separation PDF",
    ),
]

# Default validation criteria (post-hoc, not used in selection)
DEFAULT_VALIDATION_CRITERIA = [
    MetricCriterion(
        metric_id="V2",
        name="Permeability anisotropy ratio",
        tier=ValidationTier.VALIDATION,
        target_range=(1.5, 5.0),
        description="κ_axial / κ_transverse from tensor eigenvalues",
    ),
    MetricCriterion(
        metric_id="V5",
        name="Pressure drop per unit length",
        tier=ValidationTier.VALIDATION,
        target_range=(0.1, 1.0),  # Pa/mm
        description="0.37–0.67 Pa/mm for 0.5 mm/s flow (Rossinelli 2024 DNS)",
    ),
    MetricCriterion(
        metric_id="V7",
        name="Mass transfer amplification",
        tier=ValidationTier.VALIDATION,
        target_range=(5.0, 17.0),
        description="Wall strain rate amplification vs. empty annulus (Rossinelli 2024)",
    ),
    MetricCriterion(
        metric_id="V10c",
        name="Stagnation zone fraction",
        tier=ValidationTier.VALIDATION,
        max_value=0.30,  # No more than 30% stagnant
        description="Fraction of fluid voxels with |u| < 0.01 × ⟨|u|⟩",
    ),
    MetricCriterion(
        metric_id="V11",
        name="Dispersion proxy (Taylor-Aris)",
        tier=ValidationTier.VALIDATION,
        # No target range — used for ranking and thesis figure, not filtering
        description="Velocity-variance-based D_eff estimate; key thesis metric",
    ),
]

# Default independent test criteria (Level 2 Brinkman simulation)
DEFAULT_TEST_CRITERIA = [
    MetricCriterion(
        metric_id="T1",
        name="Peak cervical velocity",
        tier=ValidationTier.INDEPENDENT_TEST,
        target_range=(2.0, 5.0),  # cm/s
        description="From Yiallourou et al. 2012 4D PC-MRI",
    ),
    MetricCriterion(
        metric_id="T2",
        name="Velocity waveform NRMSE",
        tier=ValidationTier.INDEPENDENT_TEST,
        max_value=0.20,
        description="Normalized RMSE vs. published clinical velocity waveforms",
    ),
    MetricCriterion(
        metric_id="T3",
        name="Phase lag per vertebral segment",
        tier=ValidationTier.INDEPENDENT_TEST,
        target_range=(40.0, 60.0),  # ms
        description="Phase lag between craniocaudal levels; clinical target 40–60 ms",
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Validation Results
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class TierResult:
    """Result of evaluating a sample against one validation tier."""

    tier: ValidationTier
    # Per-criterion results: metric_id → (value, pass/fail, criterion)
    results: dict[str, tuple[float, bool, MetricCriterion]] = field(
        default_factory=dict
    )
    # Overall tier pass (all criteria satisfied)
    tier_pass: bool = False
    # Composite score (calibration tier only)
    composite_score: Optional[float] = None


@dataclass
class ValidationResult:
    """Complete validation result for one LHS sample across all tiers."""

    sample_id: int = 0
    calibration: Optional[TierResult] = None
    validation: Optional[TierResult] = None
    independent_test: Optional[TierResult] = None


# ──────────────────────────────────────────────────────────────────────────────
# Validation Framework
# ──────────────────────────────────────────────────────────────────────────────


class ValidationFramework:
    """Three-tier validation framework for the LHS parameter sweep.

    Implements the calibration/validation/test paradigm from §5.6:

    1. **Calibration**: Evaluate all LHS samples against calibration criteria.
       Samples that pass all criteria form the candidate set.

    2. **Validation**: For the candidate set, compute validation-tier metrics
       (which were NOT used for selection). Rank candidates by composite
       validation score. Dispersion proxy (V11) is the key ranking metric
       for the paper thesis.

    3. **Independent test**: For the top-N candidates, run Level 2 Brinkman
       simulation on the full cervical domain and compare against 4D PC-MRI
       clinical data. This is completely decoupled from calibration.

    Args:
        calibration_criteria: Override default calibration criteria.
        validation_criteria: Override default validation criteria.
        test_criteria: Override default independent test criteria.
    """

    def __init__(
        self,
        calibration_criteria: Optional[list[MetricCriterion]] = None,
        validation_criteria: Optional[list[MetricCriterion]] = None,
        test_criteria: Optional[list[MetricCriterion]] = None,
    ):
        self.calibration_criteria = (
            calibration_criteria or DEFAULT_CALIBRATION_CRITERIA
        )
        self.validation_criteria = (
            validation_criteria or DEFAULT_VALIDATION_CRITERIA
        )
        self.test_criteria = test_criteria or DEFAULT_TEST_CRITERIA

    def evaluate_criterion(
        self,
        criterion: MetricCriterion,
        value: float,
    ) -> bool:
        """Check whether a metric value satisfies its criterion.

        Args:
            criterion: The criterion to check against.
            value: The measured metric value.

        Returns:
            True if the value satisfies the criterion.
        """
        if criterion.target_range is not None:
            low, high = criterion.target_range
            if not (low <= value <= high):
                return False
        if criterion.max_value is not None and value > criterion.max_value:
            return False
        if criterion.min_value is not None and value < criterion.min_value:
            return False
        return True

    def evaluate_calibration(
        self,
        sample_id: int,
        metrics: dict[str, float],
    ) -> TierResult:
        """Evaluate a sample against calibration-tier criteria.

        Args:
            sample_id: Sample identifier.
            metrics: Dict mapping metric IDs to measured values.

        Returns:
            TierResult with per-criterion pass/fail and composite score.
        """
        results = {}
        weighted_sum = 0.0
        total_weight = 0.0
        all_pass = True

        for criterion in self.calibration_criteria:
            value = metrics.get(criterion.metric_id)
            if value is None:
                results[criterion.metric_id] = (float("nan"), False, criterion)
                all_pass = False
                continue

            passed = self.evaluate_criterion(criterion, value)
            results[criterion.metric_id] = (value, passed, criterion)

            if not passed:
                all_pass = False

            # Composite score: lower is better (distance from target center)
            if criterion.target_range is not None:
                center = (criterion.target_range[0] + criterion.target_range[1]) / 2
                span = criterion.target_range[1] - criterion.target_range[0]
                normalized_dist = abs(value - center) / (span / 2) if span > 0 else 0
                weighted_sum += criterion.weight * normalized_dist
            elif criterion.max_value is not None:
                weighted_sum += criterion.weight * (value / criterion.max_value)

            total_weight += criterion.weight

        composite = weighted_sum / total_weight if total_weight > 0 else float("inf")

        return TierResult(
            tier=ValidationTier.CALIBRATION,
            results=results,
            tier_pass=all_pass,
            composite_score=composite,
        )

    def evaluate_validation(
        self,
        sample_id: int,
        metrics: dict[str, float],
    ) -> TierResult:
        """Evaluate a sample against validation-tier criteria (post-hoc).

        This should only be called for samples that passed calibration.

        Args:
            sample_id: Sample identifier.
            metrics: Dict mapping metric IDs to measured values.

        Returns:
            TierResult with validation metrics — used for ranking, not filtering.
        """
        results = {}
        all_pass = True

        for criterion in self.validation_criteria:
            value = metrics.get(criterion.metric_id)
            if value is None:
                results[criterion.metric_id] = (float("nan"), False, criterion)
                continue

            passed = self.evaluate_criterion(criterion, value)
            results[criterion.metric_id] = (value, passed, criterion)

            if not passed:
                all_pass = False

        return TierResult(
            tier=ValidationTier.VALIDATION,
            results=results,
            tier_pass=all_pass,
        )

    def evaluate_independent_test(
        self,
        sample_id: int,
        metrics: dict[str, float],
    ) -> TierResult:
        """Evaluate against independent test tier (Level 2 Brinkman vs. MRI).

        This should only be called for top-ranked validation-passing samples.

        Args:
            sample_id: Sample identifier.
            metrics: Dict mapping test metric IDs (T1, T2, T3) to values.

        Returns:
            TierResult with clinical-comparison metrics.
        """
        results = {}
        all_pass = True

        for criterion in self.test_criteria:
            value = metrics.get(criterion.metric_id)
            if value is None:
                results[criterion.metric_id] = (float("nan"), False, criterion)
                continue

            passed = self.evaluate_criterion(criterion, value)
            results[criterion.metric_id] = (value, passed, criterion)

            if not passed:
                all_pass = False

        return TierResult(
            tier=ValidationTier.INDEPENDENT_TEST,
            results=results,
            tier_pass=all_pass,
        )

    def run_full_validation(
        self,
        sample_id: int,
        all_metrics: dict[str, float],
    ) -> ValidationResult:
        """Run all three validation tiers for a single sample.

        Note: Independent test metrics require a separate Level 2 simulation
        and may not be available during the initial sweep. Pass
        test metrics separately if available.

        Args:
            sample_id: Sample identifier.
            all_metrics: Dict with all metric IDs (V1–V11, T1–T3).

        Returns:
            ValidationResult with all tier results.
        """
        cal = self.evaluate_calibration(sample_id, all_metrics)
        val = self.evaluate_validation(sample_id, all_metrics) if cal.tier_pass else None
        test = None  # Only run after Level 2 simulation

        # Check for test-tier metrics
        test_metrics = {k: v for k, v in all_metrics.items() if k.startswith("T")}
        if test_metrics and cal.tier_pass:
            test = self.evaluate_independent_test(sample_id, test_metrics)

        return ValidationResult(
            sample_id=sample_id,
            calibration=cal,
            validation=val,
            independent_test=test,
        )

    def summarize_sweep(
        self,
        results: list[ValidationResult],
    ) -> dict[str, Any]:
        """Summarize validation results across the full LHS sweep.

        Args:
            results: List of ValidationResult from all samples.

        Returns:
            Summary dict with:
                'n_total': total samples
                'n_calibration_pass': samples passing calibration
                'n_validation_pass': samples passing validation
                'n_test_pass': samples passing independent test
                'best_calibration_score': best composite score
                'dispersion_range': (min, max) V11 among passing samples
        """
        n_cal = sum(1 for r in results if r.calibration and r.calibration.tier_pass)
        n_val = sum(1 for r in results if r.validation and r.validation.tier_pass)
        n_test = sum(1 for r in results if r.independent_test and r.independent_test.tier_pass)

        cal_scores = [
            r.calibration.composite_score
            for r in results
            if r.calibration and r.calibration.composite_score is not None
        ]

        return {
            "n_total": len(results),
            "n_calibration_pass": n_cal,
            "n_validation_pass": n_val,
            "n_test_pass": n_test,
            "best_calibration_score": min(cal_scores) if cal_scores else None,
            "calibration_pass_rate": n_cal / len(results) if results else 0,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Cross-Validation (§7.3)
# ──────────────────────────────────────────────────────────────────────────────


def cross_validate_solver(
    binary_volume: np.ndarray,
    maddening_kappa_ij: np.ndarray,
    reference_kappa_ij: np.ndarray,
    tolerance_pct: float = 2.0,
) -> dict:
    """Cross-validate MIME κ_ij against a reference solver (e.g., Palabos).

    Per §7.3: for 3–5 representative RVE configurations, run the same
    geometry in both MIME and Palabos (BSD-licensed, has Bouzidi IBB).
    Permeability tensors should agree within 1–2%. Report discrepancies >5%
    as failures requiring investigation.

    Args:
        binary_volume: The binary RVE geometry that was simulated.
        maddening_kappa_ij: 3×3 tensor from MIME.
        reference_kappa_ij: 3×3 tensor from reference solver.
        tolerance_pct: Acceptable relative difference (%).

    Returns:
        Dict with:
            'max_relative_error_pct': float
            'mean_relative_error_pct': float
            'pass': bool (within tolerance)
            'component_errors': 3×3 array of relative errors
    """
    # TODO: Implement element-wise relative error comparison
    raise NotImplementedError("Cross-validation not yet implemented")


# ──────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    framework = ValidationFramework()

    print("Validation framework stub — see docs/microstructure-generation.md §5.6.")
    print(f"  Calibration criteria:  {len(framework.calibration_criteria)}")
    print(f"  Validation criteria:   {len(framework.validation_criteria)}")
    print(f"  Independent test:      {len(framework.test_criteria)}")
    print()
    print("Tier structure:")
    for tier_name, criteria in [
        ("Calibration", framework.calibration_criteria),
        ("Validation", framework.validation_criteria),
        ("Independent test", framework.test_criteria),
    ]:
        print(f"  {tier_name}:")
        for c in criteria:
            print(f"    {c.metric_id}: {c.name}")
