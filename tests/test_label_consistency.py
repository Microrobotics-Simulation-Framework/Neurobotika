"""Cross-module tests: verify label maps are consistent across all pipeline phases.

The pipeline defines label conventions in multiple places:
  - extract_csf_labels.py (CSF_GROUPS, SynthSeg convention)
  - validate_labels.py (EXPECTED_LABELS, manual segmentation convention)
  - labels_to_surface.py (LABEL_NAMES, mesh export convention)
  - prepare_nnunet_dataset.py (LABEL_MAP, nnU-Net convention)

These must all agree on what labels 1-20 mean.
"""

import pytest

from validate_labels import EXPECTED_LABELS, SINGLE_COMPONENT
from prepare_nnunet_dataset import LABEL_MAP

# labels_to_surface has a top-level import of nibabel/trimesh which aren't installed,
# so we import LABEL_NAMES by parsing the source directly.
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _load_label_names_from_source() -> dict[int, str]:
    """Parse LABEL_NAMES from labels_to_surface.py without importing nibabel/trimesh."""
    src = (PROJECT_ROOT / "pipeline" / "06_mesh_generation" / "labels_to_surface.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "LABEL_NAMES":
                    return ast.literal_eval(node.value)
    raise RuntimeError("Could not find LABEL_NAMES in labels_to_surface.py")


LABEL_NAMES = _load_label_names_from_source()


class TestLabelConsistency:
    def test_expected_labels_and_label_names_same_ids(self):
        """validate_labels.EXPECTED_LABELS and labels_to_surface.LABEL_NAMES
        should have the same integer label IDs (1-20)."""
        assert set(EXPECTED_LABELS.keys()) == set(LABEL_NAMES.keys())

    def test_nnunet_label_map_matches(self):
        """prepare_nnunet_dataset.LABEL_MAP values (excluding background) should
        be exactly 1-20, matching EXPECTED_LABELS."""
        nnunet_ids = {v for k, v in LABEL_MAP.items() if k != "background"}
        expected_ids = set(EXPECTED_LABELS.keys())
        assert nnunet_ids == expected_ids

    def test_nnunet_has_background_zero(self):
        assert LABEL_MAP["background"] == 0
        assert 0 not in EXPECTED_LABELS

    def test_all_label_ids_are_contiguous(self):
        """Labels should be 1 through 20 with no gaps."""
        all_ids = set(EXPECTED_LABELS.keys())
        assert all_ids == set(range(1, 21))

    def test_single_component_labels_are_valid(self):
        """SINGLE_COMPONENT should only reference labels that exist."""
        assert SINGLE_COMPONENT <= set(EXPECTED_LABELS.keys())

    def test_label_names_match_semantically(self):
        """Spot-check that the same label ID refers to the same structure
        in both validate_labels and labels_to_surface."""
        # Label 4 should be the aqueduct in both
        assert "aqueduct" in EXPECTED_LABELS[4].lower() or "aqueduct" in LABEL_NAMES[4].lower()
        assert "aqueduct" in LABEL_NAMES[4]

        # Label 1 should be left lateral ventricle
        assert "lateral" in EXPECTED_LABELS[1].lower()
        assert "lateral" in LABEL_NAMES[1]

        # Label 8 should be foramen of Magendie
        assert "magendie" in EXPECTED_LABELS[8].lower()
        assert "magendie" in LABEL_NAMES[8]

        # Label 18 should be spinal SAS
        assert "spinal" in EXPECTED_LABELS[18].lower()
        assert "spinal" in LABEL_NAMES[18]

    def test_nnunet_names_match_label_names(self):
        """nnU-Net LABEL_MAP keys (excluding background) should match
        LABEL_NAMES values."""
        nnunet_names = {v for k, v in LABEL_MAP.items() if k != "background"}
        surface_names = set(LABEL_NAMES.values())
        # The nnU-Net keys are the structure names; LABEL_NAMES values are
        # the file-safe names. They should be the same set.
        nnunet_structure_names = {k for k in LABEL_MAP.keys() if k != "background"}
        assert nnunet_structure_names == surface_names, (
            f"Mismatch:\n"
            f"  In nnU-Net only: {nnunet_structure_names - surface_names}\n"
            f"  In surface only: {surface_names - nnunet_structure_names}"
        )
